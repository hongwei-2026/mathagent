from mathagent.eval.grader import extract_final_answer, math_equal
from mathagent.tools.registry import dispatch_tool


def test_extract_final_answer():
    assert extract_final_answer("steps...\nFINAL_ANSWER: 12") == "12"
    assert extract_final_answer(r"thus \boxed{7}") == "7"


def test_math_equal_numeric_and_fraction():
    assert math_equal("346", "346")
    assert math_equal("0.9", "9/10")
    assert math_equal("6", "6.0")


def test_calculator_and_solve():
    assert "346" in dispatch_tool("calculator", {"expression": "17*19+23"})
    out = dispatch_tool("sympy_solve", {"equations": "2*x + 5 = 17", "variables": "x"})
    assert "6" in out


def test_run_python_binomial():
    out = dispatch_tool(
        "run_python",
        {"code": "result = sp.binomial(10, 3)\nprint(result)"},
    )
    assert "120" in out
