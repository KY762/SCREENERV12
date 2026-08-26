"""The candidate pool.

Not tests of whether these are good stocks -- that is unknowable and not the
pool's job. Tests that the pool has the properties it was assembled for.
"""

from __future__ import annotations

from screener.universe.candidates import (
    MARKET_CONTEXT,
    TRADING_CANDIDATES,
    all_symbols,
    sector_map,
    sector_of,
    trading_symbols,
)


def test_no_symbol_appears_in_two_sectors():
    """A duplicate would be counted twice against the per-sector position cap,
    quietly allowing more correlated exposure than the limit intends."""
    seen: dict[str, str] = {}
    for sector, tickers in TRADING_CANDIDATES.items():
        for ticker in tickers:
            assert ticker not in seen, f"{ticker} in both {seen.get(ticker)} and {sector}"
            seen[ticker] = sector


def test_context_symbols_are_not_trading_candidates():
    """SPY is the benchmark and XLE is a rotation input. Screening them as
    candidates would rank the market against itself."""
    assert not set(MARKET_CONTEXT) & set(trading_symbols())


def test_the_pool_spreads_across_sectors():
    """Concentrated in one sector, the two-per-sector limit stops binding and
    positions correlate far more than their count suggests."""
    assert len(TRADING_CANDIDATES) >= 8
    largest = max(len(t) for t in TRADING_CANDIDATES.values())
    assert largest / len(trading_symbols()) < 0.20


def test_the_pool_is_large_enough_to_screen_from():
    """After liquidity, trend and tradeability filters, most of any pool is
    excluded on a given day. A pool of thirty leaves nothing to choose from."""
    assert len(trading_symbols()) >= 100


def test_all_symbols_includes_context_and_deduplicates():
    combined = all_symbols()
    assert set(MARKET_CONTEXT) <= set(combined)
    assert len(combined) == len(set(combined))


def test_a_benchmark_is_present_for_relative_strength():
    """Every relative-strength calculation needs it; without it H1 and H5
    cannot run at all."""
    assert "SPY" in MARKET_CONTEXT


def test_sector_lookup_works_both_ways():
    ticker = TRADING_CANDIDATES["Energy"][0]
    assert sector_of(ticker) == "Energy"
    assert sector_of(ticker.lower()) == "Energy"
    assert sector_of("SPY") is None
    assert sector_map()[ticker] == "Energy"


def test_the_small_cap_tier_can_be_excluded():
    """Ingesting 265 symbols on a rate-limited free tier takes hours. Someone
    starting out should be able to load the core pool first."""
    from screener.universe.candidates import SMALL_CAP_CANDIDATES

    with_small = trading_symbols(include_small_caps=True)
    without = trading_symbols(include_small_caps=False)

    assert len(with_small) > len(without)
    assert set(without) < set(with_small)
    assert sum(len(t) for t in SMALL_CAP_CANDIDATES.values()) > 100


def test_no_symbol_is_duplicated_across_the_two_tiers():
    """A duplicate would be counted twice against the per-sector cap."""
    from screener.universe.candidates import (
        SMALL_CAP_CANDIDATES,
        TRADING_CANDIDATES,
    )

    core = {t for ts in TRADING_CANDIDATES.values() for t in ts}
    small = {t for ts in SMALL_CAP_CANDIDATES.values() for t in ts}
    assert not core & small


def test_sector_lookup_covers_the_small_cap_tier():
    from screener.universe.candidates import SMALL_CAP_CANDIDATES

    ticker = SMALL_CAP_CANDIDATES["Restaurants"][0]
    assert sector_of(ticker) == "Restaurants"
    assert ticker in sector_map()
