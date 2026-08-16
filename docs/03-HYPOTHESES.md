# Research Hypotheses — Round 1

**Date:** 2026-08-16
**Status:** DRAFT — awaiting approval. **Stage B (Objective Specification)** for all three.
**Depends on:** [`02-TRADER-PROFILE.md`](02-TRADER-PROFILE.md) (approved 2026-08-16)

Three hypotheses. No more, deliberately — every additional simultaneous test multiplies the
data-mining risk described in profile §1.3. H1 exists to make H2 and H3 falsifiable.

---

## 0. Shared specification

Everything below is common to all three hypotheses. Defining it once prevents each strategy from
quietly acquiring its own favourable universe or cost model — a classic route to fake edges.

### 0.1 Universe

| Filter | Value | Reason |
| --- | --- | --- |
| Listing | US primary listings, NYSE/Nasdaq/AMEX | Data availability |
| Instrument | Common stock + ETFs | Per profile §2 |
| Price | ≥ $10.00 | Sub-$10 names have wide relative spreads and poor data quality |
| Avg dollar volume | ≥ $20M over trailing 50 days | A $2,000 position is ~0.01% of daily volume — market impact is genuinely nil |
| History | ≥ 250 trading days | Required for 200-day SMA and 52-week metrics |
| Excluded | Leveraged/inverse ETFs (2x, 3x, -1x) | Path-dependent decay makes them a different instrument with different dynamics |
| Excluded | Restricted list | Employer compliance hook (profile §12) — empty by default |

Expected universe size: **~1,200–1,800 names.** Membership is evaluated **as of each historical date**,
never as of today — a stock that fails the liquidity filter in 2019 is not tradeable in 2019.

### 0.2 Position sizing (identical across all hypotheses)

```
risk_dollars   = account_equity × risk_pct          # risk_pct = 1.0%
shares         = floor(risk_dollars / (entry - stop))
position_value = shares × entry
```

**Hard constraints, enforced by the system, no manual override:**

| Constraint | Value | Source |
| --- | --- | --- |
| Risk per trade | 1.0% of equity ($100 at $10k) | Profile §7 |
| Max position value | 25% of equity | Concentration limit at small account size |
| Max concurrent positions | 5 | Profile §6 |
| Max total open risk | 5% of equity | 5 × 1% |
| Max positions per GICS sector | 2 | Correlation control |
| Stop entry | Simultaneous with entry order | Profile §7.1 veto condition 1 |

If a computed position would exceed 25% of equity, size is reduced — **never** is the stop widened to
make the position fit. Widening a stop to accommodate a size is the mechanism behind profile §1.2.

### 0.3 Transaction cost model

| Component | Assumption | Justification |
| --- | --- | --- |
| Commission | $0.00 | Standard at Alpaca/IBKR/Schwab for equities |
| Slippage | 5 bps per side (0.10% round trip) | Deliberately conservative for $20M+ ADV names at $2k position size |
| Spread | Included in the above | |
| Borrow / shorting | N/A | All three hypotheses are long-only |

**Sensitivity requirement:** every result is reported at 5 bps *and* 15 bps per side. A strategy whose
edge disappears at 15 bps is fragile and will be reported as such.

### 0.4 Test periods — fixed now, before any code runs

| Period | Dates | Use |
| --- | --- | --- |
| **In-sample** | 2010-01-01 → 2019-12-31 | Design, parameter selection, iteration |
| **Out-of-sample** | 2020-01-01 → 2026-06-30 | **Touched exactly once, at Stage E** |

The out-of-sample window is sealed. If it is examined during design, it stops being out-of-sample and
its evidential value is gone permanently. This commitment is recorded here so it can be checked.

Regime buckets for the robustness breakdown:

| Bucket | Period | Character |
| --- | --- | --- |
| Bull | 2013–2015, 2017, 2023–2024 | Trending up |
| Correction | 2015-08, 2018-Q4, 2016-01 | Sharp drawdown, quick recovery |
| Crash | 2020-02 → 2020-04 | Volatility spike |
| Bear | 2022 | Sustained downtrend |
| Chop | 2011, 2015 | Rangebound |

### 0.5 Benchmarks — three, not one

| Benchmark | Tests for |
| --- | --- |
| **SPY buy-and-hold** | Does this beat doing nothing? |
| **Random selection** from the same universe, same trade count, same holding period, 1,000 iterations | **Does the selection rule add anything, or is the result just long exposure?** |
| **H1 (momentum control)** | Do the SMC-derived rules beat the simplest sensible alternative? |

The random-selection benchmark is the most important and the most commonly omitted. If a strategy
cannot outperform randomly chosen stocks from the same universe held for the same duration, it has no
selection edge — it has market beta.

### 0.6 Pre-registered success criteria

**Fixed before any test runs.** A hypothesis advances from Stage C to Stage D only if it meets **all**:

| Criterion | Threshold | Rationale |
| --- | --- | --- |
| Trade count (in-sample) | ≥ 200 | Below this, confidence intervals swamp the effect |
| Expectancy after costs | > 0 | Necessary condition |
| Profit factor | > 1.20 | Below this, costs and slippage variance dominate |
| vs. random benchmark | > 75th percentile of the 1,000-iteration distribution | Selection must beat chance |
| Max drawdown | < 25% | Profile §7 |
| Regime robustness | Positive expectancy in ≥ 3 of 5 buckets, and no bucket worse than −15% | Not regime-dependent |
| Parameter sensitivity | Expectancy stays > 0 across ±20% on every parameter | Not a knife-edge fit |

**Failing any criterion means the hypothesis is rejected or revised — not that the threshold moves.**
Recorded here so the thresholds cannot drift after seeing results.

---

## H1 — Relative-Strength Continuation *(CONTROL)*

> Liquid US equities in an established uptrend, ranked in the top decile of 3-month relative strength
> versus SPY, may produce positive expectancy over a fixed 5-day hold compared with random selection
> from the same universe.

**This hypothesis exists to be beaten.** It is built from the simplest, most widely documented factors
available, with the fewest parameters. If H2 or H3 cannot outperform it, their added complexity is not
earning anything — and that is a legitimate, useful research finding rather than a failure.

### Conditions
- `close > SMA(50) > SMA(200)` — established uptrend
- `RS_3m = (return_63d of symbol) − (return_63d of SPY)`, ranked cross-sectionally; take top decile
- Universe filters per §0.1

### Entry
Next session's open, following the signal date.

### Exit
- **Primary:** market-on-open exit after exactly **5 trading days**
- **Stop:** `entry − 2.0 × ATR(14)`, checked intraday, exits at stop price (slippage applied)

### Stop rationale
2×ATR is wide enough to survive normal noise, tight enough to satisfy the profile §7 constraint against
prolonged weak positions. Sensitivity-tested at 1.5× and 2.5×.

### Market regime
All regimes. Regime dependence is measured, not assumed.

### Why this might work
Cross-sectional momentum is among the most replicated anomalies in the finance literature, documented
across decades, markets, and asset classes. Short-horizon persistence is weaker than the classic 12-1
month formulation but is the honest starting point.

### Failure modes
- Short-horizon momentum is substantially weaker than 12-month momentum; 5 days may capture noise.
- Momentum crashes hard at regime turns (2009, 2020) — the regime breakdown will expose this.
- The top RS decile skews to high-beta names, so outperformance may be beta, not alpha. **This is
  exactly what the random-selection benchmark is designed to detect.**
- Fixed 5-day exit ignores whether the move is still working.

### Parameters (sensitivity-tested)
`RS lookback` (63d) · `decile cutoff` (10%) · `hold days` (5) · `ATR stop multiple` (2.0)

---

## H2 — Daily-Bar Fair Value Gap Continuation

> Liquid US equities in an uptrend that form a **bullish Fair Value Gap** on a displacement bar, then
> retrace into that gap and hold it, may produce positive expectancy over a 2R-target / 10-day-limit
> hold compared with H1 and with random selection.

This is the operator's own framework, mechanized. Profile §5 established that FVG has a crisp geometric
definition, making it genuinely testable — unusual among discretionary concepts.

### Conditions — exact definitions

**Bullish FVG** forms at bar `t` when:
```
high[t-2] < low[t]                                   # the gap: an untraded price zone
gap_bottom = high[t-2]
gap_top    = low[t]
gap_size   = gap_top − gap_bottom
```

**Displacement filter** — the middle bar must be a real impulse, not noise:
```
range[t-1] = high[t-1] − low[t-1]
range[t-1] > 1.5 × ATR(14)[t-1]
close[t-1] > open[t-1]                               # bullish displacement
```

**Trend filter:**
```
close[t] > SMA(50)[t]
SMA(50)[t] > SMA(200)[t]
```

**Gap quality filter:**
```
gap_size ≥ 0.25 × ATR(14)                            # excludes trivially small gaps
```

### Entry trigger
Within **10 trading days** of formation, price retraces into the gap and holds it:
```
low[k] ≤ gap_top          AND    close[k] > gap_bottom
```
Entry at the **next session's open** after bar `k`. If price closes below `gap_bottom` before this
triggers, the gap is **invalidated** and the setup is discarded.

### Stop
`gap_bottom − 0.10 × ATR(14)` — just beyond the gap. Per the operator's journal: *"Stop-loss goes beyond
the sweep."* Applied here to the gap boundary. **Invalidation is unambiguous and immediate**, satisfying
profile §7.

### Exit
- **Target:** `entry + 2.0 × (entry − stop)` — the 2R structure from the operator's journal (TP2, "ideal
  for funded accounts")
- **Time limit:** market-on-open exit after **10 trading days** if neither stop nor target is hit
- **Stop:** as above

### Market regime
Uptrend only, by construction (the trend filter). Expected to underperform in bear regimes — the regime
breakdown will quantify by how much.

### Why this might work
The mechanism claim is that a displacement bar leaves an imbalance, and price returning to it finds
resting demand. Whether that is real or narrative is precisely what this test determines. **The
operator's journal win-rate table (52–82%) is explicitly *not* used as a prior** (profile §1.3); we
generate our own number.

### Failure modes
- **Daily FVGs are extremely common.** The gap-quality and displacement filters may not thin them
  enough, producing signals with no selectivity. *First diagnostic to run: signal frequency per symbol
  per year, before any P&L calculation.*
- FVG may be a proxy for a simple gap-fill or pullback-in-uptrend pattern, adding nothing over H1.
- The concept originates in intraday futures. Daily equity bars include overnight gaps driven by
  earnings and news — a structurally different phenomenon from an intraday imbalance.
- Four filters (displacement, trend, gap size, retrace window) is already meaningful degrees of freedom.
  Sensitivity testing is mandatory, not optional.
- 2R target may not fit the natural excursion of these moves.

### Parameters (sensitivity-tested)
`displacement multiple` (1.5) · `gap size min` (0.25 ATR) · `retrace window` (10d) · `stop buffer`
(0.10 ATR) · `target R` (2.0) · `time limit` (10d)

---

## H3 — Liquidity Sweep Reversal in an Uptrend

> Liquid US equities in an established uptrend that **sweep a recent swing low and close back above it
> the same session** may produce positive expectancy over a 2R-target / 10-day-limit hold compared with
> H1 and with random selection.

### Conditions
```
close[t] > SMA(200)[t]                               # established uptrend
prior_low = MIN(low[t-10 : t-1])                     # 10-day swing low
low[t]   < prior_low                                 # the sweep
close[t] > prior_low                                 # the reclaim — same session
close[t] > (high[t] + low[t]) / 2                    # close in the upper half of the bar's range
```

**Optional volume confirmation, tested as a variant, not baked in:**
```
volume[t] > 1.3 × SMA(volume, 20)[t]
```

### Entry
Next session's open.

### Stop
`low[t] − 0.10 × ATR(14)` — just below the sweep low. If price returns below the sweep, the premise is
void. **Immediate, unambiguous invalidation.**

### Exit
Identical structure to H2 — 2R target, 10-day time limit — deliberately, so H2 and H3 differ **only in
the entry rule**. Any performance difference is then attributable to selection, not exit management.

### Market regime
Uptrend only. Historically this pattern family degrades sharply in bear markets, where "the dip" keeps
going. The 2022 bucket is the key test.

### Why this might work
Stops cluster below visible swing lows. A sweep that immediately reclaims is consistent with those stops
being taken and the prior trend resuming. **This is a mechanism story, not evidence** — the story is
plausible for many patterns that don't work.

### Failure modes
- **This is "buy the dip in an uptrend" with extra steps.** It may add nothing over a simple pullback
  rule — a plain-pullback variant will be tested alongside as an internal control.
- Sweep-and-reclaim is a well-known pattern; if there was ever an edge, it may be arbitraged away.
- Vulnerable to regime change — precisely when the dip does not recover.
- The same-session reclaim requirement may be too strict, yielding a small sample.

**Reconciling with profile §7:** this resembles mean reversion, which profile §7 disfavours. The
distinction is real: the entry requires a *completed* reclaim (confirmation, not a falling knife) and the
stop sits immediately below the sweep. There is no scenario where a weak position is held for long — it
is stopped within days or it works. That satisfies "no prolonged holding of weak positions."

### Parameters (sensitivity-tested)
`swing lookback` (10d) · `stop buffer` (0.10 ATR) · `target R` (2.0) · `time limit` (10d) ·
`volume filter` (on/off)

---

## 4. Test execution order

| Order | Task | Cost | Purpose |
| --- | --- | --- | --- |
| 1 | **Signal frequency diagnostic** — count signals per hypothesis per year, no P&L | Trivial | If H2 fires 40,000 times/year, the filters aren't selective and the spec needs revision before any backtest |
| 2 | H1 in-sample | Low | Establish the benchmark |
| 3 | Random-selection distribution (1,000 iterations) | Medium | Establish the null |
| 4 | H2, H3 in-sample | Low | Compare against 2 and 3 |
| 5 | Parameter sensitivity, all three | Medium | Detect knife-edge fits |
| 6 | Regime breakdown | Low | Detect regime dependence |
| 7 | **Stage E: out-of-sample — one run, no iteration** | Low | The actual test |

Step 1 first, deliberately: it is nearly free and can invalidate a specification before any expensive
work happens.

## 5. Known limitations — stated before results exist

1. **Survivorship bias.** The Alpaca free tier has limited delisted-ticker coverage, so the historical
   universe skews toward survivors. The $20M ADV filter reduces this materially — large liquid names
   rarely delist to zero — but does not eliminate it. **Every backtest report will state this.**
   Mitigation path: Polygon (~$29/mo) carries delisted tickers (profile §10 / assessment §9).
2. **Point-in-time universe.** Liquidity filters are applied as of each historical date. Sector
   classification is **not** point-in-time (current GICS applied historically), which mildly
   contaminates the sector-concentration rule but not entry signals.
3. **No intraday fills.** Stops are assumed to fill at the stop price plus slippage. Real gap-downs
   through a stop will be worse. Gap risk is reported separately.
4. **Long-only, no shorts.** Deliberate at this stage.
5. **Earnings not yet filtered.** Round 1 holds through earnings. Given 2–10 day holds this is a real
   source of variance; an earnings-exclusion variant is a Round 2 question.

## 6. What is explicitly NOT being tested

Per profile §5, and worth restating so it isn't relitigated: order flow, footprint, delta, DOM, heat
maps, volume profile, TPO, and ICT kill zones require tick or Level 2 data and cannot exist in an EOD
system. SMT divergence is deferred to Round 2 — it is testable on daily bars, but requires a
correlated-pair mapping that doesn't exist yet.

---

## 7. Approval

All three hypotheses are **Stage B**. Nothing has been tested; no result exists.

On approval, Phase 1 code is built to run the §4 sequence. The first meaningful output will be the
signal-frequency diagnostic — which may send us straight back to revise a specification, and that is a
normal and desirable outcome.
