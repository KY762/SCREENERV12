# SCREENERV12 — working notes for Claude

Personal market-research and trading-operations platform. One operator,
$10,000, US equities, daily bars, long only.

**Read `docs/01-PROJECT-CHARTER.md` before proposing anything strategic.** The
operator's documented losses came from execution — missing stops, size
escalation after losses, profit quotas — not from strategy selection. Software
that makes those decisions mechanical is the point of the project.

## Non-negotiables

These are not preferences. Violating any of them silently invalidates results.

1. **No lookahead.** Signals complete at a bar's close and fill at the NEXT
   bar's open. `tests/unit/calc/test_no_lookahead.py` and
   `tests/unit/backtest/test_no_lookahead_backtest.py` truncate the data and
   assert past trades are unchanged. Keep those passing.
2. **Raw, unadjusted prices** in `price_daily`; corporate actions stored
   separately; adjusted series derived on demand. Storing adjusted prices makes
   history mutate under you at every future split.
3. **Point-in-time universe.** Membership is stored per date, never derived
   from today's data.
4. **Pre-registered criteria are constants**, not arguments
   (`backtest/performance.py`). A threshold you can pass in is a threshold you
   can move after seeing the number.
5. **Split budgets are enforced against the database** (`backtest/budget.py`):
   development unlimited, validation 3 configs per hypothesis, test 1, once.
   Never work around this.
6. **Ambiguity resolves against us.** A bar containing both stop and target
   counts as the stop. Gaps fill at the open. Slippage is charged both sides.

## Where things stand

Phases 1–4 built and tested. **No hypothesis has passed validation.**

Round 1 (h1–h4): 40 swept configurations, all negative, all below random
selection from the same universe. Details in `docs/06-DIAGNOSTIC-RESULTS.md`.

Strongest result so far — `docs/07-STOP-DESIGN-QUESTION.md`: removing the price
stop moved H3 from −0.121R to +0.485R (5.8 SE). Exit design appears to dominate
entry selection. Confounded by trade count changing; the `*_exit_isolated`
experiments settle it and have not been run.

Round 2 (h5 momentum 12-1, h6 earnings drift, h7 range expansion) is built and
unrun.

**Every result carries a survivorship caveat**: the 51-symbol universe is
today's large caps, no delisted companies. `screener universe coverage`
measures it; that has not been run either.

## Bugs already found and fixed — do not reintroduce

Each was invisible to a passing test suite and surfaced only on real data.

- **Vacuous verification.** `verify` reported PASS after comparing zero bars.
  Zero comparisons is not a pass.
- **Impossible tolerance.** It demanded cent-exact agreement between an
  IEX-only feed and a consolidated-tape source, which see different trades.
  Now 25 bps relative, plus a systematic-bias check.
- **Stop anchored to the wrong price.** H1's stop was measured from the prior
  close instead of the entry. A gap down to just above the level left a tiny
  risk per share, so an ordinary move read as a loss of many R.
- **Regime returns in R, compared against a percentage threshold.** Printed
  "worst −19725.7%".
- **Shared CLI defaults applied to a hypothesis whose spec differs.** H1 was
  run with a 2R target it does not have.

## Commands

```bash
screener config                     # what is wired up; prints no secrets
screener ingest --symbols X --start 2010-01-01
screener verify                     # Phase 1 gate — data correctness
screener metrics build
screener universe build
screener universe coverage          # survivorship measurement
screener ingest-earnings            # SEC EDGAR filing dates
screener diagnose redundancy | signals
screener backtest run --hypothesis h5 --split development
screener backtest surface --hypothesis h5 --vary hold=21,63,126
screener research explore --battery all
```

## Conventions

- Money is `Decimal`. Indicators are floats. Never size a position off a float.
- All arithmetic lives in `calc/`. Anything that reimplements it elsewhere puts
  the golden-value and no-lookahead tests out of reach of the code that
  actually decides trades.
- Tests state what would break in the docstring, not what the function does.
- `ruff check src tests` and `pytest` both clean before committing.

## Open decisions for the operator

- **Sizing is internally inconsistent.** At 1% risk with a 2-ATR stop a
  position is 25–33% of equity, so the 25% concentration cap binds on almost
  every trade and four positions exhaust the account. "Max 5 positions" and
  "5% total open risk" never bind. Options in `docs/07` §5.
- Proposed on arithmetic, not results: 0.5% risk, 20% cap, and an account-level
  drawdown circuit breaker (−8% halve risk, −12% no new entries, −15% stop).
