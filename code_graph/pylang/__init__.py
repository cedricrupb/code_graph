
from ..ast import ASTRelationVisitor
from .cfg import ControlFlowVisitor, SubControlFlowVisitor
from .dataflow import DataFlowVisitor

def pylang_analyses():
    return {
        "ast": ASTRelationVisitor,
        "cfg": ControlFlowVisitor,
        "dataflow": DataFlowVisitor,
        "subcfg": SubControlFlowVisitor
    }