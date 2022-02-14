from .visitor import ASTVisitor

class ControlFlowVisitor(ASTVisitor):
    
    def __init__(self, graph):
        super().__init__()
        self.graph = graph
        self._last_stmts = tuple()

        self._break_from    = []
        self._continue_from = []
        self._returns_from  = []
        self._yields_from   = []


    def _add_next(self, stmt_node):
        for last_stmt_node in self._last_stmts:
            self.graph.add_relation(last_stmt_node, stmt_node, "controlflow")
        self._last_stmts = (stmt_node,)

    def _reset_last_stmts(self, reset_target):
        last_stmts = self._last_stmts
        self._last_stmts = (reset_target,)
        return last_stmts

    def visit_block(self, node):
        
        for stmt in node.children:
            self.walk(stmt)

        return False

    def visit_function_definition(self, node):
        outside_last, self._last_stmts = self._last_stmts, (node,)
        outside_returns, outside_yields = self._returns_from, self._yields_from
        self._returns_from, self._yields_from = [], []

        self.walk(
            node.child_by_field_name("body")
        )

        for stmt in self._last_stmts:
            self.graph.add_relation(stmt, node, "return_from")

        for stmt in self._returns_from:
            self.graph.add_relation(stmt, node, "return_from")

        for stmt in self._yields_from:
            self.graph.add_relation(stmt, node, "yield_from")

        self._returns_from, self._yields_from = outside_returns, outside_yields
        self._last_stmts = outside_last
        return False

    def visit_if_statement(self, node):
        self._add_next(node)

        # Consequences
        self.walk(node.child_by_field_name("consequence"))
        left_last_stmts = self._reset_last_stmts(node)

        # Alternative
        self.walk(node.child_by_field_name("alternative"))
        right_last_stmts = self._reset_last_stmts(node)

        self._last_stmts = left_last_stmts + right_last_stmts
        return False

    def visit_return_statement(self, node):
        self._add_next(node)
        self._returns_from.append(node)
        self._last_stmts = tuple()
        return False

    def visit_yield_statement(self, node):
        self._add_next(node)
        self._yields_from.append(node)
        self._last_stmts = tuple()
        return False

    def visit_break_statement(self, node):
        self._add_next(node)
        self._break_from.append(node)
        self._last_stmts = tuple()
        return False

    def visit_continue_statement(self, node):
        self._add_next(node)
        self._continue_from.append(node)
        self._last_stmts = tuple()
        return False

    def visit_for_statement(self, node):

        prev_break, prev_continue = self._break_from, self._continue_from
        self._break_from, self._continue_from = [], []

        self._add_next(node)
        self.walk(node.child_by_field_name("body"))
        self._last_stmts += tuple(self._continue_from)
        self._add_next(node)

        self.walk(node.child_by_field_name("alternative"))

        self._last_stmts += tuple(self._break_from)

        self._break_from, self._continue_from = prev_break, prev_continue
        return False

    def visit_while_statement(self, node):

        prev_break, prev_continue = self._break_from, self._continue_from
        self._break_from, self._continue_from = [], []

        self._add_next(node)
        self.walk(node.child_by_field_name("body"))
        self._last_stmts += tuple(self._continue_from)
        self._add_next(node)

        self.walk(node.child_by_field_name("alternative"))

        self._last_stmts += tuple(self._break_from)

        self._break_from, self._continue_from = prev_break, prev_continue
        return False
    
    def visit_try_statement(self, node):
        self._add_next(node)
        starting_stmt = self._last_stmts

        self.walk(node.child_by_field_name("body"))
        self.walk(node.child_by_field_name("alternative"))

        exception_starting_stmts = self._last_stmts + starting_stmt
        self._last_stmts = exception_starting_stmts
        out_last_stmts = tuple()

        finally_clauses = []
        for possible_exception in node.children:
            if possible_exception.type == "except_clause":
                self.walk(possible_exception)
                out_last_stmts += self._last_stmts
                self._last_stmts = exception_starting_stmts
            if possible_exception.type == "finally_clause":
                finally_clauses.append(possible_exception)

        self._last_stmts += out_last_stmts

        for finally_clause in finally_clauses:
            self.walk(finally_clause)

        return False

    def visit(self, node):
        # All statement node type end with statement
        # in tree-sitter
        # Therefore, we can savely do this hack.
        if node.type.endswith("statement"):
            self._add_next(node)
            return False
        return True