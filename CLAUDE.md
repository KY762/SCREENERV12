# SCREENERV12 — working notes for Claude

Personal market-research and trading-operations platform. One operator,
$10,000, US equities, daily bars, long only.

**Read `docs/01-PROJECT-CHARTER.md` before proposing anything strategic.** The
operator's documented losses came from execution — missing stops, size
escalation after losses, profit quotas — not from strategy selection. Software
that makes those decisions mechanical is the point of the project.

## How to work here

Full protocol in `docs/08-OPERATING-PROTOCOL.md`. The parts that bite:

- **The objective is evidence, not features.** This platform exists to
  determine whether trading concepts have measurable predictive value under
  realistic conditions. A feature that adds complexity without improving
  evidence quality should be argued against, not built.
- **Interpret before executing.** The request is evidence of intent, not a
  specification of it. If the proposed method conflicts with the objective,
  say so before building.
- **Disagree when there is a substantive reason.** Logically inconsistent,
  statistically weak, redundant, likely to create false confidence, or
  inferior to an obvious alternative — all grounds to push back. Never
  "that's what you asked for" as a defence of a bad result.
- **Never manufacture confidence.** No hypothesis here has passed validation.
  Do not call anything profitable. "We don't know yet" and "this cannot be
  established from the available data" are correct answers.
- **Label facts, inferences and assumptions as what they are.** An assumption
  presented as a fact is the failure mode this project is built to prevent.
- **Surface disagreement; do not act on it unilaterally.** Risk parameters,
  hypothesis specifications and pre-registered criteria are the operator's to
  change. The sizing inconsistency below is recorded rather than fixed for
  exactly this reason.
- **Audit before delivering.** State the strongest criticism of your own
  output and fix it first.

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

**Survivorship is measured, and it is asymmetric.** `screener universe
coverage` on 2026-08-26 against Tiingo: acquisitions **6/6 present**, failures
**0/6 present** (FRC, BBBY, YELL, RAD absent; SIVB and SBNY still return bars
dated today despite failing in March 2023 — reused or stale series, not
coverage). Acquisitions end at a premium and failures end near zero, so the
data keeps every good ending and loses every bad one. The bias is directional
and upward on every backtested return. Absence may also mean never-covered,
so 0/6 is a floor, not a measurement.

Consequence: Round 1's negative h1–h4 results were produced *with* this bias
helping them, which makes them more credible, not less. Value screens are the
most exposed thing here — they select distressed companies, which is exactly
the missing population. Polygon (~$29/mo) is the documented fix
(`providers/alpaca.py:12`).

**Do not spend validation or test budget until delisted coverage is fixed.**
Development is unlimited and the bias direction is known, so Round 2 can run
there. Validation (3 configs) and test (1, once) are enforced against the
database and never regenerate; spending them on knowingly biased data burns
them permanently.

Universe as of 2026-08-26: 265 candidates ingested, 263 returned bars, 307
symbols with metrics (the pool plus the earlier 51). 881,449 daily bars;
562,535 point-in-time membership rows across 3,938 dates. Two ingest failures
were both instructive — `GPS` because Gap Inc. now trades as `GAP` (fixed),
`PSTG` for reasons still unknown.

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

- **Sizing is inconsistent only below 2% ATR.** Position size as a fraction of
  equity is `0.01 / (2 × ATR_pct)`, so the 25% concentration cap binds exactly
  when ATR% < 2.0%. That holds for low-volatility mega caps — the slice this
  note was originally inferred from — and not for the wider pool. Measured on
  307 ingested symbols (2026-08-26): **185 good, 58 marginal, 64 unusable**,
  with effective risk on the good set at 0.92–0.99% against an intended 1%.
  The cap is not binding on the majority of candidates. "Max 5 positions" and
  "5% total open risk" still never bind. Options in `docs/07` §5.
- Proposed on arithmetic, not results: 0.5% risk, 20% cap, and an account-level
  drawdown circuit breaker (−8% halve risk, −12% no new entries, −15% stop).
