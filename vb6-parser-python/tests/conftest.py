import pytest

HELLO_WORLD = b"Private Sub Command1_Click ()\n   Text1.Text = \"Hello, world!\"\nEnd Sub\n"

MODULE_WITH_FUNCTION = b"""Public Function Add(x As Integer, y As Integer) As Integer
    Add = x + y
End Function

Private Sub Greet()
    MsgBox "Hello"
End Sub
"""

@pytest.fixture
def hello_world_source():
    return HELLO_WORLD

@pytest.fixture
def module_with_function_source():
    return MODULE_WITH_FUNCTION
