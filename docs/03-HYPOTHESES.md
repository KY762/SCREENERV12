# Research Hypotheses — Round 1

**Date:** 2026-08-16 (rev. 2 — operator amendments folded in)
**Status:** **Stage B (Objective Specification)** for all three. Nothing tested; no results exist.
**Depends on:** [`02-TRADER-PROFILE.md`](02-TRADER-PROFILE.md) · [`04-INDICATOR-EVALUATION.md`](04-INDICATOR-EVALUATION.md)

### Revision 2 — what changed and why

Operator review identified that rev. 1 hard-coded several numbers (`1.5 × ATR` displacement, `10`-day
sweep lookback) as though they were derived, when they were assumed. **The operator is correct, and this
is the exact failure the project exists to avoid** — importing ICT/SMC terminology and quietly attaching
arbitrary constants makes a system *look* quantitative while resting on the same unexamined folklore as
the win-rate tables rejected in profile §1.3.

Governing principle, adopted for the project:

> **Every constant is either derived from evidence, conventional and declared as such, or it is itself a
> hypothesis under test. No third category exists.**

Structural changes in this revision:

| Change | §  |
| --- | --- |
| Three-way data split (development / validation / test) replaces the two-way split | 0.4 |
| Explicit separation of **structural** questions from **parameter** questions, with different evidentiary standards | 0.7 |
| Parameter evaluation reports the **stability surface**, not the best point | 0.7 |
| H2 displacement becomes a **separable, testable filter**, not a precondition | H2 |
| H2 displacement measure (range vs body vs gap) becomes a tested question | H2 |
| H3 liquidity reference becomes **the variable under test**, not a fixed 10-day low | H3 |
| Variant budget restructured per data split rather than a single global cap | 0.8 |

---

## 0. Shared specification

### 0.1 Universe

| Filter | Value | Status |
| --- | --- | --- |
| Listing | US primary, NYSE/Nasdaq/AMEX | Structural |
| Instrument | Common stock + ETFs | Structural |
| Price | ≥ $10.00 | **Convention** — declared, not tuned |
| Avg dollar volume | ≥ $20M over trailing 50 days | **Convention** — a $2,000 position is ~0.01% of daily volume |
| History | ≥ 250 trading days | Derived — required for 252-day metrics |
| Excluded | Leveraged/inverse ETFs | Structural — path-dependent decay |
| Excluded | Restricted list | Compliance hook (profile §12), empty by default |

Universe membership is evaluated **as of each historical date**, never as of today.

The two conventions are deliberately *not* tuned. Tuning a liquidity filter to improve backtest results
is a well-known route to selecting a survivorship-favourable subset. They are held fixed and disclosed.

### 0.2 Position sizing — identical across all hypotheses

```
risk_dollars   = account_equity × 0.01
shares         = floor(risk_dollars / (entry − stop))
position_value = shares × entry
```

| Constraint | Value | Source |
| --- | --- | --- |
| Risk per trade | 1.0% of equity | Profile §7 |
| Max position value | 25% of equity | Concentration limit at $10k |
| Max concurrent positions | 5 | Profile §6 |
| Max total open risk | 5% | 5 × 1% |
| Max per GICS sector | 2 | Correlation control |
| Stop entry | Simultaneous with entry | Profile §7.1 veto 1 |

Oversized positions are **reduced**; stops are never widened to accommodate size.

### 0.3 Transaction costs

| Component | Assumption |
| --- | --- |
| Commission | $0.00 |
| Slippage | 5 bps/side baseline, **all results also reported at 15 bps/side** |
| Borrow | N/A — long only |

### 0.4 Data splits — three, not two

| Split | Dates | Use | Reuse policy |
| --- | --- | --- | --- |
| **Development** | 2010-01-01 → 2015-12-31 | Free exploration. Parameter surfaces, structural comparisons, spec revision. | **Unlimited.** Nothing here counts as evidence. |
| **Validation** | 2016-01-01 → 2019-12-31 | Confirm configurations chosen on development data | **Budgeted** — see §0.8 |
| **Test** | 2020-01-01 → 2026-06-30 | Stage E, final | **One configuration per hypothesis. Once.** |

**This three-way split is what makes the operator's amendment implementable.** Testing every assumption
is correct in principle, but doing it on a single in-sample period reintroduces the multiple-comparisons
problem that the variant budget exists to prevent. Separating exploration from confirmation resolves the
tension: **explore freely where results carry no evidential weight, and spend strictly where they do.**

Regime buckets for robustness reporting:

| Bucket | Period | Split |
| --- | --- | --- |
| Chop | 2011, 2015 | Dev |
| Bull | 2013–2014 | Dev |
| Correction | 2015-08, 2016-01, 2018-Q4 | Dev / Val |
| Bull | 2017, 2019 | Val |
| Crash | 2020-02 → 2020-04 | Test |
| Bear | 2022 | Test |
| Bull | 2023–2024 | Test |

Note the test split contains the crash and bear regimes. That is unavoidable given chronological
ordering, and it means test-set results will be regime-loaded rather than representative. **Stated now,
before results exist, so it cannot be used as a post-hoc excuse.**

### 0.5 Benchmarks

| Benchmark | Tests for |
| --- | --- |
| SPY buy-and-hold | Beats doing nothing? |
| **Random selection**, same universe / count / holding period, 1,000 iterations | **Does selection add anything beyond long exposure?** |
| H1 | Do SMC-derived rules beat the simplest alternative? |

### 0.6 Pre-registered success criteria

Fixed before any test. Advancement requires **all**:

| Criterion | Threshold |
| --- | --- |
| Trade count | ≥ 200 |
| Expectancy after costs | > 0 |
| Profit factor | > 1.20 |
| vs. random benchmark | > 75th percentile of 1,000-iteration distribution |
| Max drawdown | < 25% |
| Regime robustness | Positive in ≥ 3 of 5 buckets; none worse than −15% |
| **Parameter stability** | See §0.7 — replaces the previous ±20% rule |

Failing a criterion rejects or revises the hypothesis. **Thresholds do not move.**

### 0.7 Parameter methodology — the core of revision 2

Two categories of question, with different evidentiary standards. Conflating them is how "testing
everything" becomes data mining.

#### Structural questions — genuine hypotheses

*Does displacement matter at all? Which liquidity reference is swept? Range or body?*

These are discrete, mechanistically distinct alternatives. Each is a separate hypothesis, tested and
reported independently, and each consumes variant budget.

#### Parameter questions — estimation, not hypothesis

*Is the threshold 1.4 or 1.6 ATR? Is the lookback 8 or 12 bars?*

These are **not** answered by picking the best value. They are answered by examining the **stability
surface**:

| Surface shape | Interpretation | Action |
| --- | --- | --- |
| **Plateau** — a broad contiguous region of parameter values with positive expectancy | Consistent with a real effect | Choose the **centre of the plateau**, not the peak |
| **Spike** — one value works, neighbours fail | Consistent with noise | **Reject the parameter, and question the hypothesis** |
| **Cliff** — works above/below a boundary | Possible real threshold effect, or possible artefact | Investigate mechanism before accepting |

**Rules:**

1. Parameter surfaces are generated **on the development split only**.
2. Reports show the **full surface**, never a single number. A profit factor quoted without its
   neighbourhood is uninterpretable.
3. The selected value is the **plateau centre**, deliberately not the maximum. Choosing the maximum is
   fitting to noise by construction.
4. **A parameter with no plateau is evidence against the hypothesis**, not an invitation to search
   harder.
5. Every reported result states **how many configurations were tested** to reach it. A result selected
   from 50 trials is weaker evidence than the same result from 3, and the reader is entitled to know.

#### Convention vs. tuned parameter

Some constants are held fixed by declaration rather than tested — ATR(14), SMA(50)/(200), 252-day year,
20-day volume average. These are **conventions**: widely used defaults adopted to avoid spending
degrees of freedom on questions we have no reason to care about. Each is labelled `[CONVENTION]` in the
specs below. **A convention that turns out to be load-bearing is a finding worth reporting** — if a
result is highly sensitive to ATR(14) versus ATR(20), it is fragile regardless of how conventional 14 is.

### 0.8 Variant budget — restructured per split

| Split | Budget | Rationale |
| --- | --- | --- |
| **Development** | Unlimited | Results carry no evidential weight. Full parameter surfaces expected. |
| **Validation** | **3 configurations per hypothesis** (9 total) | Enough to compare structural alternatives; few enough to keep false-positive risk bounded |
| **Test** | **1 configuration per hypothesis** (3 total) | One shot |

Multiple-testing adjustment: validation results are reported alongside the number of development
configurations that preceded them. Where a Sharpe ratio is quoted, a **deflated Sharpe ratio** (Bailey &
López de Prado) accounting for trial count is reported beside it.

---

## H1 — Relative-Strength Continuation *(CONTROL)*

> Liquid US equities in an established uptrend, ranked by volatility-adjusted relative strength versus
> SPY, may produce positive expectancy over a fixed hold compared with random selection from the same
> universe.

**Exists to be beaten.** If H2 and H3 cannot outperform it, their complexity earns nothing — a
legitimate finding.

### Conditions
```
close > SMA(50) > SMA(200)                                    [CONVENTION: 50, 200]
SMA(200)[t] > SMA(200)[t−21]                                  # slope filter, per 04 §5.2
```

### Ranking — composite, all as rankings (no thresholds to tune)
```
RS_adj    = (ret_63d(symbol) − ret_63d(SPY)) / stdev(ret_1d, 63)     # 04 §5.1
pct_52wh  = (close − MAX(high, 252)) / MAX(high, 252)                # 04 §5.4
rvol      = volume / SMA(volume, 20)                                 # 04 §5.5
```
Baseline ranks on `RS_adj` alone; composite ranking is a development-split structural comparison.

**Structural questions (development split):** does adding `pct_52wh` improve on `RS_adj` alone? Does
`rvol`? Does an equal-weighted composite of all three beat any single one?

**Parameter surfaces (development split):** RS lookback ∈ {21, 42, 63, 126, 252}; selection cutoff ∈
{top 5%, 10%, 20%}; hold ∈ {3, 5, 10, 20} days; ATR stop multiple ∈ {1.0 … 3.0 step 0.25}.

### Entry
Next session's open.

### Exit
- Time exit at the hold horizon, market-on-open
- Stop at `entry − k × ATR(14)`, `k` selected from the surface

### Failure modes
Short-horizon momentum is much weaker than 12-month momentum. Momentum crashes at regime turns. The top
decile skews high-beta, so apparent outperformance may be beta — **which is what the random benchmark
detects.** Fixed time exit ignores whether the move is still working.

---

## H2 — Daily-Bar Fair Value Gap Continuation

> Liquid US equities in an uptrend that form a bullish Fair Value Gap, then retrace into it and hold,
> may produce positive expectancy compared with H1 and with random selection.

### Core geometry — the only fixed element *(operator-confirmed)*
```
high[t−2] < low[t]
gap_bottom = high[t−2]
gap_top    = low[t]
gap_size   = gap_top − gap_bottom
```

**This is the hypothesis.** Everything else below is a filter or parameter under test.

### Displacement — a SEPARABLE FILTER, not a precondition *(operator amendment)*

Rev. 1 required displacement to define the setup. It is now a filter tested **on and off**, so its
contribution to expectancy is measurable rather than assumed.

**Answering the range-vs-body question.** Three candidate measures, tested as structural alternatives:

| Measure | Definition | Argument |
| --- | --- | --- |
| **Body** | `\|close[t−1] − open[t−1]\| / ATR(14)` | **Most faithful to the concept.** Displacement means aggressive *directional* commitment. A doji with long wicks has large range and zero displacement — it is indecision, the opposite of what the term denotes. |
| **Range** | `(high[t−1] − low[t−1]) / ATR(14)` | Captures total bar volatility. Simpler, but conflates directional force with two-sided rejection. |
| **Gap size** | `gap_size / ATR(14)` | **Note the likely redundancy:** the gap can only exist if the move was directionally forceful, so gap size is *already* a displacement measure. This may make a separate displacement filter partly duplicative. |

**Recommendation: body**, on conceptual grounds. **But it is tested, not assumed**, and the §0.7
redundancy check between gap size and body will reveal whether a separate filter adds anything at all.

**Parameter surface:** threshold ∈ {off, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5} × ATR, for each measure.
Note `off` is included — the null that displacement contributes nothing is a live hypothesis.

### Trend filter — also separable
```
close[t] > SMA(50)  AND  SMA(50) > SMA(200)  AND  SMA(200) rising     [tested on/off]
```

### Gap quality filter — separable
`gap_size ≥ q × ATR(14)`, surface over q ∈ {0, 0.1, 0.25, 0.5, 1.0}. `q = 0` is the no-filter null.

### Entry trigger
Within `W` trading days of formation:
```
low[k] ≤ gap_top   AND   close[k] > gap_bottom
```
Entry next open. Gap **invalidated** if any close < `gap_bottom` first.

**Parameter surface:** W ∈ {3, 5, 10, 15, 20}.

### Stop
`gap_bottom − b × ATR(14)`, surface over b ∈ {0, 0.1, 0.25, 0.5}. `b = 0` means exactly at the gap edge.

### Exit
- Target `entry + R × (entry − stop)`, surface over R ∈ {1.0, 1.5, 2.0, 2.5, 3.0}
- Time limit `L` days, surface over L ∈ {5, 10, 15, 20}
- **Note:** the operator's journal specifies TP1 at 1R and TP2 at 2R. Those are tested as points on the
  surface, **not adopted as given** — the journal's source for them is unattributed (profile §1.3).

### Failure modes
- **Daily FVGs are common.** With displacement now optional, raw frequency may be enormous. *The
  signal-frequency diagnostic runs first, before any P&L.*
- FVG may proxy for simple gap-fill or pullback-in-uptrend, adding nothing over H1.
- The concept originates in intraday futures; daily equity bars contain overnight earnings and news
  gaps, which are a structurally different phenomenon from intraday imbalance.
- Displacement and gap size may be measuring the same thing (above).

---

## H3 — Liquidity Sweep Reversal

> Liquid US equities in an uptrend that sweep a **liquidity reference** and reclaim it may produce
> positive expectancy compared with H1 and with random selection.

### The liquidity reference is THE VARIABLE UNDER TEST *(operator amendment)*

Rev. 1 hard-coded a 10-day low. **That was an assumption with no evidential basis.** The reference type
is now the primary structural question, with four candidates — three from the operator's own journal
(§2.4: "session high/low, previous day high/low, Asian range, equal highs/equal lows"), filtered to
those that survive translation to daily equity bars:

| # | Reference | Definition | Notes |
| --- | --- | --- | --- |
| **A** | Prior-day low | `low[t−1]` | Highest frequency; likely least selective |
| **B** | Prior-week low | `MIN(low)` over the prior calendar week | Journal's session-extreme concept, translated |
| **C** | N-bar swing low | `MIN(low[t−N : t−1])`, **N tunable** | Surface over N ∈ {3, 5, 10, 15, 20, 30, 60} |
| **D** | Equal lows | ≥ 2 swing lows within `ε%` of each other | Journal's "equal lows." Surface over ε ∈ {0.25%, 0.5%, 1.0%} |

Journal references that do **not** survive: intraday session highs/lows and the Asian range — both
require intraday data (profile §5).

**Each reference type is a separate structural test** with its own frequency diagnostic, expectancy, and
benchmark comparison. They are **not** combined into a composite in Round 1; combining them before
knowing which carries signal is exactly the confluence-stacking that inflated the journal's win-rate
table (profile §1.3).

### Sweep + reclaim conditions
```
close[t] > SMA(200)  AND  SMA(200) rising          # trend filter, tested on/off
low[t]   < reference                                # the sweep
close[t] > reference                                # the reclaim, same session
```

**Separable filters, each tested on/off:**
- Close in upper half of bar range: `close[t] > (high[t] + low[t]) / 2`
- Volume confirmation: `volume[t] > v × SMA(volume, 20)`, surface over v ∈ {off, 1.0, 1.3, 1.5, 2.0}

### Entry
Next session's open.

### Stop
`low[t] − b × ATR(14)`, surface over b ∈ {0, 0.1, 0.25, 0.5}.

### Exit
Identical structure and surfaces to H2, deliberately — so H2 and H3 differ **only** in entry logic and
any performance difference is attributable to selection rather than exit management.

### Internal control
A **plain pullback** variant runs alongside: same trend filter, entry on any close above the prior day's
high after a 3-day decline, no sweep required. **If the sweep-and-reclaim structure cannot beat plain
pullback, the ICT framing is decorative** — an important and entirely publishable finding.

### Failure modes
- This is "buy the dip in an uptrend" with extra steps; may add nothing over the plain-pullback control.
- Well-known pattern; any edge may be arbitraged away.
- Fails precisely when the dip does not recover — the 2022 bucket is the real test.
- Same-session reclaim may be too strict, yielding small samples for references B and D.

**On profile §7 compatibility:** this resembles mean reversion, which profile §7 disfavours. The
distinction holds: entry requires a *completed* reclaim (confirmation, not a falling knife) and the stop
sits immediately below the sweep. A weak position is stopped within days or it works. No prolonged
holding of losers.

---

## 4. Execution order

| # | Task | Split | Cost |
| --- | --- | --- | --- |
| 1 | **Indicator redundancy matrix** (04 §7) — drop anything > 0.85 correlated | Dev | Minutes |
| 2 | **Signal frequency diagnostic** — counts only, no P&L, every structural variant | Dev | Minutes |
| 3 | H1 baseline + structural comparisons | Dev | Low |
| 4 | Random-selection null, 1,000 iterations | Dev | Medium |
| 5 | H2 / H3 structural comparisons — displacement on/off, all four references | Dev | Medium |
| 6 | Parameter surfaces for surviving structures | Dev | Medium |
| 7 | Plateau selection → 3 configurations per hypothesis | Dev | — |
| 8 | **Validation run** | Val | Low |
| 9 | Regime breakdown | Dev + Val | Low |
| 10 | **Stage E: test split. One configuration each. Once.** | Test | Low |

Steps 1–2 run first because they are nearly free and can invalidate a specification before any
expensive work. H2 with displacement off may fire so often it has no selectivity — better to learn that
in minutes than after a full backtest.

## 5. Known limitations — stated before results exist

1. **Survivorship bias.** Alpaca's free tier has limited delisted coverage. The $20M ADV filter reduces
   but does not remove it. Every report states this. Mitigation: Polygon (~$29/mo) carries delisted
   tickers.
2. **Non-point-in-time sector data.** Current GICS applied historically; affects the sector-concentration
   rule, not entry signals.
3. **Assumed stop fills.** Gap-downs through a stop will be worse than modelled. Gap risk reported
   separately.
4. **Long only.**
5. **No earnings filter in Round 1.** Real variance source at 2–10 day holds; an exclusion variant is a
   Round 2 question.
6. **Test split is regime-loaded** (crash + bear + bull). Chronologically unavoidable; disclosed in §0.4.

## 6. Explicitly not tested

Order flow, footprint, delta, DOM, heat maps, volume profile, TPO, ICT kill zones — all require tick or
Level 2 data (profile §5). Range compression and SMT divergence are Round 2 (04 §5.6–5.7).

---

## 7. Status

All three hypotheses: **Stage B.** Nothing tested. No results exist.

Next action on approval: Phase 1 code, then execution steps 1–2, which are cheap and may send us
straight back here to revise. That outcome is expected and desirable.
