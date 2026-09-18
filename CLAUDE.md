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
experiments settle it. **Re-run clean on 2026-09-11 — see `docs/07` §2a.** Only
H5's arms actually took the same trades (355 vs 371, 4.5%); h2/h3/h4 diverged by
24–65% and measure the old confound again, so `max_positions` is now 400 and the
report prints ISOLATION FAILED when arms diverge. H5 clean: stop +0.126R,
no stop **+0.249R**. One hypothesis, development, biased data — suggestive, not
settled.

**Weaker again after 2026-09-17.** With the target bug above fixed, holds
lengthen and h2/h3 fail isolation outright (27.3%, 28.9%). Of the arms that do
isolate, h4's no-stop **+0.294R sits at the 11th percentile** against random —
below a coin toss — leaving only h1 (+0.088R, 80th) and h5 (+0.249R, 73rd)
above random, neither above the 95th. The no-stop effect is substantially
market exposure, which is what a duration-matched benchmark is for.

Round 2 has now run on development. **H6 ran for the first time on 2026-09-17**
and is not the exception it first looked like: `reaction_size` reaches the 89th
percentile but is non-monotonic across adjacent thresholds (85.7 → 26.0 → 88.7
→ 81.0, and the no-filter cell scores 85.7, so the filter is not what produces
it), while `drift_exits` and `entry_delay` sit below random. **H5's holding
period is 21 days, monthly** (operator decision,
2026-09-11), matching its own `monthly_rebalance` flag and the horizon the
momentum literature studies. Resolved in `HOLD_DEFAULTS`, not shared with H1,
which rotates on 5.

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
- **A zero-R target is a target at the entry price.** `r_multiple=0` made
  `target = fill + 0 x risk`, so the next bar whose high touched the entry
  closed the trade at entry minus slippage. Every trade a guaranteed small
  loss, logged as a "target" exit. Found 2026-09-11 in `h7_no_stop`: 1,138
  trades, 1,090 target exits, **0% win rate**, PF 0.00. Eight experiments
  passed 0 meaning "no target", including `EXIT_ISOLATED_PORTFOLIO` and so
  every `*_exit_isolated` arm. **Those results are void.** `h5_no_stop` is the
  only no-stop experiment unaffected -- it never set `r_multiple`, so
  `resolved()` left it None. `ExitRule` now normalises any non-positive
  multiple to None.
- **The same configuration can be logged under two different budget hashes.**
  `budget.config_hash` hashes the config dict, so `r_multiple: 0` and
  `r_multiple: null` are different hashes for a run the engine executes
  identically -- `ExitRule` normalises both to None, and `resolved()` now does
  too, so rows written before 2026-09-11 carry `0` and rows after carry `null`.
  On development that costs nothing. On validation the same configuration would
  consume two of the three slots and `already_run` would not recognise the
  repeat: non-negotiable #5 failing quietly. Nothing to repair while validation
  is unspent -- confirm that with
  `SELECT split, COUNT(*) FROM research_runs WHERE split <> 'development' GROUP BY split;`
  before spending any of it.
- **Shared CLI defaults applied to a hypothesis whose spec differs.** H1 was
  run with a 2R target it does not have. **Reintroduced for Round 2 and found
  again on 2026-08-27**: the fix had hardcoded H1 as the sole exception
  (`r_multiple = None if key == "h1" else 2.0`), so h5–h7 inherited H2–H4's
  exit rules. H5's first development run therefore carried a 2R target it does
  not have and a 10-bar time limit against a spec of `hold` — testing the
  short-horizon momentum docs/03 §H1 already records as much weaker than the
  12-month form H5 exists to examine. The CLI now defers to
  `RunConfig.resolved()`, and the resolved values are what get hashed for
  budget, so a run cannot log a configuration it did not use. **That H5 result
  is void; re-run it.**
- **`resolved()` was not idempotent, so "no target" grew a target.** Found
  2026-09-17. `battery.py` resolves a config to key its candidate cache and
  `evaluate()` resolves it again before running, so `resolved()` runs twice.
  It mapped explicit `r_multiple=0` to None on the first pass, and the second
  pass read that None as *unspecified* and applied h2–h4's 2R default. Six
  experiments that declare no target ran with one — `h2/h3/h4_no_stop` and
  `h2/h3/h4_exit_isolated` — while logging `r_multiple=None`. The only visible
  symptom was `target` exits appearing in a run with no target. **Third time
  this project has recorded a configuration it did not run.** Fixed by making
  "no target" canonicalise to `0.0`, which is a fixed point, and by making
  `has_target` the single predicate both layers read, so the logged config and
  the executed rule cannot disagree. `test_resolved_is_idempotent` pins it.
- **EDGAR's `filings.recent` is one page, not the filing history.** Found
  2026-09-17. It holds roughly the latest thousand filings of *every* form,
  Form 4s included, so for an active large cap it can be only a couple of
  years deep; older filings live in `filings.files` and were never fetched.
  The early part of a window silently returned nothing, which is
  indistinguishable from a company that filed nothing: 10,391 events ingested
  but only **1,218 inside the 2010–2015 split, across 92 of 271 symbols**.
  H6's first battery scored +0.203R on 45 trades on that. After paging:
  **4,786 events across 208 symbols**, and the year counts went flat
  (876/739/755/775/801/840) instead of starved early — the flatness is the
  check that it worked.
- **A duplicate key rolled back a 307-symbol ingest, and it exited 0.** Found
  2026-09-17. Uniqueness is `(symbol_id, filed, form)`; the writer compared
  new filings against stored rows but never against each other, and a company
  can file one form twice in a day for two periods (CRVL, two `10-Q/A` on
  2010-04-09 — `earliest_per_period` collapses by PERIOD, so both survive).
  The whole run rolled back while reporting success, the same shape as the
  vacuous verification above. The seen-set now grows as the batch is written.

## The stop-design finding is 1 standard error

**2026-09-17, and it supersedes everything above about exit design.** Two-arm
comparisons never carried an error bar. Now that each arm reports a standard
error on mean per-trade return, the gaps are:

| arm | gap | standard errors |
| --- | --- | --- |
| `h5_exit_isolated` (the clean one, 4.3% divergence) | +0.123R | **0.9** |
| `h1_exit_isolated` (11.8% divergence) | +0.099R | **1.1** |
| `h5_rebalance` | +0.202R | 1.2 |
| `h1_trend_filter` | +0.004R | 0.2 |

Nothing reaches 2. And that SE assumes independent trades, which five
concurrent positions in correlated large caps are not, so the real figure is
lower. `h2/h3_exit_isolated` are vetoed separately for failed isolation (27.3%,
28.9%), and `h4_exit_isolated`'s +0.399R gap has its winner at the 40th
percentile.

So "removing the stop is worth roughly +0.1R" was never distinguishable from
noise. It was a difference nobody had put an error bar on, repeated across
three rounds of increasingly careful measurement, each of which fixed a real
confound and none of which asked whether the gap was larger than its own
uncertainty. docs/07's original 5.8 SE belongs to the confounded comparison and
does not transfer.

## Two benchmarks, and the difference between them is the timing

**Added 2026-09-17.** `random_benchmark` picks its own entry dates, so it scores
selection AND timing: a strategy whose signals cluster in a bad month loses to
it while picking perfectly well. `date_matched_benchmark` holds each real
trade's entry date and length and swaps only the symbol, so what is left is the
pick. Report both; the gap between them IS the timing contribution.

It mattered immediately. **17 of 27 experiments ranked higher once timing was
held fixed**, and the count above the 50th went 13 → 16. The largest moves:

| experiment | any day | same days |
| --- | --- | --- |
| `h2_exit_isolated` | 23rd | **57th** |
| `h4_exit_isolated` | 11th | **40th** |
| `h5_skip_matters` | 45th | 67th |
| `h6_entry_delay` | 31st | 51st |
| `h5_exit_isolated` | 73rd | 87th |

`h4_exit_isolated` at the 11th percentile was read here as "89% of random
selections beat it". Most of that was when it traded, not what it bought.
Eligibility for the swap is "had a bar that day with enough bars after it",
NOT point-in-time index membership, which is not threaded into `evaluate()` --
so the pool can include a name that was listed but out of the universe.

## What the random-selection percentile keeps showing

Added to the report tables 2026-09-17, because the caveat at the foot of every
battery called percentiles "the comparison that matters" while no table printed
one. Expectancy alone had been read as a result three times.

The benchmark samples **matched holding periods**, so it prices the market
exposure a configuration takes. Removing a stop lengthens holds, and in a
2010–2015 bull market that earns — which is why expectancy and percentile are
so often anti-correlated here. `h4_exit_isolated` has the largest no-stop
expectancy of any isolated arm, **+0.294R, at the 11th percentile**: 89% of
random selections beat it. Read without the percentile it is the best exit
result in the battery; read with it, it is beta.

Of the isolated exit arms only **h1 (80th)** and **h5 (73rd)** beat random, and
neither clears the 95th. H6's headline numbers — +0.255R `entry_delay`, +0.161R
`drift_exits` — sit at the **31st and 26th**.

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
- **Sign off (or reject) the two-arm criterion.** Implemented 2026-09-17,
  replacing plateau/spike on two-cell grids, which is a pre-registered-criteria
  change and therefore yours. An arm is selectable only if it is positive, the
  gap clears `SEPARATION_Z = 2.0` standard errors, the winner beats random on
  its own entry dates, and — for `use_stop` arms — isolation held. Shapes are
  now `separated` / `indistinct` / `none`. Under it, **no two-cell experiment
  in the battery is selectable**. The constant lives in `backtest/surface.py`
  so moving it is a visible edit.
- **Which benchmark the pre-registered criteria score against.**
  `check_criteria` still takes the uniform percentile, deliberately unchanged.
  The date-matched one is the better instrument for "did selection add
  anything", but switching what the criteria read is a criteria change.
  Nothing is scored on validation yet either way.
- **Effective sample size.** Five concurrent positions in correlated names are
  not five independent observations, so every standard error above is
  optimistic and the ≥200 trade floor may be far too low. Worth measuring
  before a validation slot is spent on an underpowered test.
- **The across-hypothesis correction.** Seven hypotheses x 3 validation configs
  is 21 shots at the bar; several clear by chance. A decision, not code, and it
  has to be made before any validation is spent or it is post-hoc.
- **The plateau/spike test may not belong on a two-cell structural question.**
  `docs/03` §0.7 rule 3 rejects a peak whose neighbours fail. On a binary arm
  — `use_stop=True/False`, `trend_filter=True/False` — a winning cell's only
  neighbour is the losing one, so SPIKE is the verdict whenever the comparison
  separates at all, which is what an A/B is supposed to do. Every
  `*_exit_isolated` arm except h5's is therefore unselectable by construction
  rather than by evidence. `battery.py` already separates structural from
  parameter questions; the verdict machinery does not. Pre-registered criteria
  are the operator's to change, so this is recorded, not fixed.
- **Earnings coverage is 208 of 271 symbols in-window, not 271.** The rest have
  no CIK on EDGAR or listed after 2015. Whether H6 can be asked anything on 208
  symbols is a judgement about the hypothesis, not about the data layer.
