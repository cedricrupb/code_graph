from ..ast import ASTRelationVisitor

from .cfg import ControlFlowVisitor
from .dataflow import DataFlowVisitor

import code_tokenize as ctok

from code_tokenize.tokens import TokenSequence


def javalang_analyses():
    return {
        "ast": ASTRelationVisitor,
        "cfg": ControlFlowVisitor,
        "dataflow": DataFlowVisitor,
    }


# Preprocessor ------------------------------------------------

def _try_tokenize_or_wrap(source_code, **kwargs):
    try:
        custom_args = {k: v for k, v in kwargs.items() if k != "syntax_error"}
        return ctok.tokenize(
            source_code, lang = "java", syntax_error = "raise", **custom_args
        ), False
    except SyntaxError:
        source_code = "public class Test {%s}" % source_code
        return ctok.tokenize(source_code, lang = "java", **kwargs), True


def java_preprocess(source_code, **kwargs):
    tokens, has_wrapped = _try_tokenize_or_wrap(source_code, **kwargs)

    if not has_wrapped:
        return _root_node(tokens), tokens

    output_tokens = TokenSequence(tokens[4:-1])
    
    root_node = output_tokens[0].ast_node
    while root_node.parent is not None:
        root_node = root_node.parent
        if root_node.type == "method_declaration": break
    
    return root_node, output_tokens
        
        
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
