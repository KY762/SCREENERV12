"""Survivorship exposure: how often a rule buys the population that is missing.

The failures are absent from the data, so a rule that buys recent losers has
had exactly those losses removed from its backtest. These tests pin the
measurement that says how much each hypothesis is exposed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
import pytest

from screener.diagnostics.survivorship import (
    RANDOM_DECILE_SHARE,
    measure,
    trailing_return_deciles,
)


@dataclass
class Sig:
    ticker: str
    signal_date: date


def ladder(n_symbols: int = 20, days: int = 60) -> dict[str, pd.DataFrame]:
    """Symbol k compounds at k basis points a day, so on every date S00 is the
    worst trailing performer and S19 the best -- a known, fixed ordering."""
    index = pd.bdate_range("2020-01-01", periods=days)
    out = {}
    for k in range(n_symbols):
        close = 100.0 * (1.0 + (k - 10) / 1000.0) ** np.arange(days)
        out[f"S{k:02d}"] = pd.DataFrame({"close": close}, index=index)
    return out


WINDOW = dict(start=date(2020, 1, 1), end=date(2030, 1, 1))


def test_a_rule_that_buys_the_biggest_losers_is_fully_exposed():
    bars = ladder()
    deciles = trailing_return_deciles(bars, lookback=5)
    dates = [d.date() for d in bars["S00"].index[10:]]

    exposure = measure("loser", [Sig("S00", d) for d in dates], deciles,
                       lookback=5, **WINDOW)

    assert exposure.bottom_decile == 1.0
    assert exposure.relative_to_random == pytest.approx(10.0)


def test_a_rule_that_buys_the_biggest_winners_never_touches_distress():
    """The momentum case. If H1 or H5 look like this, their results are far
    less damaged by the missing failures than the blanket caveat implies."""
    bars = ladder()
    deciles = trailing_return_deciles(bars, lookback=5)
    dates = [d.date() for d in bars["S19"].index[10:]]

    exposure = measure("winner", [Sig("S19", d) for d in dates], deciles,
                       lookback=5, **WINDOW)

    assert exposure.bottom_decile == 0.0
    assert exposure.top_decile == 1.0


def test_buying_every_name_lands_at_the_random_rate():
    bars = ladder()
    deciles = trailing_return_deciles(bars, lookback=5)
    d = bars["S00"].index[20].date()

    exposure = measure("all", [Sig(t, d) for t in bars], deciles, lookback=5, **WINDOW)

    assert exposure.bottom_decile == pytest.approx(RANDOM_DECILE_SHARE)


def test_the_decile_on_a_date_does_not_depend_on_anything_after_it():
    """Non-negotiable #1. A signal completes at its bar's close, so its rank
    may use that close and nothing later. Truncating the future must leave
    every past decile unchanged."""
    bars = ladder(days=60)
    full = trailing_return_deciles(bars, lookback=5)
    cut = trailing_return_deciles(
        {t: f.iloc[:30] for t, f in bars.items()}, lookback=5
    )

    pd.testing.assert_frame_equal(full.iloc[:30], cut)


def test_too_little_history_is_unranked_not_distressed():
    """A candidate with no trailing return that day has an unknown rank.
    Filing it in the bottom decile would invent the exact exposure being
    measured."""
    bars = ladder()
    deciles = trailing_return_deciles(bars, lookback=5)
    first_day = bars["S00"].index[0].date()   # no 5-day history yet

    exposure = measure("early", [Sig("S00", first_day)], deciles, lookback=5, **WINDOW)

    assert exposure.ranked == 0
    assert exposure.unranked == 1
    assert np.isnan(exposure.bottom_decile)


def test_signals_outside_the_window_are_not_counted():
    """The measurement has to cover the same window the results do."""
    bars = ladder()
    deciles = trailing_return_deciles(bars, lookback=5)
    dates = [d.date() for d in bars["S00"].index[10:]]

    exposure = measure("loser", [Sig("S00", d) for d in dates], deciles,
                       lookback=5, start=date(2019, 1, 1), end=date(2019, 12, 31))

    assert exposure.candidates == 0


def test_a_non_positive_lookback_is_refused():
    with pytest.raises(ValueError, match="lookback"):
        trailing_return_deciles(ladder(), lookback=0)
