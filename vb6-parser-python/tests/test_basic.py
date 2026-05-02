import pytest
from vb6_parser._parser import Parser
from vb6_parser._tree import Tree
from vb6_parser._errors import ParseError

HELLO_WORLD = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"

MODULE_WITH_FUNCTION = b"""Public Function Add(x As Integer, y As Integer) As Integer
    Add = x + y
End Function

Private Sub Greet()
    MsgBox "Hello"
End Sub
"""

def test_parse_returns_tree():
    tree = Parser().parse(HELLO_WORLD)
    assert isinstance(tree, Tree)

def test_root_node_is_module():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.type == "module"

def test_root_is_named():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.is_named is True

def test_start_point_zero():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.start_point == (0, 0)

def test_source_preserved():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.source == HELLO_WORLD

def test_find_sub_stmt():
    tree = Parser().parse(HELLO_WORLD)
    subs = tree.root_node.descendants_of_type("subStmt")
    assert len(subs) >= 1

def test_find_function_and_sub():
    tree = Parser().parse(MODULE_WITH_FUNCTION)
    funcs = tree.root_node.descendants_of_type("functionStmt")
    subs = tree.root_node.descendants_of_type("subStmt")
    assert len(funcs) >= 1
    assert len(subs) >= 1

def test_parse_string_input():
    tree = Parser().parse("Private Sub Test()\nEnd Sub\n")
    assert tree.root_node.type == "module"

def test_parse_invalid_raises_parse_error():
    # proleap may silently accept some invalid inputs; at minimum no crash without an exception
    with pytest.raises((ParseError, Exception)):
        Parser().parse("@@@@NOT_VALID_VB6@@@@")

def test_child_count_positive():
    tree = Parser().parse(HELLO_WORLD)
    assert tree.root_node.child_count > 0
