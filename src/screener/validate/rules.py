"""OHLCV validation.

The failure mode this guards against is not a crash -- it is a dashboard that
looks fine while showing wrong numbers. Bad ticks, unadjusted split errors, and
missing sessions all propagate silently into indicators, then into signals, then
into a backtest that reports an edge which never existed.

Every rule returns structured violations rather than raising. Ingestion records
them, quarantines the affected rows, and continues; a single bad ticker must not
abort a nightly job.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import numpy as np
import pandas as pd


class Severity(StrEnum):
    ERROR = "error"      # the row is unusable and must be quarantined
    WARNING = "warning"  # suspicious; keep the row, flag it for review


@dataclass(frozen=True)
class Violation:
    symbol: str
    trade_date: date | None
    rule: str
    severity: Severity
    detail: str


# --------------------------------------------------------------------------
# Individual rules
# --------------------------------------------------------------------------

def check_positive_prices(symbol: str, df: pd.DataFrame) -> list[Violation]:
    """Zero or negative prices are impossible, not merely unusual."""
    out: list[Violation] = []
    for col in ("open", "high", "low", "close"):
        bad = df.index[(df[col] <= 0) | df[col].isna()]
        for d in bad:
            out.append(
                Violation(symbol, _as_date(d), "positive_prices", Severity.ERROR,
                          f"{col}={df.loc[d, col]!r}")
            )
    return out


def check_ohlc_ordering(symbol: str, df: pd.DataFrame) -> list[Violation]:
    """high must be the session maximum and low the session minimum.

    A violation here means the feed is internally inconsistent -- every
    range-based indicator downstream (ATR, CLV, displacement) would be wrong.
    """
    out: list[Violation] = []
    hi_ok = df["high"] >= df[["open", "close", "low"]].max(axis=1)
    lo_ok = df["low"] <= df[["open", "close", "high"]].min(axis=1)
    for d in df.index[~hi_ok]:
        row = df.loc[d]
        out.append(
            Violation(symbol, _as_date(d), "ohlc_ordering", Severity.ERROR,
                      f"high {row['high']} below max(open={row['open']}, "
                      f"close={row['close']}, low={row['low']})")
        )
    for d in df.index[~lo_ok]:
        row = df.loc[d]
        out.append(
            Violation(symbol, _as_date(d), "ohlc_ordering", Severity.ERROR,
                      f"low {row['low']} above min(open={row['open']}, "
                      f"close={row['close']}, high={row['high']})")
        )
    return out


def check_non_negative_volume(symbol: str, df: pd.DataFrame) -> list[Violation]:
    out: list[Violation] = []
    bad = df.index[(df["volume"] < 0) | df["volume"].isna()]
    for d in bad:
        out.append(
            Violation(symbol, _as_date(d), "non_negative_volume", Severity.ERROR,
                      f"volume={df.loc[d, 'volume']!r}")
        )
    zero = df.index[df["volume"] == 0]
    for d in zero:
        out.append(
            Violation(symbol, _as_date(d), "zero_volume", Severity.WARNING,
                      "zero volume: possible halt, holiday, or missing data")
        )
    return out


def check_duplicate_dates(symbol: str, df: pd.DataFrame) -> list[Violation]:
    dupes = df.index[df.index.duplicated(keep=False)].unique()
    return [
        Violation(symbol, _as_date(d), "duplicate_dates", Severity.ERROR,
                  "more than one bar for this trading date")
        for d in dupes
    ]


def check_monotonic_dates(symbol: str, df: pd.DataFrame) -> list[Violation]:
    if df.index.is_monotonic_increasing:
        return []
    return [
        Violation(symbol, None, "monotonic_dates", Severity.ERROR,
                  "bars are not sorted ascending by date")
    ]


def check_extreme_moves(
    symbol: str, df: pd.DataFrame, threshold: float = 0.50,
    known_action_dates: frozenset[date] | None = None,
) -> list[Violation]:
    """Flag day-over-day close moves beyond ``threshold``.

    A 50% overnight move is usually an unadjusted split, not a real return.
    Dates with a known corporate action are exempt -- that is the whole reason
    corporate actions are stored separately rather than baked into prices.

    WARNING, not ERROR: real 50% moves do happen (biotech readouts, buyouts).
    The system flags them for a human rather than deleting real history.
    """
    known = known_action_dates or frozenset()
    changes = df["close"].pct_change(fill_method=None)
    out: list[Violation] = []
    for d in df.index[changes.abs() > threshold]:
        as_date = _as_date(d)
        if as_date in known:
            continue
        out.append(
            Violation(symbol, as_date, "extreme_move", Severity.WARNING,
                      f"close moved {changes.loc[d]:.1%} with no recorded corporate action")
        )
    return out


def check_calendar_gaps(
    symbol: str, df: pd.DataFrame, expected_sessions: pd.DatetimeIndex,
) -> list[Violation]:
    """Detect sessions the exchange was open for but which have no bar.

    ``expected_sessions`` comes from a real trading calendar. Deriving expected
    dates from the data itself would make the check circular -- it could never
    find a missing day.
    """
    have = {_as_date(d) for d in df.index}
    want = {_as_date(d) for d in expected_sessions}
    missing = sorted(want - have)
    return [
        Violation(symbol, d, "calendar_gap", Severity.WARNING,
                  "exchange was open but no bar was ingested")
        for d in missing
    ]


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationReport:
    symbol: str
    violations: list[Violation]

    @property
    def errors(self) -> list[Violation]:
        return [v for v in self.violations if v.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Violation]:
        return [v for v in self.violations if v.severity is Severity.WARNING]

    @property
    def is_usable(self) -> bool:
        """True when nothing ERROR-level was found. Warnings do not block use."""
        return not self.errors

    @property
    def quarantined_dates(self) -> set[date]:
        return {v.trade_date for v in self.errors if v.trade_date is not None}

    def summary(self) -> str:
        return (
            f"{self.symbol}: {len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s)"
        )


def validate_bars(
    symbol: str,
    df: pd.DataFrame,
    *,
    expected_sessions: pd.DatetimeIndex | None = None,
    known_action_dates: frozenset[date] | None = None,
    extreme_move_threshold: float = 0.50,
) -> ValidationReport:
    """Run every rule against one symbol's bars."""
    if df.empty:
        return ValidationReport(
            symbol,
            [Violation(symbol, None, "empty_frame", Severity.ERROR, "no bars returned")],
        )

    violations: list[Violation] = []
    violations += check_duplicate_dates(symbol, df)
    violations += check_monotonic_dates(symbol, df)
    violations += check_positive_prices(symbol, df)
    violations += check_ohlc_ordering(symbol, df)
    violations += check_non_negative_volume(symbol, df)
    violations += check_extreme_moves(
        symbol, df, extreme_move_threshold, known_action_dates
    )
    if expected_sessions is not None:
        violations += check_calendar_gaps(symbol, df, expected_sessions)
    return ValidationReport(symbol, violations)


def _as_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, pd.Timestamp):
        return value
    return pd.Timestamp(value).date()
