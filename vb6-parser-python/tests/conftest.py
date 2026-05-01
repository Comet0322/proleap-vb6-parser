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


@pytest.fixture(scope="module")
def hello_world_tree():
    return Parser().parse(HELLO_WORLD)


@pytest.fixture(scope="module")
def function_module_tree():
    return Parser().parse(MODULE_WITH_FUNCTION)
