# Pre-Test Diagnostic Results — Round 1

**Date:** 2026-08-20
**Data:** 51 liquid US symbols, 2010-01-04 → 2026-08-20, 200,063 raw bars from Tiingo,
verified against Yahoo (ADR 0002)
**Status:** Measured. Decisions below follow rules fixed *before* these numbers existed.

No P&L has been computed. Nothing here says any hypothesis makes money.

---

## 1. Indicator redundancy

Spearman correlation across the universe. Pre-registered rule
([`04-INDICATOR-EVALUATION.md`](04-INDICATOR-EVALUATION.md) §7): **anything correlating
≥ 0.85 with a higher-priority indicator is dropped**, regardless of how appealing it seems.

| Pair | r | Outcome |
| --- | --- | --- |
| `atr_pct_14` ↔ `realized_vol_63` | **+0.88** | **`realized_vol_63` dropped** |
| `rs_adj_63` ↔ `ret_63` | +0.80 | Kept — below threshold, but only just |
| `pct_from_252d_high` ↔ `ret_63` | +0.64 | Kept |
| `pct_from_252d_high` ↔ `atr_pct_14` | −0.55 | Kept |
| `rvol_20` ↔ everything | −0.08 … +0.13 | Kept — genuinely independent |
| `clv` ↔ everything | −0.04 … +0.15 | Kept — genuinely independent |

### Decision: drop `realized_vol_63` as a ranking input

Two measures of volatility, one of them redundant. It stays computed in `metrics_daily`
(computation is free; it is *thresholding* that costs) and remains available inside
`rs_adj_63`, where it is a denominator rather than an input.

### The two that earned their place

`rvol_20` and `clv` correlate with **nothing** in the set. Both were argued for on
theoretical grounds in `04` §5.5 and `05` §2.2.2 — as the closest available proxies for
participation and for who finished the session in control. The measurement supports the
argument: they are not restatements of price momentum.

### The one worth watching

`rs_adj_63` ↔ `ret_63` at **+0.80** sits just under the line. The volatility adjustment
(`04` §5.1) was adopted to stop the momentum ranking from becoming a volatility ranking.
It survives the rule, but 0.80 means it is mostly reproducing raw 63-day return. Whether
the adjustment earns its keep is now an empirical question for the development split, not
a settled one.

---

## 2. Signal frequency

Displacement filter **off** (the null that displacement contributes nothing —
`03-HYPOTHESES.md` §H2). Sweep lookback 10 bars.

| Setup | Signals | % of bars | Per symbol-year | Verdict |
| --- | --- | --- | --- | --- |
| H2 — bullish FVG | 10,032 | 4.72% | 11.9 | Usable |
| H3 — sweep + reclaim | 3,159 | 1.49% | 3.7 | Usable |
| H4 — inverse FVG | 3,093 | 1.45% | 3.7 | Usable |

All three clear both failure modes this diagnostic exists to catch: nothing fires so often
that it merely describes the market, and nothing is so rare that no conclusion could be
reached within a human research lifetime.

`03` §H2 flagged a specific risk — *"with displacement now optional, raw frequency may be
enormous."* At 4.72% of bars it is not enormous. **The displacement filter is therefore a
genuine test of whether displacement adds information, not a necessity for keeping the
sample manageable.** That distinction was not available before measurement.

Note that portfolio limits will reject most H2 signals: at five concurrent positions,
11.9 signals per symbol-year across 51 symbols vastly exceeds available slots. Ranking
quality will matter more than signal count.

---

## 3. Signal overlap — the pre-registered question

[`05-IFVG-AND-ORDER-FLOW.md`](05-IFVG-AND-ORDER-FLOW.md) §1.3 predicted that H3 and H4
might be one hypothesis under two names, both being "reclaimed level" strategies, and
committed in advance: **overlap > 60% of the rarer setup ⇒ H4 folds into H3 as liquidity
reference E.**

| Pair | Shared entry bars | Jaccard | % of rarer setup | Outcome |
| --- | --- | --- | --- | --- |
| H2 ↔ H3 | 115 | 0.9% | 3.6% | Distinct |
| **H2 ↔ H4** | **894** | **8.0%** | **30.7%** | Substantial — report jointly |
| **H3 ↔ H4** | **35** | **0.6%** | **1.2%** | **Distinct** |

### Decision: H4 is admitted as a standalone hypothesis

**The prediction in `05` §1.3 was wrong, and the measurement says so clearly.** H3 and H4
share 1.2% of the rarer setup's entry bars — they are as close to independent as two
long-only setups on the same universe are likely to get. The structural argument that both
are "level violated, then reclaimed" was sound as far as it went, but *which* level turns
out to matter enormously: a swing low and an inverted bearish gap almost never coincide.

Recording this explicitly, because a prediction that was going to be believed if confirmed
must also be reported when refuted.

### The overlap that does exist is elsewhere

H2 and H4 share **30.7% of H4's signals** — which in hindsight is the structurally obvious
pair, since both are built on fair value gaps. That sits below the 60% fold threshold, so
H4 stands, but the two are not independent evidence:

- Their results are **reported jointly**, never as two separate confirmations.
- If both clear the success criteria, that is **one finding about gap geometry**, not two.
- The ~31% shared subset is worth isolating later: do the shared bars carry the
  performance, or the disjoint ones?

---

## 4. What changes in the specification

| Change | Source | Type |
| --- | --- | --- |
| `realized_vol_63` dropped as a ranking input | §1, rule from `04` §7 | Automatic — rule-driven |
| H4 remains a standalone hypothesis | §3, rule from `05` §1.3 | Automatic — rule-driven |
| H2 and H4 results reported jointly | §3 | Judgement, recorded now rather than later |
| Displacement filter is a genuine test, not a sample-size necessity | §2 | Reframing |
| `rs_adj_63` vs `ret_63` at 0.80 flagged for the development split | §1 | Open question |

Nothing else moves. The hypothesis count stays at four (H1 control, H2, H3, H4), the split
budgets are untouched, and the success criteria in `03` §0.6 are unchanged.

---

## 5. Caveat that rides along with every result from this dataset

The 51 symbols are **today's** large caps, selected in 2026 with full knowledge of which
companies grew. No delisted company is present. The universe machinery resolves
point-in-time *liquidity* correctly — a stock that failed the ADV filter in 2013 is
excluded from 2013 — but it cannot resurrect companies absent from the database entirely.

**Every backtest on this universe overstates results by an unknown amount.** Whether
Tiingo's free tier carries delisted tickers is unverified (ADR 0002). Until it is measured,
this caveat appears on every reported result.
