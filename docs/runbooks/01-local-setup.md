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

- **Prices must match to the cent** against a source showing *unadjusted* data.
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
