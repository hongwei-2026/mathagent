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
    temperature: float = 0.0
    max_turns: int = 8
    code_timeout_sec: float = 8.0
    max_output_chars: int = 4000


@lru_cache
def get_settings() -> Settings:
    return Settings()
