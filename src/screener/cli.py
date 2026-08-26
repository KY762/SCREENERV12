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
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
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

# Declared at module level because ruff B008 forbids a call in a default, and
# a list-valued Option needs one.
VARY_OPTION = typer.Option(
    ..., "--vary",
    help="Parameter range, e.g. --vary r_multiple=1.0,1.5,2.0 --vary time_limit=5,10,15,20",
)


def _load_events(session, bars_by_symbol) -> dict[str, list]:
    """Stored earnings dates keyed by ticker, for the hypotheses that need them."""
    from .ingest.events import earnings_dates

    out: dict[str, list] = {}
    for symbol in session.scalars(
        select(Symbol).where(Symbol.ticker.in_(list(bars_by_symbol)))
    ):
        dates = earnings_dates(session, symbol.id)
        if dates:
            out[symbol.ticker] = dates
    return out


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
    provider_name: str = typer.Option(
        "auto", "--provider",
        help="auto, tiingo (deep history) or alpaca (recent years only).",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch, validate, and store daily bars.

    Safe to re-run over any range: unchanged bars are left untouched, so a run
    interrupted by a rate limit resumes by simply running it again.

    Provider choice matters for how far back history goes. Alpaca's free tier
    serves only the most recent years; Tiingo serves decades. 'auto' prefers
    Tiingo when a key is configured.
    """
    _configure_logging(verbose)
    from .ingest.prices import ingest_daily_bars
    from .providers.base import ProviderError

    settings = get_settings()
    choice = provider_name.strip().lower()
    if choice == "auto":
        choice = "tiingo" if settings.has_tiingo_credentials else "alpaca"

    if choice == "tiingo" and not settings.has_tiingo_credentials:
        console.print(
            "[red]Tiingo API key missing.[/] Set TIINGO_API_KEY in .env "
            "(free key at tiingo.com -- see .env.example)."
        )
        raise typer.Exit(code=1)
    if choice == "alpaca" and not settings.has_alpaca_credentials:
        console.print(
            "[red]Alpaca credentials missing.[/] Copy .env.example to .env and set "
            "ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY."
        )
        raise typer.Exit(code=1)

    tickers = [t.strip().upper() for t in symbols.split(",") if t.strip()]
    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end) if end else date.today()

    try:
        if choice == "tiingo":
            from .providers.tiingo import TiingoProvider
            provider = TiingoProvider(settings)
        elif choice == "alpaca":
            from .providers.alpaca import AlpacaProvider
            provider = AlpacaProvider(settings)
        else:
            console.print(
                f"[red]Unknown provider {provider_name!r}.[/] Expected auto, tiingo or alpaca."
            )
            raise typer.Exit(code=1)
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


research_app = typer.Typer(help="Pre-declared experiment batteries.", no_args_is_help=True)
app.add_typer(research_app, name="research")


@research_app.command("explore")
def research_explore(
    symbols: str | None = typer.Option(None, "--symbols", "-s", help="Omit for all."),
    universe_name: str | None = typer.Option(None, "--universe"),
    split: str = typer.Option("development", "--split"),
    equity: float = typer.Option(10_000.0, "--equity"),
    slippage_bps: float = typer.Option(5.0, "--slippage-bps"),
    random_iterations: int = typer.Option(
        300, "--random-iterations",
        help="Per configuration. 0 skips the random benchmark entirely.",
    ),
    seed: int = typer.Option(0, "--seed"),
    battery: str = typer.Option(
        "round1", "--battery",
        help="round1 (h1-h4), round2 (h5, h7), earnings (h6), or all.",
    ),
    out: str = typer.Option("research", "--out", help="Directory for the report."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run a declared battery of experiments and write a report.

    Twelve experiments, 118 configurations, declared in
    src/screener/research/battery.py BEFORE any of them ran -- each with the
    question it answers written beside it. A battery declared up front and run
    to completion cannot be quietly stopped once a result looks good.

    Writes Markdown and JSON to --out. Both are meant to be committed: the
    JSON so the numbers can be re-read exactly rather than re-typed from a
    screenshot.

    Development split only. This is exploration, and exploration on a split
    that carries evidential weight spends a budget nobody decided to spend.
    """
    _configure_logging(verbose)
    from pathlib import Path

    from .backtest.runner import load_symbol_bars, universe_filter
    from .backtest.splits import get_split
    from .research.battery import battery_size, run_experiment, select_battery
    from .research.report import write_report

    try:
        experiments = select_battery(battery)
    except ValueError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    chosen = get_split(split)
    if chosen.carries_evidence:
        console.print(
            f"[red]The battery is development-split only.[/] The {chosen.name} split "
            f"allows {chosen.config_budget} configuration(s) per hypothesis "
            f"(docs/03 §0.8); this battery is {battery_size(experiments)} "
            "configurations."
        )
        raise typer.Exit(code=1)

    console.print(f"[dim]{chosen.describe()}[/]")

    with session_scope() as session:
        bars_by_symbol = load_symbol_bars(session, symbols)
        if not bars_by_symbol:
            console.print("[red]No bars stored.[/] Run 'screener ingest' first.")
            raise typer.Exit(code=1)
        universe = universe_filter(session, universe_name)

        events = _load_events(session, bars_by_symbol)
        runnable = [
            e for e in experiments
            if e.hypothesis != "h6" or events
        ]
        skipped = [e for e in experiments if e not in runnable]
        if skipped:
            console.print(
                f"[yellow]Skipping {len(skipped)} experiment(s) needing earnings "
                "dates.[/] Run 'screener ingest-earnings' to include them."
            )

        console.print(
            f"[bold]{len(runnable)}[/] experiments, "
            f"[bold]{battery_size(runnable)}[/] configurations, "
            f"{len(bars_by_symbol)} symbols."
        )

        from .backtest import budget

        results = []
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            BarColumn(), TaskProgressColumn(), console=console,
        ) as progress:
            task = progress.add_task("running battery", total=battery_size(runnable))
            for experiment in runnable:
                progress.update(task, description=f"[cyan]{experiment.name}[/]")
                result = run_experiment(
                    experiment, bars_by_symbol, chosen,
                    equity=equity, slippage_bps=slippage_bps, universe=universe,
                    random_iterations=random_iterations, seed=seed,
                    events_by_symbol=events,
                    on_cell=lambda: progress.advance(task),
                )
                for cell in result.cells:
                    budget.record(
                        session, hypothesis=experiment.hypothesis, split=chosen,
                        config=cell.outcome.config.as_dict(),
                        trades=cell.outcome.stats.trades,
                        expectancy_r=cell.outcome.stats.expectancy_r,
                        profit_factor=cell.outcome.stats.profit_factor,
                        max_drawdown_pct=cell.outcome.stats.max_drawdown_pct,
                        total_return_pct=cell.outcome.stats.total_return_pct,
                        random_percentile=cell.outcome.random_percentile,
                        criteria_passed=cell.outcome.passed,
                        notes=f"battery:{experiment.name}",
                    )
                results.append(result)

    md_path, json_path = write_report(
        results, chosen,
        {"symbols": len(bars_by_symbol), "slippage_bps": slippage_bps, "equity": equity},
        Path(out),
    )

    table = Table(title="Battery summary")
    for col in ("Experiment", "Configs", "Shape", "Best", "Selected"):
        table.add_column(col, justify="left" if col == "Experiment" else "right")
    for result in results:
        colour = {"plateau": "green", "spike": "yellow", "none": "red"}[
            result.verdict.shape
        ]
        chosen_cell = result.verdict.recommended
        table.add_row(
            result.experiment.name,
            str(len(result.cells)),
            f"[{colour}]{result.verdict.shape}[/]",
            f"{result.verdict.best.expectancy:+.3f}R" if result.verdict.best else "-",
            ", ".join(f"{k}={v}" for k, v in sorted(chosen_cell.params.items()))
            if chosen_cell else "-",
        )
    console.print(table)

    console.print(f"\n[green]Report written:[/] {md_path}")
    console.print(f"[green]Raw numbers:[/]   {json_path}")
    console.print(
        "\n[bold]Send these to Claude by committing them:[/]\n"
        f"  git add {out}\n"
        '  git commit -m "battery results"\n'
        "  git push"
    )


@app.command("ingest-earnings")
def ingest_earnings_cmd(
    symbols: str | None = typer.Option(None, "--symbols", "-s", help="Omit for all."),
    start: str = typer.Option("2010-01-01", "--start"),
    end: str | None = typer.Option(None, "--end"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch earnings-related filing dates from SEC EDGAR.

    Free, no key, no account -- EDGAR asks only for a descriptive User-Agent
    with a contact address, which SEC_USER_AGENT supplies.

    A filing date is NOT an announcement date. Companies release results by
    press release and file days later; this prefers the 8-K acceptance date as
    the closest available proxy and records which form each date came from, so
    the distinction survives into analysis instead of being averaged away.
    """
    _configure_logging(verbose)
    from .ingest.events import ingest_earnings
    from .providers.base import ProviderError
    from .providers.edgar import EdgarProvider

    try:
        provider = EdgarProvider(get_settings())
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end) if end else date.today()

    with session_scope() as session:
        stmt = select(Symbol).order_by(Symbol.ticker)
        if symbols:
            wanted = [t.strip().upper() for t in symbols.split(",") if t.strip()]
            stmt = stmt.where(Symbol.ticker.in_(wanted))
        tickers = [s.ticker for s in session.scalars(stmt)]

        if not tickers:
            console.print("[red]No symbols stored.[/] Run 'screener ingest' first.")
            raise typer.Exit(code=1)

        console.print(
            f"Fetching filing dates for [bold]{len(tickers)}[/] symbol(s) "
            f"{start_date} to {end_date}. EDGAR is rate-limited to ~7/sec, so this "
            "takes about a second per symbol."
        )
        summary = ingest_earnings(session, provider, tickers, start_date, end_date)

    provider.close()
    console.print(f"[green]{summary.summary()}[/]")
    for failure in summary.failed[:10]:
        console.print(f"  [yellow]{failure.ticker}[/]: {failure.error}")


@universe_app.command("tradeable")
def universe_tradeable(
    equity: float = typer.Option(10_000.0, "--equity"),
    risk_pct: float = typer.Option(0.01, "--risk-pct"),
    stop_atr: float = typer.Option(2.0, "--stop-atr"),
    cap_pct: float = typer.Option(0.25, "--cap-pct", help="Concentration cap."),
    show: str = typer.Option("all", "--show", help="all, good, or tradeable."),
) -> None:
    """Which stored symbols this account can actually size a position in.

    Two things make a stock untradeable, both arithmetic, neither about the
    company:

    TOO FEW SHARES. Risk budget over stop distance. A $900 stock with a $26
    stop is 3 shares at $10k -- rounding throws away a third of the intended
    risk and nothing is left to adjust.

    THE CAP BINDING. A low-volatility name has a tight stop, so the same risk
    buys a position the concentration cap then cuts. The trade ends up risking
    0.5% when the rule said 1%. Conservative, but the sizing rule has stopped
    describing what happens.

    The first problem is fixed by a larger account. The second is not -- it
    depends on volatility against the risk-to-cap ratio, so more money never
    resolves it. Only a different stock does.
    """
    from decimal import Decimal

    from .calc.sizing import RiskLimits
    from .calc.tradeability import (
        assess,
        max_workable_price,
        min_workable_atr_pct,
    )
    from .db.models import MetricsDaily

    limits = RiskLimits(
        risk_pct_per_trade=Decimal(str(risk_pct)),
        max_position_pct=Decimal(str(cap_pct)),
    )

    with session_scope() as session:
        results = []
        for symbol in session.scalars(select(Symbol).order_by(Symbol.ticker)):
            metric = session.scalars(
                select(MetricsDaily)
                .where(MetricsDaily.symbol_id == symbol.id, MetricsDaily.atr_14.isnot(None))
                .order_by(MetricsDaily.date.desc()).limit(1)
            ).first()
            bar = session.scalars(
                select(PriceDaily).where(PriceDaily.symbol_id == symbol.id)
                .order_by(PriceDaily.date.desc()).limit(1)
            ).first()
            if metric is None or bar is None:
                continue
            results.append(
                assess(
                    symbol.ticker, float(bar.close), float(metric.atr_14),
                    equity=equity, stop_atr=stop_atr, limits=limits,
                )
            )

    if not results:
        console.print(
            "[yellow]No symbols with metrics.[/] Run 'screener metrics build' first."
        )
        raise typer.Exit(code=1)

    wanted = {
        "good": {"good"},
        "tradeable": {"good", "marginal"},
        "all": {"good", "marginal", "unusable"},
    }.get(show.strip().lower())
    if wanted is None:
        console.print(f"[red]Unknown --show value {show!r}.[/] Expected all, good or tradeable.")
        raise typer.Exit(code=1)

    order = {"good": 0, "marginal": 1, "unusable": 2}
    rows = sorted(
        (r for r in results if r.verdict in wanted),
        key=lambda r: (order[r.verdict], -r.shares),
    )

    table = Table(title=f"Tradeable at ${equity:,.0f} · {risk_pct:.1%} risk · {stop_atr}× ATR stop")
    for col in ("Symbol", "Price", "Stop", "Shares", "Position", "% eq", "Risk", "Verdict"):
        table.add_column(col, justify="right" if col != "Symbol" else "left")

    colour = {"good": "green", "marginal": "yellow", "unusable": "red"}
    for r in rows:
        table.add_row(
            r.ticker, f"{float(r.price):.2f}", f"{float(r.stop_distance):.2f}",
            str(r.shares), f"${float(r.position_value):,.0f}",
            f"{r.pct_of_equity:.0%}",
            f"{r.effective_risk_pct:.2%}",
            f"[{colour[r.verdict]}]{r.verdict}[/]"
            + (" [dim]capped[/]" if r.concentration_capped else ""),
        )
    console.print(table)

    counts = {v: sum(1 for r in results if r.verdict == v) for v in order}
    console.print(
        f"\n[green]{counts['good']} good[/] · "
        f"[yellow]{counts['marginal']} marginal[/] · "
        f"[red]{counts['unusable']} unusable[/] of {len(results)}"
    )

    ceiling = max_workable_price(0.02, equity=equity, stop_atr=stop_atr, limits=limits)
    floor = min_workable_atr_pct(equity=equity, stop_atr=stop_atr, limits=limits)
    console.print(
        f"[bold]At this account size, look for:[/] ATR above [bold]{floor:.1%}[/] "
        f"so the cap does not bind, and price below roughly "
        f"[bold]${ceiling:,.0f}[/] at that volatility so ten shares is reachable."
    )
    if counts["good"] < 10:
        console.print(
            "[yellow]Most of this universe is too expensive for the account.[/] "
            "That is a universe problem, not a strategy problem — ingest more "
            "mid-priced names rather than loosening the risk rules."
        )


@universe_app.command("coverage")
def universe_coverage(
    tickers: str | None = typer.Option(
        None, "--tickers",
        help="Override the default probe list. Comma-separated.",
    ),
    provider_name: str = typer.Option("auto", "--provider"),
    start: str = typer.Option("2010-01-01", "--start"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """MEASURE SURVIVORSHIP: does the data provider carry delisted companies?

    Every backtest result carries an unquantified caveat -- the universe holds
    only companies that still exist, so any strategy is measured on survivors.
    This turns the caveat into a number.

    ACQUISITIONS AND FAILURES ARE REPORTED SEPARATELY, because they bias
    results in opposite directions and a single percentage hides that. An
    acquisition usually ends at a premium, so missing them understates
    returns. A bankruptcy ends near zero, so missing them OVERSTATES returns --
    and value screens select distressed companies, which is precisely where
    the missing cases would have been.

    A symbol that is supposedly delisted but still returns recent bars is
    reported as suspect rather than as coverage: either the probe is wrong or
    the provider is serving a stale or reused series.
    """
    _configure_logging(verbose)
    from .providers.base import BarRequest, ProviderError

    settings = get_settings()
    choice = provider_name.strip().lower()
    if choice == "auto":
        choice = "tiingo" if settings.has_tiingo_credentials else "alpaca"

    try:
        if choice == "tiingo":
            from .providers.tiingo import TiingoProvider
            provider = TiingoProvider(settings)
        else:
            from .providers.alpaca import AlpacaProvider
            provider = AlpacaProvider(settings)
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    # Split deliberately. These bias results in opposite directions.
    ACQUIRED = {
        "TWTR": "acquired 2022", "ATVI": "acquired 2023", "CERN": "acquired 2022",
        "XLNX": "acquired 2022", "MRO": "acquired 2024", "VMW": "acquired 2023",
    }
    FAILED = {
        "FRC": "failed 2023", "SIVB": "failed 2023", "SBNY": "failed 2023",
        "BBBY": "bankrupt 2023", "YELL": "bankrupt 2023", "RAD": "bankrupt 2023",
    }
    labels = {**ACQUIRED, **FAILED}

    probes = (
        [t.strip().upper() for t in tickers.split(",") if t.strip()]
        if tickers else list(labels)
    )
    start_date = date.fromisoformat(start)
    end_date = date.today()
    recent_cutoff = end_date - timedelta(days=45)

    console.print(f"Probing [bold]{len(probes)}[/] delisted symbol(s) against {choice}...")

    table = Table(title=f"Delisted-ticker coverage — {choice}")
    for col in ("Symbol", "Event", "Bars", "First", "Last", "Verdict"):
        table.add_column(col, justify="right" if col == "Bars" else "left")

    covered: dict[str, list[str]] = {"acquired": [], "failed": []}
    suspect: list[str] = []
    absent: list[str] = []

    for ticker in probes:
        try:
            frame = provider.get_daily_bars(
                BarRequest((ticker,), start_date, end_date, "raw")
            )
        except ProviderError as exc:
            table.add_row(ticker, labels.get(ticker, "-"), "-", "-", "-",
                          f"[yellow]error: {str(exc)[:34]}[/]")
            continue

        event = labels.get(ticker, "unknown")
        if frame.empty:
            absent.append(ticker)
            table.add_row(ticker, event, "0", "-", "-", "[red]absent[/]")
            continue

        dates = frame.index.get_level_values("date")
        last_bar = max(dates)

        if last_bar >= recent_cutoff:
            # Still trading, so this is not evidence of delisted coverage.
            suspect.append(ticker)
            verdict = "[yellow]still trading — suspect[/]"
        else:
            bucket = "failed" if ticker in FAILED else "acquired"
            covered[bucket].append(ticker)
            verdict = "[green]delisted series present[/]"

        table.add_row(
            ticker, event, f"{len(frame):,}", str(min(dates)), str(last_bar), verdict
        )

    console.print(table)
    provider.close()

    acquired_probes = [t for t in probes if t in ACQUIRED]
    failed_probes = [t for t in probes if t in FAILED]

    def share(found: list[str], probed: list[str]) -> str:
        return f"{len(found)}/{len(probed)}" if probed else "0/0"

    console.print(
        f"\n[bold]Acquisitions:[/] {share(covered['acquired'], acquired_probes)} present"
    )
    console.print(
        f"[bold]Failures:[/]     {share(covered['failed'], failed_probes)} present"
    )
    if suspect:
        console.print(
            f"[yellow]Suspect:[/] {', '.join(suspect)} — still returning recent bars "
            "despite being delisted. Either the probe is wrong or the provider is "
            "serving a stale or reused series. Do not count these as coverage."
        )

    if failed_probes and not covered["failed"]:
        console.print(
            "\n[red bold]No coverage of companies that FAILED.[/] This is the half "
            "that matters most. A bankruptcy ends near zero, so its absence "
            "OVERSTATES every backtested return -- and value screens select "
            "distressed companies, which is exactly where the missing cases "
            "would have been. The survivorship caveat stays on every result."
        )
    elif len(covered["failed"]) < len(failed_probes):
        console.print(
            "\n[yellow bold]Partial coverage of failures.[/] Better than none. "
            "Any cross-sectional result still leans toward survivors by an "
            "unmeasured amount."
        )
    else:
        console.print(
            "\n[green bold]Failures and acquisitions both covered.[/] A "
            "delisted-inclusive universe is buildable. Rebuild it before "
            "trusting any cross-sectional result."
        )

    console.print(
        "[dim]Absence can also mean the symbol was never covered rather than "
        "dropped on delisting. Treat this as a floor, not a measurement.[/]"
    )


@app.command("ingest-fundamentals")
def ingest_fundamentals_cmd(
    symbols: str | None = typer.Option(None, "--symbols", "-s", help="Omit for all."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fetch reported financials from SEC EDGAR's XBRL API.

    One request per company returns its whole filing history, so this is slow
    and runs once. Every version of every restated figure is stored, keyed on
    the accession number -- that is what makes it possible to ask what was
    reported as of a past date rather than what is true now.
    """
    _configure_logging(verbose)
    from .ingest.fundamentals import ingest_fundamentals
    from .providers.base import ProviderError
    from .providers.edgar import EdgarProvider

    try:
        provider = EdgarProvider(get_settings())
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    with session_scope() as session:
        stmt = select(Symbol).order_by(Symbol.ticker)
        if symbols:
            wanted = [t.strip().upper() for t in symbols.split(",") if t.strip()]
            stmt = stmt.where(Symbol.ticker.in_(wanted))
        tickers = [s.ticker for s in session.scalars(stmt)]

        if not tickers:
            console.print("[red]No symbols stored.[/] Run 'screener ingest' first.")
            raise typer.Exit(code=1)

        console.print(
            f"Fetching financials for [bold]{len(tickers)}[/] symbol(s). Each "
            "response covers the full filing history and can be tens of "
            "megabytes, so allow a few seconds per symbol."
        )
        summary = ingest_fundamentals(session, provider, tickers)

    provider.close()
    console.print(f"[green]{summary.summary()}[/]")
    for failure in summary.failed[:10]:
        console.print(f"  [yellow]{failure.ticker}[/]: {failure.error}")


@app.command("value")
def value_cmd(
    on: str | None = typer.Option(None, "--on", help="Date, YYYY-MM-DD. Defaults to today."),
    symbols: str | None = typer.Option(None, "--symbols", "-s"),
    sort: str = typer.Option("price_to_book", "--sort", help="Column to rank on."),
    limit: int = typer.Option(25, "--limit", "-n"),
) -> None:
    """Value screen from point-in-time financials.

    Every figure shown is one that had been FILED on or before the chosen date.
    A period ends months before its numbers are public, so screening on the
    period date would use information nobody had -- the 'reported' and 'lag'
    columns show which filing each row rests on and how stale it was.

    No ranking here implies an edge. None of these screens has been validated
    on this data.
    """
    from .fundamentals.pit import facts_as_of
    from .fundamentals.ratios import CONCEPTS, snapshot

    as_of = date.fromisoformat(on) if on else date.today()

    with session_scope() as session:
        stmt = select(Symbol).order_by(Symbol.ticker)
        if symbols:
            wanted = [t.strip().upper() for t in symbols.split(",") if t.strip()]
            stmt = stmt.where(Symbol.ticker.in_(wanted))

        rows = []
        for symbol in session.scalars(stmt):
            bar = session.scalars(
                select(PriceDaily)
                .where(PriceDaily.symbol_id == symbol.id, PriceDaily.date <= as_of)
                .order_by(PriceDaily.date.desc())
                .limit(1)
            ).first()
            if bar is None:
                continue
            facts = facts_as_of(session, symbol.id, CONCEPTS, as_of)
            if not facts:
                continue
            rows.append(snapshot(symbol.ticker, float(bar.close), facts))

    if not rows:
        console.print(
            "[yellow]No fundamentals stored for this date.[/] "
            "Run 'screener ingest-fundamentals' first."
        )
        raise typer.Exit(code=1)

    def key(row):
        value = getattr(row, sort, None)
        return (value is None, value if value is not None else 0)

    rows.sort(key=key)

    table = Table(title=f"Value screen — as filed on or before {as_of}")
    for col in ("Symbol", "Price", "P/B", "NCAV/sh", "NetCash/sh",
                "GrossProf", "ROA", "Reported", "Lag"):
        table.add_column(col, justify="right" if col != "Symbol" else "left")

    def fmt(value, spec="{:.2f}"):
        return "-" if value is None else spec.format(value)

    for row in rows[:limit]:
        flags = ""
        if row.below_ncav:
            flags = " [green]net-net[/]"
        elif row.below_net_cash:
            flags = " [green]<cash[/]"
        table.add_row(
            row.ticker + flags,
            fmt(row.price),
            fmt(row.price_to_book),
            fmt(row.ncav_per_share),
            fmt(row.net_cash_per_share),
            fmt(row.gross_profitability, "{:.3f}"),
            fmt(row.return_on_assets, "{:.3f}"),
            row.reported_as_of or "-",
            f"{row.lag_days}d" if row.lag_days is not None else "-",
        )
    console.print(table)
    console.print(
        f"[dim]{len(rows)} symbol(s) with filed financials. Lag is the gap "
        "between period end and filing date -- the window in which the figure "
        "existed but nobody could see it.[/]"
    )


@app.command("status")
def status_cmd() -> None:
    """Where the project stands, in one screen.

    Written for two readers: the operator returning after a gap, and a fresh
    Claude session that has none of the conversation behind the repository.
    Both need the same thing -- what data exists, what has been run, what has
    been decided, and what to do next.
    """
    from sqlalchemy import func

    from .backtest.splits import SPLITS
    from .db.models import EarningsEvent, Fundamental, MetricsDaily, ResearchRun

    settings = get_settings()
    next_steps: list[str] = []

    with session_scope() as session:
        symbols = list(session.scalars(select(Symbol).order_by(Symbol.ticker)))
        bar_count = session.scalar(select(func.count()).select_from(PriceDaily)) or 0
        first = session.scalar(select(func.min(PriceDaily.date)))
        last = session.scalar(select(func.max(PriceDaily.date)))
        metric_rows = session.scalar(select(func.count()).select_from(MetricsDaily)) or 0
        fundamental_rows = session.scalar(select(func.count()).select_from(Fundamental)) or 0
        earnings_rows = session.scalar(select(func.count()).select_from(EarningsEvent)) or 0
        runs = list(session.scalars(select(ResearchRun)))

        data = Table(title="Data", show_header=False)
        data.add_column("k")
        data.add_column("v", justify="right")
        data.add_row("Symbols", f"{len(symbols)}")
        data.add_row("Price bars", f"{bar_count:,}")
        data.add_row("Range", f"{first} → {last}" if first else "[red]none[/]")
        data.add_row("Metrics rows", f"{metric_rows:,}")
        data.add_row(
            "Fundamentals",
            f"{fundamental_rows:,}" if fundamental_rows else "[yellow]none[/]",
        )
        data.add_row(
            "Earnings dates",
            f"{earnings_rows:,}" if earnings_rows else "[yellow]none[/]",
        )
        data.add_row(
            "Provider",
            "tiingo" if settings.has_tiingo_credentials else "alpaca (recent years only)",
        )
        console.print(data)

        if not bar_count:
            next_steps.append("screener ingest --symbols SPY,QQQ,AAPL --start 2010-01-01")
        elif not metric_rows:
            next_steps.append("screener metrics build")
        if not fundamental_rows:
            next_steps.append("screener ingest-fundamentals   # unlocks the value screens")
        if not earnings_rows:
            next_steps.append("screener ingest-earnings       # unlocks h6 earnings drift")

        # -- research ------------------------------------------------------
        if runs:
            spent: dict[tuple[str, str], set[str]] = {}
            passed = 0
            for run in runs:
                spent.setdefault((run.hypothesis, run.split), set()).add(run.config_hash)
                if run.criteria_passed:
                    passed += 1

            research = Table(title="Research")
            for col in ("Hypothesis", "Split", "Configs", "Budget"):
                research.add_column(col, justify="left" if col == "Hypothesis" else "right")
            for (hypothesis, split_name), hashes in sorted(spent.items()):
                limit = SPLITS[split_name].config_budget if split_name in SPLITS else None
                research.add_row(
                    hypothesis, split_name, str(len(hashes)),
                    "unlimited" if limit is None else f"{len(hashes)}/{limit}",
                )
            console.print(research)

            console.print(
                f"[bold]{len(runs)}[/] recorded run(s); "
                + (
                    f"[green]{passed}[/] met every pre-registered criterion."
                    if passed
                    else "[yellow]none has met every pre-registered criterion.[/]"
                )
            )
        else:
            console.print("[yellow]No backtests recorded yet.[/]")
            next_steps.append("screener research explore --battery all")

    # -- orientation -------------------------------------------------------
    console.print(
        "\n[bold]Read before proposing anything:[/] CLAUDE.md, then "
        "docs/06-DIAGNOSTIC-RESULTS.md and docs/07-STOP-DESIGN-QUESTION.md "
        "for what the data has already said, and docs/09-REJECTED.md for what "
        "was deliberately not built and why."
    )

    if next_steps:
        console.print("\n[bold]Next:[/]")
        for step in next_steps:
            console.print(f"  {step}")


@app.command("news")
def news_cmd(
    symbols: str | None = typer.Option(None, "--symbols", "-s", help="Omit for all stored."),
    days: int = typer.Option(3, "--days", "-d", help="Look back this many days."),
    limit: int = typer.Option(40, "--limit", "-n"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Recent headlines for the symbols you follow.

    News here is CONTEXT, not signal. By publication the move has usually
    happened, and nothing in this platform can measure whether a headline
    predicts anything. Its honest use is explaining a move you can already see
    and flagging that something happened before you size into it -- a stock up
    9% with no news is a different situation from the same move on a guidance
    raise.

    No sentiment score is computed. A number derived from headlines would be
    false precision.
    """
    _configure_logging(verbose)
    from .providers.base import ProviderError
    from .providers.news import AlpacaNewsProvider, headlines_by_symbol

    try:
        provider = AlpacaNewsProvider(get_settings())
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    with session_scope() as session:
        stmt = select(Symbol).order_by(Symbol.ticker)
        if symbols:
            wanted = [t.strip().upper() for t in symbols.split(",") if t.strip()]
            stmt = stmt.where(Symbol.ticker.in_(wanted))
        tickers = tuple(s.ticker for s in session.scalars(stmt))

    if not tickers:
        console.print("[red]No symbols stored.[/] Run 'screener ingest' first.")
        raise typer.Exit(code=1)

    start = date.today() - timedelta(days=days)
    try:
        items = provider.get_news(tickers, start, date.today(), limit=limit)
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc
    finally:
        provider.close()

    if not items:
        console.print(f"[yellow]No headlines for these symbols in the last {days} day(s).[/]")
        return

    grouped = headlines_by_symbol(items)
    table = Table(title=f"Headlines — last {days} day(s)")
    for col in ("When", "Symbols", "Headline", "Source"):
        table.add_column(col, overflow="fold" if col == "Headline" else None)

    for item in items:
        mentioned = ", ".join(item.symbols[:3]) + ("…" if len(item.symbols) > 3 else "")
        table.add_row(
            item.created_at.strftime("%m-%d %H:%M"),
            mentioned,
            item.headline[:110],
            item.source,
        )
    console.print(table)
    busiest = sorted(grouped.items(), key=lambda kv: -len(kv[1]))[:5]
    console.print(
        "[dim]Most mentioned: "
        + ", ".join(f"{t} ({len(v)})" for t, v in busiest)
        + " — mention count is attention, not direction.[/]"
    )


@app.command("option")
def option_cmd(
    symbol: str = typer.Argument(..., help="Underlying ticker."),
    hold: int = typer.Option(10, "--hold", help="Planned holding period in days."),
    stop_atr: float = typer.Option(2.0, "--stop-atr", help="Stop distance in ATR(14)."),
    equity: float = typer.Option(10_000.0, "--equity"),
    risk_pct: float = typer.Option(0.01, "--risk-pct"),
    target_delta: float = typer.Option(0.75, "--delta", help="Aim for this delta."),
    feed: str = typer.Option("indicative", "--feed", help="indicative or opra."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Pick the least-bad contract for a swing plan, and price what it costs.

    This does NOT decide whether options are the right vehicle. It answers a
    narrower question: given an entry, a stop and a holding period, which
    contract expresses that view with the least friction, and what is the
    friction?

    The selection rules are deliberately restrictive -- deep in the money,
    expiry at least twice the hold, never spanning earnings, tight spreads --
    because the default retail choice of a cheap out-of-the-money option near
    expiry maximises decay and buys leverage this account size does not need.

    The stock alternative is always shown alongside. That comparison is the
    point.
    """
    _configure_logging(verbose)
    from .ingest.events import earnings_dates
    from .options.provider import AlpacaOptionsProvider
    from .options.select import (
        SelectionRules,
        choose_contract,
        eligible_contracts,
        plan_option_trade,
    )
    from .providers.base import ProviderError

    ticker = symbol.strip().upper()
    today = date.today()

    with session_scope() as session:
        sym = session.scalar(select(Symbol).where(Symbol.ticker == ticker))
        if sym is None:
            console.print(f"[red]{ticker} not ingested.[/] Run 'screener ingest' first.")
            raise typer.Exit(code=1)
        bar = session.scalars(
            select(PriceDaily).where(PriceDaily.symbol_id == sym.id)
            .order_by(PriceDaily.date.desc()).limit(1)
        ).first()
        if bar is None:
            console.print(f"[red]No bars stored for {ticker}.[/]")
            raise typer.Exit(code=1)

        from .db.models import MetricsDaily
        metric = session.scalars(
            select(MetricsDaily).where(MetricsDaily.symbol_id == sym.id)
            .order_by(MetricsDaily.date.desc()).limit(1)
        ).first()
        upcoming = [d for d in earnings_dates(session, sym.id) if d >= today]

    price = float(bar.close)
    atr = float(metric.atr_14) if metric and metric.atr_14 else price * 0.02
    stop = price - stop_atr * atr
    earnings_in = (upcoming[0] - today).days if upcoming else None

    console.print(
        f"[bold]{ticker}[/] at {price:.2f} · ATR {atr:.2f} · stop {stop:.2f} "
        f"· hold {hold}d"
        + (f" · earnings in {earnings_in}d" if earnings_in is not None else "")
    )

    try:
        provider = AlpacaOptionsProvider(get_settings())
        chain = provider.get_chain(
            ticker, expiry_after=today, expiry_before=today + timedelta(days=180),
            feed=feed,
        )
        provider.close()
    except ProviderError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    if not chain:
        console.print("[yellow]No contracts returned for this underlying.[/]")
        raise typer.Exit(code=1)

    rules = SelectionRules(target_delta=target_delta)
    kept, dropped = eligible_contracts(
        chain, as_of=today, hold_days=hold, earnings_in_days=earnings_in, rules=rules
    )
    console.print(
        f"[dim]{len(chain)} contract(s) in the chain, {len(kept)} eligible.[/]"
    )
    if dropped:
        for reason, count in sorted(dropped.items(), key=lambda kv: -kv[1])[:5]:
            console.print(f"  [dim]{count:>4} — {reason}[/]")

    contract = choose_contract(
        chain, as_of=today, hold_days=hold, earnings_in_days=earnings_in, rules=rules
    )
    if contract is None:
        console.print(
            "\n[yellow]No contract expresses this trade acceptably.[/] That is a "
            "result, not a failure — trade the stock, or wait."
        )
        raise typer.Exit(code=1)

    plan = plan_option_trade(
        contract, underlying_price=price, stop_price=stop, hold_days=hold,
        risk_budget=equity * risk_pct, cash_available=equity, as_of=today, rules=rules,
    )

    table = Table(title=f"{contract.symbol}")
    table.add_column("k")
    table.add_column("v", justify="right")
    table.add_row("Strike / expiry",
                  f"{contract.strike:.2f} · {contract.expiry} "
                  f"({contract.days_to_expiry(today)}d)")
    table.add_row("Bid / ask", f"{contract.bid:.2f} / {contract.ask:.2f}")
    table.add_row("Spread", f"{contract.spread:.2f} "
                            f"({(contract.spread_pct or 0):.1%} of mid)")
    table.add_row("Delta / theta",
                  f"{contract.delta if contract.delta is not None else '-'} · "
                  f"{contract.theta if contract.theta is not None else '-'}")
    table.add_row("Intrinsic / time value",
                  f"{contract.intrinsic(price):.2f} / {contract.extrinsic(price):.2f}")
    table.add_row("", "")
    table.add_row("Contracts", str(plan.contracts))
    table.add_row("Cost", f"${plan.cost:,.2f}")
    table.add_row("Loss if stop is hit", f"${plan.stop_loss_estimate:,.2f}")
    table.add_row("Spread cost (round trip)", f"${plan.spread_cost:,.2f}")
    table.add_row(f"Decay over {hold}d", f"${plan.decay_cost:,.2f}")
    table.add_row("Friction before direction", f"{plan.friction_pct:.1%} of cost")
    table.add_row("Breakeven at expiry", f"{plan.breakeven:.2f}")
    table.add_row("Effective leverage",
                  f"{plan.effective_leverage:.1f}x" if plan.effective_leverage else "-")
    console.print(table)

    console.print(
        f"[bold]The stock alternative:[/] same ${equity * risk_pct:,.0f} of risk buys "
        f"[bold]{plan.shares_equivalent}[/] shares at {price:.2f} "
        f"(${plan.shares_equivalent * price:,.0f}), breakeven {plan.stock_breakeven:.2f} "
        f"versus {plan.breakeven:.2f} for the option."
    )

    if plan.rejections:
        for reason in plan.rejections:
            console.print(f"[red]Rejected:[/] {reason}")
    else:
        console.print(
            "\n[dim]Quotes on the free tier are indicative, not real-time OPRA. "
            "Confirm the actual market in your broker before sending anything.[/]"
        )


@app.command("config")
def config_cmd() -> None:
    """Show what is configured, without printing any secret.

    Exists because "is my key being read?" is otherwise unanswerable without
    guessing, and a key that is present but unread looks identical to a key
    that was never pasted.
    """
    from .config import PROJECT_ROOT

    settings = get_settings()
    env_file = PROJECT_ROOT / ".env"

    table = Table(title="Configuration")
    for col in ("Setting", "Value", "Status"):
        table.add_column(col)

    if env_file.exists():
        table.add_row(".env file", str(env_file), "[green]found[/]")
    else:
        table.add_row(
            ".env file", str(env_file),
            "[red]MISSING[/] -- copy .env.example to .env",
        )

    url = settings.database_url
    table.add_row("database", url.rsplit("@", 1)[-1] if "@" in url else url, "")

    alpaca = settings.has_alpaca_credentials
    table.add_row(
        "ALPACA_API_KEY_ID / SECRET",
        "set" if alpaca else "not set",
        "[green]ready[/]" if alpaca else "[yellow]execution unavailable[/]",
    )

    tiingo = settings.has_tiingo_credentials
    table.add_row(
        "TIINGO_API_KEY",
        "set" if tiingo else "not set",
        "[green]ready[/]" if tiingo else "[yellow]deep history unavailable[/]",
    )

    console.print(table)

    if tiingo:
        console.print(
            "[green]'screener ingest' will use Tiingo[/] -- history back to the 1990s."
        )
    elif alpaca:
        console.print(
            "[yellow]'screener ingest' will use Alpaca[/] -- its free tier only "
            "serves the most recent years (measured: first bar 2020-07-27).\n"
            "Add TIINGO_API_KEY to .env for full history. Free key at tiingo.com."
        )
    else:
        console.print("[red]No market-data provider is configured.[/] See .env.example.")

@app.command("verify")
def verify_cmd(
    symbols: str = typer.Option("SPY,QQQ,AAPL", "--symbols", "-s"),
    tail: int = typer.Option(10, "--tail", "-n", help="Most recent N bars to compare."),
    reference: str = typer.Option(
        "auto", "--reference",
        help="auto (try each in turn), yahoo, or stooq.",
    ),
    tolerance_bps: float = typer.Option(
        25.0, "--tolerance-bps",
        help="Price agreement tolerance in basis points. 25 = 0.25%.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """PHASE 1 GATE: cross-check stored bars against an independent source.

    Unit tests prove the code is internally consistent. This proves the DATA is
    right, by comparing against a source that shares no code, no vendor, and no
    bugs with our ingestion path.

    Compares the MOST RECENT bars deliberately: over a short window a split is
    very unlikely, so a difference in adjustment policy cannot explain a
    mismatch.

    Prices are checked for MATERIAL agreement, not equality. The free Alpaca
    feed is IEX-only -- one venue, not the consolidated tape the reference
    reports -- so the two see different trades and a few basis points of
    disagreement is two correct measurements of the same session. Demanding an
    exact match would fail the gate on correct data. What the gate catches is
    the class of errors that would poison everything downstream: wrong symbol,
    misaligned dates, a missed split, stale bars. All are orders of magnitude
    larger than venue noise.
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
        result = compare_bars(
            ticker, ours, theirs,
            reference_name=answered, price_tolerance_bps=tolerance_bps,
        )
        if result.dates_compared == 0:
            console.print(f"[yellow]{result.summary()}[/]")
            skipped.append(ticker)
            continue
        colour = "green" if result.passed else "red"
        console.print(f"[{colour}]{result.summary()}[/]")
        (verified if result.passed else failed).append(ticker)

        if result.price_mismatches:
            table = Table(title=f"{ticker} price mismatches")
            for col in ("Date", "Field", "Ours", answered.title(), "Diff", "bps"):
                table.add_column(col)
            for m in result.price_mismatches[:15]:
                table.add_row(
                    str(m.trade_date), m.field, f"{m.ours:.4f}",
                    f"{m.theirs:.4f}", f"{m.difference:+.4f}",
                    f"{m.bps_difference:+.1f}",
                )
            console.print(table)

        if result.missing_from_ours:
            console.print(
                "  [red]sessions the reference has and we do not:[/] "
                + ", ".join(str(d) for d in result.missing_from_ours[:10])
            )

        if result.systematic_bias:
            console.print(
                "  [red]differences are one-directional, not symmetric noise[/] -- "
                "that is the signature of an adjustment or date-alignment error, "
                "not of two venues seeing different trades."
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
    r_multiple: float | None = typer.Option(
        None, "--r-multiple",
        help="Profit target in R. Omit for the hypothesis default; 0 disables. "
             "H1 has NO target in its specification -- it exits on time or stop.",
    ),
    time_limit: int | None = typer.Option(
        None, "--time-limit",
        help="Bars held before a time exit. Omit to use --hold. 0 disables.",
    ),
    slippage_bps: float = typer.Option(5.0, "--slippage-bps"),
    trend_filter: bool = typer.Option(True, "--trend-filter/--no-trend-filter"),
    use_stop: bool = typer.Option(
        True, "--stop/--no-stop",
        help="--no-stop removes the stop entirely. A diagnostic, not a way to trade: "
             "it isolates whether the entry rule or the exit design is losing money.",
    ),
    displacement: float | None = typer.Option(None, "--displacement", help="H2 only, in ATR."),
    hold: int = typer.Option(
        5, "--hold",
        help="H1 hold horizon in days: the time exit, and the rebalance interval.",
    ),
    top_pct: float = typer.Option(0.10, "--top-pct", help="H1 selection cutoff."),
    stop_atr: float = typer.Option(2.0, "--stop-atr", help="H1 stop, in ATR(14)."),
    rs_lookback: int = typer.Option(63, "--rs-lookback", help="H1 relative-strength window."),
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
    from .backtest.runner import HYPOTHESES
    from .backtest.splits import get_split
    from .metrics.compute import load_bars
    from .universe.build import universe_members

    key = hypothesis.strip().lower()
    if key not in HYPOTHESES:
        console.print(
            f"[red]Unknown hypothesis {hypothesis!r}.[/] Expected one of "
            f"{', '.join(HYPOTHESES)}."
        )
        raise typer.Exit(code=1)

    chosen = get_split(split)
    console.print(f"[dim]{chosen.describe()}[/]")

    # Defaults follow each hypothesis's own specification rather than one
    # shared setting. H1 (docs/03) exits on TIME or STOP and has no profit
    # target; H2/H3/H4 surface over R targets. Applying a 2R target to H1
    # tests something the specification does not describe.
    if time_limit is None:
        time_limit = hold if key == "h1" else 10
    if r_multiple is None:
        r_multiple = None if key == "h1" else 2.0

    config = {
        "hypothesis": key,
        "symbols": symbols or "all",
        "universe": universe_name,
        "r_multiple": r_multiple or None,
        "time_limit": time_limit or None,
        "slippage_bps": slippage_bps,
        "trend_filter": trend_filter,
        "use_stop": use_stop,
        "displacement": displacement,
        "hold": hold,
        "top_pct": top_pct,
        "stop_atr": stop_atr if key == "h1" else None,
        "rs_lookback": rs_lookback if key == "h1" else None,
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

        from .backtest.runner import RunConfig, build_candidates

        run_config = RunConfig(
            hypothesis=key, equity=equity, r_multiple=r_multiple,
            time_limit=time_limit, slippage_bps=slippage_bps,
            trend_filter=trend_filter, use_stop=use_stop,
            displacement=displacement, hold=hold, top_pct=top_pct,
            stop_atr=stop_atr, rs_lookback=rs_lookback,
        ).resolved()

        events = _load_events(session, bars_by_symbol) if key == "h6" else None
        try:
            candidates = build_candidates(
                bars_by_symbol, run_config, in_universe, events_by_symbol=events
            )
        except ValueError as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(code=1) from exc

        console.print(f"{len(candidates):,} candidate signal(s) before portfolio limits.")

        result = run_backtest(
            candidates, bars_by_symbol,
            start=chosen.start, end=chosen.end,
            starting_equity=equity,
            exit_rule=ExitRule(
                r_multiple=r_multiple or None,
                time_limit=time_limit or None,
                use_stop=use_stop,
            ),
            costs=CostModel(slippage_bps=slippage_bps),
        )

        stats = summarize(result)
        regimes = by_regime(result.trades, equity)

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
    if stats.exits:
        total = sum(stats.exits.values())
        breakdown = ", ".join(
            f"{reason} {count} ({count / total:.0%})"
            for reason, count in sorted(stats.exits.items(), key=lambda kv: -kv[1])
        )
        console.print(f"[dim]exits: {breakdown}[/]")
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
        for col in ("Regime", "Trades", "Expectancy", "Return"):
            table.add_column(col, justify="right" if col != "Regime" else "left")
        for name, bucket in regimes.items():
            table.add_row(
                name, str(bucket.trades),
                f"{bucket.expectancy_r:+.3f}R", f"{bucket.total_return_pct:+.1%}",
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


@backtest_app.command("surface")
def backtest_surface(
    hypothesis: str = typer.Option(..., "--hypothesis", "-h", help="h1, h2, h3 or h4."),
    vary: list[str] = VARY_OPTION,
    split: str = typer.Option("development", "--split"),
    symbols: str | None = typer.Option(None, "--symbols", "-s"),
    universe_name: str | None = typer.Option(None, "--universe"),
    equity: float = typer.Option(10_000.0, "--equity"),
    slippage_bps: float = typer.Option(5.0, "--slippage-bps"),
    trend_filter: bool = typer.Option(True, "--trend-filter/--no-trend-filter"),
    use_stop: bool = typer.Option(True, "--stop/--no-stop"),
    random_iterations: int = typer.Option(0, "--random-iterations"),
    seed: int = typer.Option(0, "--seed"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Sweep a parameter range and classify the resulting surface.

    Answers a parameter question the way docs/03 0.7 requires -- by looking at
    the whole neighbourhood rather than picking the best value:

      PLATEAU    broad positive region -> take its CENTRE, never the peak
      SPIKE      one value works, neighbours fail -> noise; reject it
      NONE       nothing positive -> evidence AGAINST the hypothesis

    Development split only. Surfaces are exploration, and exploration on a
    split that carries evidential weight is how a budget gets spent without
    anyone deciding to spend it.
    """
    _configure_logging(verbose)
    from .backtest import budget
    from .backtest.runner import (
        HYPOTHESES,
        RunConfig,
        _entry_key,
        build_candidates,
        evaluate,
        load_symbol_bars,
        universe_filter,
    )
    from .backtest.splits import get_split
    from .backtest.surface import Cell, analyse, parameter_grid, parse_vary

    key = hypothesis.strip().lower()
    if key not in HYPOTHESES:
        console.print(f"[red]Unknown hypothesis {hypothesis!r}.[/] Expected one of h1-h4.")
        raise typer.Exit(code=1)

    chosen = get_split(split)
    if chosen.carries_evidence:
        console.print(
            f"[red]Surfaces are development-split only.[/] The {chosen.name} split "
            f"allows {chosen.config_budget} configuration(s) per hypothesis "
            "(docs/03 0.8); a sweep would spend that in one command.\n"
            "Explore on development, then run the chosen configuration once here."
        )
        raise typer.Exit(code=1)

    try:
        varied = parse_vary(vary)
    except ValueError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    grid = parameter_grid(varied)
    base_fields = set(RunConfig(hypothesis=key).__dict__)
    unknown = [name for name in varied if name not in base_fields]
    if unknown:
        console.print(
            f"[red]Unknown parameter(s): {', '.join(unknown)}.[/]\n"
            f"Available: {', '.join(sorted(base_fields - {'hypothesis'}))}"
        )
        raise typer.Exit(code=1)

    console.print(f"[dim]{chosen.describe()}[/]")
    console.print(
        f"Sweeping [bold]{len(grid)}[/] configuration(s) of {key} over "
        f"{', '.join(f'{k}({len(v)})' for k, v in sorted(varied.items()))}..."
    )

    cells: list[Cell] = []
    with session_scope() as session:
        bars_by_symbol = load_symbol_bars(session, symbols)
        if not bars_by_symbol:
            console.print("[red]No bars stored.[/] Run 'screener ingest' first.")
            raise typer.Exit(code=1)
        universe = universe_filter(session, universe_name)
        surface_events = _load_events(session, bars_by_symbol) if key == "h6" else None

        # Signals depend only on entry-side parameters, so cells that share
        # them share one generation pass. On an exit-only sweep this is one
        # pass instead of one per cell.
        candidate_cache: dict[tuple, list] = {}

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            BarColumn(), TaskProgressColumn(), console=console,
        ) as progress:
            task = progress.add_task("sweeping", total=len(grid))
            for params in grid:
                config = RunConfig(
                    hypothesis=key, equity=equity, slippage_bps=slippage_bps,
                    trend_filter=trend_filter, use_stop=use_stop, **params,
                )
                entry_key = _entry_key(config)
                if entry_key not in candidate_cache:
                    candidate_cache[entry_key] = build_candidates(
                        bars_by_symbol, config, universe,
                        events_by_symbol=surface_events,
                    )

                outcome = evaluate(
                    candidate_cache[entry_key], bars_by_symbol, config, chosen,
                    random_iterations=random_iterations, seed=seed,
                )
                cells.append(Cell(params=params, outcome=outcome))
                budget.record(
                    session, hypothesis=key, split=chosen,
                    config=outcome.config.as_dict(),
                    trades=outcome.stats.trades,
                    expectancy_r=outcome.stats.expectancy_r,
                    profit_factor=outcome.stats.profit_factor,
                    max_drawdown_pct=outcome.stats.max_drawdown_pct,
                    total_return_pct=outcome.stats.total_return_pct,
                    random_percentile=outcome.random_percentile,
                    criteria_passed=outcome.passed,
                    notes="surface sweep",
                )
                progress.advance(task)

    verdict = analyse(cells, varied)

    table = Table(title=f"{key} parameter surface -- {chosen.name} split")
    for name in sorted(varied):
        table.add_column(name, justify="right")
    for col in ("Trades", "Expectancy", "PF", "MaxDD", "Return"):
        table.add_column(col, justify="right")

    for cell in sorted(cells, key=lambda c: -c.expectancy):
        stats = cell.outcome.stats
        marker = ""
        if verdict.recommended is not None and cell.key == verdict.recommended.key:
            marker = " [green]<- selected[/]"
        elif verdict.best is not None and cell.key == verdict.best.key:
            marker = " [dim]<- peak[/]"
        table.add_row(
            *[str(cell.params[name]) for name in sorted(varied)],
            str(stats.trades),
            f"{stats.expectancy_r:+.3f}R{marker}",
            f"{stats.profit_factor:.2f}" if stats.profit_factor != float("inf") else "inf",
            f"{stats.max_drawdown_pct:.1%}",
            f"{stats.total_return_pct:+.1%}",
        )
    console.print(table)

    colour = {"plateau": "green", "spike": "yellow", "none": "red"}[verdict.shape]
    console.print(f"[{colour} bold]{verdict.describe()}[/]")
    console.print(
        f"[dim]{verdict.total_cells} configuration(s) tested to reach this. "
        "docs/03 0.7 rule 5: a result selected from many trials is weaker "
        "evidence than the same result from few.[/]"
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
