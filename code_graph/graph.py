from io import StringIO
from collections import defaultdict

from itertools import chain

from code_tokenize.tokens import Token

class CodeGraph:

    def __init__(self, root_node, tokens, lang = "python"):

        self.tokens = tokens
        self.lang  = lang

        # Internal container
        self._ast_nodes       = {} # Nodes indexed by an AST node
        self._anonymous_nodes = [] # Unindexed nodes, can only be indexed by traversal

        prev_token = self._add_token(tokens[0])
        for token in tokens[1:]:
            token_node = self._add_token(token)
            prev_token.add_successor(token_node, "next_token")
            prev_token = token_node
        
        self.root_node = self.add_or_get_node(root_node)

    # Helper methods --------------------------------

    def _add_anonymous(self, node_obj):
        self._anonymous_nodes.append(node_obj)
        return node_obj

    def _add_ast_node(self, ast_node, node_obj = None):
        ast_node_key = node_key(ast_node)

        if ast_node_key in self._ast_nodes:
            return self._ast_nodes[ast_node_key]

        if node_obj is None:
            node_obj = SyntaxNode(ast_node)
        
        self._ast_nodes[ast_node_key] = node_obj
        return node_obj

    def _add_token(self, token):
        token_node = TokenNode(token)

        if token_node.ast_node is not None:
            return self._add_ast_node(token_node.ast_node, token_node)
        else:
            return self._add_anonymous(token_node)

    # ADD methods -----------------------------------
    # Currently, we do not support removal
    
    def add_node(self, node):
        if isinstance(node, Token):      return self._add_token(node)
        if isinstance(node, SyntaxNode): return self._add_ast_node(node.ast_node, node)
        if isinstance(node, Node):       return self._add_anonymous(node)

        return self._add_ast_node(node)

    def add_or_get_node(self, node):
        if isinstance(node, SyntaxNode):
            return self.add_or_get_node(node.ast_node)

        if isinstance(node, Node): return node
        try:
            return self._add_ast_node(node)
        except Exception:
            raise ValueError("Cannot add or get node %s. Only AST nodes can be indexed." % str(node))

    def add_relation(self, source_node, target_node, relation = "ast"):
        source_node = self.add_or_get_node(source_node)
        target_node = self.add_or_get_node(target_node)
        source_node.add_successor(target_node, relation)

    # API GET methods-----------------------------------------

    def has_node(self, ast_node):
        return node_key(ast_node) in self._ast_nodes

    def nodes(self):
        return chain(self._ast_nodes.values(), self._anonymous_nodes)

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
        return len(self._ast_nodes) + len(self._anonymous_nodes)

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

# Node types --------------------------------------------------------

class SyntaxNode(Node):

    def __init__(self, ast_node):
        super().__init__()
        self.ast_node = ast_node

    def node_name(self):
        return self.ast_node.type

    def __hash__(self):
        return hash(node_key(self.ast_node))


class TokenNode(SyntaxNode):

    def __init__(self, token):
        super().__init__(token.ast_node)
        self.token = token
    
    def node_name(self):
        return self.token.text

    def __hash__(self):
        if self.ast_node is not None:
            return hash(node_key(self.ast_node))
        return self.token.text



class SymbolNode(Node):

    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol

    def node_name(self):
        return self.symbol


# Utils --------------------------------------------------------

def node_key(node):
    start_pos, end_pos = node.start_point, node.end_point
    return (node.type, start_pos[0], start_pos[1], end_pos[0], end_pos[1])


class GraphToDot:
    
    def __init__(self, graph, edge_colors = None):
        self.graph = graph
        self.edge_colors = {} if edge_colors is None else edge_colors

    def _map_nodes_to_ix(self):
        for ix, node in enumerate(self.graph):
            node._dot_node_id = ix

    def _dot_edge(self, source_id, rel_type, target_id):
        
        edge_color = self.edge_colors.get(rel_type, "black")
        edge_style = f"color={edge_color}"

        return f'node{source_id} -> node{target_id} [label="{rel_type}" {edge_style}];\n'

    def run(self, writeable):
        self._map_nodes_to_ix()

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
                f'\tnode{node._dot_node_id}[shape="rectangle", label="{node_name}"];\n'
            )

        # Tokens
        writeable.write('\tsubgraph clusterNextToken {\n\t\tlabel="Tokens";\n\t\trank="same";\n')

        next_token_edges = []
        for token_node in tokens:
            token_text = escape(token_node.node_name())
            writeable.write(
                f'\t\tnode{token_node._dot_node_id}[shape="rectangle", label="{token_text}"];\n'
            )

            for _, edge_type, next_token in token_node.successors_by_type("next_token"):
                next_token_edges.append(
                    self._dot_edge(token_node._dot_node_id, edge_type, next_token._dot_node_id)
                )

        for edge in next_token_edges:
            writeable.write(f"\t\t{edge}")

        writeable.write("\t}\n")

        for src_node in self.graph:
            for _, edge_type, target_node in src_node.successors():
                if edge_type == "next_token": continue
                edge_str = self._dot_edge(
                    src_node._dot_node_id,
                    edge_type,
                    target_node._dot_node_id
                )
                writeable.write(f"\t{edge_str}")
        
        writeable.write("}\n")

        # Cleanup
        for src_node in self.graph:
            del src_node._dot_node_id


# Propagate to leaves ----------------------------------------------------------------

def _compute_representer(graph):
    representer = {}

    root_node = graph.root_node
    queue     = [root_node]

    while len(queue) > 0:
        current_node = queue.pop(-1)
        
        path = []
        while not hasattr(current_node, "token"):
            path.append(current_node)
            syntax_node    = current_node.ast_node
            children       = [graph.add_or_get_node(c)
                                for c in syntax_node.children 
                                if graph.has_node(c)]
            if len(children) == 0: break
            first, *others = children
            queue.extend(others)
            current_node = first

        for r in path: representer[r] = current_node

    return representer


SYNTAX_TYPES = {"child", "sibling"}

def graph_to_tokens_only(graph):
    representers = _compute_representer(graph)
    tokens       = graph.tokens

    output = CodeGraph(tokens[0].ast_node, tokens, lang = graph.lang)

    for token in graph.tokens:
        if not hasattr(token, "ast_node"): continue
        token_node  = graph.add_or_get_node(token.ast_node)
        output_node = output.add_or_get_node(token.ast_node)

        for _, edge_type, successor in token_node.successors():
            if edge_type in SYNTAX_TYPES: continue
            if not hasattr(successor, "token"): continue
            output_succ = output.add_or_get_node(successor.ast_node)
            output.add_relation(output_node, output_succ, edge_type)
            

    for node, representer in representers.items():
        output_representer = output.add_or_get_node(representer.ast_node)
        
        for _, edge_type, successor in node.successors():
            if edge_type in SYNTAX_TYPES: continue
            if successor not in representers: continue
            successor_representer = representers[successor]
            output_successor_representer = output.add_or_get_node(successor_representer.ast_node)
            output.add_relation(output_representer, 
                                output_successor_representer, 
                                edge_type)

    return output