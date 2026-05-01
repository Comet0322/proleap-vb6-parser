from vb6_parser._node import Node
from vb6_parser._tree import Tree

SAMPLE_JSON = {
    "type": "module",
    "is_named": True,
    "start_point": [0, 0], "end_point": [3, 0],
    "start_byte": 0, "end_byte": 68,
    "field_name": None, "semantic": None,
    "children": [
        {
            "type": "subStmt",
            "is_named": True,
            "start_point": [0, 0], "end_point": [2, 7],
            "start_byte": 0, "end_byte": 68,
            "field_name": None,
            "semantic": {"kind": "sub", "name": "Command1_Click", "visibility": "PRIVATE", "return_type": None},
            "children": [
                {
                    "type": "Command1_Click",
                    "is_named": False,
                    "start_point": [0, 12], "end_point": [0, 26],
                    "start_byte": 12, "end_byte": 26,
                    "field_name": "name", "semantic": None, "children": []
                }
            ]
        }
    ]
}

SOURCE = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"


def make_tree():
    return Tree(Node(SAMPLE_JSON, SOURCE), SOURCE)


def test_tree_root_node_type():
    assert make_tree().root_node.type == "module"


def test_tree_source():
    assert make_tree().source == SOURCE


def test_cursor_initial_node():
    cursor = make_tree().root_node.walk()
    assert cursor.node.type == "module"


def test_cursor_goto_first_child():
    cursor = make_tree().root_node.walk()
    moved = cursor.goto_first_child()
    assert moved is True
    assert cursor.node.type == "subStmt"


def test_cursor_goto_first_child_leaf_returns_false():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()   # -> subStmt
    cursor.goto_first_child()   # -> Command1_Click (terminal, no children)
    moved = cursor.goto_first_child()
    assert moved is False


def test_cursor_goto_next_sibling():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()
    # subStmt is only child; no sibling
    moved = cursor.goto_next_sibling()
    assert moved is False


def test_cursor_goto_parent():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()
    moved = cursor.goto_parent()
    assert moved is True
    assert cursor.node.type == "module"


def test_cursor_goto_parent_at_root_returns_false():
    cursor = make_tree().root_node.walk()
    moved = cursor.goto_parent()
    assert moved is False


def test_cursor_current_field_name():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()    # subStmt — field_name None
    cursor.goto_first_child()    # Command1_Click — field_name "name"
    assert cursor.current_field_name == "name"


def test_cursor_reset():
    cursor = make_tree().root_node.walk()
    cursor.goto_first_child()
    sub_node = cursor.node
    cursor.goto_first_child()
    cursor.reset(sub_node)
    assert cursor.node.type == "subStmt"


def test_full_traversal_visits_all_nodes():
    tree = make_tree()
    visited = []
    cursor = tree.root_node.walk()
    while True:
        visited.append(cursor.node.type)
        if cursor.goto_first_child():
            continue
        if cursor.goto_next_sibling():
            continue
        while cursor.goto_parent():
            if cursor.goto_next_sibling():
                break
        else:
            break
    assert "module" in visited
    assert "subStmt" in visited
    assert "Command1_Click" in visited
