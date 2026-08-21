"""Configuration. Single source of truth for every environment-dependent value.

Secrets are read from the environment or a local ``.env`` and are never written
to logs, committed, or exposed to a frontend. ``.env`` is git-ignored from the
first commit of this repository.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- database -----------------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://screener:screener@localhost:5432/screener",
        description="SQLAlchemy URL. Tests override this with SQLite.",
    )

    # --- market data --------------------------------------------------------
    alpaca_api_key_id: SecretStr | None = None
    alpaca_api_secret_key: SecretStr | None = None
    alpaca_data_url: str = "https://data.alpaca.markets"
    alpaca_feed: str = Field(
        default="iex",
        description="'iex' on the free tier; 'sip' requires a paid subscription.",
    )

    # Tiingo. Deeper daily history than Alpaca's free tier, and it serves raw
    # and adjusted prices as separate fields -- which is what price_daily's
    # raw-storage policy requires.
    tiingo_api_key: SecretStr | None = None
    tiingo_base_url: str = "https://api.tiingo.com"

    # --- other providers ----------------------------------------------------
    fred_api_key: SecretStr | None = None
    sec_user_agent: str = Field(
        default="",
        description="SEC EDGAR requires a descriptive User-Agent with contact email.",
    )

    # --- ai -----------------------------------------------------------------
    anthropic_api_key: SecretStr | None = None

    # --- behaviour ----------------------------------------------------------
    request_timeout_seconds: float = 30.0
    max_retries: int = 4

    @property
    def has_alpaca_credentials(self) -> bool:
        return bool(self.alpaca_api_key_id and self.alpaca_api_secret_key)

    @property
    def has_tiingo_credentials(self) -> bool:
        return bool(self.tiingo_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
