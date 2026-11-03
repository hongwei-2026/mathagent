"""Lean 4 verifier pinned to D:\\lean + D:\\mathagent\\lean_workspace (no C: pile-up)."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from mathagent.formal.lean_env import (
    lean_env,
    lean_workspace,
    resolve_lake_exe,
    resolve_lean_exe,
)


@dataclass
class LeanCheckResult:
    available: bool
    ok: bool
    stdout: str
    stderr: str
    path: str | None = None


def lean_available() -> bool:
    exe = resolve_lean_exe()
    if exe is None:
        return False
    # elan shim may exist before toolchain is installed
    env = lean_env()
    try:
        proc = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env=env,
            check=False,
        )
        return proc.returncode == 0 and "Lean" in (proc.stdout + proc.stderr)
    except Exception:
        return False


def _strip_mathlib_imports(code: str) -> tuple[str, bool]:
    """Allow core-only checking when mathlib is not fetched yet."""
    had = bool(re.search(r"^\s*import\s+Mathlib", code, re.M | re.I))
    cleaned = re.sub(r"^\s*import\s+Mathlib[^\n]*\n?", "", code, flags=re.M | re.I)
    return cleaned, had


def check_lean_snippet(code: str, timeout_sec: float = 60.0) -> LeanCheckResult:
    """
    Write sketch into the D: lake workspace Scratch.lean and typecheck.

    Prefer `lake env lean Scratch.lean` so lean-toolchain is respected.
    Falls back to bare `lean` if lake is unavailable.
    """
    env = lean_env()
    lean_exe = resolve_lean_exe()
    lake_exe = resolve_lake_exe()
    if lean_exe is None and lake_exe is None:
        return LeanCheckResult(
            available=False,
            ok=False,
            stdout="",
            stderr=(
                "Lean not found under D:\\lean\\elan. "
                "Run scripts/setup_lean_d.ps1 after toolchain install."
            ),
        )

    ws = lean_workspace()
    ws.mkdir(parents=True, exist_ok=True)
    scratch = ws / "Scratch.lean"
    cleaned, stripped_mathlib = _strip_mathlib_imports(code)
    note = ""
    if stripped_mathlib:
        note = (
            "[mathagent] stripped `import Mathlib` for core-only check; "
            "install mathlib in lean_workspace for full sketches\n"
        )
        cleaned = note + cleaned
    scratch.write_text(cleaned, encoding="utf-8")

    try:
        if lake_exe is not None:
            cmd = [str(lake_exe), "env", "lean", str(scratch)]
            cwd = str(ws)
        else:
            cmd = [str(lean_exe), str(scratch)]
            cwd = str(ws)
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            env=env,
            cwd=cwd,
            check=False,
        )
        return LeanCheckResult(
            available=True,
            ok=proc.returncode == 0,
            stdout=proc.stdout,
            stderr=(note + proc.stderr).strip(),
            path=str(scratch),
        )
    except subprocess.TimeoutExpired:
        return LeanCheckResult(
            available=True,
            ok=False,
            stdout="",
            stderr=f"lean timed out after {timeout_sec}s",
            path=str(scratch),
        )
    except FileNotFoundError as exc:
        return LeanCheckResult(
            available=False,
            ok=False,
            stdout="",
            stderr=f"lean executable missing: {exc}",
            path=str(scratch),
        )


def lake_build(timeout_sec: float = 600.0) -> LeanCheckResult:
    """Build the D: workspace library."""
    lake_exe = resolve_lake_exe()
    if lake_exe is None:
        return LeanCheckResult(False, False, "", "lake not found under D:\\lean\\elan\\bin")
    ws = lean_workspace()
    try:
        proc = subprocess.run(
            [str(lake_exe), "build"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            env=lean_env(),
            cwd=str(ws),
            check=False,
        )
        return LeanCheckResult(
            available=True,
            ok=proc.returncode == 0,
            stdout=proc.stdout,
            stderr=proc.stderr,
            path=str(ws),
        )
    except subprocess.TimeoutExpired:
        return LeanCheckResult(True, False, "", f"lake build timed out after {timeout_sec}s", str(ws))
