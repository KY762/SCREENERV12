# SCREENERV12 — Phase 0 Assessment & Architecture Proposal

**Status:** Awaiting your approval before Phase 1 begins.
**Date:** 2026-08-16
**Repo:** `KY762/SCREENERV12`

This document answers the twelve questions in the project brief, in order. Nothing has been built yet
beyond this document — that is deliberate, per your instruction to inspect first and not generate a
large application blind.

---

## 1. What currently exists

**Nothing.** This is a genuinely empty repository:

| Check | Result |
| --- | --- |
| Local commits | 0 (branch had no commits) |
| Remote branches (`git ls-remote --heads origin`) | none |
| Branches via GitHub API | `[]` |
| Files on disk (excluding `.git/`) | none |
| README, license, CI config | none |

There is no prior code to salvage, migrate, or work around. That is good news: no legacy decisions
constrain the architecture, and nothing has to be reverse-engineered before Phase 1.

## 2. Current technology stack

There is no application stack yet. The **development environment** available has:

| Tool | Version | Notes |
| --- | --- | --- |
| OS | Ubuntu 24.04.4 LTS | 4 vCPU, 15 GiB RAM, ~30 GiB free disk |
| Python | 3.11.15 | plus `uv` and `poetry` |
| Node | 22.22.2 | plus `npm`, `pnpm`, `yarn`, `bun` |
| Docker | installed | for Postgres / Redis locally |
| Postgres client | `psql` installed | server would run via Docker |
| Redis client | `redis-cli` installed | |
| Toolchain | `git`, `curl`, `jq`, `make`, `gcc` | |

**Important environment caveat:** this container is *ephemeral*. It is reclaimed after inactivity, and
the repo is re-cloned fresh each session. It is a fine place to write and test code, but it **cannot be
the home of the running application** — nightly ingestion jobs, a database of price history, and a
dashboard you open every morning need a persistent host. Deciding where that is (your own machine vs. a
small cloud box) is one of the discovery questions in §12.

## 3. What works

Nothing yet — there is no code to run. The only verified working things are environmental: the
toolchain above is installed and functional, and network access to the outside world is proxied and
partially restricted (direct fetches to several vendor sites were blocked; web search works).

## 4. What is incomplete

Everything in the brief — Parts 1 through 20 — is unbuilt. Rather than restate the brief, here is the
build surface grouped by dependency order, because that ordering *is* the roadmap:

| Layer | Contains | Depends on |
| --- | --- | --- |
| Foundation | config/secrets, database, provider abstraction, ingestion, validation, tests | nothing |
| Calculation | indicators, returns, relative strength, ATR, breadth math | Foundation |
| Analysis | screener, strategy builder, regime engine, sector rotation | Calculation |
| Decision support | trade planner, positions, thesis tracking, portfolio risk, correlation | Calculation |
| Awareness | events calendar, news, alerts | Foundation |
| Interface | web API + dashboard | Analysis + Decision support |
| AI | morning/post-market briefings, journal analysis | everything above |
| Validation | backtesting harness, performance analytics | Analysis + journal |
| Separate module | funded futures account tracker | Foundation only |

## 5. Technical problems and risks

These are the things most likely to make the finished product quietly wrong. They are listed roughly in
order of how much damage they do if ignored.

### 5.1 Survivorship bias (high severity, unavoidable on cheap data)
Most affordable providers only serve *currently listed* tickers. Any backtest run against such a
universe silently excludes every company that went to zero or got delisted, which inflates results —
often dramatically. **Mitigation:** use a provider with delisted coverage where affordable (Polygon
carries delisted tickers; Sharadar/Nasdaq Data Link is the gold standard but ~$100+/mo), and make the
backtest engine *print its own limitations* on every report rather than burying them. A backtest that
does not state whether its universe was survivorship-free is not evidence.

### 5.2 Look-ahead bias (high severity, entirely preventable)
Three common sources:
- **Adjusted prices.** A split-adjusted close for 2019 was not knowable in 2019. Storing only adjusted
  prices makes history mutate under you.
- **Restated fundamentals.** Providers usually serve the *latest* restated figures, not what was
  reported at the time.
- **Point-in-time sector/industry.** A stock's sector classification today is not its classification
  five years ago.

**Mitigation, and this is a load-bearing design decision:** store **raw, unadjusted OHLCV plus a
separate corporate-actions table**, and derive adjusted series on demand. Store the *filing date* with
every fundamental. For fundamentals specifically, SEC EDGAR's `companyfacts` API is free and inherently
point-in-time (organized by filing), which is a real advantage over commercial vendors.

### 5.3 Overfitting in the strategy builder (high severity)
A configurable strategy builder plus historical data is an overfitting machine. **Mitigation:** the
system must refuse to report an edge without: explicit in-sample/out-of-sample split, a minimum sample
size, results across at least two distinct market regimes, and a parameter-sensitivity check (does the
result survive ±20% on each threshold?). Automated parameter optimization will not be built in Phase 1;
when it is, it will be gated behind these checks.

### 5.4 LLM fabrication (high severity, design-preventable)
Per your Part 2 principle. **Mitigation:** the AI layer receives only structured JSON assembled by the
platform, is instructed to state "data unavailable" rather than infer, and every AI run is logged with
its input payload hash, model ID, output, and cost so any claim can be traced back to the rows that
produced it. No AI call ever performs arithmetic that the calculation engine can do.

### 5.5 Data quality and provider fragility (medium-high)
Free/unofficial endpoints (Yahoo via `yfinance`) break without notice and are ToS-gray for anything
beyond personal exploration. Even paid feeds have bad ticks, missing days, and unadjusted split errors.
**Mitigation:** a validation layer that runs on every ingest — no negative or zero prices, high ≥ max(open,
close) and low ≤ min(open, close), volume ≥ 0, no gaps against the exchange trading calendar, no
day-over-day move beyond a sanity threshold without a corresponding corporate action. Failures are
logged and the row is quarantined, not silently accepted.

### 5.6 Stale data presented as fresh (medium-high)
The most dangerous UI failure mode is a dashboard that looks fine while showing yesterday's numbers.
**Mitigation:** every screen shows a data-as-of timestamp; the ingestion run table records success or
failure per symbol per day; the dashboard renders a hard banner if the last successful ingest is older
than the last trading day.

### 5.7 Timezone and trading-calendar bugs (medium)
Off-by-one-day errors in returns and "distance to earnings" are endemic. **Mitigation:** all timestamps
stored UTC, all market logic through the `exchange_calendars` library, never `date.today()` for
"is the market open."

### 5.8 Float arithmetic on money (medium)
**Mitigation:** `NUMERIC` in Postgres and `Decimal` in Python for prices, P&L, and position sizing.
Floats are fine for indicators and statistics.

### 5.9 Secrets and exposure (medium)
**Mitigation:** `.env` never committed (enforced by `.gitignore` and a pre-commit secret scan), all API
keys read server-side only, no key ever reaches the frontend. If the app is ever exposed beyond
localhost, it gets real authentication first — a personal trading dashboard on an open port is a
target.

### 5.10 Cost creep (low-medium, easy to control)
Multiple $30–100/mo subscriptions accumulate. **Mitigation:** start on free tiers, add paid providers
only when a specific limitation blocks a specific feature, and log AI token spend per run.

### 5.11 Scope risk (low severity, high probability)
The brief describes roughly two years of solo evenings if built to the letter. **Mitigation:** the phase
gates in §11 — nothing proceeds until the prior phase is verified — plus a deliberately narrow Phase 1.

---

## 6. Recommended architecture

Your Part 5 diagram is sound. Here is the concrete instantiation of it.

```
                    ┌────────────── providers/ (swappable) ──────────────┐
                    │  Alpaca   SEC EDGAR   FRED   [Polygon]  [EODHD]    │
                    └───────────────────────┬────────────────────────────┘
                                            │  Protocol interfaces
                                            ▼
                              ingest/  ──►  validate/  ──►  Postgres
                                                               │
                                            ┌──────────────────┤
                                            ▼                  ▼
                                     calc/ (pure fns)    metrics_daily
                                            │             (precomputed
                    ┌───────────────────────┼──────────────┐   nightly)
                    ▼                       ▼              ▼
              regime/ + breadth/       screener/      portfolio/
                    │                       │              │
                    └───────────────────────┼──────────────┘
                                            ▼
                                    api/ (FastAPI, JSON)
                                            │
                          ┌─────────────────┼─────────────────┐
                          ▼                 ▼                 ▼
                      web/ (React)      ai/ (briefings)   alerts/
                                            │
                                            ▼
                                       YOUR DECISION
```

**Key architectural commitments:**

1. **The calculation layer is pure functions.** `calc/` takes DataFrames in, returns DataFrames out, has
   no database or network access, and is therefore trivially unit-testable against hand-computed golden
   values. This is where correctness is won.

2. **Providers sit behind Protocol interfaces.** `PriceProvider`, `FundamentalsProvider`,
   `EventsProvider`, `NewsProvider` — each with a small method surface (`get_daily_bars(symbols, start,
   end)` etc.). Swapping Alpaca for Polygon means writing one new adapter class, not touching the rest
   of the app. Same for the AI provider.

3. **Metrics are precomputed nightly into `metrics_daily`.** Screening 3,000 symbols by recomputing 200
   days of moving averages per query is slow and fragile; screening becomes a single indexed SQL query
   when the metrics already exist as columns. Recomputation is idempotent and re-runnable.

4. **Screen results are immutable point-in-time snapshots.** When a screen runs, it writes the *metric
   values that caused each match* alongside the match. Six weeks later you can answer "why did this
   qualify on June 3rd?" exactly, rather than approximately.

5. **Rules are versioned.** Regime classifications and strategy definitions carry a version number, so a
   change to your rules does not retroactively rewrite what the system said last month.

6. **The AI layer is a consumer, not a source.** It reads from the API like any other client. It can be
   removed entirely and the platform still works — which is the correct dependency direction.

### Stack recommendation

| Layer | Choice | Why, and what I considered instead |
| --- | --- | --- |
| Core language | **Python 3.11** | The quant/data ecosystem (pandas, numpy, statsmodels, exchange_calendars) is here. Not a close call. |
| Database | **Postgres 16** (Docker locally) | One dependable choice. A 3,000-symbol × 10-year daily universe is ~7.5M rows — trivial for Postgres, no TimescaleDB needed. SQLAlchemy means SQLite still works for fast unit tests. Considered SQLite-only (zero ops, but migration pain later) and DuckDB (excellent for backtest scans — can be added later for that specific job without replacing Postgres). |
| API | **FastAPI** | Async, typed, auto-generated OpenAPI docs, same language as the calc engine. |
| Frontend | **React + Vite + TypeScript**, added at Phase 5 | Considered Streamlit: much faster to a first screen, but it becomes a ceiling for dense tables, keyboard workflows, alerting UI, and mobile. Given you want to live in this tool daily, I'd rather pay the cost once. **Phases 1–4 have no UI at all** — CLI output only — so this decision can be revisited before it's expensive. |
| Scheduling | **APScheduler** in-process initially; cron or systemd timers on the host | No Airflow. It is a distributed-workflow engine for a job that is "run this at 5pm." |
| Migrations | **Alembic** | |
| Testing | **pytest** + `hypothesis` for the math | |
| Config | **pydantic-settings** + `.env` | |
| AI | **Anthropic API**, behind an `LLMProvider` interface | |

## 7. Recommended folder structure

```
SCREENERV12/
├── docs/
│   ├── 00-PROJECT-ASSESSMENT.md      # this file
│   ├── 01-REQUIREMENTS.md            # written after discovery answers
│   ├── decisions/                    # ADRs — one file per significant choice
│   └── runbooks/                     # "the nightly job failed, now what"
├── src/screener/
│   ├── config.py                     # pydantic-settings, single source of env truth
│   ├── db/
│   │   ├── models.py                 # SQLAlchemy ORM
│   │   ├── session.py
│   │   └── migrations/               # alembic
│   ├── providers/
│   │   ├── base.py                   # Protocol definitions — the abstraction boundary
│   │   ├── alpaca.py
│   │   ├── edgar.py
│   │   ├── fred.py
│   │   ├── polygon.py                # added when/if you subscribe
│   │   └── registry.py               # config-driven provider selection
│   ├── ingest/
│   │   ├── prices.py
│   │   ├── corporate_actions.py
│   │   ├── fundamentals.py
│   │   ├── events.py
│   │   └── runs.py                   # ingestion run bookkeeping
│   ├── validate/
│   │   ├── rules.py                  # OHLCV sanity, calendar gaps, outliers
│   │   └── report.py
│   ├── calc/                         # PURE. no db, no network.
│   │   ├── indicators.py             # SMA, EMA, ATR, RVOL, hist vol
│   │   ├── returns.py
│   │   ├── relative_strength.py
│   │   ├── structure.py              # consolidation, pullback, 52wk proximity
│   │   ├── position_sizing.py
│   │   ├── stats.py                  # expectancy, profit factor, drawdown
│   │   └── correlation.py
│   ├── universe/
│   ├── metrics/                      # nightly metrics_daily computation
│   ├── screener/
│   │   ├── strategy.py               # strategy definition model
│   │   ├── engine.py
│   │   └── builtin/                  # shipped starter strategies
│   ├── regime/
│   ├── breadth/
│   ├── sectors/
│   ├── portfolio/
│   │   ├── positions.py
│   │   ├── thesis.py                 # health rules: healthy/monitor/warning/invalidated
│   │   ├── risk.py
│   │   └── concentration.py
│   ├── planner/                      # trade planning + rule violations
│   ├── journal/
│   ├── events/                       # earnings, econ calendar, catalyst priority
│   ├── alerts/
│   ├── backtest/
│   ├── ai/
│   │   ├── provider.py               # LLMProvider interface
│   │   ├── context.py                # builds the structured payload
│   │   ├── prompts/
│   │   └── runs.py                   # audit log of every AI call
│   ├── futures/                      # SEPARATE module — no shared risk logic
│   ├── api/
│   │   └── routers/
│   ├── cli.py                        # typer — the Phase 1-4 interface
│   └── jobs/                         # scheduled job definitions
├── tests/
│   ├── unit/
│   │   └── calc/                     # golden-value tests, the correctness core
│   ├── integration/
│   └── fixtures/                     # frozen known-good market data
├── web/                              # React app, created at Phase 5
├── scripts/
├── docker-compose.yml                # postgres (+ redis later)
├── pyproject.toml
├── .env.example                      # committed
├── .env                              # NEVER committed
└── .gitignore
```

## 8. Database architecture

Postgres. Money and prices are `NUMERIC`, never `float`. All timestamps `TIMESTAMPTZ` in UTC; trading
dates are plain `DATE` in exchange-local terms.

### Reference & market data

| Table | Purpose | Key columns / notes |
| --- | --- | --- |
| `symbols` | instrument master | `id`, `ticker`, `name`, `exchange`, `asset_type`, `sector`, `industry`, `cik`, `is_active`, `first_date`, `last_date`, `delisted_date` |
| `symbol_aliases` | ticker changes over time | `symbol_id`, `ticker`, `valid_from`, `valid_to` — prevents history breaking on a rename |
| `price_daily` | **unadjusted** OHLCV | PK `(symbol_id, date)`; `open/high/low/close/volume`, `source`, `ingested_at` |
| `corporate_actions` | splits & dividends | `symbol_id`, `ex_date`, `type`, `ratio`, `amount` — adjustment factors derived from here |
| `metrics_daily` | precomputed derived metrics | PK `(symbol_id, date)`; sma20/50/200, ema, atr14, atr_pct, hist_vol, rvol, avg_vol_20/50, dollar_vol, ret_1w/1m/3m/6m/12m, rs_vs_spy, rs_vs_sector, pct_from_52w_high, ma_alignment flag, range compression score. **This table is what makes screening fast.** |
| `sectors` / `sector_etf_map` | sector definitions + proxy ETFs | XLK, XLF, XLE, … |
| `universes` / `universe_members` | named, dated symbol sets | supports "S&P 500 as of 2023-01-01" |
| `ingestion_runs` | one row per job execution | `job`, `started_at`, `finished_at`, `status`, `symbols_ok`, `symbols_failed` |
| `data_quality_log` | per-symbol validation failures | `symbol_id`, `date`, `rule`, `detail`, `severity` |

### Market state

| Table | Purpose |
| --- | --- |
| `market_regime_daily` | `date`, `classification`, `rule_version`, **`inputs` JSONB** (every value that fed the decision), `explanation` |
| `breadth_daily` | `date`, `universe_id`, pct above 20/50/200 DMA, new highs, new lows, advance/decline |
| `sector_performance_daily` | `date`, `sector_id`, returns over 1w/1m/3m/6m, return vs SPY, RS rank, trend state |

### Strategy & screening

| Table | Purpose |
| --- | --- |
| `strategies` | `name`, `definition` JSONB (the criteria tree), `version`, `enabled`, `created_at` |
| `screen_runs` | `strategy_id`, `strategy_version`, `run_at`, `universe_id`, `match_count` |
| `screen_results` | `run_id`, `symbol_id`, `rank`, **`metrics_snapshot` JSONB** — the point-in-time "why it qualified" |
| `watchlist_items` | `symbol_id`, `added_at`, `source_run_id`, `notes`, `active` |

### Trading

| Table | Purpose |
| --- | --- |
| `trade_plans` | pre-trade: entry, stop, target, size, computed R:R, risk $, flags raised |
| `positions` | `symbol_id`, `strategy_id`, `status`, `opened_at`, `closed_at`, avg entry, initial stop, current stop, initial target, current target, `original_thesis`, `invalidation_criteria` |
| `fills` | supports scaling in/out — `position_id`, `side`, `qty`, `price`, `filled_at`, `fees` |
| `thesis_checks` | health evaluation history: `position_id`, `checked_at`, `status`, `failed_conditions` JSONB |
| `trades` | closed round-trips (the journal record) — P&L, R multiple, holding days, market regime at entry, setup, rule adherence, mistakes, notes |
| `journal_entries` / `tags` | free-form notes and tagging |

### Awareness & AI

| Table | Purpose |
| --- | --- |
| `events` | `symbol_id` (nullable for macro), `type` (earnings/econ/fed), `scheduled_at`, `timing` (BMO/AMC), `source`, `confirmed` |
| `news` | `symbol_id`, `headline`, `url`, `source`, `published_at`, `summary` |
| `alerts` | `severity` (critical/important/informational), `type`, `symbol_id`, `message`, `created_at`, `acknowledged_at` |
| `ai_runs` | **audit trail** — `kind`, `model`, `input_payload` JSONB, `input_hash`, `output`, `input_tokens`, `output_tokens`, `cost_usd`, `created_at` |

### Futures (separate schema `futures.`)

Deliberately isolated: `futures.accounts` (provider, rules), `futures.daily_pnl`,
`futures.trades`, `futures.rule_violations`. No shared risk calculation with the swing portfolio. As
your brief requires, this module will not be built until you supply the exact provider and its current
published rules — I will not assume drawdown mechanics, which vary materially between firms.

## 9. Data providers, ranked

Prices below were checked in August 2026 via web search; vendor sites were not directly reachable from
this environment, so **verify current pricing at signup** before committing. Ranked for *your* use case:
end-of-day swing screening of US equities and ETFs.

### Market data (daily OHLCV — the backbone)

| Rank | Provider | Cost | Strengths | Limitations |
| --- | --- | --- | --- | --- |
| **1** | **Alpaca Market Data (Free)** | **$0** with a free brokerage account | Unlimited historical daily bars, real-time IEX feed, free Benzinga-sourced news API, clean Python SDK, 200 req/min | US equities/ETFs only; SIP data delayed 15 min on free tier; limited delisted-ticker coverage; no fundamentals |
| **2** | **Tiingo** | ~$30/mo (free tier is symbol-limited) | Carefully curated adjusted EOD back to 1962, 80k+ symbols, strong data-cleaning reputation, news API included on paid | Fundamentals are a paid add-on via a third party |
| **3** | **Polygon.io** | ~$29/mo Starter (delayed, 5yr) / ~$79 Developer (real-time, deeper history) | Excellent API design, splits & dividends, **delisted tickers**, ticker metadata incl. sector, news included | Per-asset-class billing; the company rebranded to Massive.com in July 2026, so pricing pages are in flux — confirm before subscribing |
| **4** | **EODHD** | ~$20/mo EOD-only, ~$60 fundamentals, ~$100 all-in-one | One vendor for EOD + fundamentals + calendars + global markets; 100k calls/day | Priciest of the mid-tier if you need the bundle |
| **5** | FMP | ~$20–50/mo | Cheap, very broad coverage | Recurring data-quality complaints; I would not build risk calculations on it without cross-checking |
| **6** | `yfinance` / Yahoo | $0 | Instant to prototype with | Unofficial, undocumented, breaks without notice, ToS-gray. **Prototype only — never the production source.** |
| — | Databento | usage-based, institutional | Tick-level fidelity | Vastly overkill and overpriced for EOD swing trading |

### Fundamentals

| Rank | Provider | Cost | Notes |
| --- | --- | --- | --- |
| **1** | **SEC EDGAR `companyfacts` API** | **$0** | Authoritative, free, and **inherently point-in-time** (organized by filing date) — which directly mitigates risk 5.2. Requires a declared User-Agent and respect for rate limits, plus real work to map XBRL tags to a usable schema. Worth it. |
| 2 | EODHD Fundamentals | ~$60/mo | 20+ years, 80+ standardized indicators, far less integration work |
| 3 | Sharadar SF1 (via Nasdaq Data Link) | ~$100+/mo | The correct answer if serious point-in-time backtesting with delisted coverage becomes the priority |

### Events

| Type | Provider | Cost |
| --- | --- | --- |
| Economic releases + FOMC | **FRED API** | **$0** — authoritative, excellent, includes release calendars |
| Earnings calendar | Polygon / EODHD / FMP | included with the above subscriptions |
| Earnings (free path) | SEC filing-based estimation | free but approximate; a paid calendar is worth it here |

### News

| Provider | Cost | Notes |
| --- | --- | --- |
| **Alpaca News API** | **$0** | Benzinga-sourced, real-time, included with the free account. Strong default. |
| Polygon news | included on paid tiers | also Benzinga-sourced |
| Tiingo news | paid add-on | |

### AI

**Anthropic API.** Current per-million-token pricing:

| Model | Input | Output | Use for |
| --- | --- | --- | --- |
| Claude Opus 5 | $5 | $25 | Briefings, journal pattern analysis — the reasoning-heavy work |
| Claude Sonnet 5 | $3 | $15 | High-volume summarization (news digests) |
| Claude Haiku 4.5 | $1 | $5 | Trivial classification |

Prompt caching cuts repeated-context reads to ~0.1× input price (writes cost 1.25×), and the Batch API
gives 50% off for anything not latency-sensitive. Both apply well here, since briefings reuse a large
stable instruction prefix.

### Recommended combination for Phase 1

**Alpaca (free) + SEC EDGAR (free) + FRED (free) + Anthropic API.** This costs essentially nothing but
AI tokens, covers every Phase 1–4 requirement, and defers the decision on a paid feed until you have
working code that can tell you exactly which limitation is blocking you. If and when you outgrow it,
**Polygon** is my recommended upgrade — the delisted-ticker coverage directly addresses the most
damaging bias in §5.1, which no other option at that price does.

## 10. Estimated monthly cost

| Tier | Components | Monthly |
| --- | --- | --- |
| **Tier 0 — Phase 1–4 (recommended start)** | Alpaca free + SEC EDGAR + FRED + local Postgres in Docker + Anthropic API | **$10–30** (AI tokens only) |
| **Tier 1 — production personal use** | Tier 0 + Polygon Starter (~$29) or Tiingo (~$30) + small cloud host (~$5–15) | **$45–75** |
| **Tier 2 — serious backtesting** | Tier 1 + fundamentals feed (~$60) *or* Sharadar (~$100) + Polygon Developer (~$79) | **$150–220** |

**AI cost derivation** (so you can sanity-check it): two briefings per trading day ≈ 44 runs/month. At
roughly 30k input + 2k output tokens per run on Opus 5, that is 30,000 × $5/1M + 2,000 × $25/1M ≈ $0.20
per run ≈ **$9/month**, before prompt caching. Ad-hoc queries and journal analysis push realistic usage
to $10–30. Routing news summarization to Sonnet 5 or Haiku 4.5 lowers it further.

One-time costs: **$0**. Everything recommended has a free tier or is open source.

## 11. Phased implementation roadmap

Each phase has explicit success criteria. Nothing proceeds until the prior phase passes.

| Phase | What we build | Success criteria (the gate) |
| --- | --- | --- |
| **0** | Discovery + requirements doc | You've answered §12; a written PRD exists and you agree with it |
| **1** | Repo skeleton, config, Postgres + migrations, provider abstraction, Alpaca adapter, daily-bar ingestion, validation layer, test harness | SPY/AAPL/QQQ daily bars for 5 years match an independent reference to the penny; all validation rules pass; re-running ingestion is idempotent; CI green |
| **2** | Indicator & metrics engine, nightly `metrics_daily` computation | Every indicator matches a hand-computed golden value in tests; a full-universe metrics rebuild completes in acceptable time |
| **3** | Universe management + screener v1 (fixed strategies) + CLI output | A named strategy returns a ranked list; every match includes the metric values that caused it; spot-checks against a chart are correct |
| **4** | Regime engine, breadth, sector rotation | Every classification is reproducible from stored inputs and explains itself in plain rules |
| **5** | FastAPI + React dashboard: screener, regime, sectors | You use it every morning instead of the CLI |
| **6** | Trade planner + position management + thesis tracking | Position sizing matches manual calculation exactly; health status changes when a defined condition breaks |
| **7** | Portfolio risk: exposure, concentration, correlation clusters | Correlated clusters are flagged on a deliberately correlated test portfolio |
| **8** | Events calendar, news, alert engine with severity tiers | Earnings for a held position raises a CRITICAL alert at the right time; no duplicate alert spam |
| **9** | AI layer: morning + post-market briefings | Every factual claim in a briefing traces to a stored row; missing data is stated as missing, never inferred |
| **10** | Journal + performance analytics | Metrics match hand calculation on a known trade set; sample size shown everywhere; low-n conclusions flagged |
| **11** | Backtesting & validation harness | Every report auto-prints its own methodological limitations; in-sample/out-of-sample split enforced |
| **12** | Automation, scheduling, notification delivery | Nightly job runs unattended and fails loudly, not silently |
| **13** | Custom strategy builder (UI) | You can create, save, enable, and compare strategies without touching code |
| **14** | Funded futures module (separate) | *Blocked until you provide exact provider + current rules* |

Backtesting sits at Phase 11 deliberately — but note the implication: **until Phase 11 exists, no
strategy in this system is evidence of an edge.** It is a way of finding candidates that match criteria
you chose, which is useful and is not the same thing. If you'd rather validate earlier, Phase 11 can be
pulled forward to sit right after Phase 3; say the word and I'll reorder.

## 12. What you need to do first

### Step 1 — Answer the discovery questions

I only need the answers that change technical decisions. Anything you're unsure about, say so and I'll
pick a sensible default and flag the assumption.

**Trading**
1. Which markets and instruments will the screener scan — US equities only, or equities + ETFs? Any ADRs or international?
2. Roughly how many symbols should the universe cover — S&P 500 (~500), a liquid US universe (~2,000–3,000), or everything (~8,000+)?
3. Typical holding period for a swing trade — days, one to three weeks, longer?
4. Which setups do you actually trade today? Even rough descriptions ("pullback to 20 DMA in an uptrend", "breakout from a multi-week base") are enough to build the first strategies around.
5. Which indicators do you genuinely use, versus which are just conventional?
6. What are your risk rules — max risk per trade as % of account, minimum R:R, max position size, max sector concentration?
7. Do you hold through earnings?
8. Approximate portfolio size? (Needed for position sizing and to know whether $-based or %-based constraints dominate. A rough range is fine.)
9. Do you need **intraday** data, or is end-of-day sufficient? *(This is the single biggest cost driver.)*
10. Which broker do you use — and would you eventually want positions imported automatically rather than entered by hand?

**Technical**
11. Where should the application actually run: your own machine (Mac/Windows/Linux?), a small cloud VM, or a managed host? *(Remember §2 — this dev container can't be it.)*
12. Do you need mobile access to the dashboard and alerts, or is desktop enough initially?
13. How do you want alerts delivered — email, push, SMS, Telegram/Discord?
14. What's your comfortable monthly budget ceiling for data + hosting + AI?
15. Which accounts do you already have? (Alpaca, any broker with an API, Anthropic API, any data subscriptions.)

**Futures (deferred)**
16. Which funded-account provider, and can you share their current published rule set when we get to Phase 14? I will not assume these.

### Step 2 — Create two accounts (both free, ~10 minutes)

**Alpaca** — free market data + news:
1. Go to `alpaca.markets` and create an account.
2. Complete signup; you do **not** need to fund the account for market data.
3. Open the dashboard and switch to **Paper Trading**.
4. Find **API Keys** and generate a new key pair.
5. Copy both the **Key ID** and the **Secret Key** — the secret is shown once.
6. Save them in your `.env` file as `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY`.

**Anthropic API** — for the AI layer (not needed until Phase 9, but free to set up now):
1. Go to `console.anthropic.com` and create an account.
2. Go to **API Keys** → **Create Key**, name it `screenerv12`.
3. Copy the key and save it as `ANTHROPIC_API_KEY` in `.env`.
4. Set a **monthly spend limit** in billing settings — recommend $25 to start.

**Optional, free, no signup:** FRED requires a free API key from `fred.stlouisfed.org/docs/api/api_key.html`
(one form, instant). SEC EDGAR requires no key at all, only a declared User-Agent string with your email.

**Never share any of these keys with me.** They go in `.env`, which will be git-ignored from the first
commit. I will write code that reads them from the environment and will never ask you to paste one.

### Step 3 — Approve, adjust, or push back

Tell me which parts of this you want changed. In particular, I'd flag three decisions worth your
explicit sign-off:

- **React over Streamlit** (§6) — I'm optimizing for a tool you'll use daily for years, at the cost of a
  slower first UI. If you'd rather see something visual sooner, Streamlit at Phase 3 is a legitimate
  alternative and I'll say so plainly.
- **Free data for Phases 1–4** (§9) — deliberately deferring a paid feed until code proves what's
  missing. If you'd rather start on Polygon and skip the migration, that's ~$29/mo and I'd support it.
- **Backtesting at Phase 11** (§11) — see the note above about what that means for Phases 3–10.

Once you approve, Phase 1 begins: repo skeleton, config, database, provider abstraction, Alpaca
ingestion, validation, and tests — ending with the verification that SPY's last five years of daily bars
match an independent source to the penny.
