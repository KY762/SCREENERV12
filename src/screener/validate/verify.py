"""Cross-check stored bars against an independent source.

This is the Phase 1 gate. The unit tests prove the code is internally
consistent; only this proves the DATA is right, because it compares against a
source sharing no code, no vendor, and no bugs with our ingestion path.

Tolerances are asymmetric on purpose:

- PRICE must match to the cent. A price discrepancy means one of the two feeds
  is wrong, and everything downstream -- indicators, signals, backtests -- is
  built on it.
- VOLUME is expected to differ. The free Alpaca feed is IEX-only, roughly a
  single exchange rather than the full consolidated tape, so its figures are a
  fraction of total volume. Direction and relative magnitude should track;
  exact equality should not be expected, and demanding it would produce a
  failing gate on correct data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

PRICE_TOLERANCE = 0.005  # half a cent -- covers rounding, not a real difference


@dataclass(frozen=True)
class BarComparison:
    trade_date: date
    field: str
    ours: float
    theirs: float

    @property
    def difference(self) -> float:
        return self.ours - self.theirs

    @property
    def pct_difference(self) -> float:
        return (self.ours - self.theirs) / self.theirs if self.theirs else float("inf")


@dataclass
class VerificationResult:
    ticker: str
    reference: str
    dates_compared: int
    price_mismatches: list[BarComparison]
    volume_differences: list[BarComparison]
    missing_from_ours: list[date]
    missing_from_reference: list[date]

    @property
    def passed(self) -> bool:
        """Prices must match. Volume differences and reference gaps do not fail
        the gate -- the reference is not authoritative about which sessions
        exist, and its volume is measured differently."""
        return not self.price_mismatches and not self.missing_from_ours

    def summary(self) -> str:
        if self.passed:
            return (
                f"{self.ticker}: PASS -- {self.dates_compared} bars match "
                f"{self.reference} on OHLC to the cent"
            )
        parts = []
        if self.price_mismatches:
            parts.append(f"{len(self.price_mismatches)} price mismatch(es)")
        if self.missing_from_ours:
            parts.append(f"{len(self.missing_from_ours)} session(s) we are missing")
        return f"{self.ticker}: FAIL -- " + ", ".join(parts)


def compare_bars(
    ticker: str,
    ours: dict[date, dict[str, float]],
    theirs: dict[date, dict[str, float]],
    *,
    reference_name: str = "reference",
    price_tolerance: float = PRICE_TOLERANCE,
    volume_tolerance_pct: float = 0.02,
) -> VerificationResult:
    """Compare two sets of bars keyed by trading date.

    Only dates present in BOTH are compared on price. A date the reference lacks
    is reported but does not fail -- reference sources have their own gaps, and
    treating them as authoritative about session existence would be circular.
    """
    shared = sorted(set(ours) & set(theirs))

    price_mismatches: list[BarComparison] = []
    volume_differences: list[BarComparison] = []

    for d in shared:
        a, b = ours[d], theirs[d]
        for field in ("open", "high", "low", "close"):
            if field not in a or field not in b:
                continue
            if abs(a[field] - b[field]) > price_tolerance:
                price_mismatches.append(BarComparison(d, field, a[field], b[field]))
        if "volume" in a and "volume" in b and b["volume"]:
            rel = abs(a["volume"] - b["volume"]) / b["volume"]
            if rel > volume_tolerance_pct:
                volume_differences.append(
                    BarComparison(d, "volume", a["volume"], b["volume"])
                )

    return VerificationResult(
        ticker=ticker,
        reference=reference_name,
        dates_compared=len(shared),
        price_mismatches=price_mismatches,
        volume_differences=volume_differences,
        missing_from_ours=sorted(set(theirs) - set(ours)),
        missing_from_reference=sorted(set(ours) - set(theirs)),
    )
