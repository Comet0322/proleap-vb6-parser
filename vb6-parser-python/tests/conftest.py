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

# Module where Main calls Add and PrintResult — exercises params + callers
CALL_GRAPH_MODULE = b"""Public Function Add(x As Double, y As Double) As Double
    Add = x + y
End Function

Private Sub PrintResult(val As Double)
    Debug.Print val
End Sub

Public Sub Main()
    Dim r As Double
    r = Add(1.0, 2.0)
    PrintResult r
End Sub
"""


@pytest.fixture(scope="module")
def hello_world_tree():
    return Parser().parse(HELLO_WORLD)


@pytest.fixture(scope="module")
def function_module_tree():
    return Parser().parse(MODULE_WITH_FUNCTION)


@pytest.fixture(scope="module")
def call_graph_tree():
    return Parser().parse(CALL_GRAPH_MODULE, module_name="CallGraph")
