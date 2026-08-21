"""Command-line interface.

The CLI is the entire user interface for Phases 1-4. That is deliberate: it
forces the calculation and data layers to be correct and independently testable
before any dashboard exists to hide behind.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

from .config import get_settings
from .db.models import DataQualityLog, IngestionRun, PriceDaily, Symbol
from .db.session import create_all, get_engine, session_scope

app = typer.Typer(
    help="SCREENERV12 -- market intelligence and trading operations.",
    no_args_is_help=True,
)
db_app = typer.Typer(help="Database management.", no_args_is_help=True)
metrics_app = typer.Typer(help="Derived metrics.", no_args_is_help=True)
app.add_typer(db_app, name="db")
universe_app = typer.Typer(help="Universe construction.", no_args_is_help=True)
diag_app = typer.Typer(help="Pre-test diagnostics.", no_args_is_help=True)
backtest_app = typer.Typer(help="Backtesting.", no_args_is_help=True)
app.add_typer(metrics_app, name="metrics")
app.add_typer(universe_app, name="universe")
app.add_typer(diag_app, name="diagnose")
app.add_typer(backtest_app, name="backtest")

console = Console()


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )


@db_app.command("init")
def db_init() -> None:
    """Create all tables. Safe to re-run -- existing tables are left alone."""
    engine = get_engine()
    create_all(engine)
    console.print(f"[green]Schema ready[/] at {engine.url.render_as_string(hide_password=True)}")


@db_app.command("status")
def db_status() -> None:
    """Row counts and stored date span per symbol."""
    with session_scope() as session:
        symbols = session.scalars(select(Symbol).order_by(Symbol.ticker)).all()
        if not symbols:
            console.print("[yellow]No symbols ingested yet.[/]")
            return

        table = Table(title="Stored data")
        for col in ("Ticker", "Bars", "First", "Last"):
            table.add_column(col, justify="right" if col == "Bars" else "left")

        for sym in symbols:
            count = session.scalar(
                select(func.count()).select_from(PriceDaily).where(
                    PriceDaily.symbol_id == sym.id
                )
            )
            table.add_row(
                sym.ticker, f"{count:,}",
                str(sym.first_date or "-"), str(sym.last_date or "-"),
            )
        console.print(table)


@app.command("ingest")
def ingest(
    symbols: str = typer.Option(..., "--symbols", "-s", help="Comma-separated tickers."),
    start: str = typer.Option(..., "--start", help="Start date, YYYY-MM-DD."),
    end: str | None = typer.Option(None, "--end", help="End date, YYYY-MM-DD. Defaults to today."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch, validate, and store daily bars.

    Safe to re-run over any range: unchanged bars are left untouched.
    """
    _configure_logging(verbose)
    from .ingest.prices import ingest_daily_bars
    from .providers.alpaca import AlpacaProvider
    from .providers.base import ProviderError

    settings = get_settings()
    if not settings.has_alpaca_credentials:
        console.print(
            "[red]Alpaca credentials missing.[/] Copy .env.example to .env and set "
            "ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY."
        )
        raise typer.Exit(code=1)

    tickers = [t.strip().upper() for t in symbols.split(",") if t.strip()]
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end) if end else date.today()

    try:
        provider = AlpacaProvider(settings)
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    console.print(
        f"Ingesting [bold]{len(tickers)}[/] symbol(s) "
        f"{start_date} to {end_date} from {provider.name}..."
    )
    with session_scope() as session:
        summary = ingest_daily_bars(session, provider, tickers, start_date, end_date)

    colour = {"succeeded": "green", "partial": "yellow", "failed": "red"}[summary.status]
    console.print(f"[{colour}]{summary.status}[/]: {summary.summary()}")
    for result in summary.failed:
        console.print(f"  [red]{result.ticker}[/]: {result.error}")
    if summary.status == "failed":
        raise typer.Exit(code=1)


@app.command("runs")
def runs(limit: int = typer.Option(10, "--limit", "-n")) -> None:
    """Recent ingestion runs.

    This is how a silent failure becomes a visible one -- a screen showing stale
    numbers while looking current is the most dangerous failure mode there is.
    """
    with session_scope() as session:
        rows = session.scalars(
            select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
        ).all()
        if not rows:
            console.print("[yellow]No ingestion runs recorded.[/]")
            return

        table = Table(title="Ingestion runs")
        for col in ("Started", "Job", "Provider", "Status", "OK", "Failed", "Rows"):
            table.add_column(col)

        colours = {"succeeded": "green", "partial": "yellow", "failed": "red", "running": "cyan"}
        for r in rows:
            table.add_row(
                r.started_at.strftime("%Y-%m-%d %H:%M"),
                r.job, r.provider,
                f"[{colours.get(r.status, 'white')}]{r.status}[/]",
                str(r.symbols_ok), str(r.symbols_failed), f"{r.rows_written:,}",
            )
        console.print(table)


@app.command("quality")
def quality(
    limit: int = typer.Option(20, "--limit", "-n"),
    severity: str | None = typer.Option(None, "--severity", help="'error' or 'warning'."),
) -> None:
    """Data-quality violations recorded during ingestion."""
    with session_scope() as session:
        stmt = select(DataQualityLog).order_by(DataQualityLog.created_at.desc()).limit(limit)
        if severity:
            stmt = stmt.where(DataQualityLog.severity == severity)
        rows = session.scalars(stmt).all()
        if not rows:
            console.print("[green]No data-quality violations recorded.[/]")
            return

        table = Table(title="Data quality")
        for col in ("Ticker", "Date", "Rule", "Severity", "Detail"):
            table.add_column(col)
        for r in rows:
            colour = "red" if r.severity == "error" else "yellow"
            table.add_row(
                r.ticker, str(r.trade_date or "-"), r.rule,
                f"[{colour}]{r.severity}[/]", (r.detail or "")[:60],
            )
        console.print(table)


@app.command("freshness")
def freshness(max_age_days: int = typer.Option(4, "--max-age-days")) -> None:
    """Flag symbols whose most recent bar is older than expected.

    Deliberately blunt: a hard failure is better than a dashboard quietly
    serving last week's prices as though they were today's.
    """
    cutoff = date.today() - timedelta(days=max_age_days)
    with session_scope() as session:
        stale = session.scalars(
            select(Symbol).where(Symbol.last_date.is_not(None), Symbol.last_date < cutoff)
            .order_by(Symbol.last_date)
        ).all()
        total = session.scalar(select(func.count()).select_from(Symbol))

    if not total:
        console.print("[yellow]No symbols stored.[/]")
        raise typer.Exit(code=1)
    if not stale:
        console.print(f"[green]All {total} symbol(s) current[/] (newer than {cutoff}).")
        return

    console.print(f"[red]{len(stale)} of {total} symbol(s) stale[/] (older than {cutoff}):")
    for sym in stale[:20]:
        console.print(f"  {sym.ticker}: last bar {sym.last_date}")
    raise typer.Exit(code=1)


@metrics_app.command("build")
def metrics_build(
    symbols: str | None = typer.Option(
        None, "--symbols", "-s", help="Comma-separated; omit for all."
    ),
    benchmark: str = typer.Option("SPY", "--benchmark", help="Relative-strength benchmark."),
    rebuild: bool = typer.Option(False, "--rebuild", help="Delete and recompute."),
    since: str | None = typer.Option(
        None, "--since", help="Only write rows on/after this date (YYYY-MM-DD). "
        "History is still used for the calculation."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Compute derived metrics from stored bars into metrics_daily.

    Safe to re-run: unchanged rows are left untouched. metrics_daily is a cache
    fully reproducible from price_daily, so --rebuild is always safe.
    """
    _configure_logging(verbose)
    from .metrics.compute import build_metrics

    tickers = [t.strip().upper() for t in symbols.split(",")] if symbols else None
    with session_scope() as session:
        results = build_metrics(
            session, tickers, benchmark_ticker=benchmark, rebuild=rebuild,
            since=date.fromisoformat(since) if since else None,
        )

    ok = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    rows = sum(r.rows_written for r in ok)

    console.print(
        f"[green]{len(ok)}[/] symbol(s) computed, [bold]{rows:,}[/] row(s) written"
        + (f", [red]{len(failed)}[/] skipped" if failed else "")
    )
    for r in failed:
        console.print(f"  [yellow]{r.ticker}[/]: {r.error}")
    if not ok:
        raise typer.Exit(code=1)


@metrics_app.command("show")
def metrics_show(
    symbol: str = typer.Argument(..., help="Ticker."),
    tail: int = typer.Option(5, "--tail", "-n"),
) -> None:
    """Print stored metrics for one symbol."""
    from .db.models import MetricsDaily

    ticker = symbol.strip().upper()
    with session_scope() as session:
        sym = session.scalar(select(Symbol).where(Symbol.ticker == ticker))
        if sym is None:
            console.print(f"[red]{ticker} not found.[/]")
            raise typer.Exit(code=1)
        rows = session.scalars(
            select(MetricsDaily).where(MetricsDaily.symbol_id == sym.id)
            .order_by(MetricsDaily.date.desc()).limit(tail)
        ).all()

    if not rows:
        console.print(f"[yellow]No metrics for {ticker}. Run 'screener metrics build'.[/]")
        raise typer.Exit(code=1)

    table = Table(title=f"{ticker} -- metrics (NULL = insufficient history)")
    for col in ("Date", "SMA50", "SMA200", "Aligned", "ATR%", "RVOL", "RS63", "52wH%"):
        table.add_column(col, justify="right" if col != "Date" else "left")

    def fmt(value, spec="{:.2f}"):
        return "-" if value is None else spec.format(value)

    for r in reversed(rows):
        table.add_row(
            str(r.date), fmt(r.sma_50), fmt(r.sma_200),
            "-" if r.ma_aligned is None else ("yes" if r.ma_aligned else "no"),
            fmt(r.atr_pct_14, "{:.2%}"), fmt(r.rvol_20),
            fmt(r.rs_63, "{:+.2%}"), fmt(r.pct_from_252d_high, "{:.1%}"),
        )
    console.print(table)


@universe_app.command("build")
def universe_build(
    name: str = typer.Option("liquid_us", "--name"),
    min_price: float = typer.Option(10.0, "--min-price"),
    min_dollar_volume: float = typer.Option(20_000_000.0, "--min-adv"),
    min_history: int = typer.Option(250, "--min-history"),
    rebuild: bool = typer.Option(False, "--rebuild"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Evaluate point-in-time universe membership and persist it.

    Membership is stored per date, never derived from today's data. Screening
    history against today's universe silently selects the companies that went on
    to become large and liquid.
    """
    _configure_logging(verbose)
    from .universe.build import build_universe
    from .universe.definition import UniverseDefinition

    definition = UniverseDefinition(
        name=name, min_price=min_price,
        min_dollar_volume=min_dollar_volume, min_history_days=min_history,
    )
    console.print(f"[dim]{definition.describe()}[/]")

    with session_scope() as session:
        result = build_universe(session, definition, rebuild=rebuild)

    console.print(f"[green]{result.summary()}[/]")
    for ticker, reason in list(result.symbols_excluded_static.items())[:15]:
        console.print(f"  [yellow]{ticker}[/]: {reason}")


@universe_app.command("members")
def universe_members_cmd(
    on: str = typer.Option(..., "--on", help="Date, YYYY-MM-DD."),
    name: str = typer.Option("liquid_us", "--name"),
) -> None:
    """List universe members on a specific date."""
    from .universe.build import universe_members

    with session_scope() as session:
        tickers = universe_members(session, name, date.fromisoformat(on))

    if not tickers:
        console.print(f"[yellow]No members in {name} on {on}.[/]")
        return
    console.print(f"[bold]{len(tickers)}[/] member(s) of {name} on {on}:")
    console.print("  " + ", ".join(tickers))


@diag_app.command("redundancy")
def diagnose_redundancy(
    threshold: float = typer.Option(0.85, "--threshold"),
    sample: int = typer.Option(50_000, "--sample", help="Max rows to sample."),
) -> None:
    """Correlation matrix across candidate indicators.

    Anything correlating at or above the threshold with a higher-priority
    indicator is dropped -- on evidence rather than judgement. This can overrule
    the recommendations in docs/04, which is the point.
    """
    import pandas as pd

    from .db.models import MetricsDaily
    from .diagnostics.redundancy import find_redundant

    columns = [
        "rs_adj_63", "ret_63", "ret_21", "pct_from_252d_high",
        "rvol_20", "clv", "atr_pct_14", "realized_vol_63",
    ]
    with session_scope() as session:
        rows = session.execute(
            select(*[getattr(MetricsDaily, c) for c in columns]).limit(sample)
        ).all()

    if not rows:
        console.print("[yellow]No metrics stored. Run 'screener metrics build'.[/]")
        raise typer.Exit(code=1)

    frame = pd.DataFrame(rows, columns=columns).astype("float64")
    report = find_redundant(frame, priority=columns, threshold=threshold)

    console.print(f"[bold]{report.summary()}[/]\n")
    table = Table(title=f"Spearman correlation (n={report.observations:,})")
    table.add_column("")
    for c in columns:
        table.add_column(c[:11], justify="right")
    for row_name in columns:
        cells = []
        for col_name in columns:
            r = report.matrix.loc[row_name, col_name]
            if pd.isna(r):
                cells.append("-")
            elif row_name == col_name:
                cells.append("[dim]1.00[/]")
            else:
                mark = "[red]" if abs(r) >= threshold else ""
                close = "[/]" if mark else ""
                cells.append(f"{mark}{r:+.2f}{close}")
        table.add_row(row_name, *cells)
    console.print(table)

    for pair in report.redundant_pairs:
        console.print(
            f"  [red]drop[/] {pair.dropped} (r={pair.correlation:+.3f} with {pair.kept})"
        )


@diag_app.command("signals")
def diagnose_signals(
    symbols: str | None = typer.Option(None, "--symbols", "-s", help="Omit for all."),
    displacement: float | None = typer.Option(
        None, "--displacement", help="Min displacement in ATR. Omit to disable the filter."
    ),
    sweep_lookback: int = typer.Option(10, "--sweep-lookback"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Signal frequency and overlap for H2, H3, and H4 -- no P&L computed.

    Answers two questions cheaply, either of which can invalidate a
    specification before a backtest is worth running:

    FREQUENCY -- does the setup select anything? A rule firing on 40% of bars is
    a description of the market, not a signal.

    OVERLAP -- are these separate hypotheses, or one hypothesis under three
    names? H3 and H4 are both reclaimed-level strategies. If they fire on the
    same bars, crediting both double-counts one piece of evidence.
    """
    _configure_logging(verbose)
    from .calc.indicators import slope_positive, sma
    from .calc.patterns import fvg_entry_events, ifvg_entry_events, sweep_entry_events
    from .diagnostics.signals import frequency_report, overlap_matrix
    from .metrics.compute import load_bars

    with session_scope() as session:
        stmt = select(Symbol).order_by(Symbol.ticker)
        if symbols:
            wanted = [t.strip().upper() for t in symbols.split(",")]
            stmt = stmt.where(Symbol.ticker.in_(wanted))
        universe = [(s.id, s.ticker) for s in session.scalars(stmt)]
        bars_by_symbol = {
            ticker: load_bars(session, sid) for sid, ticker in universe
        }

    bars_by_symbol = {k: v for k, v in bars_by_symbol.items() if len(v) >= 250}
    if not bars_by_symbol:
        console.print(
            "[yellow]No symbol has >= 250 bars. Ingest more history first.[/]"
        )
        raise typer.Exit(code=1)

    setups: dict[str, dict] = {"h2_fvg": {}, "h3_sweep": {}, "h4_ifvg": {}}

    for ticker, bars in bars_by_symbol.items():
        close = bars["close"]
        sma50, sma200 = sma(close, 50), sma(close, 200)
        trend = (
            (close > sma50) & (sma50 > sma200) & slope_positive(sma200, 21).fillna(False)
        )
        setups["h2_fvg"][ticker] = fvg_entry_events(
            bars, displacement_min=displacement, trend_mask=trend
        )
        setups["h3_sweep"][ticker] = sweep_entry_events(
            bars, reference_kind="n_bar", n_bar=sweep_lookback, trend_mask=trend
        )
        setups["h4_ifvg"][ticker] = ifvg_entry_events(bars, trend_mask=trend)

    disp_label = "off" if displacement is None else f"{displacement}x ATR"
    console.print(
        f"[dim]{len(bars_by_symbol)} symbol(s); displacement filter: {disp_label}; "
        f"sweep lookback: {sweep_lookback} bars[/]\n"
    )

    table = Table(title="Signal frequency (no P&L)")
    for col in ("Setup", "Signals", "% of bars", "Per symbol-yr", "Verdict"):
        table.add_column(col, justify="right" if col != "Setup" and col != "Verdict" else "left")

    for name, events in setups.items():
        report = frequency_report(name, events, bars_by_symbol)
        colour = {"usable frequency": "green"}.get(report.verdict, "yellow")
        table.add_row(
            name, f"{report.total_signals:,}", f"{report.signals_per_bar:.2%}",
            f"{report.signals_per_symbol_year:.1f}",
            f"[{colour}]{report.verdict}[/]",
        )
    console.print(table)

    console.print("\n[bold]Signal overlap[/]")
    for result in overlap_matrix(setups):
        colour = "red" if "FOLD" in result.verdict else (
            "yellow" if "jointly" in result.verdict else "green"
        )
        console.print(f"  [{colour}]{result.summary()}[/]")


@app.command("verify")
def verify_cmd(
    symbols: str = typer.Option("SPY,QQQ,AAPL", "--symbols", "-s"),
    tail: int = typer.Option(10, "--tail", "-n", help="Most recent N bars to compare."),
    reference: str = typer.Option(
        "auto", "--reference",
        help="auto (try each in turn), yahoo, or stooq.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """PHASE 1 GATE: cross-check stored bars against an independent source.

    Unit tests prove the code is internally consistent. This proves the DATA is
    right, by comparing against a source that shares no code, no vendor, and no
    bugs with our ingestion path.

    Compares the MOST RECENT bars deliberately: over a short window a split is
    very unlikely, so a difference in adjustment policy cannot explain a
    mismatch. Prices must agree to the cent. Volume is expected to differ --
    the free Alpaca feed is IEX-only, not the consolidated tape.
    """
    _configure_logging(verbose)
    import httpx

    from .providers.reference import ReferenceUnavailable, build_reference
    from .validate.verify import compare_bars

    tickers = [t.strip().upper() for t in symbols.split(",") if t.strip()]
    try:
        ref = build_reference(reference)
    except ValueError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc
    verified: list[str] = []     # actually compared, and matched
    failed: list[str] = []       # actually compared, and did not match
    skipped: list[str] = []      # never compared -- proves nothing either way

    for ticker in tickers:
        with session_scope() as session:
            sym = session.scalar(select(Symbol).where(Symbol.ticker == ticker))
            if sym is None:
                console.print(f"[yellow]{ticker}: not ingested, skipping.[/]")
                skipped.append(ticker)
                continue
            bars = session.scalars(
                select(PriceDaily).where(PriceDaily.symbol_id == sym.id)
                .order_by(PriceDaily.date.desc()).limit(tail)
            ).all()

        if not bars:
            console.print(f"[yellow]{ticker}: no stored bars.[/]")
            skipped.append(ticker)
            continue

        ours = {
            b.date: {
                "open": float(b.open), "high": float(b.high),
                "low": float(b.low), "close": float(b.close),
                "volume": float(b.volume),
            }
            for b in bars
        }
        lo, hi = min(ours), max(ours)

        try:
            ref_bars = ref.get_bars(ticker, lo, hi)
        except (httpx.HTTPError, ReferenceUnavailable) as exc:
            console.print(f"[yellow]{ticker}: reference unavailable ({exc}). Skipped.[/]")
            skipped.append(ticker)
            continue

        theirs = {
            b.trade_date: {
                "open": b.open, "high": b.high, "low": b.low,
                "close": b.close, "volume": b.volume,
            }
            for b in ref_bars
        }

        answered = getattr(ref, "last_source", None) or ref.name
        result = compare_bars(ticker, ours, theirs, reference_name=answered)
        if result.dates_compared == 0:
            console.print(f"[yellow]{result.summary()}[/]")
            skipped.append(ticker)
            continue
        colour = "green" if result.passed else "red"
        console.print(f"[{colour}]{result.summary()}[/]")
        (verified if result.passed else failed).append(ticker)

        if result.price_mismatches:
            table = Table(title=f"{ticker} price mismatches")
            for col in ("Date", "Field", "Ours", answered.title(), "Diff"):
                table.add_column(col)
            for m in result.price_mismatches[:15]:
                table.add_row(
                    str(m.trade_date), m.field, f"{m.ours:.4f}",
                    f"{m.theirs:.4f}", f"{m.difference:+.4f}",
                )
            console.print(table)

        if result.missing_from_ours:
            console.print(
                "  [red]sessions the reference has and we do not:[/] "
                + ", ".join(str(d) for d in result.missing_from_ours[:10])
            )

        if result.volume_differences:
            console.print(
                f"  [dim]volume differs on {len(result.volume_differences)}/"
                f"{result.dates_compared} bars -- expected on the IEX-only free feed, "
                "not a failure[/]"
            )

    ref.close()

    console.print(
        f"\n{len(verified)} verified, {len(failed)} mismatched, {len(skipped)} not compared."
    )

    if failed:
        console.print(
            "[red bold]Phase 1 gate: FAILED[/] -- do not proceed. "
            "There is no point testing hypotheses against wrong prices."
        )
        raise typer.Exit(code=1)

    if not verified:
        # The single most dangerous outcome, because it looks like success if
        # the skip lines scroll past. Nothing was checked, so nothing is known.
        console.print(
            "[red bold]Phase 1 gate: INCONCLUSIVE[/] -- NOTHING WAS COMPARED.\n"
            "The reference source could not be reached for any symbol, so this "
            "run is not evidence that the stored prices are right.\n"
            "Try a single source to see why: [bold]screener verify --reference yahoo -v[/]\n"
            "Or verify by eye: [bold]screener show SPY -n 10[/] against your broker "
            "or TradingView. Ten bars checked by hand is real evidence; a green "
            "line that compared nothing is not."
        )
        raise typer.Exit(code=1)

    if skipped:
        console.print(
            f"[yellow bold]Phase 1 gate: PARTIAL[/] -- {', '.join(verified)} "
            f"match an independent source; {', '.join(skipped)} were not compared.\n"
            "Re-run to cover the rest before treating the gate as passed."
        )
        raise typer.Exit(code=1)

    console.print(
        "[green bold]Phase 1 gate: PASSED[/] -- stored prices match "
        "an independent source."
    )


@app.command("show")
def show(
    symbol: str = typer.Argument(..., help="Ticker."),
    tail: int = typer.Option(10, "--tail", "-n", help="Most recent N bars."),
) -> None:
    """Print stored bars for one symbol, for eyeballing against a chart."""
    ticker = symbol.strip().upper()
    with session_scope() as session:
        sym = session.scalar(select(Symbol).where(Symbol.ticker == ticker))
        if sym is None:
            console.print(f"[red]{ticker} not found.[/] Ingest it first.")
            raise typer.Exit(code=1)
        bars = session.scalars(
            select(PriceDaily).where(PriceDaily.symbol_id == sym.id)
            .order_by(PriceDaily.date.desc()).limit(tail)
        ).all()

    table = Table(title=f"{ticker} -- last {len(bars)} bars (raw, unadjusted)")
    for col in ("Date", "Open", "High", "Low", "Close", "Volume"):
        table.add_column(col, justify="right" if col != "Date" else "left")
    for bar in reversed(bars):
        table.add_row(
            str(bar.date), f"{bar.open:.2f}", f"{bar.high:.2f}",
            f"{bar.low:.2f}", f"{bar.close:.2f}", f"{bar.volume:,}",
        )
    console.print(table)


@backtest_app.command("run")
def backtest_run(
    hypothesis: str = typer.Option(..., "--hypothesis", "-h", help="h1, h2, h3 or h4."),
    split: str = typer.Option("development", "--split", help="development, validation or test."),
    symbols: str | None = typer.Option(None, "--symbols", "-s", help="Omit for all."),
    universe_name: str | None = typer.Option(
        None, "--universe", help="Restrict entries to this point-in-time universe."
    ),
    equity: float = typer.Option(10_000.0, "--equity"),
    r_multiple: float | None = typer.Option(2.0, "--r-multiple", help="Target in R. 0 disables."),
    time_limit: int | None = typer.Option(10, "--time-limit", help="Bars held. 0 disables."),
    slippage_bps: float = typer.Option(5.0, "--slippage-bps"),
    trend_filter: bool = typer.Option(True, "--trend-filter/--no-trend-filter"),
    displacement: float | None = typer.Option(None, "--displacement", help="H2 only, in ATR."),
    hold: int = typer.Option(5, "--hold", help="H1 rebalance interval in days."),
    top_pct: float = typer.Option(0.10, "--top-pct", help="H1 selection cutoff."),
    random_iterations: int = typer.Option(1000, "--random-iterations"),
    seed: int = typer.Option(0, "--seed"),
    confirm: bool = typer.Option(
        False, "--confirm-spend",
        help="Required on validation and test: acknowledges spending budget.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run one configuration of one hypothesis over one split.

    Entries fill at the next session's open, never the signal bar's close.
    Ambiguous bars resolve to the stop. Slippage is charged both ways. The
    result is compared against random selection over the same window with the
    same holding periods, because a strategy that cannot beat that has not
    demonstrated selection, only exposure.

    On validation and test splits this consumes pre-registered budget
    (docs/03-HYPOTHESES.md 0.8) and the spend is recorded in the database.
    """
    _configure_logging(verbose)
    from .backtest import budget
    from .backtest.benchmarks import buy_and_hold, random_benchmark, trade_returns
    from .backtest.engine import CostModel, ExitRule, run_backtest
    from .backtest.performance import by_regime, check_criteria, summarize
    from .backtest.splits import get_split
    from .backtest.strategies import (
        TrendFilter,
        pattern_candidates,
        relative_strength_candidates,
    )
    from .metrics.compute import load_bars
    from .universe.build import universe_members

    key = hypothesis.strip().lower()
    if key not in {"h1", "h2", "h3", "h4"}:
        console.print(f"[red]Unknown hypothesis {hypothesis!r}.[/] Expected h1, h2, h3 or h4.")
        raise typer.Exit(code=1)

    chosen = get_split(split)
    console.print(f"[dim]{chosen.describe()}[/]")

    config = {
        "hypothesis": key,
        "symbols": symbols or "all",
        "universe": universe_name,
        "r_multiple": r_multiple or None,
        "time_limit": time_limit or None,
        "slippage_bps": slippage_bps,
        "trend_filter": trend_filter,
        "displacement": displacement,
        "hold": hold,
        "top_pct": top_pct,
    }

    with session_scope() as session:
        if chosen.carries_evidence:
            state = budget.status(session, key, chosen, config)
            if not state.already_run and not confirm:
                console.print(
                    f"[yellow]{state.describe()}[/]\n"
                    f"This run would spend budget on the [bold]{chosen.name}[/] split, "
                    "which carries evidential weight.\n"
                    "Re-run with [bold]--confirm-spend[/] if that is intended."
                )
                raise typer.Exit(code=1)
            try:
                budget.check(session, key, chosen, config)
            except budget.BudgetExceeded as exc:
                console.print(f"[red]{exc}[/]")
                raise typer.Exit(code=1) from exc

        stmt = select(Symbol).order_by(Symbol.ticker)
        if symbols:
            wanted = [t.strip().upper() for t in symbols.split(",") if t.strip()]
            stmt = stmt.where(Symbol.ticker.in_(wanted))
        rows = [(s.id, s.ticker) for s in session.scalars(stmt)]
        bars_by_symbol = {ticker: load_bars(session, sid) for sid, ticker in rows}
        bars_by_symbol = {k: v for k, v in bars_by_symbol.items() if not v.empty}

        if not bars_by_symbol:
            console.print("[red]No bars stored.[/] Run 'screener ingest' first.")
            raise typer.Exit(code=1)

        members_cache: dict[date, set[str]] = {}

        def in_universe(ticker: str, day: date) -> bool:
            if universe_name is None:
                return True
            if day not in members_cache:
                members_cache[day] = set(universe_members(session, universe_name, day))
            return ticker in members_cache[day]

        trend = TrendFilter(enabled=trend_filter)
        if key == "h1":
            candidates = relative_strength_candidates(
                bars_by_symbol, trend=trend, rebalance_days=hold,
                top_pct=top_pct, universe=in_universe,
            )
        else:
            extra = {"displacement_min": displacement} if key == "h2" else {}
            candidates = pattern_candidates(
                bars_by_symbol, hypothesis=key, trend=trend,
                universe=in_universe, **extra,
            )

        console.print(f"{len(candidates):,} candidate signal(s) before portfolio limits.")

        result = run_backtest(
            candidates, bars_by_symbol,
            start=chosen.start, end=chosen.end,
            starting_equity=equity,
            exit_rule=ExitRule(
                r_multiple=r_multiple or None,
                time_limit=time_limit or None,
            ),
            costs=CostModel(slippage_bps=slippage_bps),
        )

        stats = summarize(result)
        regimes = by_regime(result.trades)

        percentile = None
        holds = [t.bars_held for t in result.closed_trades if t.bars_held > 0]
        if holds and random_iterations > 0:
            bench = random_benchmark(
                bars_by_symbol, start=chosen.start, end=chosen.end,
                n_trades=len(holds), hold_periods=holds,
                iterations=random_iterations, seed=seed,
                costs=CostModel(slippage_bps=slippage_bps),
            )
            observed = trade_returns(result.closed_trades)
            mean_return = sum(observed) / len(observed) if observed else 0.0
            percentile = bench.percentile_of(mean_return)
            console.print(f"[dim]{bench.describe(mean_return)}[/]")

        criteria = check_criteria(stats, regimes, percentile)
        passed = all(c.passed for c in criteria)

        budget.record(
            session, hypothesis=key, split=chosen, config=config,
            trades=stats.trades, expectancy_r=stats.expectancy_r,
            profit_factor=stats.profit_factor,
            max_drawdown_pct=stats.max_drawdown_pct,
            total_return_pct=stats.total_return_pct,
            random_percentile=percentile, criteria_passed=passed,
        )

    console.print(f"\n[bold]{stats.describe()}[/]")
    if result.rejected:
        top = sorted(result.rejected.items(), key=lambda kv: -kv[1])[:4]
        console.print(
            "[dim]signals not taken: "
            + ", ".join(f"{reason} ({count})" for reason, count in top)
            + "[/]"
        )

    if "SPY" in bars_by_symbol:
        spy = buy_and_hold(
            bars_by_symbol["SPY"], chosen.start, chosen.end,
            CostModel(slippage_bps=slippage_bps),
        )
        console.print(f"[dim]SPY buy-and-hold over the same window: {spy:+.1%}[/]")

    if regimes:
        table = Table(title="By regime")
        for col in ("Regime", "Trades", "Expectancy", "Total R"):
            table.add_column(col, justify="right" if col != "Regime" else "left")
        for name, bucket in regimes.items():
            table.add_row(
                name, str(bucket.trades),
                f"{bucket.expectancy_r:+.3f}R", f"{bucket.total_return_pct:+.2f}",
            )
        console.print(table)

    table = Table(title="Pre-registered criteria (docs/03-HYPOTHESES.md 0.6)")
    for col in ("Criterion", "Observed", "Required", "Result"):
        table.add_column(col, justify="left")
    for criterion in criteria:
        table.add_row(
            criterion.name, criterion.observed, criterion.required,
            "[green]pass[/]" if criterion.passed else "[red]fail[/]",
        )
    console.print(table)

    verdict = "[green]ALL CRITERIA MET[/]" if passed else "[yellow]criteria not met[/]"
    console.print(
        f"\n{verdict} -- recorded on the {chosen.name} split"
        + ("" if chosen.carries_evidence else " (exploratory: proves nothing)")
    )


@backtest_app.command("budget")
def backtest_budget(
    hypothesis: str | None = typer.Option(None, "--hypothesis", "-h"),
) -> None:
    """Show how much of each split's budget has been spent.

    Runs are listed whatever their result. A research log that only records
    the encouraging runs is how a hypothesis gets credited for its best look.
    """
    from .backtest.splits import SPLITS
    from .db.models import ResearchRun

    with session_scope() as session:
        stmt = select(ResearchRun).order_by(ResearchRun.run_at.desc())
        if hypothesis:
            stmt = stmt.where(ResearchRun.hypothesis == hypothesis.strip().lower())
        runs = list(session.scalars(stmt))

        if not runs:
            console.print("[yellow]No research runs recorded yet.[/]")
            return

        spent: dict[tuple[str, str], set[str]] = {}
        for run in runs:
            spent.setdefault((run.hypothesis, run.split), set()).add(run.config_hash)

        table = Table(title="Split budget")
        for col in ("Hypothesis", "Split", "Spent", "Limit", "Remaining"):
            table.add_column(col, justify="right" if col not in ("Hypothesis", "Split") else "left")
        for (hyp, split_name), hashes in sorted(spent.items()):
            limit = SPLITS[split_name].config_budget if split_name in SPLITS else None
            remaining = "unlimited" if limit is None else str(max(limit - len(hashes), 0))
            table.add_row(
                hyp, split_name, str(len(hashes)),
                "unlimited" if limit is None else str(limit), remaining,
            )
        console.print(table)

        recent = Table(title="Recent runs")
        for col in ("When", "Hypothesis", "Split", "Trades", "Expectancy", "PF", "Passed"):
            recent.add_column(col, justify="right" if col != "When" else "left")
        for run in runs[:15]:
            recent.add_row(
                run.run_at.strftime("%Y-%m-%d %H:%M") if run.run_at else "-",
                run.hypothesis, run.split,
                str(run.trades if run.trades is not None else "-"),
                f"{run.expectancy_r:+.3f}R" if run.expectancy_r is not None else "-",
                f"{run.profit_factor:.2f}" if run.profit_factor is not None else "-",
                "[green]yes[/]" if run.criteria_passed else "no",
            )
        console.print(recent)


if __name__ == "__main__":
    app()
