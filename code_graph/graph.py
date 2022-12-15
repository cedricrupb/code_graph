from io import StringIO
from collections import defaultdict

from code_tokenize.tokens import Token


class CodeGraph:

    def __init__(self, root_node, tokens, lang = "python"):

        self.tokens = tokens
        self.root_node = root_node
        self.lang = lang

        self.__nodes     = [] # General container for all nodes
        self.__ast_nodes = {} # Nodes indexed by AST

        # Init graph
        self.token_nodes = []

        prev_token = self._add_token(tokens[0])
        self.token_nodes.append(prev_token)

        for token in tokens[1:]:
            token_node = self._add_token(token)
            prev_token.add_successor(token_node, "next_token")
            prev_token = token_node
            self.token_nodes.append(token_node)
        
        self.root_node = self.add_node(root_node)

    # Add nodes ----------------------------------------------------------------

    def _add_node(self, node):

        if hasattr(node, "_graph_idx"):
            # Node is already assigned to a graph
            graph_idx = node._graph_idx
            assert self.__nodes[graph_idx] == node, "Node is already assigned to another graph"
            return node

        if hasattr(node, "ast_node") and node.ast_node is not None:
            ast_key = node_key(node.ast_node)
            try:
                return self.__ast_nodes[ast_key]
            except KeyError:
                self.__ast_nodes[ast_key] = node

        node._graph_idx = len(self.__nodes)
        self.__nodes.append(node)
        return node

    def _add_ast_node(self, ast_node):
        return self._add_node(SyntaxNode(ast_node))

    def _add_token(self, token):
        return self._add_node(TokenNode(token))

    def add_node(self, node):
        if isinstance(node, Node): return self._add_node(node)
        if isinstance(node, Token): return self._add_token(node)
        if isinstance(node, str): return self._add_node(SymbolNode(node))

        return self._add_ast_node(node)

    def add_relation(self, source_node, target_node, relation = "ast", no_create = False):

        if no_create:
            if not self.has_node(source_node): return
            if not self.has_node(target_node): return

        source_node = self.add_node(source_node)
        target_node = self.add_node(target_node)
        source_node.add_successor(target_node, relation)

    # API GET methods-----------------------------------------

    def has_node(self, ast_node):
        try:
            return self.__nodes[ast_node._graph_idx] == ast_node
        except (IndexError, AttributeError):
            return node_key(ast_node) in self.__ast_nodes

    def node_by_ast(self, ast_node):
        if not self.has_node(ast_node): return None
        return self.__ast_nodes[node_key(ast_node)]

    def is_token(self, ast_node):
        return hasattr(self.node_by_ast(ast_node), "token")

    def nodes(self):
        return self.__nodes

    def todot(self, file_name = None, edge_colors = None):
        dotwriter = GraphToDot(self, edge_colors)

        if file_name is not None:
            with open(file_name, "w") as f:
                dotwriter.run(f)
        else:
            with StringIO() as f:
                dotwriter.run(f)
                f.seek(0)
                return f.read()

    def tokens_only(self):
        """
        Computes a graph containing only tokens

        Any edges of inner nodes will be propagated down to leaves.
        The first token related to an inner node acts as an representant

        """
        return graph_to_tokens_only(self)
         
      
    # Internal GET methods -----------------------------------

    def __len__(self):
        return len(self.__nodes)

    def __iter__(self):
        return iter(self.nodes())

    def __repr__(self):
        name = self.lang[0].upper() + self.lang[1:]
        return "%sCodeGraph(%d)" % (name, len(self))

    

# Basic node ------------------------------------

class Node:
    
    def __init__(self):
        self._successors   = defaultdict(set)
        self._predecessors = defaultdict(set)

    # Helper methods --------------------------------

    def _add_predecessor(self, predecessor, edge_type):
        # This should never be called explicitly
        self._predecessors[edge_type].add(predecessor)

    def _iter_successors(self, edge_type = None):
        if edge_type is None:
            edge_types = self._successors.keys()
        else:
            edge_types = [edge_type]

        for edge_type in edge_types:
            for successor in self._successors[edge_type]:
                yield self, edge_type, successor

    def _iter_predecessors(self, edge_type = None):
        if edge_type is None:
            edge_types = self._predecessors.keys()
        else:
            edge_types = [edge_type]

        for edge_type in edge_types:
            for predecessor in self._predecessors[edge_type]:
                yield predecessor, edge_type, self

    def __repr__(self):
        class_name = self.__class__.__name__
        name       = self.node_name()
        num_succ   = self.num_successors()
        num_pred   = self.num_predecessors()
        return "%s[%s](ingoing: %d, outgoing: %d)" % (class_name, name, num_pred, num_succ)

    # API methods ------------------------------------

    def node_name(self):
        return "ast"

    def add_successor(self, successor_node, edge_type = "ast"):
        if successor_node is None: return
        self._successors[edge_type].add(successor_node)
        successor_node._add_predecessor(self, edge_type)

    def num_successors(self):
        return sum(len(succs) for succs in self._successors.values())

    def num_predecessors(self):
        return sum(len(pre) for pre in self._predecessors.values())

    def successors(self):
        return self._iter_successors()

    def successors_by_type(self, edge_type):
        return self._iter_successors(edge_type)

    def predecessors(self):
        return self._iter_predecessors()

    def predecessors_by_type(self, edge_type):
        return self._iter_predecessors(edge_type)

    def clone(self):
        return Node()

# Node types --------------------------------------------------------

class SyntaxNode(Node):

    def __init__(self, ast_node):
        super().__init__()
        self.ast_node = ast_node

    def node_name(self):
        return self.ast_node.type

    def clone(self):
        return SyntaxNode(self.ast_node)

    def __hash__(self):
        return hash(node_key(self.ast_node))


class TokenNode(SyntaxNode):

    def __init__(self, token):
        token_node = token.ast_node if hasattr(token, 'ast_node') else None
        super().__init__(token_node)
        self.token = token
    
    def node_name(self):
        return self.token.text
    
    def clone(self):
        return TokenNode(self.token)

    def __hash__(self):
        if self.ast_node is not None:
            return hash(node_key(self.ast_node))
        return hash(self.token.text)


class SymbolNode(Node):

    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol

    def node_name(self):
        return self.symbol

    def clone(self):
        return SymbolNode(self.symbol)

    def __hash__(self):
        return hash(self.symbol)


# Utils --------------------------------------------------------

def node_key(node):
    start_pos, end_pos = node.start_point, node.end_point
    child_count = node.child_count
    return (node.type, child_count, start_pos[0], start_pos[1], end_pos[0], end_pos[1])


class GraphToDot:
    
    def __init__(self, graph, edge_colors = None):
        self.graph = graph
        self.edge_colors = {} if edge_colors is None else edge_colors

    def _dot_edge(self, source_id, rel_type, target_id):
        
        edge_color = self.edge_colors.get(rel_type, "black")
        edge_style = f"color={edge_color}"

        return f'node{source_id} -> node{target_id} [label="{rel_type}" {edge_style}];\n'

    def run(self, writeable):

        def escape(token):
            return token.replace('"', '\\"')

        writeable.write("digraph {\n\tcompound=true;\n")

        tokens = []

        for node in self.graph:
            if isinstance(node, TokenNode): 
                tokens.append(node)
                continue
            node_name = node.node_name()
            writeable.write(
                f'\tnode{node._graph_idx}[shape="rectangle", label="{node_name}"];\n'
            )

        # Tokens
        writeable.write('\tsubgraph clusterNextToken {\n\t\tlabel="Tokens";\n\t\trank="same";\n')

        next_token_edges = []
        for token_node in tokens:
            token_text = escape(token_node.node_name())
            writeable.write(
                f'\t\tnode{token_node._graph_idx}[shape="rectangle", label="{token_text}"];\n'
            )

            for _, edge_type, next_token in token_node.successors_by_type("next_token"):
                next_token_edges.append(
                    self._dot_edge(token_node._graph_idx, edge_type, next_token._graph_idx)
                )

        for edge in next_token_edges:
            writeable.write(f"\t\t{edge}")

        writeable.write("\t}\n")

        for src_node in self.graph:
            for _, edge_type, target_node in src_node.successors():
                if edge_type == "next_token": continue
                edge_str = self._dot_edge(
                    src_node._graph_idx,
                    edge_type,
                    target_node._graph_idx
                )
                writeable.write(f"\t{edge_str}")
        
        writeable.write("}\n")


# Propagate to leaves ----------------------------------------------------------------

def _children(root_node):
    return [c for _, edge_type, c in root_node.successors() if edge_type == "child"]

def _bfs_token_search(root_node):
    token_nodes = []
    queue = [root_node]

    while len(queue) > 0:
        current_node = queue.pop()

        if hasattr(current_node, "token"): token_nodes.append(current_node)

        if len(token_nodes) == 0:
            queue.extend(_children(current_node))

    return min(token_nodes, key =lambda c: c._graph_idx)


def _left_token_search(root_node):
    while not hasattr(root_node, "token"):
        root_node = min(_children(root_node), key=lambda c: c._graph_idx)
    return root_node


def _compute_representer(graph):
    representer = {}

    root_node = graph.root_node
    queue     = [root_node]

    while len(queue) > 0:
        current_node = queue.pop(-1)

        if current_node in representer: continue

        representer[current_node] = _left_token_search(current_node)
        queue.extend(_children(current_node))

    return representer


SYNTAX_TYPES = {"child", "sibling"}

def graph_to_tokens_only(graph):
    representers = _compute_representer(graph)
    tokens       = graph.tokens

    output = CodeGraph(tokens[0].ast_node, tokens, lang = graph.lang)

    for ix, token_node in enumerate(graph.token_nodes):
        output_node = output.token_nodes[ix]

        for _, edge_type, successor in token_node.successors():
            if edge_type in SYNTAX_TYPES: continue
            if not hasattr(successor, "token"): continue

            output_succ = output.token_nodes[successor._graph_idx]
            output.add_relation(output_node, output_succ, edge_type)

    for node, representer in representers.items():
        token_idx = representer._graph_idx
        output_representer = output.token_nodes[token_idx]
        
        for _, edge_type, successor in node.successors():
            if edge_type in SYNTAX_TYPES: continue
            if successor not in representers: continue
            successor_representer = representers[successor]
            output_successor_representer = output.token_nodes[successor_representer._graph_idx]
            output.add_relation(output_representer, 
                                output_successor_representer, 
                                edge_type)

    return output