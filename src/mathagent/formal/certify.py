"""Cheap certificates for subgoals — SymPy / finite check / optional Lean."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import sympy as sp

from mathagent.formal.lean_check import LeanCheckResult, check_lean_snippet, lean_available
from mathagent.tools.registry import dispatch_tool
from mathagent.tools.sympy_ops import normalize_expr


@dataclass
class CertificateResult:
    ok: bool
    method: str
    detail: str


def _sympify(expr: str) -> Any:
    return sp.sympify(normalize_expr(expr), evaluate=True)


def _positive_symbols(statement: str) -> set[str]:
    """Extract symbol names constrained to be positive from informal statement text."""
    names: set[str] = set()
    # "x, y > 0" / "x,y>0" / "for positive reals x and y"
    for m in re.finditer(
        r"\b([a-zA-Z](?:\s*,\s*[a-zA-Z])*)\s*(?:>|≥)\s*0",
        statement,
    ):
        for part in m.group(1).split(","):
            names.add(part.strip())
    if re.search(r"positive\s+reals?\s+[a-zA-Z]", statement, re.I):
        m = re.search(r"positive\s+reals?\s+([a-zA-Z])(?:\s+and\s+([a-zA-Z]))?", statement, re.I)
        if m:
            names.add(m.group(1))
            if m.group(2):
                names.add(m.group(2))
    return {n for n in names if n}


def _check_nonneg_poly(expr: str, positive_vars: set[str] | None = None) -> CertificateResult:
    """Heuristic: expand and see if expression is a square / sum of squares-ish / identically >=0."""
    positive_vars = positive_vars or set()
    try:
        e = sp.simplify(sp.expand(_sympify(expr)))
    except Exception as exc:  # noqa: BLE001
        return CertificateResult(False, "sympy", f"parse error: {exc}")

    if e == 0:
        return CertificateResult(True, "sympy", "identically 0")
    if e.is_number:
        ok = bool(e.is_real and e >= 0)
        return CertificateResult(ok, "sympy", f"constant {e}")

    try:
        if sp.ask(sp.Q.nonnegative(e)) is True:
            return CertificateResult(True, "sympy", f"nonnegative: {e}")
    except Exception:
        pass

    try:
        factored = sp.factor(e)
        if factored.is_Pow and factored.exp % 2 == 0:
            return CertificateResult(True, "sympy", f"even power: {factored}")
        terms = sp.Add.make_args(sp.expand(e))
        if terms and all(
            (t.is_Pow and t.exp % 2 == 0)
            or (t.is_Mul and any(f.is_Pow and f.exp % 2 == 0 for f in sp.Mul.make_args(t)))
            or (t.is_number and t >= 0)
            for t in terms
        ):
            if all(c >= 0 for c in sp.Poly(sp.expand(e)).coeffs()):
                return CertificateResult(True, "sympy", f"nonneg coeffs poly: {e}")
    except Exception:
        pass

    free = list(e.free_symbols)
    if not free:
        return CertificateResult(False, "sympy", f"could not certify {e}")
    import random

    bad = 0
    for _ in range(64):
        subs = {}
        for s in free:
            if s.name in positive_vars:
                subs[s] = random.uniform(1e-3, 5)
            else:
                subs[s] = random.uniform(-3, 3)
        try:
            val = complex(e.evalf(subs=subs))
            if abs(val.imag) > 1e-8 or val.real < -1e-6:
                bad += 1
        except Exception:
            bad += 1
    domain = f"pos={sorted(positive_vars)}" if positive_vars else "reals"
    if bad == 0:
        return CertificateResult(True, "sympy_sample", f"64 samples >=0 on {domain} for {e}")
    return CertificateResult(False, "sympy", f"failed samples={bad}/64 on {domain} expr={e}")


def certify_algebraic_claim(hint: str, statement: str = "") -> CertificateResult:
    """
    Accept hints like:
      - "(x-y)**2"                         (show >= 0)
      - "a**2+b**2-2*a*b"                   (show >= 0)
      - "(x+y)**2 = 4*x*y + (x-y)**2"       (identity)
      - "(x+y)**2 >= 4*x*y"                 → check (x+y)**2 - 4xy >= 0
    """
    hint = hint.strip()
    if not hint:
        return CertificateResult(False, "sympy", "empty hint")
    pos = _positive_symbols(statement)

    if re.search(r"(>=|≥)", hint):
        left, right = re.split(r">=|≥", hint, maxsplit=1)
        return _check_nonneg_poly(f"({left})-({right})", pos)
    if re.search(r"(<=|≤)", hint):
        left, right = re.split(r"<=|≤", hint, maxsplit=1)
        return _check_nonneg_poly(f"({right})-({left})", pos)
    if "=" in hint and not hint.lstrip().startswith("Eq"):
        left, right = hint.split("=", 1)
        try:
            diff = sp.simplify(_sympify(left) - _sympify(right))
            ok = diff == 0
            return CertificateResult(ok, "sympy", f"identity diff={diff}")
        except Exception as exc:  # noqa: BLE001
            return CertificateResult(False, "sympy", str(exc))

    return _check_nonneg_poly(hint, pos)


def certify_subgoal(subgoal: dict[str, Any], solver_payload: dict[str, Any] | None = None) -> CertificateResult:
    certify = (subgoal.get("certify") or "manual").lower()
    solver_payload = solver_payload or {}
    cert = solver_payload.get("certificate") or {}

    def _clean_sympy_hint() -> str:
        candidates = [
            subgoal.get("sympy_hint"),
            cert.get("payload") if cert.get("type") in {"sympy", "text"} else None,
        ]
        junk = ("import ", "theorem", "example", ":= by", "def ", "print(", "\n")
        for c in candidates:
            if not c:
                continue
            s = str(c).strip()
            if any(j in s for j in junk):
                continue
            if len(s) > 240:
                continue
            return s
        return ""

    stmt = str(subgoal.get("statement", ""))

    # Prefer hard Lean when requested AND available; fall back to SymPy on failure.
    if (certify == "lean" or cert.get("type") == "lean") and lean_available():
        code = ""
        payload = str(cert.get("payload") or "")
        sketch = str(subgoal.get("lean_sketch") or "")
        for candidate in (payload, sketch):
            if candidate and "theorem" in candidate and len(candidate) > 20:
                code = candidate
                break
            if candidate and "example" in candidate and len(candidate) > 20:
                code = candidate
                break
            if candidate and ":=" in candidate:
                code = candidate
                break
        if code:
            lean_res: LeanCheckResult = check_lean_snippet(code)
            if lean_res.ok:
                return CertificateResult(True, "lean", lean_res.stderr or lean_res.stdout or "ok")
            # keep lean error but try sympy fallback below
            lean_err = lean_res.stderr or lean_res.stdout
        else:
            lean_err = "no usable lean sketch/payload"

        hint = _clean_sympy_hint()
        if hint:
            sym = certify_algebraic_claim(hint, statement=stmt)
            if sym.ok:
                return CertificateResult(True, f"sympy_fallback", f"{sym.detail} | lean_err={lean_err[:200]}")
        return CertificateResult(False, "lean", lean_err)

    if certify in {"lean", "sympy"} or cert.get("type") in {"lean", "sympy", "text"}:
        hint = _clean_sympy_hint()
        if hint and cert.get("type") != "python":
            return certify_algebraic_claim(hint, statement=stmt)
        if certify == "lean" and not lean_available():
            m = re.search(r"([a-zA-Z0-9_\+\-\*/\(\)\s\^]+)\s*(>=|≥)\s*0", stmt)
            if m:
                return _check_nonneg_poly(m.group(1).replace("^", "**"))
            return CertificateResult(
                False,
                "lean_unavailable",
                "lean not installed; provide sympy_hint for cheap certification",
            )

    if certify == "finite_check" or cert.get("type") == "python":
        code = cert.get("payload") or subgoal.get("sympy_hint") or ""
        if not code:
            return CertificateResult(False, "python", "missing python payload")
        out = dispatch_tool("run_python", {"code": code})
        ok = out.startswith("OK") and (
            "True" in out or "passed" in out.lower() or "result = True" in out
        )
        return CertificateResult(ok, "python", out)

    status = (solver_payload.get("status") or "").lower()
    return CertificateResult(
        status == "proved",
        "manual",
        solver_payload.get("informal_proof") or "no hard certificate",
    )
