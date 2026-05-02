ProLeap VB6 Parser — Python + Java
====================================

A **Visual Basic 6.0 parser** with a tree-sitter-compatible Python API, backed by the [ProLeap ANTLR4 VB6 grammar](src/main/antlr4/io/proleap/vb6/VisualBasic6.g4).

The Java core produces a concrete syntax tree (CST) enriched with semantic information (procedure signatures, call relationships, variable types). The Python wrapper exposes a tree-sitter-style interface so analysis code doesn't need to know about the underlying Java implementation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


Python Quick Start
------------------

**Requirements:** Python >= 3.10, Java 17+ on PATH (or `JAVA_HOME` set).

### Install

```bash
pip install --no-build-isolation ./vb6-parser-python/
```

### Parse VB6 code

```python
from vb6_parser import Parser

tree = Parser().parse("""
Private Sub Command1_Click()
    Text1.Text = "Hello, world!"
End Sub
""")

root = tree.root_node
print(root.type)        # module
print(root.semantic)    # {'kind': 'module', 'name': 'Module', ...}
```

### Parse a file

```python
tree = Parser().parse_file("MyForm.bas")
```


Python API Reference
--------------------

### Parser

```python
from vb6_parser import Parser

parser = Parser()                          # auto-locate bundled jar
parser = Parser(jar_path="/path/to.jar")  # explicit jar
```

| Method | Returns | Description |
|--------|---------|-------------|
| `parse(code, module_name="Module")` | `Tree` | Parse str or bytes |
| `parse_file(path)` | `Tree` | Parse a .bas / .cls file |

### Tree

| Property | Type | Description |
|----------|------|-------------|
| `root_node` | `Node` | Root of the CST |
| `source` | `bytes` | Original source bytes |

### Node

Mirrors the [tree-sitter Node API](https://tree-sitter.github.io/tree-sitter/using-parsers#syntax-nodes).

| Property / Method | Description |
|-------------------|-------------|
| `type` | Rule name, e.g. `"subStmt"`, `"module"` |
| `is_named` | `True` for rule nodes, `False` for terminals |
| `start_point` | `(row, col)` 0-indexed |
| `end_point` | `(row, col)` 0-indexed |
| `start_byte` / `end_byte` | Byte offsets into source |
| `text` | `bytes` slice of source |
| `children` | `list[Node]` all children |
| `named_children` | `list[Node]` named children only |
| `child_count` / `named_child_count` | `int` |
| `parent` | `Node or None` |
| `semantic` | `dict or None` enriched metadata (see below) |
| `child_by_field_name(name)` | `Node or None` |
| `children_by_field_name(name)` | `list[Node]` |
| `descendants_of_type(*types)` | `list[Node]` recursive search |
| `walk()` | `TreeCursor` |

### TreeCursor

```python
cursor = tree.root_node.walk()
cursor.goto_first_child()   # -> bool
cursor.goto_next_sibling()  # -> bool
cursor.goto_parent()        # -> bool
cursor.reset(node)          # reposition to any Node
cursor.node                 # current Node
cursor.current_field_name   # str | None
```

### Semantic dict

For procedure and variable nodes the `semantic` property returns a dict:

```python
# subStmt / functionStmt / propertyGetStmt / propertyLetStmt / propertySetStmt
{
    "kind":        "sub" | "function" | "propertyGet" | "propertyLet" | "propertySet",
    "name":        "MyProc",
    "visibility":  "PUBLIC" | "PRIVATE" | None,
    "return_type": "Integer" | None,          # None for subs
    "params": [
        {"name": "x", "type": "Double", "is_optional": False},
        ...
    ],
    "callers": [
        {"name": "CallingProc", "line": 14},  # 0-indexed line number
        ...
    ]
}

# variableSubStmt
{"kind": "variable", "name": "total", "visibility": "PRIVATE", "return_type": "Double"}

# module root
{"kind": "module", "name": "Calculator", "visibility": None, "return_type": None}
```

`callers` lists every call-site that invokes this procedure. To derive **callees** (what a procedure calls), invert the relationship in Python:

```python
procs = root.descendants_of_type("subStmt", "functionStmt")
callees_of_main = {
    p.semantic["name"]
    for p in procs
    if any(c["name"] == "Main" for c in p.semantic["callers"])
}
```


Usage Examples
--------------

### List all procedures with signatures

```python
from vb6_parser import Parser

tree = Parser().parse_file("Module1.bas")
procs = tree.root_node.descendants_of_type(
    "subStmt", "functionStmt",
    "propertyGetStmt", "propertyLetStmt", "propertySetStmt"
)

for p in procs:
    s = p.semantic
    params = ", ".join(
        f"{a['name']}: {a['type'] or '?'}" for a in s["params"]
    )
    ret = s["return_type"] or "void"
    print(f"[{s['visibility']}] {s['kind']} {s['name']}({params}) -> {ret}")
```

Output:
```
[PUBLIC] function Add(x: Double, y: Double) -> Double
[PRIVATE] sub PrintResult(val: Double) -> void
[PUBLIC] sub Main() -> void
```

### Build a call graph

```python
procs = tree.root_node.descendants_of_type("subStmt", "functionStmt")

for p in procs:
    name = p.semantic["name"]
    callees = [
        q.semantic["name"] for q in procs
        if any(c["name"] == name for c in q.semantic["callers"])
    ]
    print(f"{name} -> {callees}")
```

### Cursor-based DFS traversal

```python
cursor = tree.root_node.walk()
while True:
    print(cursor.node.type, cursor.node.start_point)
    if cursor.goto_first_child():
        continue
    if cursor.goto_next_sibling():
        continue
    while cursor.goto_parent():
        if cursor.goto_next_sibling():
            break
    else:
        break
```

### Find variable declarations

```python
variables = tree.root_node.descendants_of_type("variableSubStmt")
for v in variables:
    if v.semantic:
        print(f"{v.semantic['name']} : {v.semantic['return_type']}")
```


Error Handling
--------------

```python
from vb6_parser import Parser, ParseError, VbRuntimeError

try:
    tree = Parser().parse(code)
except ParseError as e:
    print("VB6 parse failed:", e)
    print("Java stderr:", e.stderr)
except VbRuntimeError as e:
    print("Java not found or timed out:", e)
```


Architecture
------------

```
Python caller
    |
    v
vb6_parser.Parser.parse()          # Python subprocess bridge
    |  writes tempfile, spawns:
    v
java -jar vb6parser.jar            # ASTJsonSerializer + VbParserCLI
    |  stdout = JSON tree
    v
vb6_parser.Tree / Node             # tree-sitter-compatible Python objects
```

The Java layer uses proleap's ANTLR4 runner to build an ASG, then `ASTJsonSerializer` walks the parse tree and emits one JSON object per node with 9 fields: `type`, `is_named`, `start_point`, `end_point`, `start_byte`, `end_byte`, `field_name`, `semantic`, `children`.

The Python layer wraps that JSON in `Node` objects with `__slots__` for efficiency. No native extensions required — just subprocess + JSON.


Java API (advanced)
-------------------

The Java core can be used directly as a Maven dependency for JVM projects.

### Add dependency

```xml
<dependency>
  <groupId>io.github.uwol</groupId>
  <artifactId>proleap-vb6-parser</artifactId>
  <version>3.0.0</version>
</dependency>
```

### Generate ASG and traverse AST

```java
java.io.File inputFile = new java.io.File("HelloWorld.cls");
io.proleap.vb6.asg.metamodel.Program program =
    new io.proleap.vb6.asg.runner.impl.VbParserRunnerImpl().analyzeFile(inputFile);

// navigate ASG
io.proleap.vb6.asg.metamodel.Module module = program.getClazzModule("HelloWorld");
io.proleap.vb6.asg.metamodel.Variable var = module.getVariable("I");
io.proleap.vb6.asg.metamodel.type.Type type = var.getType();

// traverse AST with visitor
io.proleap.vb6.VisualBasic6BaseVisitor<Boolean> visitor =
    new io.proleap.vb6.VisualBasic6BaseVisitor<Boolean>() {
        @Override
        public Boolean visitVariableSubStmt(
                io.proleap.vb6.VisualBasic6Parser.VariableSubStmtContext ctx) {
            io.proleap.vb6.asg.metamodel.Variable v =
                (io.proleap.vb6.asg.metamodel.Variable)
                program.getASGElementRegistry().getASGElement(ctx);
            return visitChildren(ctx);
        }
    };
for (io.proleap.vb6.asg.metamodel.Module m : program.getModules()) {
    visitor.visit(m.getCtx());
}
```

### Build the fat JAR (CLI / Python bridge)

```bash
mvn package -DskipTests
# produces target/vb6parser.jar — copy to vb6-parser-python/vb6_parser/resources/
```


Grammar Notes
-------------

* Line-based grammar distinguishes member calls (`A.B`) from WITH-context calls (`.B`).
* Keywords may be used as identifiers depending on context (`A.Type` valid; `Type.B` not).
* Derived from the [VB6 language reference](http://msdn.microsoft.com/en-us/library/aa338033%28v=vs.60%29.aspx), tested against MSDN statement examples.


Build & Test
------------

**Java (requires JDK 17+, Maven 3+):**

```bash
mvn clean package     # build + test
mvn test              # test only
```

**Python (requires Python >= 3.10):**

```bash
cd vb6-parser-python
pip install --no-build-isolation .
pytest tests/
```


License
-------

Licensed under the MIT License. See LICENSE for details.
