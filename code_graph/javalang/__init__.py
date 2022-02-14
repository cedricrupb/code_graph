from ..ast import ASTRelationVisitor

from .cfg import ControlFlowVisitor
from .dataflow import DataFlowVisitor

def javalang_analyses():
    return {
        "ast": ASTRelationVisitor,
        "cfg": ControlFlowVisitor,
        "dataflow": DataFlowVisitor,
    }