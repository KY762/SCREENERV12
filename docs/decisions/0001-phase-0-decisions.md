# ADR 0001 — Phase 0 Decisions

**Date:** 2026-08-16
**Status:** Accepted
**Context:** Answers to the four architecture-gating questions in
[`docs/00-PROJECT-ASSESSMENT.md`](../00-PROJECT-ASSESSMENT.md) §12.

---

## Decision 1 — Deployment: local now, cloud later

The application runs on the operator's own machine through Phase 4, moving to a cloud host when the
dashboard arrives at Phase 5.

**Consequences:**
- Postgres runs via `docker-compose` locally; nothing is coupled to a specific host.
- Configuration is environment-driven from Phase 1 (`pydantic-settings` + `.env`), so the move to a
  cloud host is a config change and a database dump/restore, not a rewrite.
- Scheduled jobs are defined in `src/screener/jobs/` and invoked by an external scheduler (cron locally,
  systemd timers or a platform scheduler in cloud) rather than being hard-wired to one mechanism.
- **Open caveat:** while local, the nightly ingest only runs if the machine is awake. Ingestion is
  designed idempotent and backfill-capable so a missed night is recoverable by re-running, not a gap.

## Decision 2 — Data scope: end-of-day, ~2,000–3,000 liquid US names

Universe is US equities and ETFs filtered to a liquid subset. Daily bars only; no intraday feed.

**Consequences:**
- Fully served by the free Alpaca tier for Phases 1–4.
- Storage is modest: ~3,000 symbols × 10 years ≈ 7.5M rows in `price_daily`, plus a comparable
  `metrics_daily`. Postgres handles this without partitioning or a time-series extension.
- The liquidity filter itself becomes a Phase 3 deliverable (min price, min average dollar volume) and
  is stored as a named, dated universe so historical membership is reconstructable.
- Screener design assumes multi-day holds. Intraday entry timing is explicitly out of scope; if that
  changes it means a paid feed and a new provider adapter, not a schema change.

## Decision 3 — Frontend: React + Vite + TypeScript at Phase 5

**Consequences:**
- Phases 1–4 ship with a CLI (`typer`) only. This is a feature, not a gap — it forces the API and
  calculation layers to be correct and independently testable before any UI exists.
- The FastAPI layer returns JSON and is the sole interface between backend and frontend, so the
  frontend can be replaced without touching business logic.
- Accepted cost: no visual output until Phase 5. Revisit only if the CLI proves to be a genuine barrier
  to daily use during Phases 3–4.

## Decision 4 — Budget: $50–100/month

**Consequences:**
- Phases 1–4 run at Tier 0 (~$10–30/mo, AI tokens only) — the budget is a ceiling, not a target.
- A paid price feed is affordable when needed. **Polygon (~$29/mo)** remains the recommended upgrade,
  chosen specifically for delisted-ticker coverage, which is the only mitigation at that price for the
  survivorship bias described in assessment §5.1.
- A small cloud host (~$5–15/mo) fits comfortably at Phase 5.
- Out of reach at this tier: Sharadar-grade point-in-time fundamentals with delisted coverage (~$100+).
  **This is a real constraint on Phase 11**, and the backtest engine must state it in its limitations
  output rather than let the operator assume otherwise. SEC EDGAR covers point-in-time fundamentals for
  *listed* companies at no cost, which narrows but does not close the gap.
- AI cost is controlled by prompt caching (~0.1× on repeated context), Batch API (50% off for
  non-latency-sensitive work), and routing summarization to Sonnet 5 / Haiku 4.5 rather than Opus 5.

---

## Still outstanding before the PRD

These determine the screener's starter strategies, the position-sizing rules, and the alert design.
They cannot be defaulted without inventing the operator's trading process.

1. Setups actually traded today (rough descriptions suffice)
2. Indicators genuinely used, versus conventional ones
3. Typical holding period
4. Risk rules: max risk per trade, minimum R:R, max position size, max sector concentration
5. Whether positions are held through earnings
6. Approximate portfolio size (a range is fine)
7. Broker, and whether automatic position import is eventually wanted
8. Preferred alert delivery channel
9. Which relevant accounts already exist

Deferred to Phase 14: funded-futures provider and its exact current rule set. These will not be
assumed — drawdown mechanics vary materially between firms.
