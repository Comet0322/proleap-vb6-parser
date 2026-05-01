from vb6_parser import Parser


def test_sub_semantic_kind(hello_world_tree):
    subs = hello_world_tree.root_node.descendants_of_type("subStmt")
    assert len(subs) == 1
    assert subs[0].semantic["kind"] == "sub"


def test_sub_semantic_name(hello_world_tree):
    subs = hello_world_tree.root_node.descendants_of_type("subStmt")
    assert subs[0].semantic["name"] == "Command1_Click"


def test_sub_semantic_visibility(hello_world_tree):
    subs = hello_world_tree.root_node.descendants_of_type("subStmt")
    assert subs[0].semantic["visibility"] == "PRIVATE"


def test_function_semantic_kind(function_module_tree):
    funcs = function_module_tree.root_node.descendants_of_type("functionStmt")
    assert len(funcs) == 1
    assert funcs[0].semantic["kind"] == "function"


def test_function_semantic_name(function_module_tree):
    funcs = function_module_tree.root_node.descendants_of_type("functionStmt")
    assert funcs[0].semantic["name"] == "Add"


def test_function_semantic_return_type(function_module_tree):
    funcs = function_module_tree.root_node.descendants_of_type("functionStmt")
    assert funcs[0].semantic["return_type"] == "Integer"


def test_module_semantic_kind(hello_world_tree):
    assert hello_world_tree.root_node.semantic["kind"] == "module"


def test_module_semantic_name():
    # module_name is the caller-supplied name forwarded by Parser.parse()
    tree = Parser().parse(b"Private Sub Test()\nEnd Sub\n", module_name="MyModule")
    assert tree.root_node.semantic["name"] == "MyModule"


def test_sub_name_child_field(hello_world_tree):
    subs = hello_world_tree.root_node.descendants_of_type("subStmt")
    name_node = subs[0].child_by_field_name("name")
    assert name_node is not None
    assert name_node.type == "ambiguousIdentifier"


def test_cursor_walks_to_module_body(hello_world_tree):
    cursor = hello_world_tree.root_node.walk()
    cursor.goto_first_child()
    # The direct first child of module root is moduleBody (wraps subStmt)
    assert cursor.node.type == "moduleBody"
