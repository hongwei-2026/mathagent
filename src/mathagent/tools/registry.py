from __future__ import annotations

from typing import Any, Callable

from mathagent.config import get_settings
from mathagent.tools.sandbox import run_python
from mathagent.tools.sympy_ops import calculator, sympy_eval, sympy_simplify, sympy_solve


def _tool(
    name: str,
    description: str,
    parameters: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _tool(
        "run_python",
        "Execute a short Python program for math. sympy/numpy preloaded as sp/np. "
        "Print results or assign to variable `result`. No imports allowed.",
        {"code": {"type": "string", "description": "Python source code"}},
        ["code"],
    ),
    _tool(
        "sympy_solve",
        "Solve algebraic equation(s) with SymPy.",
        {
            "equations": {
                "type": "string",
                "description": "Equation(s), e.g. 'x**2-4=0' or 'x+y=3; x-y=1'",
            },
            "variables": {
                "type": "string",
                "description": "Comma-separated unknowns, default 'x'",
            },
        },
        ["equations"],
    ),
    _tool(
        "sympy_simplify",
        "Simplify a symbolic expression.",
        {"expression": {"type": "string"}},
        ["expression"],
    ),
    _tool(
        "sympy_eval",
        "Evaluate an expression; set numeric=true for floating output.",
        {
            "expression": {"type": "string"},
            "numeric": {"type": "boolean", "description": "If true, return N(expr)"},
        },
        ["expression"],
    ),
    _tool(
        "calculator",
        "Evaluate a safe arithmetic / closed-form expression.",
        {"expression": {"type": "string"}},
        ["expression"],
    ),
]


def dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    settings = get_settings()
    handlers: dict[str, Callable[..., str]] = {
        "run_python": lambda **kw: run_python(
            kw["code"],
            timeout_sec=settings.code_timeout_sec,
            max_chars=settings.max_output_chars,
        ),
        "sympy_solve": lambda **kw: sympy_solve(
            kw["equations"], kw.get("variables", "x")
        ),
        "sympy_simplify": lambda **kw: sympy_simplify(kw["expression"]),
        "sympy_eval": lambda **kw: sympy_eval(
            kw["expression"], bool(kw.get("numeric", False))
        ),
        "calculator": lambda **kw: calculator(kw["expression"]),
    }
    if name not in handlers:
        return f"Error: unknown tool '{name}'"
    try:
        return handlers[name](**arguments)
    except Exception as exc:  # noqa: BLE001 — surface to agent for self-correction
        return f"Error: {type(exc).__name__}: {exc}"
