import code_tokenize as ctok

from .graph import CodeGraph

from .ast import ASTRelationVisitor
from .cfg import ControlFlowVisitor
from .dataflow import DataFlowVisitor


GRAPH_ANALYSES = {
    "ast": ASTRelationVisitor,
    "cfg": ControlFlowVisitor,
    "dataflow": DataFlowVisitor,
}

def codegraph(source_code, lang = "guess", analyses = None, **kwargs):
    tokens = ctok.tokenize(source_code, lang = lang, **kwargs)
    root_node = _root_node(tokens)

    if analyses is None:
        analyses = GRAPH_ANALYSES.keys()
    else:
        assert all(a in GRAPH_ANALYSES for a in analyses), \
                "Not all analyses are supported. Available analyses are: %s" % ", ".join(GRAPH_ANALYSES.keys())
    
    graph = CodeGraph(root_node, tokens, lang = lang)
    
    for analysis in analyses:
        analysis_visitor = GRAPH_ANALYSES[analysis]
        analysis_visitor(graph)(root_node)

    return graph

    

# Helper methods --------------------------------

def _root_node(tokens):
    if len(tokens) == 0: raise ValueError("Empty program has no root node")

    base_token  = tokens[0]
    current_ast = base_token.ast_node 
    
    while current_ast.parent is not None:
        current_ast = current_ast.parent

    # If root only has one child skip to child
    if current_ast.child_count == 1:
        current_ast = current_ast.children[0]
    
    return current_ast