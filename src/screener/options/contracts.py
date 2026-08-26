"""OCC symbol handling and contract records.

The OCC 21-character format is positional and unforgiving:

    AAPL  260116C00150000
    root  YYMMDD  C/P  strike x 1000, zero-padded to 8

Parsing it wrong produces a valid-looking contract at the wrong strike, which
is the kind of error that shows up as a mysterious loss rather than an
exception. Hence a parser with tests rather than string slicing at the call
site.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

OCC_PATTERN = re.compile(
    r"^(?P<root>[A-Z]{1,6})"
    r"(?P<yy>\d{2})(?P<mm>\d{2})(?P<dd>\d{2})"
    r"(?P<cp>[CP])"
    r"(?P<strike>\d{8})$"
)


@dataclass(frozen=True)
class OptionContract:
    """One listed contract and its current market."""

    symbol: str                 # OCC symbol
    underlying: str
    expiry: date
    strike: float
    right: str                  # "C" or "P"
    bid: float
    ask: float
    last: float | None = None
    volume: int = 0
    open_interest: int = 0
    delta: float | None = None
    theta: float | None = None          # per day, normally negative
    implied_volatility: float | None = None

    @property
    def mid(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.last or self.ask or self.bid

    @property
    def spread(self) -> float:
        return max(self.ask - self.bid, 0.0)

    @property
    def spread_pct(self) -> float | None:
        """Spread as a fraction of mid. The single best liquidity filter, and
        the cost you pay twice -- once entering, once leaving."""
        mid = self.mid
        return (self.spread / mid) if mid > 0 else None

    def days_to_expiry(self, as_of: date) -> int:
        return (self.expiry - as_of).days

    def intrinsic(self, underlying_price: float) -> float:
        if self.right == "C":
            return max(0.0, underlying_price - self.strike)
        return max(0.0, self.strike - underlying_price)

    def extrinsic(self, underlying_price: float) -> float:
        """The part that decays to nothing. Everything you pay above intrinsic
        is rent on time."""
        return max(0.0, self.mid - self.intrinsic(underlying_price))


def parse_occ(symbol: str) -> OptionContract | None:
    """Parse an OCC symbol into its parts. Returns None if malformed."""
    match = OCC_PATTERN.match(symbol.strip().upper())
    if match is None:
        return None
    try:
        expiry = date(
            2000 + int(match["yy"]), int(match["mm"]), int(match["dd"])
        )
    except ValueError:
        return None
    return OptionContract(
        symbol=symbol.strip().upper(),
        underlying=match["root"],
        expiry=expiry,
        strike=int(match["strike"]) / 1000.0,
        right=match["cp"],
        bid=0.0,
        ask=0.0,
    )


def build_occ(underlying: str, expiry: date, right: str, strike: float) -> str:
    """Build an OCC symbol. Round-trips with ``parse_occ``."""
    right = right.strip().upper()
    if right not in ("C", "P"):
        raise ValueError("right must be C or P")
    return (
        f"{underlying.strip().upper()}"
        f"{expiry.strftime('%y%m%d')}"
        f"{right}"
        f"{int(round(strike * 1000)):08d}"
    )
