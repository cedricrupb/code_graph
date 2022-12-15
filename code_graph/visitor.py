from code_ast import ASTVisitor as BaseVisitor

class ASTVisitor(BaseVisitor):

    # Error handling ------------------------------------------------

    def visit_ERROR(self, node):
        """
        An ERROR node is introduced if the parser reacts to an syntax error.

        The subtree rooted an ERROR node might node be conventional
        or a tree (might include cycles).
        The walk function however assumes a tree as input and will
        run in an infinite loop for errors.

        Therefore, default strategy is to skip error nodes.
        Can be overriden by subclasses.
        
        """
        return False