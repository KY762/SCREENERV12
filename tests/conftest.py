import pandas as pd
import pytest

# Every credential the app reads. Blanked for every test so that whatever sits
# in a developer's .env cannot change what the suite does.
PROVIDER_CREDENTIALS = (
    "TIINGO_API_KEY",
    "ALPACA_API_KEY_ID",
    "ALPACA_API_SECRET_KEY",
    "POLYGON_API_KEY",
    "FRED_API_KEY",
    "ANTHROPIC_API_KEY",
)


@pytest.fixture(autouse=True)
def no_ambient_credentials(monkeypatch):
    """Stop a real .env from leaking into the test suite.

    pydantic-settings reads the project .env, so a machine with a live
    TIINGO_API_KEY ran a different code path from one without. `ingest`
    resolves provider "auto" to Tiingo whenever a key exists
    (`cli.py` line 129), so the end-to-end tests substituted a fake Alpaca
    provider and then went to the real network anyway -- passing on a clean
    checkout, hanging or rate-limiting on the operator's own machine.

    Blanking rather than deleting is deliberate: `monkeypatch.delenv` removes
    only the process variable and lets the .env value take its place, which is
    exactly the bug `test_config_warns_when_only_alpaca_is_available` hit. An
    empty SecretStr is falsy, so every `has_*_credentials` property reports
    False and each test states its own requirements.
    """
    for name in PROVIDER_CREDENTIALS:
        monkeypatch.setenv(name, "")

    from screener import config

    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def bars() -> pd.DataFrame:
    """Six-bar fixture. Every golden value in the indicator tests is hand-computed
    from exactly this data -- see the arithmetic in each test's docstring."""
    return pd.DataFrame(
        {
            "open":   [100.0, 103.0, 107.0, 105.0, 111.0, 110.0],
            "high":   [105.0, 108.0, 110.0, 112.0, 115.0, 113.0],
            "low":    [ 98.0, 102.0, 104.0, 103.0, 109.0, 106.0],
            "close":  [103.0, 107.0, 105.0, 111.0, 110.0, 112.0],
            "volume": [1000.0, 1200.0, 800.0, 1500.0, 900.0, 1100.0],
        },
        index=pd.date_range("2024-01-02", periods=6, freq="B"),
    )
