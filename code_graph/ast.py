from .visitor import ASTVisitor


class ASTRelationVisitor(ASTVisitor):

    def __init__(self, graph):
        super().__init__()
        self.graph = graph

    def visit(self, ast_node):
        graph = self.graph

        for child in ast_node.children:
            graph.add_relation(ast_node, child, "child")
        
        prev_sibling = ast_node.prev_sibling
        if prev_sibling is not None:
            graph.add_relation(prev_sibling, ast_node, "sibling")