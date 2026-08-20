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
app.add_typer(db_app, name="db")

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


if __name__ == "__main__":
    app()
