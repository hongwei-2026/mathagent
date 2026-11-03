"""Optional Lean 4 verifier. Degrades gracefully when Lean is not installed."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LeanCheckResult:
    available: bool
    ok: bool
    stdout: str
    stderr: str
    path: str | None = None


def lean_available() -> bool:
    return shutil.which("lean") is not None


def check_lean_snippet(code: str, timeout_sec: float = 30.0) -> LeanCheckResult:
    """
    Try `lean --stdin` / temp file check.
    Without a lake project + mathlib this only catches syntax / kernel errors
    on self-contained snippets — still useful as a hard filter.
    """
    if not lean_available():
        return LeanCheckResult(
            available=False,
            ok=False,
            stdout="",
            stderr="lean not found on PATH; install Lean 4 to enable hard verification",
        )

    with tempfile.TemporaryDirectory(prefix="mathagent_lean_") as td:
        path = Path(td) / "Sketch.lean"
        path.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["lean", str(path)],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            return LeanCheckResult(
                available=True,
                ok=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                path=str(path),
            )
        except subprocess.TimeoutExpired:
            return LeanCheckResult(
                available=True,
                ok=False,
                stdout="",
                stderr=f"lean timed out after {timeout_sec}s",
                path=str(path),
            )
