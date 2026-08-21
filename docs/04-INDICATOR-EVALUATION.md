# Indicator Evaluation — Pre-Test Screening

**Date:** 2026-08-16
**Status:** APPROVED 2026-08-16. Amendments folded into [`03-HYPOTHESES.md`](03-HYPOTHESES.md) rev. 2. Variant budget in §6 superseded.
**Question:** Are there indicators that improve the hypotheses **without adding complexity**?

---

## 1. The methodological trap, and how we avoid it

There is a wrong way to answer this question, and it is the default way:

> Pick indicators that seem good → add them → test → keep whatever improved results.

That procedure **manufactures edges that do not exist.** Test twenty variants at a 5% significance
level and one will look significant by chance alone. Keep that one, discard the other nineteen, and you
have a beautiful backtest of pure noise. This is the single most common way retail quantitative research
fails, and it is indistinguishable from success until real money is deployed.

The correct procedure:

1. **Screen candidates on criteria assessable *before* testing** — redundancy, definability, parameter
   cost, published evidence, operator comprehension.
2. **Commit to the indicator set before any backtest runs.**
3. **Declare a variant budget in advance** and count every variant tested against it (§6).
4. **Prefer substitution over addition.** Swapping an indicator for a better one is free; adding one is
   not.

Nothing below is a claim that any indicator *works*. These are priors about which candidates are worth
spending test budget on.

## 2. Two kinds of complexity, and only one of them is expensive

| Type | Cost | Example |
| --- | --- | --- |
| **Computational** | Cheap | Another column in `metrics_daily`. Effectively free once ingestion exists. |
| **Parametric** | **Expensive** | Every tunable threshold is a degree of freedom, and every degree of freedom is a chance to overfit. |

**This distinction drives every recommendation below.** Computing ten indicators costs nothing.
*Thresholding* on ten indicators is how you overfit.

**A corollary worth internalizing: using an indicator for *ranking* is far cheaper than using it as a
*filter*.** A filter needs a cutoff — a number to tune, therefore a number to overfit. A ranking needs
only an ordering. Where a candidate below is recommended, it is recommended as a ranking input wherever
possible.

## 3. Current indicator load

The hypotheses are already lean, which is worth seeing plainly before adding anything:

| Indicator | Used in | Parameters |
| --- | --- | --- |
| SMA(50), SMA(200) | H1, H2, H3 | 2 (both conventional, not tuned) |
| ATR(14) | All — stops and sizing | 1 (conventional) |
| 63-day return vs SPY | H1 | 1 |
| Price geometry (FVG, swing low) | H2, H3 | Per-hypothesis |
| Volume SMA(20) | H3 (optional) | 1 |

**Total: roughly five indicators, nearly all at conventional settings.** There is genuine room to improve
*quality* here without increasing count.

## 4. Evaluation criteria

Each candidate is scored on what we can assess without testing:

| Criterion | Question |
| --- | --- |
| **Additive information** | Does it capture something the existing set does not? A candidate correlating ~0.9 with an existing indicator adds a parameter and no information. |
| **Objective definition** | Computable from OHLCV with no discretionary judgment? |
| **Parameter cost** | How many new tunable numbers? |
| **Published evidence** | Independent support, or trading-education folklore? |
| **Operator comprehension** | Will the operator understand and trust it? An indicator he doesn't believe gets overridden at the worst moment — profile §1.2. |

---

## 5. Candidates assessed

### Tier 1 — Substitutions. Net zero added complexity. **Recommended.**

#### 5.1 Raw momentum → volatility-adjusted momentum *(H1)*

```
current:  RS_3m = return_63d(symbol) − return_63d(SPY)
proposed: RS_adj = (return_63d(symbol) − return_63d(SPY)) / stdev(daily_returns, 63)
```

**Same inputs, one division. Zero new parameters, zero new data.**

Raw momentum ranking systematically favours high-volatility names — they simply move more in both
directions. That means H1's top decile is partly a *volatility* portfolio, not a *strength* portfolio,
which is precisely the confound the random-selection benchmark exists to catch. Dividing by realized
volatility ranks on strength *per unit of risk*, which is closer to what "relative strength" is meant to
capture. Risk-adjusted momentum variants are well documented in the factor literature.

**Verdict: adopt.** Strictly better information at identical cost.

#### 5.2 Add slope condition to the trend filter *(H1, H2, H3)*

```
current:  close > SMA(50) > SMA(200)
proposed: close > SMA(50) > SMA(200)  AND  SMA(200)[t] > SMA(200)[t-21]
```

Reuses an existing indicator. Excludes the case where price sits above a *declining* 200-day average —
common in bear-market rallies, which is exactly where a long-only trend strategy gets hurt.

**Parameter cost: one lookback (21 days ≈ one month), and it is not a threshold to tune.**

**Verdict: adopt.** Should improve the bear-regime bucket specifically.

#### 5.3 Report ATR as ATR% *(all)*

`ATR% = ATR(14) / close`. Same indicator, expressed comparably across price levels. Stops still use
dollar ATR; ATR% is for cross-sectional filtering and reporting.

**Verdict: adopt.** Presentational, free.

---

### Tier 2 — Additions with real informational value. **Recommended, as ranking inputs.**

#### 5.4 Distance from 52-week high

```
pct_from_52w_high = (close − MAX(high, 252)) / MAX(high, 252)
```

**Why it earns its place:** proximity to the 52-week high has independent published support as a
momentum signal (George & Hwang, *Journal of Finance*, 2004 — the "52-week high effect"), and it is
**not** redundant with 63-day relative strength. A stock can be up 30% in three months while still 40%
below its high (a bounce in a downtrend) or up 5% while sitting at a new high (a controlled advance).
Those are different situations, and the existing indicator set cannot distinguish them.

It is also conceptually native to how the operator already thinks about strength, which matters for
whether he'll trust the output.

**Parameter cost: one window (252 days), conventional and not tuned.** Used as a ranking input, not a
filter — so no threshold to overfit.

**Verdict: adopt as a ranking input for H1.**

#### 5.5 Relative volume (RVOL)

```
RVOL = volume / SMA(volume, 20)
```

**This is the most important candidate on the list, for a reason specific to this operator.** Profile §5
established that footprint, delta, DOM, and heat maps are unavailable in an EOD system — that is the
half of his expertise that does not transfer. **RVOL is the closest EOD proxy for participation and
conviction that exists.** It is a crude substitute for order flow, and it should be presented as crude.
But it is *directionally* the same question: is unusual activity confirming this move?

He already specified volume in H3, and his journal's most self-critical entry names the failure directly:
*"What I missed is that volume was dead and buyers and sellers were exhausted."* This indicator addresses
a mistake he has already diagnosed in himself.

**Parameter cost: one lookback (20 days), conventional.**

**Verdict: adopt.** Ranking input for H1 and H2; already present in H3, promoted from optional to a
tested variant.

---

### Tier 3 — Deferred to Round 2. Genuinely promising, but these are new *hypotheses*, not indicator tweaks.

#### 5.6 Range compression / volatility squeeze

```
compression = ATR(14) / ATR(50)        # or N-day range percentile
```

**The strongest conceptual bridge to the operator's existing framework.** Auction Market Theory's
balance → imbalance transition *is* compression → expansion. The journal already frames markets this way
("Balance: fair value found / Imbalance: price discovery"). A daily-bar squeeze is the EOD expression of
the same idea, and unlike volume profile or TPO it requires no intraday data.

**Why not now:** this is not an indicator added to an existing hypothesis — it is a different setup with
a different entry logic, i.e. an H4. Adding it to Round 1 would breach the three-hypothesis limit and
the variant budget. **Recorded as the leading Round 2 candidate.**

#### 5.7 SMT divergence

Testable on daily bars, and natively an index-pair construct — closer to its original form on QQQ/SPY
than on single stocks. The required sector-ETF mapping table is needed anyway for sector relative
strength, so it is cheaper than first estimated.

**Why not now:** requires the pair mapping plus a divergence-window parameter. Round 2, alongside 5.6.

---

### Tier 4 — Rejected. Reasons stated so these are not relitigated.

| Indicator | Why rejected |
| --- | --- |
| **RSI** | Highly redundant with short-horizon return, which we already have. Adds a lookback *and* two thresholds. Weak standalone evidence. |
| **MACD** | Three parameters. It is a transformation of two EMAs — nearly all its information is already in the MA alignment. |
| **Stochastics** | Same objection as RSI, with more parameters. |
| **Bollinger %B** | Redundant with ATR-based volatility measures already present. Band width is interesting, but that is 5.6, expressed better. |
| **Ichimoku** | Five parameters. Unjustifiable parameter cost. |
| **Fibonacci retracements** | **Not objectively definable** — requires discretionary swing-point selection. Fails the mechanization criterion outright. |
| **Multi-timeframe (weekly + daily)** | Doubles the data surface and roughly doubles the variant space, for information largely captured by the 200-day SMA. |
| **OBV / accumulation-distribution** | Cumulative indicators are path-dependent and start-date sensitive, which makes cross-sectional comparison unsound. RVOL answers the same question more cleanly. |

**Note on the rejections:** none of these are claims that the indicator "doesn't work." Each is a claim
that its *parameter cost exceeds its expected informational contribution* given what we already compute.
That is the only question that matters when the budget is finite.

---

## 6. Variant budget — SUPERSEDED by hypotheses rev. 2

The flat twelve-variant cap originally specified here was replaced during operator review. It solved
the multiple-comparisons problem by forbidding exploration — which also forbade testing the assumptions
embedded in the specification, and those assumptions were themselves unexamined.

The replacement is a **per-split budget** ([`03-HYPOTHESES.md`](03-HYPOTHESES.md) §0.4, §0.8):

| Split | Budget |
| --- | --- |
| Development (2010–2015) | Unlimited — carries no evidential weight |
| Validation (2016–2019) | 3 configurations per hypothesis |
| Test (2020–2026) | 1 configuration per hypothesis, once |

This permits exhaustive exploration where results prove nothing and enforces strict discipline where
they do — resolving the conflict between "test every assumption" and "don't data-mine" rather than
trading one failure for the other.

Parameter selection now follows the **stability-surface** method in `03-HYPOTHESES.md` §0.7: choose the
centre of a plateau, never the peak, and treat the absence of a plateau as evidence against the
hypothesis.

## 7. Empirical redundancy check — cheap, and runs before any backtest

Once Phase 1 ingestion exists, compute the **cross-sectional correlation matrix** of all candidate
indicators across the universe. Cost: minutes of compute, zero AI tokens.

**Decision rule declared in advance:** any candidate correlating **> 0.85** with an already-included
indicator is dropped, regardless of how appealing it seems. It is contributing a parameter and no
information.

This runs *before* the signal-frequency diagnostic and could remove candidates from §5 on evidence
rather than on my judgement — which is strictly better.

> **MEASURED 2026-08-20.** `realized_vol_63` correlates **+0.88** with `atr_pct_14` and is dropped as
> a ranking input, on evidence rather than judgement. `rvol_20` and `clv` correlate with nothing in
> the set, supporting the arguments in §5.5 and `05` §2.2.2. `rs_adj_63` ↔ `ret_63` at **+0.80** sits
> just under the threshold — the volatility adjustment survives, but whether it earns its keep is now
> an open empirical question. See [`06-DIAGNOSTIC-RESULTS.md`](06-DIAGNOSTIC-RESULTS.md) §1.

## 8. Summary of proposed amendments to `03-HYPOTHESES.md`

| # | Change | Type | Net parameter cost |
| --- | --- | --- | --- |
| 5.1 | H1 momentum → volatility-adjusted | Substitution | **0** |
| 5.2 | Add SMA(200) slope > 0 to trend filter | Substitution | +1 (untuned lookback) |
| 5.3 | ATR reported as ATR% | Presentational | **0** |
| 5.4 | 52-week-high distance as ranking input | Addition | +1 (conventional window) |
| 5.5 | RVOL as ranking input (H1, H2); tested variant (H3) | Addition | +1 (conventional lookback) |

**Net: three new parameters, all conventional, none a tunable threshold.** Two of the five changes cost
nothing at all. The hypothesis count stays at three, and the variant budget is capped at twelve.

Deferred to Round 2: range compression (5.6), SMT divergence (5.7).

---

## 9. Approval

These are proposed amendments. On approval they are folded into `03-HYPOTHESES.md` and the specification
is frozen for Round 1 — after which changes cost out-of-sample credibility, not just time.
