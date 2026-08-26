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

On pool size
------------
A bigger pool does NOT produce more trades. At five slots and a ten-day hold
the account can hold roughly 126 positions a year, while 127 symbols already
generate around 1,500 H2 signals -- so under a tenth of what is available is
takeable. Doubling the pool halves that fraction and changes nothing else,
unless the ranking that chooses between candidates is good, and no ranking here
has been validated.

The reason to expand is therefore qualitative, not quantitative: SMALLER
companies, where a $10,000 account has a structural advantage. A fund running
billions cannot take a meaningful position in a $500M company; inefficiency
persists where large capital cannot reach. That is the one edge available to
this account that does not depend on forecasting anything.

Two costs come with it, both real. Small caps delist far more often, so the
survivorship problem in `universe coverage` gets worse, not better. And spreads
are wider, which the flat 5 bps slippage assumption in the backtest understates
-- results on small caps should be re-run at 15 bps before being believed.
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

# Smaller companies, added deliberately rather than to inflate the count. This
# is where the account's size stops being a limitation -- see the module
# docstring. Expect a higher ingestion-failure rate here: some of these will
# have been acquired or delisted since the list was written, and a failed
# symbol is information rather than a problem.
SMALL_CAP_CANDIDATES: dict[str, tuple[str, ...]] = {
    "Semis & equipment (small)": (
        "RMBS", "SITM", "POWI", "SLAB", "DIOD", "ACLS", "UCTT", "ICHR",
        "COHU", "FORM", "ONTO", "AEIS", "CRUS", "MKSI",
    ),
    "Software (small)": (
        "APPF", "BLKB", "ENV", "WK", "SPT", "ASAN", "BRZE", "AI",
        "BIGC", "FROG", "JAMF", "PD", "YEXT", "DOMO",
    ),
    "Retail (small)": (
        "BOOT", "SHOO", "WWW", "OXM", "ZUMZ", "BKE", "TLYS",
        "FIVE", "OLLI", "BURL", "DKS", "ASO",
    ),
    "Restaurants": (
        "WEN", "JACK", "PLAY", "CAKE", "TXRH", "SHAK", "WING",
        "PTLO", "CBRL", "DENN", "EAT",
    ),
    "Regional banks": (
        "WAL", "ZION", "CMA", "SNV", "PB", "UMBF", "ONB", "FHN",
        "VLY", "ASB", "BOKF", "CBSH",
    ),
    "Industrials (small)": (
        "AIT", "MLI", "GBX", "WNC", "ALG", "TRN", "MYRG", "PRIM",
        "IESC", "ROAD", "STRL", "TILE",
    ),
    "Energy (small)": (
        "SM", "MTDR", "CRC", "GPOR", "CRK", "NOG", "VTLE", "REPX",
    ),
    "Health care (small)": (
        "HALO", "MEDP", "ICUI", "LNTH", "ITGR", "MMSI", "AMED",
        "EHC", "SEM", "PNTG", "CRVL",
    ),
    "Homebuilding": (
        "KBH", "TPH", "CCS", "LGIH", "MHO", "BZH", "HOV", "SKY",
    ),
    "Mining & materials (small)": (
        "SXC", "HCC", "ARCH", "BTU", "CDE", "HL", "PAAS", "AG",
        "EXK", "UEC",
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


def pool(include_small_caps: bool = True) -> dict[str, tuple[str, ...]]:
    """The candidate groups, optionally without the small-cap tier."""
    groups = dict(TRADING_CANDIDATES)
    if include_small_caps:
        groups.update(SMALL_CAP_CANDIDATES)
    return groups


def trading_symbols(include_small_caps: bool = True) -> tuple[str, ...]:
    """Every candidate, deduplicated, in a stable order."""
    seen: dict[str, None] = {}
    for tickers in pool(include_small_caps).values():
        for ticker in tickers:
            seen.setdefault(ticker, None)
    return tuple(seen)


def all_symbols(include_small_caps: bool = True) -> tuple[str, ...]:
    """Candidates plus the context symbols the regime panel needs."""
    seen: dict[str, None] = {t: None for t in trading_symbols(include_small_caps)}
    for ticker in MARKET_CONTEXT:
        seen.setdefault(ticker, None)
    return tuple(seen)


def sector_of(ticker: str) -> str | None:
    """Which pool group a ticker belongs to, for the per-sector position cap.

    This is the pool's own grouping, not a GICS classification. It is good
    enough for limiting correlated positions and honest about being coarse.
    """
    target = ticker.strip().upper()
    for sector, tickers in pool().items():
        if target in tickers:
            return sector
    return None


def sector_map() -> dict[str, str]:
    return {t: s for s, ts in pool().items() for t in ts}
