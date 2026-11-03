from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MATHAGENT_",
        extra="ignore",
    )

    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    # Prefer a reasoner for formal planning when set (e.g. deepseek-reasoner)
    formal_model: str = ""
    temperature: float = 0.0
    max_turns: int = 8
    code_timeout_sec: float = 8.0
    max_output_chars: int = 4000

    @property
    def resolved_formal_model(self) -> str:
        return self.formal_model or self.model


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
