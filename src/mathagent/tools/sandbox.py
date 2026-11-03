"""Restricted Python execution for math code (ToRA-style interpreter)."""

from __future__ import annotations

import ast
import io
import multiprocessing as mp
import traceback
from contextlib import redirect_stdout
from typing import Any


FORBIDDEN_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.With,
    ast.AsyncWith,
    ast.AsyncFunctionDef,
    ast.AsyncFor,
    ast.ClassDef,
    ast.Global,
    ast.Nonlocal,
    ast.Lambda,
)


def _validate_ast(code: str) -> None:
    tree = ast.parse(code, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            raise ValueError(f"Disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("Dunder attribute access is not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise ValueError("Dunder names are not allowed")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"eval", "exec", "compile", "open", "__import__", "input"}:
                raise ValueError(f"Call to {node.func.id} is not allowed")


def _build_globals() -> dict[str, Any]:
    import math

    import numpy as np
    import sympy as sp

    safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "pow": pow,
        "print": print,
        "range": range,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
    }
    return {
        "__builtins__": safe_builtins,
        "math": math,
        "np": np,
        "numpy": np,
        "sp": sp,
        "sympy": sp,
        "symbols": sp.symbols,
        "Symbol": sp.Symbol,
        "Eq": sp.Eq,
        "solve": sp.solve,
        "simplify": sp.simplify,
        "expand": sp.expand,
        "factor": sp.factor,
        "diff": sp.diff,
        "integrate": sp.integrate,
        "limit": sp.limit,
        "summation": sp.summation,
        "Matrix": sp.Matrix,
        "Rational": sp.Rational,
        "Integer": sp.Integer,
        "Float": sp.Float,
        "N": sp.N,
        "pi": sp.pi,
        "E": sp.E,
        "oo": sp.oo,
        "sin": sp.sin,
        "cos": sp.cos,
        "tan": sp.tan,
        "log": sp.log,
        "exp": sp.exp,
        "sqrt": sp.sqrt,
        "factorial": sp.factorial,
        "binomial": sp.binomial,
        "gcd": sp.gcd,
        "lcm": sp.lcm,
        "floor": sp.floor,
        "ceiling": sp.ceiling,
    }


def _worker(code: str, queue: mp.Queue, max_chars: int) -> None:
    try:
        _validate_ast(code)
        g = _build_globals()
        buf = io.StringIO()
        with redirect_stdout(buf):
            exec(compile(code, "<mathagent>", "exec"), g, g)  # noqa: S102
        out = buf.getvalue()
        if "result" in g and g["result"] is not None:
            out = (out + f"\nresult = {g['result']}").strip()
        if not out.strip():
            # last expression fallback already handled; provide hint
            out = "(no stdout; assign to `result` or use print())"
        queue.put({"ok": True, "output": out[-max_chars:]})
    except Exception:
        queue.put({"ok": False, "output": traceback.format_exc()[-max_chars:]})


def run_python(code: str, timeout_sec: float = 8.0, max_chars: int = 4000) -> str:
    """Run math Python in a child process with a hard timeout."""
    queue: mp.Queue = mp.Queue()
    proc = mp.Process(target=_worker, args=(code, queue, max_chars))
    proc.start()
    proc.join(timeout_sec)
    if proc.is_alive():
        proc.terminate()
        proc.join(1)
        return f"Error: execution timed out after {timeout_sec}s"
    if queue.empty():
        return "Error: no result from sandbox"
    payload = queue.get()
    prefix = "OK:\n" if payload["ok"] else "Error:\n"
    return prefix + str(payload["output"])
