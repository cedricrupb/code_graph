
from ..visitor import ASTVisitor

from itertools import chain
from copy import copy
from contextlib import contextmanager
from collections import defaultdict

# Identifier context --------------------------------

@contextmanager
def _context(self, identifier_ctx):
    current_context = getattr(self, '_id_context', None)
    try:
        self._id_context = identifier_ctx
        yield
    finally:
        self._id_context = current_context

def context(identifier_ctx):

    def visitor_decorator(visitor_fn):
        
        def contextual_visitor(self, node):
            with _context(self, identifier_ctx):
                return visitor_fn(self, node)
        
        return contextual_visitor

    return visitor_decorator


def current_context(self):
    return getattr(self, '_id_context', None)

# ----------------------------------------------------

class DataFlowVisitor(ASTVisitor):

    def __init__(self, graph):
        super().__init__()
        self.graph = graph

        self._last_writes = defaultdict(set)
        self._last_reads  = defaultdict(set)

        self._returns_from_rw  = []
        self._continue_from_rw = []
        self._break_from_rw    = []

        self._var_scopes    = {}
        self._current_scope = ["G"]

    # Scope handling ----------------------------------------------------
    
    def register_in_scope(self, var_name):
        current_scope = self._var_scopes
        for scope in self._current_scope:
            if scope not in current_scope:
                current_scope[scope] = {"__vars__": set()}
            current_scope = current_scope[scope]
        current_scope["__vars__"].add(var_name)
        return ".".join(self._current_scope + [var_name])
    
    def qualname(self, var_name):
        candidate_scopes = []
        current_scope    = self._var_scopes
        for scope in self._current_scope:
            if scope not in current_scope: break
            candidate_scopes.append((scope, current_scope[scope]))
            current_scope = current_scope[scope]

        while len(candidate_scopes) > 1 and var_name not in candidate_scopes[-1][1]["__vars__"]:
            candidate_scopes.pop(-1)
        
        return ".".join([c[0] for c in candidate_scopes] + [var_name])
        

    # Variable writes ----------------------------------------------------

    def record_write(self, node):
        node = self.graph.add_or_get_node(node)
        qname = self.register_in_scope(node.token.text)
        self._last_reads[qname] = set()
        self._last_writes[qname] = {node}


    def record_read(self, node):
        node  = self.graph.add_or_get_node(node)
        qname = self.qualname(node.token.text)
        
        for last_read in self._last_reads[qname]:
            self.graph.add_relation(last_read, node, "next_may_use")
        self._last_reads[qname] = {node}

        for last_write in self._last_writes[qname]:
            self.graph.add_relation(last_write, node, "last_may_write")


    def visit_identifier(self, node):
        node_context = current_context(self)
        if node_context is None  :  return self.record_read(node) # Default to read variable
        if node_context == "read":  return self.record_read(node)
        if node_context == "write": return self.record_write(node)

    # Read / Write handler ------------------------------------------
    
    def _copy_rw_context(self):
        return (copy(self._last_reads), copy(self._last_writes))

    def _restore_rw_context(self, rw_context):
        rcontext, wcontext = rw_context
        self._last_reads, after_rcontext  = rcontext, self._last_reads
        self._last_writes, after_wcontext = wcontext, self._last_writes

        return (after_rcontext, after_wcontext)

    def _join_rw_context(self, rw_context):
        self._last_reads, self._last_writes = merge_rw_contexts(
            (self._last_reads, self._last_writes),
            rw_context
        )

    def _reset_rw_context(self):
        self._last_reads = defaultdict(set)
        self._last_writes = defaultdict(set)

    # Scopes --------------------------------------------------------

    def visit_block(self, node):
        self._current_scope.append("<block>")

        for child in node.children:
            self.walk(child)

        self._current_scope.pop(-1)
        return False

    # Functions --------------------------------------------------------

    def visit_return_statement(self, node):
        with _context(self, "read"):
            for child in node.children: self.walk(child)

        self._returns_from_rw[-1] = merge_rw_contexts(
            self._returns_from_rw[-1], (self._last_reads, self._last_writes)
        )
        self._reset_rw_context()
        return False

    def visit_method_declaration(self, node):
        self._returns_from_rw.append((defaultdict(set), defaultdict(set)))
        name_node = node.child_by_field_name("name")
        name      = self.graph.tokens.get_token_by_node(name_node).text
        self._current_scope.append(name)

        with _context(self, "write"):
            self.walk(node.child_by_field_name("parameters"))

        self.walk(node.child_by_field_name("body"))

        self._current_scope.pop(-1)
        self._join_rw_context(self._returns_from_rw.pop(-1))
        return False

    # Control structures --------------------------------------------------------
    
    def visit_if_statement(self, node):
        with _context(self, "read"):
            self.walk(node.child_by_field_name("condition"))

        last_rw_context = self._copy_rw_context()

        self.walk(node.child_by_field_name("consequence"))

        after_rw_context = self._restore_rw_context(last_rw_context)

        self.walk(node.child_by_field_name("alternative"))

        self._join_rw_context(after_rw_context)

        return False

    def visit_while_statement(self, node): 
        with _context(self, "read"):
            self.walk(node.child_by_field_name("condition"))

        after_test_context = self._copy_rw_context()

        self._break_from_rw.append((defaultdict(set), defaultdict(set)))
        self._continue_from_rw.append((defaultdict(set), defaultdict(set)))

        self.walk(node.child_by_field_name("body"))
        self._join_rw_context(self._continue_from_rw.pop(-1))

        self._break_from_rw[-1] = (defaultdict(set), defaultdict(set))
        self._continue_from_rw.append((defaultdict(set), defaultdict(set)))
        # No fixpoint computation?
        # Is this enough?
        with _context(self, "read"):
            self.walk(node.child_by_field_name("condition"))
        self.walk(node.child_by_field_name("body"))
        self._join_rw_context(self._continue_from_rw.pop(-1))

        with _context(self, "read"):
            self.walk(node.child_by_field_name("condition"))
            
        self._join_rw_context(after_test_context)
        self._join_rw_context(self._break_from_rw.pop(-1))

        return False


    def visit_do_statement(self, node):

        self._break_from_rw.append((defaultdict(set), defaultdict(set)))
        self._continue_from_rw.append((defaultdict(set), defaultdict(set)))

        self.walk(node.child_by_field_name("body"))
        self._join_rw_context(self._continue_from_rw.pop(-1))

        self._break_from_rw[-1] = (defaultdict(set), defaultdict(set))
        self._continue_from_rw.append((defaultdict(set), defaultdict(set)))
        # No fixpoint computation?
        # Is this enough?
        with _context(self, "read"):
            self.walk(node.child_by_field_name("condition"))
        self.walk(node.child_by_field_name("body"))
        self._join_rw_context(self._continue_from_rw.pop(-1))

        with _context(self, "read"):
            self.walk(node.child_by_field_name("condition"))

        self._join_rw_context(self._break_from_rw.pop(-1))

        return False


    def visit_for_statement(self, node): 
        self._current_scope.append("<if>") # We have to cheat here for registering id in the right scope
        self.walk(node.child_by_field_name("init"))
        with _context(self, "read"):
            self.walk(node.child_by_field_name("condition"))
        
        after_zero_iterations = self._copy_rw_context()

        self._break_from_rw.append((defaultdict(set), defaultdict(set)))
        self._continue_from_rw.append((defaultdict(set), defaultdict(set)))

        self.walk(node.child_by_field_name("body"))
        self._join_rw_context(self._continue_from_rw.pop(-1))
        self.walk(node.child_by_field_name("update"))

        self._break_from_rw[-1] = (defaultdict(set), defaultdict(set))
        self._continue_from_rw.append((defaultdict(set), defaultdict(set)))

        # No fixpoint computation?
        # Is this enough?
        with _context(self, "read"):
            self.walk(node.child_by_field_name("condition"))
        self.walk(node.child_by_field_name("body"))
        self._join_rw_context(self._continue_from_rw.pop(-1))
        self.walk(node.child_by_field_name("update"))

        self._join_rw_context(after_zero_iterations)
        self._join_rw_context(self._break_from_rw.pop(-1))

        self._current_scope.pop(-1)
        return False

    # Field access -------------------------------------------------------

    def visit_field_access(self, node):
        with _context(self, "read"):
            self.walk(node.child_by_field_name("object"))
        return False

    def visit_method_invocation(self, node):
        with _context(self, "read"):
            self.walk(node.child_by_field_name("object"))

        with _context(self, "read"):
            self.walk(node.child_by_field_name("arguments"))
        
        return False

    def visit_object_creation_expression(self, node):
        with _context(self, "read"):
            self.walk(node.child_by_field_name("arguments"))
        return False

    # Assignments --------------------------------------------------------

    def visit_variable_declarator(self, node):
        
        with _context(self, "read"):
            self.walk(node.child_by_field_name("value"))

        with _context(self, "write"):
            self.walk(node.child_by_field_name("name"))
        
        return False

    def visit_assignment_expression(self, node):
        with _context(self, "read"):
            self.walk(node.child_by_field_name("right"))

        with _context(self, "write"):
            self.walk(node.child_by_field_name("left"))
        
        return False

    def visit_update_expression(self, node):
        with _context(self, "read"):
            for child in node.children: self.walk(child)
        
        with _context(self, "write"):
            for child in node.children: self.walk(child)
        
        return False

    def visit_resource(self, node):
        with _context(self, "read"):
            self.walk(node.child_by_field_name("value"))

        with _context(self, "write"):
            self.walk(node.child_by_field_name("name"))
        
        return False

    def visit_lambda_expression(self, node):
        self._current_scope.append("<lambda>")
        self._returns_from_rw.append((defaultdict(set), defaultdict(set)))
        rw_context = self._copy_rw_context()

        with _context(self, "write"):
            self.walk(node.child_by_field_name("parameters"))

        self.walk(node.child_by_field_name("body"))

        self._restore_rw_context(rw_context)

        self._current_scope.pop(-1)
        self._returns_from_rw.pop(-1)
        return False


# Helper --------------------------------------------------------

def merge_flows(source_flow, target_flow):
    common_vars = set.union(set(source_flow.keys()), set(target_flow.keys()))
    return defaultdict(set, {v: set(chain(source_flow[v], target_flow[v])) for v in common_vars})

def merge_rw_contexts(source_rw_contex, target_rw_contex):
    source_rcontext, source_wcontext = source_rw_contex
    target_rcontext, target_wcontext = target_rw_contex

    result_rcontext = merge_flows(source_rcontext, target_rcontext)
    result_wcontext = merge_flows(source_wcontext, target_wcontext)

    return (result_rcontext, result_wcontext)