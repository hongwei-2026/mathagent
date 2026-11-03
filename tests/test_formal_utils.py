from mathagent.formal.certify import certify_subgoal
from mathagent.formal.json_util import extract_json
from mathagent.formal.lean_check import lean_available


def test_extract_json_fenced():
    raw = 'Sure.\n```json\n{"a": 1, "b": "x"}\n```\n'
    assert extract_json(raw)["a"] == 1


def test_certify_sympy_identity():
    sg = {"certify": "sympy", "sympy_hint": "(x+y)**2 = x**2 + 2*x*y + y**2"}
    res = certify_subgoal(sg, {"status": "proved", "certificate": {"type": "sympy", "payload": ""}})
    assert res.ok, res.detail


def test_certify_sympy_inequality():
    sg = {"certify": "sympy", "sympy_hint": "(x+y)**2 >= 4*x*y"}
    res = certify_subgoal(sg, {})
    assert res.ok, res.detail


def test_certify_lean_fallback_to_sympy_hint():
    sg = {
        "certify": "lean",
        "lean_sketch": "theorem t : True := by trivial",
        "sympy_hint": "(a-b)**2",
        "statement": "For all real a,b, (a-b)^2 >= 0",
    }
    res = certify_subgoal(sg, {"status": "proved", "certificate": {"type": "lean", "payload": "theorem"}})
    assert res.ok, res.detail



def test_lean_available_bool():
    assert isinstance(lean_available(), bool)
