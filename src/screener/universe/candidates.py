"""Candidate symbol pool, sized for a small account.

Why this exists
---------------
The original 51 symbols were mega-caps, chosen before anyone had computed what
a $10,000 account can actually size. Measured against the risk rules, most of
them fail: COST at $949 is two shares, AAPL is seven, and a name with ATR below
2% trips the concentration cap and quietly risks half of what the rule says.

That is a universe problem with a free fix -- trade something else -- and the
alternative, loosening the risk rules to accommodate expensive stocks, is the
exact move the platform exists to prevent.

What this list is and is NOT
----------------------------
It is a CANDIDATE POOL, not a screened universe. Prices and volatility drift,
and nothing here has been checked against today's market. The pool is
deliberately wide; the DATA decides what survives:

    screener ingest --symbols "$(screener universe candidates --plain)" --start 2010-01-01
    screener metrics build
    screener universe build
    screener universe tradeable --show good

Selection criteria for inclusion were liquidity, a price range where ten shares
is reachable at a 1% risk budget, and enough volatility that the concentration
cap does not bind. Sector spread matters too -- a pool concentrated in
semiconductors would make the two-per-sector limit meaningless and the
correlation between positions much higher than the position count suggests.

No claim is made that any of these is a good investment. They are instruments
this account can express a position in, which is a prerequisite, not a
recommendation.
"""

from __future__ import annotations

# Grouped by sector so the pool can be checked for concentration at a glance,
# and so the per-sector position limit has something to bite on.
TRADING_CANDIDATES: dict[str, tuple[str, ...]] = {
    "Semiconductors": (
        "AMD", "MU", "MRVL", "ON", "SWKS", "QRVO", "MCHP", "TER",
        "AMKR", "LSCC", "WOLF", "ENTG", "NXPI", "GFS",
    ),
    "Hardware & storage": (
        "INTC", "WDC", "STX", "NTAP", "HPQ", "DELL", "PSTG", "SMCI",
    ),
    "Software & internet": (
        "DDOG", "NET", "ZS", "OKTA", "TWLO", "DOCU", "ZM", "PATH",
        "GTLB", "CFLT", "BOX", "DBX", "PINS", "SNAP", "RBLX", "U",
    ),
    "Consumer discretionary": (
        "F", "GM", "CHWY", "ETSY", "EBAY", "CROX", "SKX", "ANF",
        "AEO", "URBN", "M", "KSS", "BBWI", "VFC", "RL", "GPS",
    ),
    "Travel & transport": (
        "AAL", "DAL", "UAL", "LUV", "JBLU", "CAR", "NCLH", "CCL", "RCL",
    ),
    "Energy": (
        "DVN", "APA", "OXY", "HAL", "SLB", "BKR", "CHRD", "RRC",
        "EQT", "AR", "PR", "CIVI",
    ),
    "Financials": (
        "SOFI", "ALLY", "KEY", "RF", "CFG", "HBAN", "FITB", "SYF",
        "LC", "UPST", "AFRM", "HOOD", "SCHW",
    ),
    "Health care": (
        "VTRS", "TEVA", "EXAS", "ILMN", "CRSP", "NTLA", "BEAM",
        "MRNA", "BNTX", "INCY", "HOLX", "BAX", "PFE", "BMY", "JAZZ",
    ),
    "Industrials & materials": (
        "FCX", "AA", "X", "CLF", "MP", "ALB", "MOS", "CF", "NEM", "RIG",
    ),
    "Clean energy": (
        "FSLR", "ENPH", "RUN", "PLUG", "NEE", "RIVN", "LCID",
    ),
    "Communication & media": (
        "WBD", "PARA", "LYV", "MTCH", "IQ", "ROKU", "SIRI",
    ),
}

# Not for trading. These feed the regime panel, the sector-rotation strip and
# the relative-strength benchmark, and are screened out of candidate lists.
MARKET_CONTEXT: tuple[str, ...] = (
    # Broad market
    "SPY", "QQQ", "IWM",
    # Sectors
    "XLE", "XLF", "XLK", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE", "XLC",
    # Commodities, dollar, rates, credit, volatility
    "USO", "BNO", "UNG", "GLD", "CPER", "UUP", "TLT", "IEF", "SHY",
    "HYG", "LQD", "VIXY",
)


def trading_symbols() -> tuple[str, ...]:
    """Every candidate, deduplicated, in a stable order."""
    seen: dict[str, None] = {}
    for tickers in TRADING_CANDIDATES.values():
        for ticker in tickers:
            seen.setdefault(ticker, None)
    return tuple(seen)


def all_symbols() -> tuple[str, ...]:
    """Candidates plus the context symbols the regime panel needs."""
    seen: dict[str, None] = {t: None for t in trading_symbols()}
    for ticker in MARKET_CONTEXT:
        seen.setdefault(ticker, None)
    return tuple(seen)


def sector_of(ticker: str) -> str | None:
    """Which pool group a ticker belongs to, for the per-sector position cap.

    This is the pool's own grouping, not a GICS classification. It is good
    enough for limiting correlated positions and honest about being coarse.
    """
    target = ticker.strip().upper()
    for sector, tickers in TRADING_CANDIDATES.items():
        if target in tickers:
            return sector
    return None


def sector_map() -> dict[str, str]:
    return {t: s for s, ts in TRADING_CANDIDATES.items() for t in ts}
