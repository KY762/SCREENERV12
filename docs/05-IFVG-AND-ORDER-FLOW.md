# Inverse FVG & Order-Flow Concepts at End-of-Day

**Date:** 2026-08-17
**Status:** Approved. §1.3's overlap prediction was MEASURED on 2026-08-20 and **refuted** —
H3 and H4 share 1.2% of the rarer setup's entry bars, not the >60% that would have folded
them together. H4 is admitted standalone. See [`06-DIAGNOSTIC-RESULTS.md`](06-DIAGNOSTIC-RESULTS.md) §3.
**Prompted by:** operator question — has IFVG been explored, and what about other order-flow concepts?

**Correction first:** profile §5 listed Inverse FVG as transferable to daily bars, and then no hypothesis
specified it. That was an oversight, not a judgement. This document fixes it.

---

# PART 1 — Inverse Fair Value Gap

## 1.1 What an IFVG is

A Fair Value Gap that **fails**, and then acts in the opposite direction. The ICT claim is that a level
which was violated carries more information than one that was merely respected — a failed move implies
the opposing side was overwhelmed.

For a **long-only** system, the relevant construct is the **bullish IFVG**, which begins as a *bearish*
gap:

```
1. A bearish FVG forms at bar t:        low[t−2] > high[t]
                                        zone = [ high[t] , low[t−2] ]

2. Price later closes above the zone:   close[j] > low[t−2]     for some j > t
   → the bearish gap has INVERTED. Former resistance is now claimed as support.

3. Price retraces back into the zone
   and holds it:                        low[k] ≤ low[t−2]  AND  close[k] > high[t]
   → entry trigger
```

Fully objective, computable from daily OHLCV, no discretionary judgement. It passes the mechanization
test that Fibonacci retracements fail.

Note the operator's journal treats IFVG as **"confirmation only"** — one of four required confluences,
never a standalone trigger. That framing is testable too, and §1.4 explains why it should be tested
*separately* rather than adopted.

## 1.2 Why it might work

The mechanism story: a bearish FVG represents an imbalance where sellers moved price down so forcefully
they left an untraded zone. If buyers subsequently absorb that entire zone and close above it, the
sellers who created the imbalance are underwater. On a retest, that zone plausibly attracts demand —
both from buyers who missed the initial move and from trapped sellers covering.

**That is a plausible story. Plausible stories are not evidence** — the same reasoning shape supports
dozens of patterns that don't survive testing. It is a reason to test, not a reason to believe.

## 1.3 Structural relationship to H3 — the important observation

**Bullish IFVG and H3's sweep-reclaim may be measuring nearly the same thing.**

| | H3 sweep-reclaim | Bullish IFVG |
| --- | --- | --- |
| Structure | Level violated, then reclaimed | Level violated, then reclaimed |
| Level type | Prior low / swing low / equal lows | Bearish FVG zone |
| Confirmation | Close back above the level | Close back above the zone |
| Entry | Next open | On retest of the zone |

The difference is **which level** and **when you enter** — not the underlying idea. Both are
"reclaimed-level" strategies.

This matters concretely: if IFVG and H3 signals overlap on 70% of the same bars, they are one hypothesis
with two names, and testing both as independent findings would double-count the same evidence. **A
signal-overlap matrix is therefore mandatory before either is credited** — cheap to compute, and it
belongs alongside the redundancy check in `04` §7.

> **MEASURED 2026-08-20 — this prediction was wrong.** H3 and H4 share **1.2%** of the rarer setup's
> entry bars (35 of 3,093). The structural argument above was sound as far as it went, but *which*
> level is reclaimed turns out to dominate: a swing low and an inverted bearish gap almost never
> coincide. The real overlap is **H2 ↔ H4 at 30.7%** — both are built on fair value gaps — which is
> below the fold threshold but means their results are reported jointly, never as two independent
> confirmations. Full numbers in [`06-DIAGNOSTIC-RESULTS.md`](06-DIAGNOSTIC-RESULTS.md) §3.

## 1.4 Red Team — the conditional-sample problem

IFVG is a **conditional construct**: it requires a bearish FVG to form, *and* be inverted, *and* be
retested. Each condition shrinks the sample multiplicatively.

This is the confluence-stacking mechanism identified in profile §1.3, and the operator's journal shows
it directly:

| Confluences required | Claimed win rate |
| --- | --- |
| FVG alone | 52–56% |
| + Sweep | 60–65% |
| + SMT | 67–74% |
| + IFVG (all four) | 70–82% |

**Win rate rising monotonically as sample size falls is what selection bias looks like.** It is not
evidence of a better setup; it is the expected signature of slicing a dataset thinner. The journal's
own four-confluence model may fire only a handful of times a year on any single instrument — at which
point no statistically meaningful conclusion is reachable within a human research lifetime.

**Design consequence:** IFVG is tested **standalone first**. Only if it carries signal on its own does
stacking it with other conditions become a question worth spending sample on. Testing the four-confluence
model directly would produce an impressive, uninterpretable number.

## 1.5 Proposed specification — H4 (candidate)

> Liquid US equities in an uptrend that form a bearish FVG, subsequently close above it, and then retest
> and hold the inverted zone may produce positive expectancy compared with H1, with H3, and with random
> selection.

| Element | Specification |
| --- | --- |
| Bearish FVG | `low[t−2] > high[t]`; zone `[high[t], low[t−2]]` |
| Zone quality | `zone_size ≥ q × ATR(14)`, surface over q ∈ {0, 0.1, 0.25, 0.5} |
| Inversion | `close[j] > low[t−2]`, within `V` bars; surface over V ∈ {3, 5, 10, 20} |
| Trend filter | `close > SMA(200)`, SMA(200) rising — **tested on/off** |
| Entry trigger | `low[k] ≤ low[t−2]` and `close[k] > high[t]`, within `W` bars of inversion; W ∈ {3, 5, 10, 20} |
| Stop | `high[t] − b × ATR(14)`; b ∈ {0, 0.1, 0.25, 0.5} |
| Exit | Same surfaces as H2/H3 — R ∈ {1.0, 1.5, 2.0, 2.5, 3.0}, time limit L ∈ {5, 10, 15, 20} |
| Mandatory pre-test | Signal frequency; **signal-overlap matrix vs H3** |

**Recommendation: admit H4 to Round 1, conditional on the overlap matrix.** If it overlaps H3 by more
than ~60%, it is folded into H3 as a fourth liquidity-reference type (reference **E**) rather than
standing as a separate hypothesis. That keeps the hypothesis count honest.

---

# PART 2 — Order-flow concepts at end-of-day

## 2.1 The finding that matters most: horizon mismatch

Profile §5 excluded footprint, DOM, and heat maps on **data availability** grounds — tick and Level 2
data are intraday-only and expensive. That reasoning was correct but incomplete, and the missing half is
more important:

**The documented predictive horizon of order-flow imbalance is far shorter than a 2–5 day hold.**

The microstructure literature is consistent on this. Order-flow imbalance shows a near-linear
relationship with price changes **within tens of seconds**; impulse-response estimates find shocks
dissipate almost entirely **within one second**; cross-impact terms carry forecasting information over
**up to several minutes**, decaying quickly; and predictive effects **decay rapidly beyond a one-day
horizon**.

Sources: [Returns and Order Flow Imbalances: Intraday Dynamics](https://arxiv.org/abs/2508.06788) ·
[Cross-impact of order flow imbalance in equity markets](https://www.tandfonline.com/doi/full/10.1080/14697688.2023.2236159) ·
[Optimal Signal Extraction from Order Flow](https://arxiv.org/pdf/2512.18648)

**The implication is significant and worth stating plainly:** even with a Bookmap subscription, an
institutional data feed, and unlimited budget, order-flow signals would have largely decayed **before a
2–5 day holding period even begins**. The constraint is not primarily cost or data access — it is that
the effect operates on a timescale mismatched to the strategy.

This reframes the exclusion constructively. It is not a limitation being worked around; it is a reason
the operator's swing-trading track and his order-flow knowledge are **structurally separate disciplines**.
Order flow is genuinely powerful — for execution timing and intraday trading. It is not the missing
ingredient in a multi-day swing strategy.

**This also means the journal's footprint win-rate table** (Absorption Fade ~72%, Delta Divergence ~68%,
POC Rejection ~70%) **is not merely unsourced — it is measuring a different timeframe than the one being
traded here.** Even if those numbers were rigorously derived, they would not transfer.

## 2.2 What IS available at EOD — ranked by value

Order flow asks: *who is in control, and with what conviction?* Several OHLCV-derived measures address
that question imperfectly but genuinely.

### Tier 1 — Recommended

#### 2.2.1 Market breadth as aggregate order flow ⭐ *the best available substitute*

You cannot see the order book for AAPL. You **can** measure what fraction of the entire market
participated in today's move:

```
pct_above_20/50/200_SMA         across the universe
advance_decline_ratio           advancers / decliners
up_volume_ratio                 volume in advancing names / total volume
new_highs_minus_new_lows        52-week
```

**This is order flow measured across the universe rather than within one instrument** — and for
*positioning* decisions on a multi-day horizon it is arguably more useful than single-instrument
microstructure, because it operates on a matching timescale.

A rally where 70% of stocks participate is structurally different from one where 15% do. That
distinction is invisible in any single name's chart and is exactly the "is this move real?" question the
operator's journal keeps circling. Already planned as the Phase 4 breadth engine — **this document
promotes it from infrastructure to a research input.**

#### 2.2.2 Close Location Value (CLV) — cleanest single-bar proxy

```
CLV = ((close − low) − (high − close)) / (high − low)        # range −1 to +1
```

Zero parameters. Answers, for one session: *did buyers or sellers finish in control?* +1 means the close
was at the high, −1 at the low. It is the numerator of Accumulation/Distribution, but used per-bar it
avoids the path-dependence that got cumulative OBV rejected in `04` §Tier 4.

Already implicitly present — H3's "close in upper half of range" filter *is* a CLV threshold. This makes
it explicit and continuous rather than binary. **Recommended as a ranking input.**

#### 2.2.3 Effort vs. Result — the Wyckoff / AMT bridge ⭐

```
effort_result = (range / ATR(14)) / (volume / SMA(volume, 20))
```

Directly expresses a concept the operator already works in:

| Reading | Interpretation |
| --- | --- |
| **Low** — heavy volume, narrow range | **Absorption.** Someone is filling size against the move. |
| **High** — light volume, wide range | **Thin market.** Little opposition; the move may lack conviction or may be genuine lack of supply. |

This is Wyckoff's effort-versus-result, which underlies the Auction Market Theory framing in the
operator's journal. **It is the closest EOD expression of what footprint charts measure** — not
equivalent, but asking the same question with the data actually available.

It also speaks directly to the journal's sharpest self-observation: *"What I missed is that volume was
dead and seller and buyer were exhausted."* That is an effort-versus-result reading, made after the fact.
This computes it in advance.

**Recommended — but as a Round 2 hypothesis, not a Round 1 indicator.** Absorption is a *setup*, not a
filter, and deserves its own specification.

### Tier 2 — Computable, weaker, deferred

| Concept | EOD form | Assessment |
| --- | --- | --- |
| Anchored VWAP | `Σ(typical_price × volume) / Σ(volume)` from a pivot | Real and usable; daily granularity makes it coarse. Round 2. |
| Up/down volume ratio | Volume on up days ÷ down days over N | Crude delta proxy. Likely redundant with CLV and RVOL — the correlation matrix decides. |
| Gap behaviour | `open[t]` vs `close[t−1]`, and whether it fills | Genuine order-flow question answerable at EOD. Round 2. |

### Tier 3 — Not available at EOD, at any price

Footprint · Delta · DOM · Heat maps · Volume profile / POC / value area · TPO · Iceberg detection ·
Absorption at price level

All require tick or Level 2 data. **And per §2.1, all operate on horizons that decay before a 2–5 day
hold begins.** Two independent reasons, either sufficient.

## 2.3 What this changes

| Concept | Prior status | New status |
| --- | --- | --- |
| IFVG | Named, never specified | **H4 candidate**, conditional on overlap matrix |
| Market breadth | Phase 4 infrastructure | **Research input** — best available order-flow substitute |
| CLV | Implicit in an H3 filter | **Explicit ranking input** |
| Effort vs Result | Not considered | **Round 2 hypothesis** — the Wyckoff/AMT bridge |
| Anchored VWAP, gap behaviour, up/down volume | Not considered | Round 2 candidates |
| Footprint / DOM / heat map / TPO | Excluded on data grounds | Excluded on data **and horizon** grounds |

---

# PART 3 — Recommendations

## Add to Round 1
1. **H4 — Bullish IFVG**, conditional on the signal-overlap matrix vs H3 (§1.3). If overlap > 60%, fold
   into H3 as liquidity reference **E** rather than a standalone hypothesis.
2. **CLV as a ranking input** for H1 and H2. Zero parameters, subject to the >0.85 redundancy rule.

## Add to the pre-test diagnostic sequence
3. **Signal-overlap matrix** across H2 / H3 / H4 — before any P&L. Cheap, and it determines whether we
   have three hypotheses or one hypothesis wearing three names.

## Round 2 queue (unchanged in priority order, now with additions)
4. Range compression / squeeze (`04` §5.6)
5. **Effort vs Result / absorption** — new, and arguably ahead of the above given operator fit
6. SMT divergence (`04` §5.7)
7. Anchored VWAP, gap behaviour

## Explicitly closed
8. Footprint, DOM, heat maps, volume profile, TPO. **Not revisitable within this project** — not for
   budget reasons, but because §2.1 establishes the horizon mismatch. Should the operator later pursue
   intraday trading, these become relevant again in that context, as a separate discipline.

---

## Approval

Nothing here is tested. H4 is Stage A (Idea) pending the overlap matrix; everything else is a proposed
amendment to the Round 1 diagnostic sequence.
