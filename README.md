# SCREENERV12

A personal market intelligence and trading operations platform: swing screening, market regime
analysis, sector rotation, position and portfolio risk management, catalyst awareness, trade
journaling, performance analytics, and AI-assisted research.

**Design principle:** deterministic code owns every price, indicator, position-size, P&L, risk, and
statistical calculation. AI summarizes and explains what the platform has already computed — it never
invents prices, indicators, news, or numbers. Where reliable data is unavailable, the system says so
rather than filling the gap.

The operator makes every trading decision. This tool exists to make those decisions better informed,
better organized, and more consistent.

## Status

**Phase 0 — assessment complete, awaiting approval.** No application code has been written yet.

Start here: [`docs/00-PROJECT-ASSESSMENT.md`](docs/00-PROJECT-ASSESSMENT.md) — repository assessment,
risk analysis, recommended architecture, database design, ranked data providers with costs, and the
phased roadmap.

## Planned stack

Python 3.11 · PostgreSQL · FastAPI · React (from Phase 5) · Anthropic API (from Phase 9)
