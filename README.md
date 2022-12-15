# Code Graph
> Fast program graph generation in Python

Many Programming Language Processing (PLP) exploit the fact that programming languages are highly structured. Therefore, it is easy to parse a program
into an abstract syntax tree, analyse its control flow and track data flow 
relations between variables (the last one is a bit more harder :D).

**code.graph** provides easy access to graph representations of program codes for code written in Java and Python. The library is mainly designed to replicate the graph representation introduced in [Self-Supervised Bug Detection and Repair](https://arxiv.org/abs/2105.12787) for Python and published in NeurIPS21 by Allamanis et al.
Therefore, the implementation is close to the implementation used by the original
[authors](https://github.com/microsoft/neurips21-self-supervised-bug-detection-and-repair).

**Note:** This implementation does not compute interprocedural relations currently and its main purpose is parsing the implementation of single functions.


## Installation
The package is tested under Python 3. It can be installed by cloning this repository and installing the package via:
```
pip install -e .
```

## Usage
code.graph can be used to transform Java and Python program into a graph representation with a few lines of code:
```python
import code_graph as cg

# Python
cg.codegraph(
    '''
        def my_func():
            print("Hello World")
    ''',
lang = "python")

# Output: PythonCodeGraph(19), a graph with 19 nodes

# Java
cg.codegraph(
    '''
        public static void main(String[] args){
          System.out.println("Hello World");
        }
    ''',
lang = "java", 
syntax_error = "ignore")

# Output: JavaCodeGraph(32)

```
Further, you can easily traverse the code graph, e.g. via depth-first search:
```python
graph = cg.codegraph(...)

dfs_stack = [graph.root_node] # Root of the parsed AST
while len(dfs_tack) > 0:
    node = dfs_stack.pop(-1)

    for current, edge_type, next_node in node.successors():
        dfs_stack.append(next_node)

```
Alternatively, you can also export the graph int Dot Format by:
```python
graph.todot("file_name.dot")
```

## Project Info
This is currently developed as a helper library for internal research projects. Therefore, it will only be updated as needed.

Feel free to open an issue if anything unexpected
happens. 

Distributed under the MIT license. See ``LICENSE`` for more information.

We thank the developer of [tree-sitter](https://tree-sitter.github.io/tree-sitter/) library. Without tree-sitter this project would not be possible. 