# VB6 Tree-sitter Adapter Design

**Date:** 2026-05-01  
**Status:** Approved

## Goal

Wrap proleap-vb6-parser (Java/ANTLR4) behind a tree-sitter-compatible API, exposed as a Python library and CLI. Agent code uses standard tree-sitter patterns and never imports proleap directly.

## Approach

Subprocess + JSON serialization (Option A). Python spawns a fat jar, reads JSON tree from stdout, builds an in-memory `Node` tree. No JVM in the Python process.

## Architecture

```
┌─────────────────────────────────┐
│  Python Package: vb6_parser     │
│                                 │
│  Parser.parse(code) ──────────► │──► subprocess
│  Tree.root_node                 │         │
│  Node (tree-sitter API)         │    Java fat jar
│  TreeCursor                     │         │
│  Node.semantic  (dict, bonus)   │◄── stdout JSON
└─────────────────────────────────┘
```

**Data flow:**
1. `Parser.parse(code)` writes tempfile → `java -jar vb6parser.jar --file tmp.bas`
2. Java: proleap parse → walk ANTLR4 CST + ASGElementRegistry → emit JSON to stdout
3. Python: parse JSON → build `Node` tree → return `Tree`

## Repository Layout

```
proleap-vb6-parser/              # existing Java repo (add CLI + serializer)
  src/main/java/io/proleap/vb6/
    cli/
      VbParserCLI.java           # main(), --file / --code / --module-name args
      ASTJsonSerializer.java     # walk CST + ASG → JSON
  pom.xml                        # add maven-shade-plugin

vb6-parser-python/               # new Python package (sibling dir or subdir)
  vb6_parser/
    __init__.py                  # Parser, Tree, Node, TreeCursor exports
    _jar.py                      # resolve bundled jar path
    _node.py                     # Node class
    _tree.py                     # Tree class
    _cursor.py                   # TreeCursor class
    _parser.py                   # Parser class (subprocess logic)
  resources/
    vb6parser.jar                # fat jar copied here at build time
  pyproject.toml
  tests/
    test_basic.py
    test_semantic.py
    test_cursor.py
```

## JSON Node Schema

Each node in the tree:

```json
{
  "type": "subStmt",
  "is_named": true,
  "start_point": [3, 0],
  "end_point": [5, 9],
  "start_byte": 42,
  "end_byte": 87,
  "field_name": "name",
  "semantic": {
    "kind": "procedure",
    "name": "CalcTotal",
    "visibility": "PUBLIC",
    "return_type": null
  },
  "children": [ ... ]
}
```

- `field_name`: set on the child from a static field map (see below); `null` when no mapping defined
- `semantic`: present when proleap's `ASGElementRegistry` has a matching `ASGElement`; otherwise `null`
- Terminal (anonymous) nodes: `is_named: false`, `type` = token literal text

**Note on `field_name`:** VisualBasic6.g4 has no ANTLR4 labeled fields (`name=rule` syntax). Field names are sourced from a static Python dict `FIELD_MAP: dict[str, dict[int, str]]` mapping `(parent_type, child_index) → field_name` for the most commonly queried rules (e.g., `subStmt[1] → "name"`, `functionStmt[1] → "name"`). `child_by_field_name()` uses this map; unregistered rules return `None`/empty.

### Semantic `kind` values

| kind | ASG source |
|------|-----------|
| `procedure` | `Procedure` (Sub/Function) |
| `module` | `Module` (Standard/Class) |
| `variable` | `Variable` |
| `type` | `TypeElement` |
| `enumeration` | from `EnumerationRegistry` |

## Java Components

### `VbParserCLI`

```
usage: java -jar vb6parser.jar [--file <path>] [--code <string>] [--module-name <name>]
output: JSON to stdout, errors to stderr, exit 1 on parse failure
```

### `ASTJsonSerializer`

- Recursively walks ANTLR4 `ParserRuleContext`
- `ctx.getClass().getSimpleName()` stripped of `"Context"` suffix → `type`
- `TerminalNode` → `is_named: false`
- Position: `ctx.start.getLine()-1` (0-indexed row), `ctx.start.getCharPositionInLine()` (col)
- Byte offsets computed from line/col + source string
- Looks up `ASGElementRegistry` by `ctx` instance → fills `semantic` when found
- `field_name` on children populated from static `FIELD_MAP` in Python (grammar has no labels)

### Maven change

Add `maven-shade-plugin` to produce `vb6parser.jar` with main class `io.proleap.vb6.cli.VbParserCLI`.

## Python API

### `Parser`

```python
class Parser:
    def __init__(self, jar_path: str | Path | None = None): ...
    def parse(self, code: str | bytes, module_name: str = "Module") -> Tree: ...
    def parse_file(self, path: str | Path) -> Tree: ...
```

- `jar_path=None` → use bundled jar from `resources/`
- Spawns subprocess, captures stdout JSON, raises `ParseError` on non-zero exit

### `Tree`

```python
class Tree:
    root_node: Node
    source: bytes   # original source for node.text slicing
```

### `Node`

Full tree-sitter-compatible surface:

```python
class Node:
    # identity
    type: str
    is_named: bool

    # position
    start_point: tuple[int, int]   # (row, col), 0-indexed
    end_point: tuple[int, int]
    start_byte: int
    end_byte: int

    # content
    text: bytes                    # source[start_byte:end_byte]

    # navigation
    parent: Node | None
    children: list[Node]
    named_children: list[Node]
    child_count: int
    named_child_count: int

    # field queries (Level B)
    def child_by_field_name(self, name: str) -> Node | None: ...
    def children_by_field_name(self, name: str) -> list[Node]: ...
    def descendants_of_type(self, *types: str) -> list[Node]: ...

    # cursor
    def walk(self) -> TreeCursor: ...

    # bonus (not in tree-sitter, non-conflicting)
    semantic: dict | None
```

### `TreeCursor`

```python
class TreeCursor:
    node: Node
    current_field_name: str | None
    def goto_first_child(self) -> bool: ...
    def goto_next_sibling(self) -> bool: ...
    def goto_parent(self) -> bool: ...
    def reset(self, node: Node) -> None: ...
```

## Usage Examples

```python
from vb6_parser import Parser

parser = Parser()
tree = parser.parse(vb6_source)

# Pure tree-sitter pattern — no proleap knowledge needed
for proc in tree.root_node.descendants_of_type("subStmt", "functionStmt"):
    name_node = proc.child_by_field_name("name")
    if name_node:
        print(name_node.text.decode())

# Optional semantic enrichment
if proc.semantic and proc.semantic["visibility"] == "PUBLIC":
    print(f"  -> public proc: {proc.semantic['name']}")
```

## Error Handling

- Parse failure → Java exits 1, stderr captured → Python raises `vb6_parser.ParseError`
- JRE not found → `vb6_parser.RuntimeError` with install hint
- JSON decode failure → `vb6_parser.InternalError` (should not happen; indicates serializer bug)

## Testing Strategy

- `test_basic.py`: parse hello-world VB6, assert root type, child count, positions
- `test_semantic.py`: verify `node.semantic` on known procedure/module nodes
- `test_cursor.py`: full cursor traversal matches `descendants_of_type` results
- Use existing `src/test/resources/` VB6 fixtures from proleap test suite
