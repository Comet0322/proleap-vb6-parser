import pytest
from vb6_parser import Parser

HELLO_WORLD = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"

MODULE_WITH_FUNCTION = b"""Public Function Add(x As Integer, y As Integer) As Integer
    Add = x + y
End Function

Private Sub Greet()
    MsgBox "Hello"
End Sub
"""

def test_sub_semantic_kind():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    assert len(subs) >= 1
    assert subs[0].semantic["kind"] == "sub"

def test_sub_semantic_name():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    assert subs[0].semantic["name"] == "Command1_Click"

def test_sub_semantic_visibility():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    assert subs[0].semantic["visibility"] == "PRIVATE"

def test_function_semantic_kind():
    tree = Parser().parse(MODULE_WITH_FUNCTION)
    funcs = tree.root_node.descendants_of_type("functionStmt")
    assert len(funcs) >= 1
    assert funcs[0].semantic["kind"] == "function"

def test_function_semantic_name():
    tree = Parser().parse(MODULE_WITH_FUNCTION)
    funcs = tree.root_node.descendants_of_type("functionStmt")
    assert funcs[0].semantic["name"] == "Add"

def test_function_semantic_return_type():
    tree = Parser().parse(MODULE_WITH_FUNCTION)
    funcs = tree.root_node.descendants_of_type("functionStmt")
    assert funcs[0].semantic["return_type"] == "Integer"

def test_module_semantic_kind():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.semantic["kind"] == "module"

def test_module_semantic_name():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.semantic["name"] == "Module"

def test_sub_name_child_field():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    name_node = subs[0].child_by_field_name("name")
    assert name_node is not None
    assert name_node.type == "ambiguousIdentifier"

def test_cursor_walks_to_sub():
    tree = Parser().parse(HELLO_WORLD)
    cursor = tree.root_node.walk()
    cursor.goto_first_child()
    # The first child of the module root is moduleBody, which wraps subStmt
    assert cursor.node.type == "moduleBody"
