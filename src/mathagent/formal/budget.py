"""Token / attempt budgets — EconProver-style cost control."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Budget:
    max_tokens: int = 12_000
    max_llm_calls: int = 16
    max_repair: int = 2
    max_direct_samples: int = 3
    max_depth: int = 4
    used_tokens: int = 0
    used_calls: int = 0
    log: list[str] = field(default_factory=list)

    def can_call(self, est_tokens: int = 800) -> bool:
        return (
            self.used_calls < self.max_llm_calls
            and self.used_tokens + est_tokens <= self.max_tokens
        )

    def record(self, label: str, tokens: int = 0) -> None:
        self.used_calls += 1
        self.used_tokens += max(tokens, 0)
        self.log.append(
            f"{label} calls={self.used_calls}/{self.max_llm_calls} "
            f"tok≈{self.used_tokens}/{self.max_tokens}"
        )

    @property
    def exhausted(self) -> bool:
        return not self.can_call(1)
