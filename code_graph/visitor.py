
class ASTVisitor:

    def __init__(self):
        self._ast_handler = None

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


    # Custom handler  ------------------------------------------------

    @staticmethod
    def _parse_visit_pattern(name):
        if name == "visit": return [("ast", "all"),]
        parts = name.split("_")

        if parts[0] != "visit": return []
        
        # We cannot decide whether
        # function_definition is the node type
        # or function is the node type
        # and definition is the edge type
        # Therefore, we register both
        # Assumption:
        #  - No node type function with edge definition
        #  - or no node type function_definition

        atomic_name = "_".join(parts[1:])
        node_name   = "_".join(parts[1:-1])
        edge_name   = parts[-1]

        return [(atomic_name, "all"), (node_name, edge_name)]

    def _register_handler(self):
        if self._ast_handler is not None: return

        self._ast_handler = {}
        possible_fields = filter(lambda x: x.startswith("visit"), dir(self))

        for visit_field in possible_fields:
            for node_type, edge_type in ASTVisitor._parse_visit_pattern(visit_field):
                if node_type not in self._ast_handler:
                    self._ast_handler[node_type] = {}
                edge_handler = self._ast_handler[node_type]
                edge_handler[edge_type] = visit_field

    def _handler_name(self, node_type, edge_type):
        if node_type not in self._ast_handler: return None
        edge_handlers = self._ast_handler[node_type]
        if edge_type not in edge_handlers: return None
        return edge_handlers[edge_type]

    def _handler(self, node_type, edge_type):
        handler_name = self._handler_name(node_type, edge_type)
        if handler_name is None: return lambda node: True

        handler_fn = getattr(self, handler_name)
        if not callable(handler_fn): 
            return lambda node: True
        else:
            return handler_fn

    def _visit_node(self, node):
        if self._handler(node.type, "all")(node) is False: return False
        if self._handler("ast", "all")(node) is False    : return False
        return True

    def _visit_edges(self, node):
        node_type = node.type
        if node_type not in self._ast_handler: return True

        for edge_type in self._ast_handler[node_type].keys():
            if edge_type == "all": continue

            child = node.child_by_field_name(edge_type)
            if child is None: continue
            if self._handler(node_type, edge_type)(child) is False: return False

        return True

    def _visit(self, node):
        # Phase 1: Visit node
        if self._visit_node(node) is False: return False

        # Phase 2: Visit specific edges
        if self._visit_edges(node) is False: return False
        return True

    # Navigation ----------------------------------------------------------------
    # To decrease memory, we only store the current node

    def _next_child(self, node):
        try:
            return node.children[0]
        except IndexError:
            return None

    def _next_sibling(self, node):
        return node.next_sibling

    def walk(self, root_node):
        self._register_handler()

        current_node = root_node
        next_node    = None

        while current_node is not None:
            # Step 1: Try to go to next child if we continue the subtree
            if self._visit(current_node):
                next_node = self._next_child(current_node)
            else:
                next_node = None

            # Step 2: Stop if parent or sibling is out of subtree
            if next_node is None and current_node == root_node:
                break

            # Step 3: Try to go to next sibling
            if next_node is None:
                next_node = self._next_sibling(current_node)

            previous_node = current_node

            # Step 4: Go up until sibling exists
            while next_node is None and current_node.parent is not None:
                current_node = current_node.parent
                if node_equal(current_node, root_node): break
                next_node    = self._next_sibling(current_node)

                if node_equal(previous_node, next_node): 
                    # A loop can occur if the program is not syntactically correct
                    # Is this enough?
                    next_node = None

            current_node = next_node

    def __call__(self, root_node):
        return self.walk(root_node)


# Helper --------------------------------

def node_equal(n1, n2):
    if n1 == n2: return True
    try:
        return (n1.type == n2.type 
                    and n1.start_point == n2.start_point
                    and n1.end_point   == n2.end_point)
    except AttributeError:
        return n1 == n2


# Compositions ----------------------------------------------------------------

class VisitorComposition(ASTVisitor):

    def __init__(self, *visitors):
        super().__init__()
        self.base_visitors = visitors

    def _register_handler(self):
        for base_visitor in self.base_visitors:
            base_visitor._register_handler()

    def _visit(self, node):
        for base_visitor in self.base_visitors:
            if base_visitor._visit(node) is False: return False
        return True
