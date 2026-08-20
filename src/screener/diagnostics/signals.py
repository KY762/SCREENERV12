"""Signal frequency and overlap diagnostics.

These run BEFORE any P&L calculation, deliberately. Two questions they answer
cheaply, either of which can invalidate a specification:

FREQUENCY -- does the setup actually select anything? A rule firing on 40% of
bars is not a signal, it is a description of the market. With H2's displacement
filter now optional, raw Fair Value Gap frequency may be enormous, and learning
that in seconds is worth more than a full backtest that says the same thing
slowly.

OVERLAP -- are these separate hypotheses or one hypothesis under three names?
H3 (sweep and reclaim) and H4 (inverse FVG) are both reclaimed-level strategies;
they differ in which level and when entry occurs, not in the underlying idea. If
they fire on the same bars, crediting both would double-count one piece of
evidence. Per docs/05 section 1.3, overlap above ~60% folds H4 into H3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..calc.patterns import SignalEvent


@dataclass
class FrequencyReport:
    setup: str
    total_signals: int
    total_bars: int
    symbols: int
    per_year: dict[int, int] = field(default_factory=dict)

    @property
    def signals_per_bar(self) -> float:
        return self.total_signals / self.total_bars if self.total_bars else 0.0

    @property
    def signals_per_symbol_year(self) -> float:
        """Roughly how often a trader would see this setup on one symbol."""
        years = self.total_bars / 252 if self.total_bars else 0
        return self.total_signals / years if years else 0.0

    @property
    def verdict(self) -> str:
        """A blunt readability aid, not a pass/fail gate.

        Thresholds are judgement calls stated openly rather than hidden: a setup
        firing on more than a fifth of bars is not selecting, and one firing on
        fewer than ~200 occasions in total cannot reach the pre-registered
        minimum sample.
        """
        rate = self.signals_per_bar
        if rate > 0.20:
            return "too frequent -- not selective"
        if self.total_signals < 200:
            return "too rare -- below the 200-trade minimum"
        return "usable frequency"

    def summary(self) -> str:
        return (
            f"{self.setup}: {self.total_signals:,} signal(s) across "
            f"{self.symbols} symbol(s) / {self.total_bars:,} bars "
            f"({self.signals_per_bar:.2%} of bars) -- {self.verdict}"
        )


def frequency_report(
    setup: str,
    events_by_symbol: dict[str, list[SignalEvent]],
    bars_by_symbol: dict[str, pd.DataFrame],
) -> FrequencyReport:
    """Count signals without computing a single dollar of P&L."""
    total_signals = sum(len(v) for v in events_by_symbol.values())
    total_bars = sum(len(v) for v in bars_by_symbol.values())

    per_year: dict[int, int] = {}
    for ticker, events in events_by_symbol.items():
        index = bars_by_symbol.get(ticker)
        if index is None or index.empty:
            continue
        for event in events:
            if 0 <= event.trigger_idx < len(index):
                year = pd.Timestamp(index.index[event.trigger_idx]).year
                per_year[year] = per_year.get(year, 0) + 1

    return FrequencyReport(
        setup=setup,
        total_signals=total_signals,
        total_bars=total_bars,
        symbols=len(bars_by_symbol),
        per_year=dict(sorted(per_year.items())),
    )


@dataclass
class OverlapResult:
    setup_a: str
    setup_b: str
    signals_a: int
    signals_b: int
    shared: int

    @property
    def jaccard(self) -> float:
        """Shared entries over the union. Symmetric, so it does not flatter
        whichever setup happens to fire less often."""
        union = self.signals_a + self.signals_b - self.shared
        return self.shared / union if union else 0.0

    @property
    def overlap_of_smaller(self) -> float:
        """Share of the RARER setup's signals also produced by the other.

        The asymmetric view matters: a setup firing 100 times, all of which the
        other also produces, is fully contained even if Jaccard looks modest.
        """
        smaller = min(self.signals_a, self.signals_b)
        return self.shared / smaller if smaller else 0.0

    @property
    def verdict(self) -> str:
        if self.overlap_of_smaller >= 0.60:
            return "FOLD -- treat as one hypothesis (docs/05 section 1.3)"
        if self.overlap_of_smaller >= 0.30:
            return "substantial overlap -- report results jointly"
        return "distinct"

    def summary(self) -> str:
        return (
            f"{self.setup_a} vs {self.setup_b}: {self.shared:,} shared entry bar(s); "
            f"Jaccard {self.jaccard:.1%}, "
            f"{self.overlap_of_smaller:.1%} of the rarer setup -- {self.verdict}"
        )


def overlap(
    setup_a: str,
    events_a: dict[str, list[SignalEvent]],
    setup_b: str,
    events_b: dict[str, list[SignalEvent]],
) -> OverlapResult:
    """Compare two setups on (symbol, entry bar).

    Entry bar rather than trigger bar: two setups that trigger on different bars
    but put you into the same position on the same day are, for evidential
    purposes, the same trade.
    """
    keys_a = {(sym, e.entry_idx) for sym, evs in events_a.items() for e in evs}
    keys_b = {(sym, e.entry_idx) for sym, evs in events_b.items() for e in evs}
    return OverlapResult(
        setup_a=setup_a,
        setup_b=setup_b,
        signals_a=len(keys_a),
        signals_b=len(keys_b),
        shared=len(keys_a & keys_b),
    )


def overlap_matrix(
    events_by_setup: dict[str, dict[str, list[SignalEvent]]]
) -> list[OverlapResult]:
    """Pairwise overlap across every setup."""
    names = list(events_by_setup)
    out: list[OverlapResult] = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            out.append(overlap(a, events_by_setup[a], b, events_by_setup[b]))
    return out
