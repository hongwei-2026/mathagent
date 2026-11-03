#!/usr/bin/env python
"""Offline smoke test for SymPy / sandbox tools (no API key)."""

from mathagent.eval.grader import extract_final_answer, math_equal
from mathagent.tools.registry import dispatch_tool


def main() -> None:
    cases = [
        ("calculator", {"expression": "17*19+23"}, "346"),
        ("sympy_eval", {"expression": "(3/4)/(5/6)"}, "9/10"),
        ("sympy_solve", {"equations": "2*x+5=17", "variables": "x"}, "6"),
        ("sympy_solve", {"equations": "x+y=10; x-y=2", "variables": "x,y"}, "x"),
        ("run_python", {"code": "result = sp.binomial(10, 3)\nprint(result)"}, "120"),
    ]
    for name, args, expect in cases:
        out = dispatch_tool(name, args)
        print(f"{name}: {out}")
        assert "Error" not in out.splitlines()[0] or "OK" in out, out

    assert math_equal("9/10", "0.9")
    assert math_equal(extract_final_answer("blah\nFINAL_ANSWER: 42"), "42")
    print("smoke ok")


if __name__ == "__main__":
    main()
