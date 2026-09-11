"""Render a battery run as Markdown and JSON.

Both are written. The Markdown is for a person; the JSON is so the numbers can
be re-read exactly rather than re-typed from a screenshot.

Every experiment is reported, in the order it was declared -- including the
ones that found nothing. A report containing only the interesting experiments
is a report of a search, not of a result.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..backtest.runner import RunConfig
from ..backtest.splits import Split
from .battery import ExperimentResult

MAX_ROWS = 12


def _cell_row(cell) -> dict[str, Any]:
    stats = cell.outcome.stats
    return {
        **{k: v for k, v in sorted(cell.params.items())},
        "trades": stats.trades,
        "expectancy_r": round(stats.expectancy_r, 4),
        "win_rate": round(stats.win_rate, 4),
        "profit_factor": (
            None if stats.profit_factor == float("inf") else round(stats.profit_factor, 3)
        ),
        "max_drawdown_pct": round(stats.max_drawdown_pct, 4),
        "total_return_pct": round(stats.total_return_pct, 4),
        "random_percentile": (
            None if cell.outcome.random_percentile is None
            else round(cell.outcome.random_percentile, 1)
        ),
        "exits": stats.exits,
    }


def to_json(
    results: list[ExperimentResult], split: Split, context: dict[str, Any]
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "split": {"name": split.name, "start": str(split.start), "end": str(split.end)},
        "context": context,
        "experiments": [
            {
                "name": r.experiment.name,
                "hypothesis": r.experiment.hypothesis,
                "kind": r.experiment.kind,
                "question": r.experiment.question,
                # Both: what the experiment declared, and what the engine
                # resolved it to. They differ wherever a hypothesis's own spec
                # applies or a value is normalised, and a reader six months
                # from now needs to see which number produced the cells.
                "base": r.experiment.base,
                "base_resolved": _as_run(r.experiment),
                "varied": {k: list(v) for k, v in r.experiment.vary.items()},
                "configurations_tested": len(r.cells),
                "verdict": {
                    "shape": r.verdict.shape,
                    "detail": r.verdict.detail,
                    "positive_cells": r.verdict.positive_cells,
                    "recommended": (
                        r.verdict.recommended.params if r.verdict.recommended else None
                    ),
                    "best": r.verdict.best.params if r.verdict.best else None,
                },
                "cells": [_cell_row(c) for c in sorted(
                    r.cells, key=lambda c: -c.expectancy
                )],
            }
            for r in results
        ],
    }


def to_markdown(
    results: list[ExperimentResult], split: Split, context: dict[str, Any]
) -> str:
    lines: list[str] = []
    add = lines.append

    add(f"# Development-split battery — {split.name}")
    add("")
    add(f"**Generated:** {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}")
    add(f"**Window:** {split.start} → {split.end}")
    add(f"**Symbols:** {context.get('symbols', 0)}  ")
    add(f"**Configurations tested:** {sum(len(r.cells) for r in results)}")
    add("")
    add("Development-split results carry **no evidential weight** "
        "(docs/03-HYPOTHESES.md §0.4). Nothing here confirms a hypothesis; "
        "it can only rule things out and suggest what to confirm elsewhere.")
    add("")

    add("## Summary")
    add("")
    add("| Experiment | Kind | Configs | Shape | Best expectancy | Selected |")
    add("| --- | --- | --- | --- | --- | --- |")
    for r in results:
        best = r.verdict.best
        chosen = r.verdict.recommended
        add(
            f"| `{r.experiment.name}` | {r.experiment.kind} | {len(r.cells)} | "
            f"**{r.verdict.shape}** | "
            f"{best.expectancy:+.3f}R | "
            f"{_fmt_params(chosen.params) if chosen else '—'} |"
        )
    add("")

    for r in results:
        add(f"## `{r.experiment.name}` — {r.experiment.hypothesis.upper()}")
        add("")
        add(f"**Question:** {r.experiment.question}")
        if r.experiment.base:
            add("")
            add(f"**Held fixed:** {_fmt_params(_as_run(r.experiment))}")
        add("")
        add(f"**Verdict — {r.verdict.shape.upper()}:** {r.verdict.detail}")
        add("")

        divergence = _isolation_warning(r)
        if divergence:
            add(divergence)
            add("")

        varied = sorted(r.experiment.vary)
        header = varied + ["Trades", "Win%", "Expectancy", "PF", "MaxDD", "Return", "Exits"]
        add("| " + " | ".join(header) + " |")
        add("| " + " | ".join("---" for _ in header) + " |")

        ordered = sorted(r.cells, key=lambda c: -c.expectancy)
        for cell in ordered[:MAX_ROWS]:
            stats = cell.outcome.stats
            pf = "inf" if stats.profit_factor == float("inf") else f"{stats.profit_factor:.2f}"
            exits = ", ".join(
                f"{k} {v}" for k, v in sorted(stats.exits.items(), key=lambda kv: -kv[1])
            ) or "—"
            add(
                "| "
                + " | ".join(
                    [str(cell.params[name]) for name in varied]
                    + [
                        str(stats.trades),
                        f"{stats.win_rate:.0%}",
                        f"{stats.expectancy_r:+.3f}R",
                        pf,
                        f"{stats.max_drawdown_pct:.1%}",
                        f"{stats.total_return_pct:+.1%}",
                        exits,
                    ]
                )
                + " |"
            )
        if len(ordered) > MAX_ROWS:
            add("")
            add(f"*{len(ordered) - MAX_ROWS} further configuration(s) omitted from this "
                "table; all are present in the JSON.*")
        add("")

    add("## Caveats attached to every number above")
    add("")
    add("- The universe is **today's** large caps. No delisted company is present, "
        "so every result is inflated by an unknown amount (ADR 0002).")
    add("- Ambiguous bars resolve to the stop, gaps fill at the open, and slippage "
        "is charged both ways. Those understate results.")
    add("- Random-selection percentiles, where present, are the comparison that "
        "matters: beating zero is not the test, beating random long exposure is.")
    return "\n".join(lines) + "\n"


def _fmt_params(params: dict[str, Any]) -> str:
    return ", ".join(f"`{k}={v}`" for k, v in sorted(params.items()))


# Above this spread in trade count, a stop-vs-no-stop comparison is no longer
# comparing the same trades. 25% is generous: h5's arms differed by 4.5%.
ISOLATION_TOLERANCE = 0.25


def _isolation_warning(result) -> str | None:
    """Flag a use_stop comparison whose arms did not take the same trades.

    A stop exits early and frees the slot, so the stop arm takes more trades.
    When that gap is large the comparison measures the exit rule AND which
    signals each arm had room for -- the confound docs/07 exists to describe.
    The 2026-09-11 run hit 65% on h2 and nobody would have seen it without
    reading the trade column by hand.

    Only applies to experiments varying use_stop alone, because that is where
    the claim "both arms take the same signals" is actually being made. A
    parameter sweep over hold or time_limit is expected to change trade counts.
    """
    if set(result.experiment.vary) != {"use_stop"}:
        return None

    counts = [cell.outcome.stats.trades for cell in result.cells]
    if len(counts) < 2 or min(counts) <= 0:
        return None

    spread = (max(counts) - min(counts)) / max(counts)
    if spread <= ISOLATION_TOLERANCE:
        return (
            f"**Isolation held:** arms differ by {spread:.1%} in trade count "
            f"({min(counts):,} vs {max(counts):,}), so both took substantially "
            "the same signals and the difference is the exit rule."
        )

    return (
        f"**ISOLATION FAILED — do not read this as an exit-rule result.** The "
        f"arms differ by {spread:.1%} in trade count ({min(counts):,} vs "
        f"{max(counts):,}). A stop frees its slot early, so the arms took "
        "different signals and this measures exit design and selection "
        "together -- the confound of docs/07. Raise `max_positions` until the "
        "counts converge."
    )


def _as_run(experiment) -> dict[str, Any]:
    """The base config as the engine actually ran it, not as it was written.

    `RunConfig.resolved()` applies each hypothesis's own specification and
    normalises nonsense: `r_multiple=0` becomes None, because a target at 0R
    sits on the entry price and is not a target. Printing the raw dict made
    the exit-isolated arms report `r_multiple=0` after that had stopped being
    true, which describes a run that did not happen.

    Falls back to the raw base rather than failing a report over a key the
    config does not recognise -- a report that refuses to render is worse than
    one that renders the input.
    """
    try:
        resolved = RunConfig(hypothesis=experiment.hypothesis, **experiment.base).resolved()
    except TypeError:
        return dict(experiment.base)
    return {key: getattr(resolved, key, experiment.base[key]) for key in experiment.base}


def write_report(
    results: list[ExperimentResult],
    split: Split,
    context: dict[str, Any],
    out_dir: Path,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    md_path = out_dir / f"{stamp}-{split.name}-battery.md"
    json_path = out_dir / f"{stamp}-{split.name}-battery.json"

    md_path.write_text(to_markdown(results, split, context), encoding="utf-8")
    json_path.write_text(
        json.dumps(to_json(results, split, context), indent=2), encoding="utf-8"
    )
    return md_path, json_path


__all__ = ["to_json", "to_markdown", "write_report"]
