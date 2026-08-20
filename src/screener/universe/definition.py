"""Universe definition -- which instruments are eligible, as of a given date.

Two properties matter more than the filter values themselves.

POINT-IN-TIME. Membership is evaluated with data available on that date and
never with today's data. A stock that failed the liquidity filter in 2019 was
not tradeable in 2019, and screening history against today's universe is a
textbook survivorship and look-ahead error -- it quietly selects the companies
that went on to become large and liquid.

VERSIONED AND UNTUNED. The thresholds are declared conventions, not parameters
to optimise. Tuning a liquidity filter until backtest results improve is a
well-known route to selecting a survivorship-favourable subset, so the version
string is stored with every snapshot and a change to any value is a change of
definition, not a tweak.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Leveraged and inverse products are path-dependent: daily rebalancing means
# their multi-day return is not the multiple of the underlying's. They are a
# structurally different instrument, not a louder version of the same one.
# Prefix matching on "ultra", not \bultra\b: ProShares names run the words
# together ("UltraPro", "UltraShort"), so a trailing word boundary never matches.
_LEVERAGED_NAME_PATTERNS = (
    r"\b\d(?:\.\d)?x\b",          # "2x", "3X", "1.5x"
    r"\bultra",                     # Ultra, UltraPro, UltraShort
    r"\bleveraged\b",
    r"\binverse\b",
    r"\bdaily\b.*\b(bull|bear)\b",
    r"\b(bull|bear)\b.*\b\d(?:\.\d)?x\b",
)

_LEVERAGED_RE = re.compile("|".join(_LEVERAGED_NAME_PATTERNS), re.IGNORECASE)

# Name matching is a heuristic and will miss products whose names are opaque.
# Known issuers of leveraged/inverse ETFs are listed explicitly so the common
# cases are caught deterministically rather than by regex luck.
_KNOWN_LEVERAGED_TICKERS = frozenset({
    "TQQQ", "SQQQ", "QLD", "QID", "UPRO", "SPXU", "SPXL", "SPXS", "SSO", "SDS",
    "UDOW", "SDOW", "DDM", "DXD", "TNA", "TZA", "URTY", "SRTY", "UWM", "TWM",
    "SOXL", "SOXS", "LABU", "LABD", "FAS", "FAZ", "TECL", "TECS", "NUGT", "DUST",
    "JNUG", "JDST", "ERX", "ERY", "GUSH", "DRIP", "YINN", "YANG", "UVXY", "SVXY",
    "VIXY", "TMF", "TMV", "TBT", "UBT", "AGQ", "ZSL", "UGL", "GLL", "BOIL", "KOLD",
    "UCO", "SCO", "NRGU", "NRGD", "WEBL", "WEBS", "CURE", "RETL", "DPST", "SPXE",
})


@dataclass(frozen=True)
class UniverseDefinition:
    """A named, versioned set of eligibility rules.

    Defaults are the values approved in docs/03-HYPOTHESES.md section 0.1.
    """

    name: str = "liquid_us"
    version: str = "v1"

    min_price: float = 10.00
    min_dollar_volume: float = 20_000_000.0
    min_history_days: int = 250

    allowed_asset_types: frozenset[str] = frozenset({"equity", "etf"})
    exclude_leveraged: bool = True
    restricted_tickers: frozenset[str] = field(default_factory=frozenset)

    def describe(self) -> str:
        return (
            f"{self.name}/{self.version}: price >= ${self.min_price:,.2f}, "
            f"ADV >= ${self.min_dollar_volume:,.0f}, "
            f">= {self.min_history_days} bars of history"
        )


def is_leveraged_or_inverse(ticker: str, name: str | None = None) -> bool:
    """Heuristic detection of leveraged and inverse products.

    Imperfect by construction: an issuer can name a 3x product anything it
    likes. The ticker list catches the liquid US cases deterministically; the
    name regex catches the rest when a name is available. False negatives are
    possible and will show up as unusually high ATR% in screening output.
    """
    if ticker.strip().upper() in _KNOWN_LEVERAGED_TICKERS:
        return True
    if name and _LEVERAGED_RE.search(name):
        return True
    return False


def passes_static_filters(
    definition: UniverseDefinition,
    *,
    ticker: str,
    asset_type: str,
    name: str | None = None,
) -> tuple[bool, str | None]:
    """Filters that do not depend on a date. Returns (passed, reason_if_failed)."""
    upper = ticker.strip().upper()

    if upper in definition.restricted_tickers:
        return False, "restricted list"
    if asset_type not in definition.allowed_asset_types:
        return False, f"asset type {asset_type!r} not eligible"
    if definition.exclude_leveraged and is_leveraged_or_inverse(upper, name):
        return False, "leveraged or inverse product"
    return True, None
