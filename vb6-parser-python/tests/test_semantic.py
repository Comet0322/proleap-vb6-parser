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


# ── params ────────────────────────────────────────────────────────────────────

def test_function_params_present(call_graph_tree):
    funcs = call_graph_tree.root_node.descendants_of_type("functionStmt")
    params = funcs[0].semantic["params"]
    assert isinstance(params, list)
    assert len(params) == 2


def test_function_params_names(call_graph_tree):
    funcs = call_graph_tree.root_node.descendants_of_type("functionStmt")
    params = funcs[0].semantic["params"]
    assert params[0]["name"] == "x"
    assert params[1]["name"] == "y"


def test_function_params_types(call_graph_tree):
    funcs = call_graph_tree.root_node.descendants_of_type("functionStmt")
    params = funcs[0].semantic["params"]
    assert params[0]["type"] == "Double"
    assert params[1]["type"] == "Double"


def test_function_params_not_optional(call_graph_tree):
    funcs = call_graph_tree.root_node.descendants_of_type("functionStmt")
    params = funcs[0].semantic["params"]
    assert params[0]["is_optional"] is False
    assert params[1]["is_optional"] is False


def test_sub_params_present(call_graph_tree):
    subs = call_graph_tree.root_node.descendants_of_type("subStmt")
    print_result = next(s for s in subs if s.semantic["name"] == "PrintResult")
    params = print_result.semantic["params"]
    assert len(params) == 1
    assert params[0]["name"] == "val"
    assert params[0]["type"] == "Double"


def test_sub_no_params(call_graph_tree):
    subs = call_graph_tree.root_node.descendants_of_type("subStmt")
    main = next(s for s in subs if s.semantic["name"] == "Main")
    assert main.semantic["params"] == []


# ── callers ───────────────────────────────────────────────────────────────────

def test_add_has_caller_main(call_graph_tree):
    funcs = call_graph_tree.root_node.descendants_of_type("functionStmt")
    add = next(f for f in funcs if f.semantic["name"] == "Add")
    caller_names = [c["name"] for c in add.semantic["callers"]]
    assert "Main" in caller_names


def test_caller_has_line_number(call_graph_tree):
    funcs = call_graph_tree.root_node.descendants_of_type("functionStmt")
    add = next(f for f in funcs if f.semantic["name"] == "Add")
    main_call = next(c for c in add.semantic["callers"] if c["name"] == "Main")
    assert isinstance(main_call["line"], int)
    assert main_call["line"] >= 0


def test_print_result_has_caller_main(call_graph_tree):
    subs = call_graph_tree.root_node.descendants_of_type("subStmt")
    pr = next(s for s in subs if s.semantic["name"] == "PrintResult")
    caller_names = [c["name"] for c in pr.semantic["callers"]]
    assert "Main" in caller_names


def test_main_has_no_callers(call_graph_tree):
    subs = call_graph_tree.root_node.descendants_of_type("subStmt")
    main = next(s for s in subs if s.semantic["name"] == "Main")
    assert main.semantic["callers"] == []


def test_call_graph_inversion(call_graph_tree):
    # Derive callees of Main by inverting callers lists
    procs = call_graph_tree.root_node.descendants_of_type("subStmt", "functionStmt")
    callees_of_main = {
        p.semantic["name"]
        for p in procs
        if any(c["name"] == "Main" for c in p.semantic["callers"])
    }
    assert callees_of_main == {"Add", "PrintResult"}
