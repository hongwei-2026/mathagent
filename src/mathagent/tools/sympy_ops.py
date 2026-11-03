"""Deterministic SymPy tools — perception vs execution split (Neuro-Symbolic pattern)."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


def normalize_expr(text: str) -> str:
    s = text.strip()
    if "=" in s and not s.lstrip().startswith("Eq"):
        # keep equations for solve; strip "f(x) =" wrappers for eval
        pass
    s = s.replace("^", "**")
    s = s.rstrip(".;")
    return s


def _parse(expr: str, local_dict: dict[str, Any] | None = None) -> Any:
    return parse_expr(
        normalize_expr(expr),
        transformations=TRANSFORMATIONS,
        local_dict=local_dict or {},
        evaluate=True,
    )


def sympy_eval(expression: str, numeric: bool = False) -> str:
    """Evaluate / simplify a single expression."""
    expr = _parse(expression)
    if numeric:
        return str(sp.N(expr))
    return str(sp.simplify(expr))


def sympy_simplify(expression: str) -> str:
    return str(sp.simplify(_parse(expression)))


def sympy_solve(equations: str, variables: str = "x") -> str:
    """
    Solve equation(s).

    equations: e.g. "x**2 - 4" or "Eq(x**2, 4)" or "x+y=3; x-y=1"
    variables: comma-separated, e.g. "x" or "x,y"
    """
    vars_ = [sp.Symbol(v.strip()) for v in variables.split(",") if v.strip()]
    local = {str(v): v for v in vars_}

    parts = re.split(r"[;\n]+", equations.strip())
    eqs = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "=" in part and not part.startswith("Eq"):
            left, right = part.split("=", 1)
            eqs.append(sp.Eq(_parse(left, local), _parse(right, local)))
        else:
            eqs.append(_parse(part, local))

    if len(eqs) == 1 and len(vars_) == 1:
        sol = sp.solve(eqs[0], vars_[0], dict=True)
    else:
        sol = sp.solve(eqs, vars_, dict=True)
    return str(sol)


def calculator(expression: str) -> str:
    """Safe arithmetic via SymPy (no builtins eval)."""
    expr = _parse(expression)
    val = sp.N(expr)
    # prefer exact if still rational-like
    simplified = sp.simplify(expr)
    if simplified.is_number and not simplified.is_Float:
        return str(simplified)
    return str(val)
