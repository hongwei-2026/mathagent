"""Detect OpenAI-compatible local servers (Ollama) for zero-API proving."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass
class LocalLLMStatus:
    available: bool
    base_url: str
    models: list[str]
    preferred: str | None
    detail: str


PREFERRED_LOCAL = (
    "yothgewalt/DeepSeek-Prover-V2-7B-GGUF:Q4_K_M",
    "deepseek-prover-v2-7b",
    "goedel-prover",
    "qwen2.5:7b",
    "qwen2.5:14b",
)


def ollama_base() -> str:
    return os.environ.get("MATHAGENT_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")


def probe_ollama(timeout: float = 2.0) -> LocalLLMStatus:
    base = ollama_base()
    try:
        r = httpx.get(f"{base}/api/tags", timeout=timeout)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        preferred = None
        for cand in PREFERRED_LOCAL:
            for m in models:
                if cand.lower() in m.lower() or m.lower() in cand.lower():
                    preferred = m
                    break
            if preferred:
                break
        if preferred is None and models:
            preferred = models[0]
        return LocalLLMStatus(
            available=True,
            base_url=f"{base}/v1",
            models=models,
            preferred=preferred,
            detail=f"{len(models)} model(s)",
        )
    except Exception as exc:  # noqa: BLE001
        return LocalLLMStatus(
            available=False,
            base_url=f"{base}/v1",
            models=[],
            preferred=None,
            detail=str(exc),
        )
