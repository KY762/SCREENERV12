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

**Re-measured three times on 2026-09-17; the current reading is below, under
"The stop-design finding, with the right test".** In short: h2/h3 fail
isolation outright; paired and month-clustered, **h1's no-stop advantage is 2.9
SE**, h4's 1.9 with its winner below random, h5's 1.5. Two intermediate
readings from the same day — "h4 at the 11th percentile" (a benchmark that
scored timing as selection) and "the finding is 1 SE" (an unpaired test) — were
both wrong and are superseded.

Round 2 has now run on development. **H6 ran for the first time on 2026-09-17**
and is not the exception it first looked like: `reaction_size` reaches the 89th
percentile but is non-monotonic across adjacent thresholds (85.7 → 26.0 → 88.7
→ 81.0, and the no-filter cell scores 85.7, so the filter is not what produces
it), while `drift_exits` and `entry_delay` sit below random. **H5's holding
period is 21 days, monthly** (operator decision,
2026-09-11), matching its own `monthly_rebalance` flag and the horizon the
momentum literature studies. Resolved in `HOLD_DEFAULTS`, not shared with H1.

**H1 is a swing rotation since 2026-09-18** (operator decision, docs/03 §H1
amendment): hold ∈ {10, 20}, default 20 (was 5), with an optional
`entry_delay` that re-checks the ranking and trend at the last close before
the buy. Both changes were made after seeing development results, and the
3/5-day runs already logged remain counted. `h1_entry_delay` tests delays
{1, 3, 6}; with the re-check it measures waiting and re-selection together.
Because `h1_exit_isolated` takes H1's default hold as its rebalance interval,
its 2.9 SE result (measured at the old 5) has to be re-measured rather than
carried over.

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
the missing population.

**The "$29 Polygon fix" recorded here and in `providers/alpaca.py:12` was
wrong, checked 2026-09-19.** Polygon (now Massive) sells history by depth: $29
buys 5 years, which reaches about 2021 and touches neither the 2010-2015
development split nor 2016-2019 validation; $79 buys 10 years, still cutting
into validation and its warm-up; only $199 covers the window. The fix bought
instead is **EODHD at $19.99 for one month** — US history mostly from 2000,
delisted tickers included — plus the free point-in-time index membership
above, which fixes the second survivorship channel that no price feed
addresses.

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
- **The budget counted evidential runs but did not bind them.** Found
  2026-09-18. `budget.check` limited how MANY configurations a hypothesis
  could spend on validation and test, never WHICH, so a slot could go to a
  configuration picked after looking. Evidential runs now require a signed
  pre-registration naming their exact hash (see "Pre-registration" below).
  The same review found three holes in the hash itself, all in
  `backtest run`'s hand-built config dict:
  - **`equity` was not hashed.** A second validation run at a different
    account size looked like a reproduction of the first and cost nothing:
    unlimited looks at the split by changing one number.
  - **`hold` was hashed as typed.** `--hold 5` and no `--hold` (the same H1
    run) hashed differently and would have spent two slots.
  - **`r_multiple or None` re-collapsed the canonical no-target `0.0` to
    None**, the value that re-resolves to h2–h4's 2R default. The
    idempotency bug above, back in a new file, and caught on the day it was
    written by `test_resolving_twice_changes_nothing`. `time_limit or None`
    did the same to 0 ("no time exit").
  All four are fixed by `backtest/preregistration.evidential_config`, the one
  function that builds a run's identity for both the CLI and pre-registrations.
  Development hashes shifted as a result; development is unlimited, and no
  validation or test row existed to repair.

- **An identity rule nearly quarantined three live companies.** Found
  2026-09-19, while building the quarantine. `outlived_its_security` fired on
  any symbol EODHD's delisted list names whose prices run to the end of the
  data, and EODHD's list marks live companies dead -- the same unreliability
  the module docstring already recorded, used as a verdict anyway. It flagged
  **AVB, EA and EQR**, all three of which had just left the index with correct
  continuous history (EA's last closes pinned at its take-private price).
  Excluding them would have destroyed clean data to prevent contamination that
  was not there. The rule now also requires the series to have outlived the
  membership by a year: BBBY's tail is 3,328 days, AVB's was 9.
  `test_a_company_that_just_left_the_index_is_not_flagged_as_outlived` pins it.

## The first battery on data with no known defect (2026-09-20)

**180 configurations, 1,020 symbols, 25 quarantined, splits adjusted, lookahead
guarded.** `research/20260920-development-battery.md`. Every earlier battery in
this project ran on data now known to be wrong, and none of their numbers
transfer.

**The strongest result the project has produced, and it is a gradient rather
than a cell.** `h1_selection` sweeps the momentum ranking window, and the
percentile against random on the same days is monotonic in it:

| rs_lookback | same-day percentile | expectancy | PF |
| --- | --- | --- | --- |
| **252** (12 months) | **95th-98th** | +0.141R to +0.147R | 1.36-1.37 |
| 126 (6 months) | 87th-91st | +0.104R to +0.132R | 1.30-1.38 |
| 63 (3 months) | 81st-86th | **-0.130R to -0.150R** | 1.18-1.23 |
| 21 (1 month) | 48th-62nd | +0.156R to +0.179R | 1.60-1.70 |

A dose-response across three adjacent cells is much harder to produce by chance
than one good cell, and **it is the shape Jegadeesh & Titman predict**. It only
appeared after the split fix, because unadjusted splits inverted the ranking.
Note that H1's own default lookback is **63 days**, sitting in the negative
band: the project has spent four rounds testing H1 at a window the literature
says is too short.

**The selected cell passes five of six pre-registered criteria**
(`rs_lookback=252, top_pct=0.1, hold=20, stop_atr=3.0`):

| Criterion | Observed | Required | |
| --- | --- | --- | --- |
| trade_count | **171 effective** (305 raw) | >= 200 effective | **fail** |
| expectancy | +0.146R | > 0 | pass |
| profit_factor | 1.37 | > 1.20 | pass |
| max_drawdown | 13.4% | < 25% | pass |
| regime_robustness | beat random in 2 of 3, worst +3.1% | >= 2 of 3 | pass |
| vs_random | same-day p = **0.0260** | <= 0.05 | pass |

**This is not evidence and must not be reported as any.** Development proves
nothing (docs/03 §0.4). The configuration was chosen by the plateau rule AFTER
seeing 12 cells, so it is a search result, not a prediction. The p = 0.0260 is
uncorrected for the 28 experiments in this battery, and Holm across the
registered family would be stricter still. It fails the trade floor outright,
and the design effect is now 1.78 rather than the 1.4 measured before -- with
`max_positions` at 5 and 1,641 signals refused for want of a slot, concurrent
trades are more correlated than they were.

**Everything else got worse, which is the useful part.** H1's own exit
experiments all return NONE. `h5_momentum_canonical` sits at the **0th
percentile** and `h5_rebalance` at the 0th, so H5's monthly form is below random
outright. H4's exit sweep is at the 1st. `h2/h3/h4_exit_isolated` all fail
isolation again (29-29.4% divergence). `h3_no_stop` looks strong at the 96th
with PF 1.81, but on **161 trades and a 35.5% drawdown**, failing two criteria.
H7 returns NONE in all three of its experiments.

## A configuration that passes every criterion (2026-09-21)

**On development, which proves nothing.** Recorded because it is the first
time it has happened, and because how it happened matters more than that it did.

The operator chose on 2026-09-21 to raise `max_positions` from 5 to 10 at 1%
risk. **That changed nothing at all** -- identical 305 trades, identical
+0.146R, identical 171 effective observations. At 1% risk per trade the **5%
open-risk cap binds at five concurrent positions** whatever `max_positions`
says; the refusal reason simply moves from "at max concurrent positions" to
"total open risk would reach 5.92%". An earlier note here called the position
count "the binding constraint on effective sample size". It was not, and that
claim is withdrawn.

The lever that works is risk per trade. At **0.5% risk with 10 positions** --
total open risk unchanged at 5%, the same money spread over twice the names:

| Criterion | 1% / 5 positions | **0.5% / 10 positions** | Required |
| --- | --- | --- | --- |
| trade_count | 171 effective (305) | **240 effective (602)** | >= 200 |
| expectancy | +0.146R | **+0.165R** | > 0 |
| profit_factor | 1.37 | **1.42** | > 1.20 |
| max_drawdown | 13.4% | **10.3%** | < 25% |
| regime_robustness | 2 of 3, worst +3.1% | **2 of 3, worst +1.4%** | >= 2 of 3 |
| vs_random | p = 0.0260 | **p = 0.0240** | <= 0.05 |
| | **fails 1 of 6** | **passes 6 of 6** | |

**The reason to believe this is that almost nothing moved.** Expectancy went
+0.146R to +0.165R and the percentile 97.5th to 97.7th. If halving risk had
transformed the result, the right conclusion would be that a new overfit had
been found. Instead the per-trade edge is unchanged and the observation count
doubled, which is what a sample-size fix is supposed to look like. Drawdown
fell because the same risk is spread wider, not because the rule improved.

**Why this is still not evidence.** Development proves nothing (docs/03 §0.4).
The lookback was chosen by the plateau rule after seeing 12 cells; four
configurations of this rule were then run on 2026-09-21 alone, and every look
adds to the multiple-comparison burden. p = 0.0240 is uncorrected for the 28
experiments in the battery, and Holm across the registered family is stricter.
The universe still enriches for momentum that persisted (survivorship channel
two, unmeasured).

**0.5% risk is not adopted.** Risk parameters are the operator's
(`docs/08`), and the operator's standing choice is 1% at 10 positions, which
the arithmetic makes identical to 1% at 5. The 0.5% figure above is a
measurement of what would clear the floor, not a change to the profile.

## Splits were never adjusted, and it inverted momentum

**Found 2026-09-20.** `price_daily` holds raw prices by design (non-negotiable
2), which makes a split a real discontinuity, and the "adjusted series derived
on demand" half of that rule was never built: `corporate_actions` held **zero
rows** and nothing read it. Through the code path the strategies use:

| | 63-day return, raw | adjusted | vol-adj RS, raw | adjusted |
| --- | --- | --- | --- | --- |
| AAPL 7-for-1, 2014-06-09 | **-81.7%** | +27.9% | **-8.21** | +14.36 |
| C 1-for-10 reverse, 2011-05-09 | **+765.6%** | -13.4% | **+6.92** | -9.74 |
| ETFC 1-for-10 reverse, 2010-06-02 | **+662.9%** | -23.7% | **+5.58** | -4.30 |

Every case flips sign. Apple after its split ranked **last** and was never
bought; Citigroup, a distressed bank reverse-splitting to keep its listing,
ranked **first** and was. The bias is directional, not noisy: forward splits
follow a price rise, so the rule systematically excluded recent winners, and
reverse splits signal distress, so it systematically bought them. **81 index
members and 130 events inside the 2010-2015 window alone.**

Fixed by `calc/splits.py` plus an EODHD splits ingest (490 splits across 339 of
1,050 symbols). `load_bars` adjusts **by default**, the polarity being
deliberate: a caller who forgets gets the correct series and must ask for raw.

**Back-adjustment is itself a lookahead risk, and it was a real one.** It
scales PAST prices by FUTURE splits. That is harmless for returns -- a split
outside the window multiplies every bar in it by one constant, which cancels in
every ratio -- but not for share counts. NBR's 1-for-50 reverse split in 2020
lifts its 2012 bars from $13.01 to $650.50, and at $10,000 equity the risk
budget then buys zero whole shares. A test written to check this went from 68
settled trades to **none**. `splits_until` now drops splits after the run's end
date at both loaders, and every backtest call site passes it. Splits the window
contains are still applied: AAPL's 2012 bar reads $80.14, not $20.04.

## The quarantine, and what liquidity revealed

**Built 2026-09-19.** `universe_members` -- the single point every backtest
reads membership through -- now filters against
`data/reference/universe_quarantine.csv`, a committed file of **24 symbols**
whose stored series is not the company that was in the index. A symbol leaves
the universe only if it appears there, with a reason and a date.

The strongest check is not vendor metadata, it is our own prices: **an S&P 500
member that traded under $1M a day while IN the index was not that member.**
Measured over 798 symbols with 60+ bars inside their membership window, the
median member trades **$152M a day** and the 5th percentile $34.5M. Ten
symbols fall below a floor set 34x under that 5th percentile -- AYE, RX, SII
and CPWR at literally **zero volume**, EP at $7/day, PARA at $32, ACS at $697,
GR at $7,140, KG at $68,372, GENZ at $338k. Every one is a company acquired or
taken private between 2010 and 2012 whose letters a shell or an ETF now holds,
and each is confirmed independently by the holder name: EP is now "Empire
Petroleum", PARA is "Banzai International", SII is "Sprott", KG is "Kestrel
Group". **None of these was caught by any rule reading vendor metadata.**

The 24 break down as 10 too illiquid, 12 whose letters now name an ETF, 1
(BBBY) the vendor calls delisted while pricing it for another nine years, and
1 hand-entered: **BBT**, which is Beacon Financial Corporation throughout --
41,810 shares a day in 2010 against JPM's 41 million -- and liquid enough
($2.1M/day median) to clear a floor set where no real member can fall. Hand
rows carry a reason no rule emits and survive `--write`.

**Not quarantined: the 34 whose history is merely ABSENT.** Their series start
after the ticker left, so there are no bars during the membership and nothing
to get wrong; excluding them would also discard a successor company's
legitimate later membership.

Whole-symbol exclusion is coarser than it should be -- the honest fix needs a
handover date the vendor does not give -- so periods that were fine are
discarded too. That costs coverage, which is the safe direction.

**The quarantine has to be applied at three doors, and only one existed.**
Membership was the obvious one, and it was also the least used: `backtest run`
and `research explore` default `--universe` to None, so every result in this
project was computed over every symbol in the database with no point-in-time
filter at all. Worse, `backtest run` carried its own hand-rolled copy of
`load_symbol_bars`, so the filter added to that function did not reach the one
command that spends validation and test budget. All three now go through
`load_symbol_bars`, which excludes quarantined tickers even when named
explicitly, logs what it dropped, and prints it.

**Measured effect on H1, development, default configuration**, through four
readings of the same run as each defect was fixed:

| | original | + quarantine | + splits | **+ lookahead guard** |
| --- | --- | --- | --- | --- |
| random, same days | 73.1th | 55.9th | 89.7th | **82.5th** |
| one-sided p | 0.270 | 0.442 | 0.104 | **0.176** |
| expectancy | -0.338R | -0.384R | +0.115R | **-0.297R** |
| profit factor | 1.03 | 1.02 | 1.24 | **1.16** |
| max drawdown | 34.1% | 33.7% | 14.8% | **25.5%** |
| regimes beating random | 2 of 3 | 1 of 3 | 1 of 3 | **1 of 3** |

**The third column was partly lookahead and must not be quoted.** It briefly
showed H1 clearing the profit-factor bar at 1.24 with a positive expectancy;
the guard took that back to 1.16 and -0.297R. The splits still help a great
deal against the second column, which is the honest comparison: the quarantine
cost H1 17 percentile points and the split fix returned 27 of them.

Against the pre-registered criteria the current reading **fails four of five**:
p=0.176 against 5%, profit factor 1.16 against 1.20, max drawdown 25.5% against
25%, and 1 of 3 regimes against 2. Only the effective-trade floor passes (229
against 200). One configuration, development, and development proves nothing.

Beating random in 1 of 3 regimes is below the pre-registered bar of 2. The
mechanism is visible: **45 of 2,241 H1 signals (2.0%) came from 10 quarantined
names**, and their development-window price ranges are ACS $0.095-$24.90
(262x), GR $0.04-$9.10 (228x), CPWR $0.0011-$0.08 (73x). Those are not company
returns, they are a series changing companies mid-window.

Be careful about the mechanism. The quarantined names are 2.3% of the pool and
produced 2.0% of H1's signals, so there is **no evidence they were selected at
an above-base rate** — an earlier note here claimed a momentum screen is drawn
to a ticker handover, and the measurement does not support it. What the data
shows is magnitude, not frequency: a handful of trades carried returns no
company produces, and 2% of signals cost 17 percentile points. Both benchmarks
draw from the same filtered pool as the strategy, so the move is the strategy
falling relative to random, not a changed yardstick.

One hypothesis, one configuration, development. **The battery has not been
re-run**; when it is, every figure in the sections above is restated.

## The EODHD purchase worked: coverage went from 15% to 96%

**Measured 2026-09-19 after the load.** This is the payoff from decision 4, and
it is the largest single improvement to data quality in the project.

| | before | after |
| --- | --- | --- |
| S&P 500 members 2010-2019 with bars in-window | **106 of 719** | **687 of 719 (96%)** |
| symbols with prices | 307 | 1,045 |
| daily bars | 881,449 | **3,726,042** |

**The point-in-time universe is now usable.** Membership resolves to 484-502
names across 2010-2019, and **92-99% of them have a bar on the day** (92% in
2010 rising to 99% in 2019). Before the load this was around 15%, which is why
every run to date used no universe filter at all.

**The missing failures are largely back, with correct endings.** FRC ends
2023-05-02 (the seizure), SIVB ends 2023-03-09 — both were absent before.
Acquisitions end at their deal dates: ATVI 2023-10-13, TWTR 2022-10-27, XLNX
2022-02-16, MXIM 2021-08-26, ALXN 2021-07-21, CERN 2022-06-08. **SBNY's tail is
a correct record, not contamination**: $110 to $70 through the March 2023
collapse, then OTC at $0.30-0.38 on a few thousand shares into 2026. It is
deliberately not quarantined. BBBY is present but contaminated and IS
quarantined. YELL, RAD, LEHMQ and WAMUQ have no symbol row because they were
never requested, not because coverage failed.

**What this does not fix.** The survivorship numbers in the section below were
measured on the old 307-symbol universe and have not been re-measured. Neither
has the battery. Both are expected to move.

## The 2026-09-19 decisions

Five open decisions, closed by the operator on 2026-09-19 after research into
what each would cost and what it would buy. All were taken **before any
validation or test run existed**, which is what makes them pre-registration
rather than revision.

**1. The criteria now all measure picking.** Recorded in docs/03 §0.6 with
what each was and why it changed: the trade floor counts **effective**
observations; "vs random" is a one-sided p against random names bought on the
**same days**, at a family-wise 5% corrected by **Holm**; regime robustness
asks whether the picks **beat random in ≥ 2 of a split's 3 buckets** rather
than whether a long-only rule made money through the 2018-Q4 correction. The
plateau rule may only select cells that beat random.

**2. Holm's family must be closed before the first validation run.** Signing
another registration afterwards changes the bar earlier runs were held to.
`screener prereg family` reports it; a single run is held to Holm's first and
strictest step, 5% ÷ m.

**3. The universe is point-in-time S&P 500 membership** (`sp500_pit`), not 307
of today's large caps. Free, MIT-licensed, vendored to `data/reference/`. It
measures the hole it fills: **719 companies were in the index across
2010-2019, this database has bars for 106**, and 303 of the missing are no
longer in the index. Caveat in `universe/sp500.py`: the membership is
point-in-time but the *symbols are not* (Yahoo's 2010 membership is filed
under `AABA`), so a renamed company can drop out by renaming rather than by
survival.

**4. The delisted-price fix is EODHD at $19.99 for one month**, not Polygon at
$29/month. The plan on record could not have worked: Polygon (now Massive)
sells history by depth — $29 buys 5 years, reaching about 2021, past the
2010-2015 development split entirely; $79 buys 10 years, which still cuts into
validation; only $199 covers it. EODHD's All World plan carries US history
mostly from 2000 with delisted tickers included. Adapter and settings are in
place; `EODHD_API_KEY` in `.env` is what it waits on.

**5. Intraday data is not needed.** Every hypothesis here runs on daily bars.

Still open, and recorded rather than decided: whether the remaining validation
slots are ever spent, and the sizing/circuit-breaker items below.

## Pre-registration

**Added 2026-09-18.** A validation or test run is refused unless a SIGNED file
in `preregistrations/` names its exact configuration. Each file is Markdown:
prose for the reasoning, plus one ```toml block the code binds to. It allows at
most the split's budget of configurations, one file per hypothesis, and an
optional `[decision]` bar that `backtest run` applies and counts toward
pass/fail. A malformed file fails the whole load rather than being skipped,
because a registration that silently fails to load is a guard that fails open.
`screener prereg show` lists status, hashes, and spend. Only the operator
signs.

`preregistrations/H1.md` is a **draft**, and its drafter recommends not signing
it. It fixes the `h1_exits` plateau centre (hold 10, stop 2.5 ATR, 63-day
lookback, top 10%) and records that this configuration **fails regime
robustness on development**: 1 of 3 regimes positive, worst −22.1%. All of its
edge comes from the 2013–14 bull market, and it trailed SPY (+52.9% vs
+81.2%). Its value is that the configuration is now fixed before any further
decision about regimes, coverage, or holds can reshape it.

## H1 as a swing rotation: the delay hurts and the stop finding does not survive

**2026-09-18, battery after the H1 amendment (hold default 20, delay added).
Supersedes the H1 figure in the next section.**

- **Entry delay, with the buy-day re-check:** delay 1 gives +0.069R (79th
  percentile same-day), delay 3 **+0.023R (70th)**, delay 6 **−0.023R (9th)**.
  Waiting makes H1 worse at every step, and the plateau rule selects no delay.
  The Jegadeesh & Titman skip-a-week motivation doesn't carry over to this
  rule. (The experiment measures waiting plus re-selection; the data can't
  separate them.)
- **The no-stop advantage was a property of the 5-day rotation.** Measured
  when H1 re-ranked every 5 sessions and held 20, it was 2.9 SE paired. With
  re-ranking every 20 sessions (the new default), no-stop still leads, +0.205R
  vs +0.107R, but by **0.8 SE** over 453 pairs. No exit comparison in the
  battery now clears 2 SE.
- **Narrowing the hold grid moved the plateau centre**, as recorded in the
  amendment: from hold 10 / 2.5 ATR on the 4 × 5 grid to **hold 10 / 2.0 ATR on
  the 2 × 5 grid, which fails the profit-factor bar** (1.154 against 1.20).
  `h1_no_stop` now selects hold 20, which also fails it (1.17).
  `preregistrations/H1.md` keeps the configuration chosen before the change.

Taken together, H1 under the operator's swing definition has no rule-selected
configuration that clears every pre-registered criterion on development.

## The stop-design finding, with the right test (as measured on the 5-day rotation)

**2026-09-17. Superseded for H1 by the section above,** which re-measures it
under the 20-day default. Kept because it records why the unpaired "1 SE"
figure was the wrong test.

The exit-isolated arms take the same signals and differ only in the exit, so
the question is whether each no-stop trade beat ITS OWN stop twin — same stock,
same day. The first error bar put on this compared the arms as two independent
means, which counts the stock's own move (common to both twins, and most of
each trade's return) as noise. Paired, and clustered by entry month so
correlated trades are not counted as independent:

| arm | pairs | mean gap / trade | unpaired | paired | **paired, month-clustered** | paired, qtr-clustered |
| --- | --- | --- | --- | --- | --- | --- |
| `h1_exit_isolated` | 705 | +0.87% | 1.1 | 3.2 | **2.9** | 3.0 |
| `h4_exit_isolated` | 2,040 | +0.65% | 2.3 | 3.8 | **1.9** | 1.7 |
| `h5_exit_isolated` | 352 | +0.64% | 0.9 | 1.8 | **1.5** | 1.5 |

So: **H1's no-stop advantage clears 2 SE under every version of the test.**
H4's clears only while trades are treated as independent, and its winning arm
sits at the 40th percentile against random besides. H5's does not clear.
`h2/h3_exit_isolated` remain vetoed for failed isolation (27.3%, 28.9%) —
pairing on the shared subset would not repair arms that took different trades.

This is one hypothesis clearing on the development split, with clustering that
charges for trades opened together but not for trades opened apart and held
through the same stretch. It is the strongest single result in the project and
it is still not evidence (docs/03 §0.4). docs/07's original 5.8 SE belongs to
the confounded comparison and does not transfer.

## Effective sample size

**Measured 2026-09-17** with `screener diagnose sample-size`, on configurations
declared before they ran. Design effects are modest — the correlation between
concurrent trades costs 15-40% of nominal N, not the two-thirds that was feared:

| configuration | trades | design effect (month / qtr) | effective N | nominal needed for 200 |
| --- | --- | --- | --- | --- |
| h1 plateau centre (hold 10, 2.5 ATR) | 566 | 1.5 / 1.2 | 385-480 | 294 |
| **h1 selection (126d, top 20%)** | 308 | 1.4 / 1.2 | 227-257 | **271** |
| h5 specification | 211 | 1.1 / 1.3 | 163-189 | 259 |
| h4 no stop, 20 bars | 249 | 1.5 / 1.3 | 165-187 | 302 |
| h6 reaction 0.03 | **96** | 1.4 / 1.6 | **59-68** | 328 |

The pre-registered floor of 200 would need roughly **260-330 nominal trades**
to mean 200 independent observations. H5, H4 and H6 do not reach that, and
H6's 93rd-percentile result rests on about 60 effective observations. The
`h1_selection` configuration (308 trades) does reach it, but it was
called "the H1 lead" on 2026-09-17 in error: it is that surface's plateau
centre, with **profit factor 1.099, below the 1.20 bar**. The 97th percentile
belonged to the peak, which the plateau rule rejects. Month- and quarter-clustering disagree in both directions; with
only ~21 quarters the quarterly estimate is noisy, which is why scoring uses
monthly (`backtest/inference.py`).

## Survivorship exposure, per hypothesis

**Measured 2026-09-17** with `screener diagnose survivorship`. Failures are
absent and acquisitions present, so a rule that buys recent losers has had its
worst outcomes removed. The diagnostic ranks every signal's trailing return
against the cross-section on its signal date; random selection lands in the
bottom decile 10% of the time (1.00x).

| | trend filter on (as run) | trend filter off |
| --- | --- | --- |
| H1 | 0.00x | **0.08x** |
| H5 | 0.00x | **0.11x** |
| H2 | 0.00x | 0.74x |
| H4 | 0.01x | 0.91x |
| H7 | 0.02x | 0.95x |
| H3 | 0.02x | **1.28x** |

Two findings, not one. **The trend filter is what protects H2/H3/H4/H7** —
their own selection is roughly random with respect to distress, and H3 seeks it.
**H1 and H5 avoid distress intrinsically**, still near zero with the filter off,
so their protection is structural rather than a setting. Momentum-rule results
are much less damaged by the missing failures than the blanket caveat implies.

**What this does not cover, and it matters for momentum specifically.** It
bounds the slow-decline channel only: a sudden collapse (fraud, failed trial,
bank run) is invisible to trailing return. And it measures the missing
FAILURES, which is one of two survivorship channels. The other is the universe
itself — today's large caps, selected on having succeeded by 2026. A 2012 stock
with strong momentum that later stagnated out of large-cap status is absent
without ever having failed. That channel enriches the universe for momentum
that *persisted*, which flatters exactly the rules this table clears.
It is not measured here, and it cuts against validating momentum before
coverage is fixed.

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
screener universe identify          # what each ticker refers to now
screener universe quarantine        # symbols excluded from every universe, and why
screener diagnose identity          # is this series the company we think it is?
screener diagnose survivorship      # per-hypothesis exposure to missing failures
screener diagnose sample-size       # effective N; paired exit comparisons
screener prereg show                # what validation/test may be spent on
screener backtest run --hypothesis h5 --split development
screener backtest surface --hypothesis h5 --vary hold=21,63,126
screener research explore --battery all
screener forward record -h h1 --since 2026-09-22   # paper book: append today's signals
screener forward book   -h h1                      # what they have done since
screener ingest-actions             # splits; nothing works correctly without them
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
  its own entry dates, and — for `use_stop` arms — isolation held. The gap is
  tested PAIRED for `use_stop` arms (same stock, same day) and unpaired
  otherwise, both with month-clustered standard errors. Shapes are now
  `separated` / `indistinct` / `none`. The constant lives in
  `backtest/surface.py` so moving it is a visible edit.
- ~~Which benchmark the criteria score against~~ — **decided 2026-09-19**:
  the same-day (date-matched) one, as a p-value. See docs/03 §0.6.
- ~~The regime criterion demands every regime in a split be positive~~ —
  **decided 2026-09-19**: beat random in ≥ 2 of the split's 3 buckets, keeping
  the −15% floor. Original note kept for the record:
- **The regime criterion demands every regime in a split be positive.**
  docs/03 §0.6 says "positive in ≥ 3 of 5 buckets", but `REGIMES` puts
  exactly three buckets in each split, so "≥ 3 positive" in practice means all
  of them. On validation that includes the 2018-Q4 correction: a long-only rule
  must finish net positive through a quarter when the S&P fell about 14%. The
  spec and the code also disagree on the buckets themselves (the spec lists
  corrections in 2015-08 and 2016-01 that the code doesn't define). This must
  be resolved before any validation is spent. The resolution is also being
  made after seeing H1 fail this criterion on development
  (`preregistrations/H1.md` §4), and that should be written down with it.
- ~~The plateau rule selects configurations that lose to random~~ —
  **decided 2026-09-19**: it may only select cells that beat random. Original
  note kept for the record:
- **The plateau rule selects configurations that lose to random.** docs/03
  §0.7 asks only whether a positive cell has positive neighbours. It never
  consults the random benchmark, so on the 2026-09-18 battery it marks four
  configurations selectable that sit BELOW random on their own entry dates:
  `h7_no_stop` (26th), `h6_drift_exits` (34th), `h5_no_stop` (40th),
  `h7_compression_depth` (44th). The two-arm criterion added the same day does
  require the winner to beat random, so the two rules now disagree about what
  "selectable" means. Adding the same requirement to the plateau rule is a
  change to pre-registered criteria, so it is recorded here, not made.
- ~~Raise the trade floor?~~ — **decided 2026-09-19**: the floor is 200
  EFFECTIVE observations. Original note kept for the record:
- **Raise the trade floor?** Measured (see "Effective sample size"): 200
  effective observations need roughly 260-330 nominal trades at these design
  effects. Whether the pre-registered floor of 200 should become ~300 is a
  criteria change, so it is recorded rather than made. As things stand the
  floor would pass H5 (211) and H4 (249) configurations that hold well under
  200 independent observations.
- ~~The across-hypothesis correction~~ — **decided 2026-09-19**: Holm at a
  family-wise 5% across the registered validation tests, with the family
  closed before the first run.
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
