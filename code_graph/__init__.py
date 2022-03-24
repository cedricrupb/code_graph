import code_tokenize as ctok

from .graph import CodeGraph

from .pylang   import pylang_analyses
from .javalang import javalang_analyses, java_preprocess


def codegraph(source_code, lang = "guess", analyses = None, **kwargs):
    root_node, tokens = preprocess_code(source_code, lang, **kwargs)

    graph_analyses = load_lang_analyses(tokens[0].config.lang)

    if analyses is None:
        analyses = graph_analyses.keys()
    else:
        assert all(a in graph_analyses.keys() for a in analyses), \
                "Not all analyses are supported. Available analyses are: %s" % ", ".join(GRAPH_ANALYSES.keys())
    
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