"""Resolve Lean 4 installation that lives on D: (never force C:\\Users\\...\\.elan)."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ELAN_HOME = Path("D:/lean/elan")
DEFAULT_WORKSPACE = Path("D:/mathagent/lean_workspace")
DEFAULT_TMP = Path("D:/lean/tmp")
DEFAULT_CACHE = Path("D:/lean/cache")


def lean_elan_home() -> Path:
    return Path(os.environ.get("MATHAGENT_LEAN_HOME") or os.environ.get("ELAN_HOME") or DEFAULT_ELAN_HOME)


def lean_workspace() -> Path:
    return Path(os.environ.get("MATHAGENT_LEAN_WORKSPACE") or DEFAULT_WORKSPACE)


def lean_bin_dir() -> Path:
    return lean_elan_home() / "bin"


def lean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for subprocesses: force D: elan/tmp/cache onto PATH."""
    env = os.environ.copy()
    elan = str(lean_elan_home())
    tmp = str(Path(os.environ.get("MATHAGENT_LEAN_TMP") or DEFAULT_TMP))
    cache = str(Path(os.environ.get("MATHAGENT_LEAN_CACHE") or DEFAULT_CACHE))
    Path(tmp).mkdir(parents=True, exist_ok=True)
    Path(cache).mkdir(parents=True, exist_ok=True)

    env["ELAN_HOME"] = elan
    env["MATHAGENT_LEAN_HOME"] = elan
    env["MATHAGENT_LEAN_WORKSPACE"] = str(lean_workspace())
    env["TMP"] = tmp
    env["TEMP"] = tmp
    env["XDG_CACHE_HOME"] = cache
    # Prefer D: home for any tools that expand ~
    env.setdefault("HOME", "D:/lean/home")

    bin_dir = str(lean_bin_dir())
    path = env.get("Path") or env.get("PATH") or ""
    if bin_dir.lower() not in path.lower():
        env["Path"] = bin_dir + os.pathsep + path
        env["PATH"] = env["Path"]

    if extra:
        env.update(extra)
    return env


def resolve_lean_exe() -> Path | None:
    candidates = [
        lean_bin_dir() / "lean.exe",
        lean_bin_dir() / "lean",
    ]
    for c in candidates:
        if c.exists():
            return c
    # elan shim
    shim = lean_bin_dir() / "elan.exe"
    if shim.exists():
        return lean_bin_dir() / "lean.exe"
    return None


def resolve_lake_exe() -> Path | None:
    for name in ("lake.exe", "lake"):
        p = lean_bin_dir() / name
        if p.exists():
            return p
    return None
