import json
from vb6_parser._node import Node

SAMPLE_JSON = {
    "type": "module",
    "is_named": True,
    "start_point": [0, 0],
    "end_point": [3, 0],
    "start_byte": 0,
    "end_byte": 68,
    "field_name": None,
    "semantic": None,
    "children": [
        {
            "type": "subStmt",
            "is_named": True,
            "start_point": [0, 0],
            "end_point": [2, 7],
            "start_byte": 0,
            "end_byte": 68,
            "field_name": None,
            "semantic": {"kind": "sub", "name": "Command1_Click", "visibility": "PRIVATE", "return_type": None},
            "children": [
                {
                    "type": "Command1_Click",
                    "is_named": False,
                    "start_point": [0, 12],
                    "end_point": [0, 26],
                    "start_byte": 12,
                    "end_byte": 26,
                    "field_name": "name",
                    "semantic": None,
                    "children": []
                }
            ]
        }
    ]
}

SOURCE = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"

def make_root():
    return Node(SAMPLE_JSON, SOURCE)

def test_type():
    assert make_root().type == "module"

def test_is_named():
    assert make_root().is_named is True

def test_start_point():
    assert make_root().start_point == (0, 0)

def test_end_point():
    assert make_root().end_point == (3, 0)

def test_start_byte():
    assert make_root().start_byte == 0

def test_end_byte():
    assert make_root().end_byte == 68

def test_text():
    assert make_root().text == SOURCE[0:68]

def test_children_count():
    root = make_root()
    assert root.child_count == 1

def test_named_children():
    root = make_root()
    assert len(root.named_children) == 1
    assert root.named_children[0].type == "subStmt"

def test_named_child_count():
    assert make_root().named_child_count == 1

def test_parent_is_none_for_root():
    assert make_root().parent is None

def test_parent_set_on_children():
    root = make_root()
    child = root.children[0]
    assert child.parent is root

def test_semantic_is_none_for_root():
    assert make_root().semantic is None

def test_semantic_on_sub_stmt():
    root = make_root()
    sub = root.children[0]
    assert sub.semantic["kind"] == "sub"
    assert sub.semantic["name"] == "Command1_Click"

def test_descendants_of_type():
    root = make_root()
    subs = root.descendants_of_type("subStmt")
    assert len(subs) == 1
    assert subs[0].type == "subStmt"

def test_descendants_of_type_multiple():
    root = make_root()
    results = root.descendants_of_type("subStmt", "module")
    types = {n.type for n in results}
    assert "subStmt" in types

def test_child_by_field_name():
    root = make_root()
    sub = root.children[0]
    name_node = sub.child_by_field_name("name")
    assert name_node is not None
    assert name_node.type == "Command1_Click"

def test_child_by_field_name_missing():
    root = make_root()
    assert root.child_by_field_name("nonexistent") is None

def test_children_by_field_name():
    root = make_root()
    sub = root.children[0]
    results = sub.children_by_field_name("name")
    assert len(results) == 1

def test_walk_returns_cursor():
    from vb6_parser._cursor import TreeCursor
    cursor = make_root().walk()
    assert isinstance(cursor, TreeCursor)
    assert cursor.node.type == "module"
