# Runbook: local setup

One-time setup on the machine that will run the platform. Roughly 30 minutes.

Per [ADR 0001](../decisions/0001-phase-0-decisions.md), the platform runs locally
through Phase 4 and moves to a cloud host at Phase 5. The Claude Code container is
a development environment, not the runtime -- it is wiped between sessions, and ten
years of price history cannot live somewhere that disappears.

---

## 1. Prerequisites

| Tool | Why | Check |
| --- | --- | --- |
| Python 3.11+ | Runtime | `python3 --version` |
| Docker Desktop | Runs Postgres | `docker --version` |
| Git | Clone the repo | `git --version` |

macOS: `brew install python@3.11 git` and Docker Desktop from docker.com.
Windows: python.org installer (tick "Add to PATH"), Docker Desktop, Git for Windows.

## 2. Clone and install

```bash
git clone https://github.com/KY762/SCREENERV12.git
cd SCREENERV12
git checkout claude/trading-platform-design-9i2pba

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Verify:

```bash
pytest -q          # expect: all tests pass
```

**If the tests pass, the calculation engine is verified on your machine** -- every
indicator matched a hand-computed value and no indicator can see the future.

## 3. Credentials

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
ALPACA_API_KEY_ID=PK...your key id...
ALPACA_API_SECRET_KEY=...your secret...
```

Get these from alpaca.markets -> Paper Trading -> API Keys -> Generate. The secret
displays once; copy it immediately.

`.env` is git-ignored and can never be committed. **Never paste these keys into a
chat**, including with Claude -- the code reads them from the environment.

## 4. Start Postgres

```bash
docker compose up -d
docker compose ps          # expect: screener-postgres, healthy
```

Then create the schema:

```bash
screener db init
```

## 5. First ingestion

```bash
screener ingest --symbols SPY,QQQ,AAPL --start 2019-01-01
```

Then inspect:

```bash
screener db status      # bars stored per symbol, with date span
screener runs           # what happened, and whether it succeeded
screener quality        # any validation violations
screener show SPY -n 10 # last 10 raw bars
```

---

## 6. Phase 1 gate -- verify to the penny

**This is the check that decides whether Phase 1 is done.** Automated tests prove
the code is internally consistent; only this proves the *data* is right.

1. Run `screener show SPY -n 10`.
2. Open the same symbol on any independent source -- TradingView, Yahoo Finance,
   your broker.
3. Compare the last 10 daily bars: open, high, low, close, volume.

**Expect an exact match on OHLC.** These are raw, unadjusted bars, so:

- **Prices must agree materially** -- within 25 bps by default -- against a
  source showing *unadjusted* data. Exact equality is not achievable: the free
  Alpaca feed is IEX-only, one venue rather than the consolidated tape, so the
  two sources see different trades. Observed on liquid names: 1-3 bps, either
  sign. The gate is sized to catch wrong symbols, misaligned dates, missed
  splits and stale bars, all of which are far larger. Tighten it with
  `--tolerance-bps` if you ever move to a consolidated feed.
- If your reference shows *adjusted* prices, older bars will differ after any split
  or dividend. That is correct behaviour, not a bug -- see the adjustment policy in
  `providers/base.py`.
- **Volume may differ slightly.** The free Alpaca feed is IEX-only, which is one
  exchange rather than the full consolidated tape. Direction and magnitude should
  track; exact figures will not. This is a documented free-tier limitation and one
  of the reasons Polygon is the recommended upgrade.

Repeat for QQQ and AAPL. If prices match on all three, Phase 1 has passed its gate.

If they do not match, stop and report it. A discrepancy here invalidates everything
downstream -- there is no point testing hypotheses against wrong prices.

---

## 7. Routine use

```bash
screener ingest --symbols SPY,QQQ,AAPL --start 2024-01-01   # safe to re-run
screener freshness                                          # exits 1 if data is stale
```

Re-running any range is safe: unchanged bars are left untouched, so a missed night
is recovered by simply running the command again.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Alpaca credentials missing` | `.env` absent or blank. Check you copied `.env.example` and filled both keys. |
| `connection refused` on port 5432 | Postgres not running. `docker compose up -d`. |
| `403` from Alpaca | Key mistyped, or the key is from the live dashboard rather than paper. |
| Empty result for a valid ticker | The free IEX feed has thinner coverage on some symbols. Try SPY first to confirm the pipeline works. |
| `screener: command not found` | Virtualenv not active. `source .venv/bin/activate`. |

---

## 8. Metrics (Phase 2)

Once bars are ingested, compute the derived metrics that screening reads:

```bash
screener metrics build                    # all symbols, full history
screener metrics show SPY -n 5            # inspect
```

Nightly, after ingestion, use `--since` so only new rows are written:

```bash
screener ingest --symbols SPY,QQQ,AAPL --start 2024-01-01
screener metrics build --since 2026-08-01
```

`--since` limits which rows are **written**, never which are **computed**. A
200-day average needs 200 prior bars, so the full series is always calculated
and only the tail persisted.

**Measured on this hardware** (SQLite, synthetic data, 1,500 bars/symbol):

| Operation | 25 symbols | Extrapolated to 1,500 |
| --- | --- | --- |
| Full rebuild | 9.5 s | ~9.5 min |
| Nightly `--since` | 0.9 s | ~0.9 min |

The arithmetic itself is ~19 ms per symbol; the rest is database writes. A full
rebuild is therefore something to run occasionally, not nightly -- which is what
`--since` exists for. `metrics_daily` is a pure cache reproducible from
`price_daily`, so `--rebuild` is always safe.

---

## 9. Universe and diagnostics (Phase 3 prerequisites)

Build point-in-time universe membership from the metrics:

```bash
screener universe build
screener universe members --on 2026-08-14
```

Membership is stored **per date**, never derived from today's data. A stock that
failed the liquidity filter in 2019 was not tradeable in 2019, and screening
history against today's universe silently selects the companies that went on to
become large and liquid.

### The two pre-test diagnostics

Both run before any P&L, and either can invalidate a specification:

```bash
screener diagnose redundancy          # correlation across candidate indicators
screener diagnose signals             # frequency + overlap for H2, H3, H4
```

**Redundancy** drops any indicator correlating at or above 0.85 with a
higher-priority one. It can overrule the recommendations in `docs/04` -- that is
the point: measurement beats judgement.

**Signals** answers two questions cheaply:

- *Frequency* -- does the setup select anything? A rule firing on 40% of bars is
  a description of the market, not a signal.
- *Overlap* -- are these separate hypotheses, or one hypothesis under three
  names? Overlap above 60% of the rarer setup means fold them (`docs/05` 1.3).

Vary the parameters that `docs/03` marks as under test rather than assumed:

```bash
screener diagnose signals --displacement 1.5      # displacement filter on
screener diagnose signals                         # filter off (the null)
screener diagnose signals --sweep-lookback 5
```

---

## 10. Backtesting (Phase 4)

Nothing in this section should be run before `screener verify` passes. A
backtest on unverified prices produces a confident number about nothing.

### The command

```bash
screener backtest run --hypothesis h2 --split development
```

That runs one configuration of one hypothesis over one split and prints the
trade statistics, per-regime breakdown, and the pre-registered criteria from
[`docs/03-HYPOTHESES.md`](../03-HYPOTHESES.md) §0.6 with a pass or fail against
each one.

What the engine assumes, all of it stated so results can be read honestly:

| | |
| --- | --- |
| Fill | Next session's **open** -- never the close of the signal bar |
| Ambiguous bar (stop and target both inside the range) | Resolves to the **stop** |
| Gap through the stop | Fills at the **open**, worse than the stop |
| Slippage | 5 bps per side by default, charged on entry and exit |
| Sizing | `calc.sizing.plan_position` -- the same function the live path uses |

The first three understate results. That is deliberate: daily bars cannot
resolve intrabar order, and every ambiguity resolving in your favour is how a
backtest becomes fiction.

### The benchmark that matters

Each run compares against random selection over the same window, with the same
holding periods, drawn from the same symbols -- 1,000 iterations by default:

```
random: median +0.412%, 95th +1.885% | strategy +0.930% = 78.4th percentile
```

**A strategy that cannot beat that distribution has not demonstrated selection,
only exposure.** It is the criterion most likely to fail and the one worth
believing.

### Splits and the budget

```bash
screener backtest budget           # what has been spent, and on what
```

| Split | Window | Budget |
| --- | --- | --- |
| `development` | 2010-2015 | Unlimited. Carries no evidential weight. |
| `validation` | 2016-2019 | 3 configurations per hypothesis |
| `test` | 2020-2026 | **1 configuration per hypothesis, once** |

Explore freely on `development` -- results there prove nothing, which is exactly
what makes free exploration safe. The other two splits require
`--confirm-spend`, and once a hypothesis has spent its configurations there, the
CLI refuses further runs. Re-running an *identical* configuration is always
allowed; that is reproduction, not a second look.

Every run is recorded in `research_runs` whether or not the result was liked.
The budget lives in the database rather than in your memory precisely because a
rule kept in someone's head relaxes the day a result disappoints.

### Order of work

```bash
# 1. explore on development -- surfaces, structural questions, spec revision
screener backtest run --hypothesis h2 --split development --r-multiple 2.0
screener backtest run --hypothesis h2 --split development --r-multiple 1.5
screener backtest run --hypothesis h2 --split development --no-trend-filter

# 2. pick a plateau CENTRE, never a peak (docs/03 0.7), then confirm
screener backtest run --hypothesis h2 --split validation --confirm-spend ...

# 3. only when everything else is settled
screener backtest run --hypothesis h2 --split test --confirm-spend ...
```

Always run H1 too. It is the control, and if the pattern hypotheses cannot beat
plain relative strength, their extra complexity earned nothing -- which is a
real finding, not a failure of the exercise.


---

## 11. The development battery (one command)

Running experiments one at a time invites stopping when a result looks good.
The battery is declared in full, in `src/screener/research/battery.py`, before
any of it runs -- twelve experiments, 118 configurations, each with the question
it answers written beside it:

```bash
screener research explore
```

It writes `research/<date>-development-battery.md` for reading and a matching
`.json` so the numbers can be re-read exactly rather than re-typed from a
screenshot. Both are meant to be committed:

```bash
git add research
git commit -m "battery results"
git push
```

**Development split only.** A 118-configuration sweep on validation would spend
a three-configuration budget in a single command, which is the failure mode the
budget exists to prevent.

### What each experiment is for

| Experiment | Question |
| --- | --- |
| `*_exits` | Is there ANY target and holding period where this is profitable? |
| `*_no_stop` | Same entries, no stop. Entry rule or exit design? |
| `h1_selection` | Does the momentum lookback or selection cutoff matter? |
| `h1_trend_filter` | Does requiring an uptrend help, or just trade less? |
| `h2_displacement` | Does the displacement filter contribute anything? |
| `h3_lookback` | Which liquidity reference is being swept? |

The `_no_stop` experiments matter most when everything is losing. If removing
the stop turns a configuration profitable, the entry rule was never the problem
and the finding is about exit design -- a different result with different
consequences.
