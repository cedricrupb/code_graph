import code_tokenize as ctok

from .graph import CodeGraph

from .pylang   import pylang_analyses
from .javalang import javalang_analyses, java_preprocess


DEFAULT_ANALYSES = ["ast", "cfg", "dataflow"]


def codegraph(source_code, lang = "guess", analyses = None, **kwargs):
    """
    Transforms source code into an annotated AST.

    Given source code as string, this function quickly transforms
    the given code into an annotated AST. The AST is annotated with multiple 
    (configurable) relations like control flow and data flow.  
    The function uses tree-sitter as a backend. Therefore, this
    function can in theory support most programming languages (see README).
    However, since control flow and data flow have to be tailored to a specific
    language only Java and Python are supported at the moment.

    All transformations are based on the transformations used in 
    'Self-Supervised Bug Detection and Repair' (Allamanis et al., 2021).
    The original implementation for Python can be found here: 
    https://github.com/microsoft/neurips21-self-supervised-bug-detection-and-repair
    Note that interprocedural analysis (and relations) are currently not supported.


    Parameters
    ----------
    source_code : str
        Source code to parsed as a string. Also
        supports parsing of incomplete source code
        snippets (by deactivating the syntax checker; see syntax_error)
    
    lang : [python, java]
        String identifier of the programming language
        to be parsed. Supported are most programming languages
        including python, java and javascript (see README)
        Default: guess (Guesses language / Not supported currently throws error currently)
    
    analyses: list of [ast, cfg, dataflow, subcfg]
        The analyses that should be applied during parsing the source code and
        the relations included the output.
        ast: Include relations based on the abstract syntax tree (the AST is always computed)
        cfg: Relations related to the control flow in the program (on a statement level)
        dataflow: Relations related to the data flow between variables
        subcfg: Relations related to the control flow (on a subexpression level)
    
    syntax_error : [raise, warn, ignore]
        Reaction to syntax error in code snippet.
        raise:  raises a Syntax Error
        warn:   prints a warning to console
        ignore: Ignores syntax errors. Helpful for parsing code snippets.
        Default: raise

    Returns
    -------
    SourceCodeGraph
        A labelled multi graph representing the given source code
    """

    root_node, tokens = preprocess_code(source_code, lang, **kwargs)

    graph_analyses = load_lang_analyses(tokens[0].config.lang)

    if analyses is None: analyses = DEFAULT_ANALYSES

    assert all(a in graph_analyses.keys() for a in analyses), \
            "Not all analyses are supported. Available analyses are: %s" % ", ".join(graph_analyses.keys())

    graph = CodeGraph(root_node, tokens, lang = lang)
    
    for analysis in analyses:
        analysis_visitor = graph_analyses[analysis]
        analysis_visitor(graph)(root_node)

    return graph


def load_lang_analyses(lang):
    if lang == 'python': return pylang_analyses()
    if lang == 'java'  : return javalang_analyses()

    raise NotImplementedError("Language %s is not supported" % lang)


def preprocess_code(source_code, lang, **kwargs):

    if lang == "java": return java_preprocess(source_code, **kwargs)

    return default_preprocess(source_code, lang, **kwargs)


def default_preprocess(source_code, lang, **kwargs):
    tokens = ctok.tokenize(source_code, lang = lang, **kwargs)
    root_node = _root_node(tokens)
    return root_node, tokens 

# Helper methods --------------------------------

def _root_node(tokens):
    if len(tokens) == 0: raise ValueError("Empty program has no root node")

    i = 0
    while not hasattr(tokens[i], "ast_node"):
        i += 1

    base_token = tokens[i]

    current_ast = base_token.ast_node 
    
    while current_ast.parent is not None:
        current_ast = current_ast.parent

    # If root only has one child skip to child
    if current_ast.child_count == 1:
        current_ast = current_ast.children[0]
    
    return current_ast