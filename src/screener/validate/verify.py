"""Cross-check stored bars against an independent source.

This is the Phase 1 gate. The unit tests prove the code is internally
consistent; only this proves the DATA is right, because it compares against a
source sharing no code, no vendor, and no bugs with our ingestion path.

What "match" can and cannot mean
--------------------------------
The free Alpaca feed is IEX-only: roughly one venue, not the consolidated tape.
Reference sources report the consolidated tape. The two therefore see DIFFERENT
TRADES, so their open, high, low and close are different measurements of the
same session rather than the same measurement twice.

    An exact match is not achievable on this feed, and demanding one produces
    a failing gate on correct data.

Observed in practice on large caps: a few basis points, differences of either
sign, spread across all four price fields. That is the signature of a venue
difference. What the gate is actually for is the class of errors that would
poison everything downstream, all of which are orders of magnitude larger:

    wrong symbol            hundreds of bps or more
    wrong date alignment    large, and usually one-directional
    missed split            ~50% or ~100%
    stale or repeated bars  large on any day with real movement
    unit or scale errors    enormous

So the test is MATERIAL agreement, with a tolerance stated in basis points, plus
a check for SYSTEMATIC bias -- because a small offset in a consistent direction
is the signature of an adjustment mismatch, which venue noise cannot produce.

Volume is compared but never fails the gate: on an IEX-only feed it is a
fraction of consolidated volume by construction.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date

# 25 bps = 0.25%. Comfortably above observed venue noise (single-digit bps on
# liquid names), far below every error class the gate exists to catch.
PRICE_TOLERANCE_BPS = 25.0

# Floor for low-priced stocks, where a fixed bps figure is tighter than the
# tick size: at $2, 25 bps is half a cent.
PRICE_TOLERANCE_ABS = 0.01

# A systematic offset this large, in a consistent direction, is not venue noise.
SYSTEMATIC_BIAS_BPS = 10.0
SYSTEMATIC_SIGN_AGREEMENT = 0.90


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

    @property
    def bps_difference(self) -> float:
        return self.pct_difference * 10_000.0


@dataclass
class VerificationResult:
    ticker: str
    reference: str
    dates_compared: int
    price_mismatches: list[BarComparison]
    volume_differences: list[BarComparison]
    missing_from_ours: list[date]
    missing_from_reference: list[date]
    deviations_bps: list[float] = field(default_factory=list)
    tolerance_bps: float = PRICE_TOLERANCE_BPS

    # -- shape of the differences ------------------------------------------

    @property
    def median_abs_deviation_bps(self) -> float:
        if not self.deviations_bps:
            return 0.0
        return statistics.median(abs(d) for d in self.deviations_bps)

    @property
    def max_abs_deviation_bps(self) -> float:
        return max((abs(d) for d in self.deviations_bps), default=0.0)

    @property
    def sign_agreement(self) -> float:
        """Fraction of differences sharing the dominant sign.

        Near 0.5 means noise: we are sometimes above and sometimes below. Near
        1.0 means one series is consistently offset from the other, which is
        what an adjustment or alignment error looks like.
        """
        signed = [d for d in self.deviations_bps if d != 0]
        if not signed:
            return 0.0
        positive = sum(1 for d in signed if d > 0)
        return max(positive, len(signed) - positive) / len(signed)

    @property
    def systematic_bias(self) -> bool:
        """A small but consistently one-directional offset. Venue differences
        do not produce this; a missed split or a date shift does."""
        return (
            self.median_abs_deviation_bps > SYSTEMATIC_BIAS_BPS
            and self.sign_agreement >= SYSTEMATIC_SIGN_AGREEMENT
        )

    # -- verdict ------------------------------------------------------------

    @property
    def passed(self) -> bool:
        """Zero bars compared is NOT a pass. A check that examined nothing has
        produced no evidence, and reporting that as success is worse than
        reporting failure: it retires the question."""
        return (
            self.dates_compared > 0
            and not self.price_mismatches
            and not self.missing_from_ours
            and not self.systematic_bias
        )

    def summary(self) -> str:
        if self.dates_compared == 0:
            return f"{self.ticker}: INCONCLUSIVE -- no overlapping bars to compare"
        if self.passed:
            return (
                f"{self.ticker}: PASS -- {self.dates_compared} bars agree with "
                f"{self.reference} within {self.tolerance_bps:.0f} bps "
                f"(median {self.median_abs_deviation_bps:.1f} bps, "
                f"max {self.max_abs_deviation_bps:.1f} bps)"
            )
        parts = []
        if self.price_mismatches:
            parts.append(
                f"{len(self.price_mismatches)} price(s) beyond "
                f"{self.tolerance_bps:.0f} bps"
            )
        if self.systematic_bias:
            parts.append(
                f"systematic bias: median {self.median_abs_deviation_bps:.1f} bps "
                f"with {self.sign_agreement:.0%} sign agreement"
            )
        if self.missing_from_ours:
            parts.append(f"{len(self.missing_from_ours)} session(s) we are missing")
        return f"{self.ticker}: FAIL -- " + ", ".join(parts)


def compare_bars(
    ticker: str,
    ours: dict[date, dict[str, float]],
    theirs: dict[date, dict[str, float]],
    *,
    reference_name: str = "reference",
    price_tolerance_bps: float = PRICE_TOLERANCE_BPS,
    price_tolerance_abs: float = PRICE_TOLERANCE_ABS,
    volume_tolerance_pct: float = 0.02,
) -> VerificationResult:
    """Compare two sets of bars keyed by trading date.

    Only dates present in BOTH are compared. A date the reference lacks is
    reported but does not fail -- reference sources have their own gaps, and
    treating them as authoritative about session existence would be circular.
    """
    shared = sorted(set(ours) & set(theirs))

    price_mismatches: list[BarComparison] = []
    volume_differences: list[BarComparison] = []
    deviations_bps: list[float] = []

    for d in shared:
        a, b = ours[d], theirs[d]
        for name in ("open", "high", "low", "close"):
            if name not in a or name not in b:
                continue
            comparison = BarComparison(d, name, a[name], b[name])
            if b[name]:
                deviations_bps.append(comparison.bps_difference)
            allowed = max(price_tolerance_abs, abs(b[name]) * price_tolerance_bps / 10_000.0)
            if abs(comparison.difference) > allowed:
                price_mismatches.append(comparison)
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
        deviations_bps=deviations_bps,
        tolerance_bps=price_tolerance_bps,
    )
