from ..visitor import ASTVisitor

from collections import defaultdict

class ControlFlowVisitor(ASTVisitor):
    
    def __init__(self, graph):
        super().__init__()
        self.graph = graph
        self._last_stmts = tuple()

        self._returns_from  = []
        self._continue_from = defaultdict(list)
        self._break_from    = defaultdict(list)

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

    # Methods --------------------------------------------------------

    def visit_method_declaration(self, node):
        outside_last, self._last_stmts = self._last_stmts, (node,)
        outside_returns = self._returns_from
        self._returns_from = []

        self.walk(
            node.child_by_field_name("body")
        )

        for stmt in self._last_stmts:
            self.graph.add_relation(stmt, node, "return_from")

        for stmt in self._returns_from:
            self.graph.add_relation(stmt, node, "return_from")

        self._returns_from = outside_returns
        self._last_stmts = outside_last
        return False

    def visit_return_statement(self, node):
        self._add_next(node)
        self._returns_from.append(node)
        self._last_stmts = tuple()
        return False

    # Labeled statements --------------------------------

    def visit_labeled_statement(self, node):
        name_node, _, body = node.children
        name = self.graph.add_or_get_node(name_node) # has to be a token
        name = name.token.text

        self.walk(body)
        
        current_last = self._last_stmts
        self._last_stmts = tuple(self._continue_from[name])
        self._add_next(body)
        self._continue_from[name] = []

        self._last_stmts = current_last + tuple(self._break_from[name])
        self._break_from[name] = []
        return False

    def visit_break_statement(self, node):
        self._add_next(node)

        jump_label = "__LOOP__"
        if node.child_count > 2:
            name_node  = node.children[1]
            name_token = self.graph.add_or_get_node(name_node)
            jump_label = name_token.token.text

        self._break_from[jump_label].append(node)
        self._last_stmts = tuple()
        return False

    def visit_continue_statement(self, node):
        self._add_next(node)

        jump_label = "__LOOP__"
        if node.child_count > 2:
            name_node  = node.children[1]
            name_token = self.graph.add_or_get_node(name_node)
            jump_label = name_token.token.text

        self._continue_from[jump_label].append(node)
        self._last_stmts = tuple()
        return False

    # Control structures --------------------------------

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

    def visit_for_statement(self, node):

        jump_label = "__LOOP__"
        prev_break, prev_continue = self._break_from[jump_label], self._continue_from[jump_label]
        self._break_from[jump_label], self._continue_from[jump_label] = [], []

        self._add_next(node)
        self.walk(node.child_by_field_name("body"))
        self._last_stmts += tuple(self._continue_from[jump_label])
        self._add_next(node)

        self._last_stmts += tuple(self._break_from[jump_label])

        self._break_from[jump_label], self._continue_from[jump_label] = prev_break, prev_continue
        return False

    def visit_while_statement(self, node): 

        jump_label = "__LOOP__"
        prev_break, prev_continue = self._break_from[jump_label], self._continue_from[jump_label]
        self._break_from[jump_label], self._continue_from[jump_label] = [], []

        self._add_next(node)
        self.walk(node.child_by_field_name("body"))
        self._last_stmts += tuple(self._continue_from[jump_label])
        self._add_next(node)

        self._last_stmts += tuple(self._break_from[jump_label])

        self._break_from[jump_label], self._continue_from[jump_label] = prev_break, prev_continue
        return False

    def visit_do_statement(self, node): 

        jump_label = "__LOOP__"
        prev_break, prev_continue = self._break_from[jump_label], self._continue_from[jump_label]
        self._break_from[jump_label], self._continue_from[jump_label] = [], []

        self._add_next(node)
        self.walk(node.child_by_field_name("body"))
        self._last_stmts += tuple(self._continue_from[jump_label])
        self._add_next(node)

        self._last_stmts += tuple(self._break_from[jump_label])

        self._break_from[jump_label], self._continue_from[jump_label] = prev_break, prev_continue
        return False
    

    def visit_try_statement(self, node):
        self._add_next(node)
        starting_stmt = self._last_stmts

        self.walk(node.child_by_field_name("body"))

        exception_starting_stmts = self._last_stmts + starting_stmt
        self._last_stmts = exception_starting_stmts
        out_last_stmts = tuple()

        finally_clauses = []
        for possible_exception in node.children:
            if possible_exception.type == "catch_clause":
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