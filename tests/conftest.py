import pandas as pd
import pytest


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
