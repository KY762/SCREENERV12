# Trader Profile & Initial Research Direction

**Date:** 2026-08-16
**Status:** DRAFT — awaiting operator approval. No hypotheses will be written and no code built until approved.
**Evidence base:** operator interviews (2026-08-16) + Notion "FINANCE JOURNAL" export covering 2025-12-09 → 2026-03-20.

---

## 1. Evidence review: the journal

### 1.1 What the journal actually is

A **futures intraday journal**, not a swing-equity one. NQ/ES micro contracts, ICT/Smart Money
methodology, NY open (09:30–11:00) and NY PM (13:30–15:00) kill zones, on a Tradify funded account.

| Measure | Value |
| --- | --- |
| Documented trades with outcomes | ~6 |
| Span | 2025-12-09 → 2026-03-20 (with a ~3 month gap Dec 11 → Mar 11) |
| Instruments | NQ, MNQ (futures) |
| Recorded P&L points | +$36, −$150 net on one day, one "best trade" (unquantified), eval passed |
| Stop losses used | Not consistently; explicitly absent on at least one loss |

**Statistical verdict (Statistician):** n≈6 supports **no conclusion whatsoever** about strategy
performance. At this sample, a 100% win rate and a 0% win rate are both consistent with a coin flip.
Nothing in this journal is evidence for or against the ICT model. It is, however, strong evidence about
*execution*, which is what follows.

### 1.2 What the journal is genuinely evidence of

These are direct quotes. They form a consistent, recognizable pattern:

| Quote | Pattern |
| --- | --- |
| "I didn't enter based on information I got from my sources—it was more intuition" | No mechanical rule at the point of decision |
| "Was at work trying to multi-task and manage the trade… almost forcing the trade" | Trading while attention-divided |
| "I had no clue what the market was doing but still entered" | Entry without setup |
| "KYLER, START PUTTING STOP LOSSES! … I'm stupid and don't want to use a SL" | Undefined risk |
| "I decided I needed to get it back so I could make my $100 profit for the day" | Daily quota driving entries |
| "This is where I started gambling to reclaim my lost profits—and luckily it worked" | Loss-chasing, rewarded by chance |
| "I switched to NQ—fuck micros—and started balling" | Size escalation after a loss |
| Took a trade immediately post-eval "so I could have a minimum profit of $100 for the trading day" | Quota again, independent of setup quality |

**Risk Manager assessment.** This is not a strategy problem. Every single documented loss traces to one
of four things: no predefined stop, a self-imposed daily profit quota, divided attention during the
session, or size increase following a loss. A profitable strategy executed this way still loses money;
an unprofitable one loses it faster. **This is the highest-priority finding in the entire engagement,
and it is a systems problem with a systems solution — not a discipline failing to be willed away.**

The encouraging part: you documented all of it yourself, accurately, in real time. Most traders cannot
see this pattern in their own behavior for years. You wrote it down within days. That is the single
most useful trait for quantitative work, and it is the reason a rules-based platform is likely to help
you specifically — it externalizes the decisions that your own journal shows get made worst under
pressure.

**Note the internal contradiction worth resolving:** your written plan specifies max risk per trade of
0.25–0.5% and max daily drawdown of 0.5–1%. Those are disciplined, well-chosen numbers. The journal
shows trades taken with **no stop at all**, meaning realized risk was undefined and unbounded. The rules
aren't wrong; nothing enforces them. Enforcement is a software problem, which is convenient.

### 1.3 Red Team: the win-rate tables

The journal contains two performance tables that must be treated as **unvalidated**:

| Claim | Source given | Assessment |
| --- | --- | --- |
| FVG alone 52–56%; +Sweep 60–65%; +SMT 67–74%; full model 70–82% | "Based on backtested ICT criteria" | **No source, no sample size, no period, no instrument, no cost assumptions, no methodology.** Unverifiable. Cannot be used as a prior. |
| Absorption Fade ~72%, Delta Divergence ~68%, Stacked Imbalances ~64%, POC Rejection ~70%, Iceberg ~58% | "order-flow strategy testing from trading research platforms" | Same. The journal itself already flags these as "practitioner results, not academic consensus" — correct instinct, and it should be extended to the ICT table above it, which carries no such caveat. |

Two structural problems with all such numbers, independent of who published them:

1. **Win rate alone is not an edge.** A 75% win rate with a 1:3 loss-to-win ratio loses money. Expectancy
   requires win rate *and* payoff ratio *and* costs. None of these tables report payoff or costs.
2. **Monotonically increasing win rate with added confluences is what selection bias looks like.** Each
   added filter shrinks the sample, and shrinking samples produce higher apparent win rates by chance
   alone. Without out-of-sample validation, "more confluences = higher win rate" is indistinguishable
   from curve-fitting.

**This is not a claim that the ICT model doesn't work.** It is a statement that these specific numbers
are not evidence either way, and that we will generate our own.

### 1.4 The second system in the journal

The journal also contains a **FINVIZ value screener** (regional/major banks: P/E<12, P/B<1.2, yield>2%,
D/E<0.8, above 200 SMA; and precious metals: P/E<15, P/S<2, P/CF<10, 1-month perf >+3%, insider
ownership >5%). This is a **long-horizon investing** system, structurally different from 2–5 day swing
trading. It is noted, kept separate, and not merged into swing research.

The associated claim "100% equities historically outperform ~87% of the time over 30 years" is broadly
directionally consistent with published long-horizon research, but the specific figure is unsourced and
should be verified before it anchors any allocation decision.

---

## 2. Trading Universe

| Item | Value |
| --- | --- |
| Primary research track | US equities and ETFs, ~2,000–3,000 liquid names |
| Data granularity | End-of-day daily bars |
| Options | **Wanted**, deferred as a separate track (see §7) |
| Futures | **Out of scope.** No funded account currently held; the Tradify account is not active. Phase 14 removed. |
| Long-horizon value screener | Separate track, lower priority |

**Universe caveat:** the equity/ETF split is contingent on the employer personal-trading policy in §12.
If individual securities are restricted but broad-based ETFs are exempt (the common pattern), the
universe becomes ~50–150 liquid sector and index ETFs instead.

## 3. Time Horizon

- **Target:** 2–5 days optimal, up to ~1 week maximum.
- **Explicitly not:** intraday. This is a change from current practice and is deliberate — see §5.
- Holding-period optimality within the 2–10 day band is itself an open research question and will be
  measured, not assumed.

## 4. Current Strategy

**None defined.** Stated directly by the operator: entry criteria still require research. The journal
corroborates this — the ICT model is written down in detail but the documented trades were entered on
"intuition," not on the written rules.

This is a **clean and honest starting point**, and better than a false one. It means we design from
hypotheses rather than reverse-engineering a process that isn't consistently applied.

## 5. Knowledge & Skills

### What transfers to daily-bar equities (the good news)

The operator's background is ICT/Smart Money Concepts and order flow. Several of these concepts have
**crisp, objective, mechanizable definitions** and translate directly to daily bars:

| Concept | Daily-bar definition | Testable? |
| --- | --- | --- |
| **Fair Value Gap (FVG)** | 3-bar pattern: gap between bar 1 high and bar 3 low (bullish) or bar 1 low and bar 3 high (bearish) | **Yes** — fully mechanical |
| **Inverse FVG** | Prior FVG traded through and now acting as opposing support/resistance | **Yes** |
| **Liquidity sweep** | Trade below prior N-day low (or above high) followed by close back inside range | **Yes** |
| **SMT divergence** | Correlated pair (e.g. QQQ/SPY, or a stock vs its sector ETF) making non-confirming highs/lows | **Yes** |
| **Break of structure (BOS)** | Close beyond the most recent swing high/low, swing defined by fractal lookback | **Yes**, once swing definition is fixed |
| **Displacement** | Large-range bar relative to ATR, creating the FVG | **Yes** |

This is a genuinely favorable position. Most discretionary traders arrive with concepts that resist
formalization. FVG, sweep, and BOS are unusually well-suited to mechanical definition — they are
geometric, not interpretive.

### What does NOT transfer (hard constraint)

| Concept | Why it cannot be in an EOD swing screener |
| --- | --- |
| Footprint / delta / bid-ask aggression | Requires tick-level trade data with aggressor side. Not derivable from daily OHLCV at any price we'd pay. |
| DOM / order book | Requires Level 2 depth. Real-time only, not historical for backtesting, expensive. |
| Heat maps (Bookmap-style) | Requires full order-book replay data. Institutional cost. |
| Volume profile / POC / value area | Requires intraday volume-at-price. Possible in principle, but needs intraday data — outside current scope and budget. |
| Auction Market Theory in its operational form | Depends on the above. The *conceptual* balance/imbalance framing survives; the tooling does not. |
| ICT kill zones (NY open/PM sessions) | Intraday by definition. Meaningless on daily bars. |

**This is a real and unavoidable conflict**, and it is better named now than discovered in Phase 9. The
order-flow half of the operator's expertise is intraday-futures tooling. It does not port to an
end-of-day equity screener, and no amount of engineering changes that — it's a data availability
constraint, not a software one.

**Terminology:** "TVOP" confirmed by the operator as **TPO** (Time Price Opportunity, the Market Profile
construct). Like volume profile, it requires intraday data and is not available in an EOD screener.

### Structural conflict: session times vs. employment

The journal documents trading NY open (09:30–11:00 EST) **while at work**, and explicitly attributes at
least two poor trades to that divided attention. Intraday futures trading during working hours is not
compatible with holding a job — this is a scheduling fact, not a discipline question.

**End-of-day swing trading resolves this completely.** Screens run after the close, decisions get made
in the evening, orders are placed before the open. It fits the stated 30–60 min/day budget and removes
the single most cited cause of bad execution in the journal. This alignment is the strongest argument
for the swing track being the right primary focus.

## 6. Constraints

| Constraint | Value |
| --- | --- |
| Swing capital | **$10,000**, side funds, not yet deployed |
| Employment | **Branch banker.** Mon–Fri 09:00–17:00, Sat 08:00–12:00 |
| Weekday time | 30–60 min, evenings only |
| Weekend time | Saturday afternoon + Sunday |
| Concurrent positions | 4–5 realistic at $10k |
| PDT rule | Applies under $25k on margin, but **does not affect 2–5 day holds** |
| Costs | Commissions ~$0 at major brokers. Market impact ~zero at this size — a genuine advantage. |
| **Compliance** | **See §12 — potentially binding on holding period and universe** |

### 6.1 Schedule fit

The EOD design aligns cleanly with the work schedule: market closes 16:00 ET, screens run ~16:30,
results are ready for an evening review, orders are placed pre-open. **No decision is ever required
during working hours** — which removes the most frequently cited cause of poor execution in §1.2.

### 6.2 Capital sizing at $10,000

| Metric | Value |
| --- | --- |
| Risk per trade @ 1% | $100 |
| Position value @ 5% stop | ~$2,000 (20% of account) |
| Position value @ 8% stop | ~$1,250 (12.5% of account) |
| Slippage / market impact | Negligible |

**Assessment: $10,000 is appropriate for the objective**, which is generating a validated process and a
real track record, not income. Returns at this size are not financially material (20% = $2,000), and
that is expected rather than a problem.

**The specific hazard at this capital is oversizing to make results feel meaningful** — the exact
pattern documented in §1.2. Small capital does not remove that instinct; it only changes the number
attached to it. Position size is therefore computed by the system with no manual override.

**Deployment recommendation: hold the $10,000 uninvested until a strategy clears validation Stage E.**
Forward-test (Stage F) on paper. Nothing is lost by waiting — no validated strategy will exist for
months regardless.

## 7. Risk Profile

| Parameter | Value | Notes |
| --- | --- | --- |
| Max account drawdown | ~25% | Operator-stated |
| Qualifier | **No prolonged holding of weak positions** | The most informative constraint given |
| Provisional per-trade risk | 0.75–1.5% ($190–375) | To be finalized from backtested drawdown distributions, not chosen now |
| Provisional max open risk | ~6% across the book | 4–6 positions |
| Stop discipline | **MANDATORY, pre-entry, non-negotiable** | See §7.1 |

### 7.1 Risk Manager veto — standing conditions

Under the veto authority granted in the project brief, these are non-negotiable for any strategy that
reaches live capital, and each maps to a documented failure in the journal:

1. **Every position has a predefined stop, entered before or simultaneously with the entry order.** No
   exceptions. Journal evidence: "I'm stupid and don't want to use a SL."
2. **No daily, weekly, or monthly profit quota.** Quotas caused documented loss-chasing. The platform
   will not display a "profit needed today" figure anywhere.
3. **Position size is a fixed fraction of equity, computed by the system.** Never increased after a loss.
   Journal evidence: "switched to NQ—fuck micros—and started balling."
4. **No trade decisions during working hours.** Structurally enforced by the EOD design.
5. **A trade with no logged pre-entry thesis is a rule violation**, and gets recorded as one regardless
   of outcome. A profitable rule-break is still a rule-break — arguably worse, since it reinforces the
   behavior. The journal contains exactly one such case, described as "luckily it worked."

**The drawdown qualifier translated:** "25% but don't prolong weak positions" implies tolerance for a
losing *streak* but not a slow bleed in a single name. This rules out mean reversion, averaging down,
and wide-stop strategies as a matter of fit, and favors trend/momentum continuation with fast, objective
invalidation. That is a genuinely useful narrowing.

## 8. Goals

Ranked as selected: **long-term wealth building**, **learning quantitative research**, **eventually
significant trading income**.

**Honest arithmetic on the third.** At under $25k, a sustained and genuinely excellent 20%/year is
~$5,000; an exceptional 30% is ~$7,500. Neither is income. Over the next 2–3 years the realistic
deliverable is **a validated process and a real track record**; account growth comes primarily from
contributions and compounding. The edge is what makes larger capital worth deploying later. The first
two goals are exactly right for this capital level and are fully compatible with the third arriving
afterward.

## 9. Initial Research Direction

Three candidate directions, in the order the Lead Quant recommends investigating them. Formal
hypotheses come **after** this profile is approved.

### Direction 1 — Momentum/relative-strength continuation *(the benchmark)*
Run first, deliberately, as a **control**. Cross-sectional momentum is among the most widely replicated
anomalies in the academic literature, which makes it the honest yardstick: any SMC-derived strategy must
beat *this*, not merely beat zero. Establishing it first prevents mistaking a broad market or momentum
factor exposure for a novel edge — the exact trap the brief's Red Team is meant to catch.

### Direction 2 — Daily-bar FVG / displacement continuation *(the operator's own concept, mechanized)*
Translate FVG + displacement + BOS to daily bars on liquid equities. Directly leverages existing
knowledge; fully objective; testable. Tests whether the operator's framework carries signal on a
timeframe and instrument class where it can actually be executed around a job.

### Direction 3 — Liquidity sweep reversal in an established uptrend
Sweep of prior N-day low followed by a reclaim, filtered to names already in an uptrend. Also from the
operator's framework, also mechanical, and structurally compatible with the "no prolonged weak
positions" constraint — invalidation is unambiguous and immediate.

**Deliberately excluded from the first round:** anything requiring order flow, footprint, DOM, or
volume profile (data-infeasible per §5); intraday timing (incompatible per §5); multi-factor
combinations (each added confluence shrinks the sample and invites the overfitting described in §1.3).

### Options — a separate, later track

Requested, and reasonable to want. Deferred deliberately, for three reasons:

1. **Methodological.** Validating an entry signal and an options expression simultaneously means two
   sets of free parameters and no way to attribute a result to either. The correct sequence is: prove
   the underlying signal on shares, *then* test whether expressing it in options improves risk-adjusted
   return.
2. **Cost.** Options chains, IV surfaces, and greeks are a separate data subscription that would consume
   most of the $50–100/mo budget currently allocated to equity data.
3. **Instrument risk.** On 2–5 day holds at under $25k, bid-ask spread and theta are material — often
   larger than the edge being tested. Options can *amplify* an edge; they cannot create one.

The requested **option-contract selection feature** (choosing strike/expiry/liquidity for a given thesis)
is a well-defined, genuinely useful deterministic tool, and is planned — after a share-based signal
clears validation Stage E.

### Futures — removed from scope

No funded account is currently held. **Phase 14 is deleted.** The journal's futures content is retained
as behavioral evidence (§1.2), not as a system to support.

Secondary benefit: this project becomes the operator's *only* trading activity, so there is no parallel
account in which the quota-chasing and size-escalation patterns of §1.2 can operate unchecked during
development.

---

## 10. Broker selection

Contingent on §12 — an employer approved-broker list overrides everything below.

**Recommended: Alpaca.** The reasoning is integration-specific rather than generic. Alpaca is already
the chosen market-data provider; its paper-trading environment exposes an **identical API** to live
trading; and portfolio position import uses the same client again. One adapter therefore serves data,
Stage F forward testing, and execution. At $10k, **fractional shares** (a $400 stock remains tradeable)
and $0 commissions (a $1,250 position isn't eaten by fees) matter more than platform polish.

*Caveats:* developer-first, so no advanced charting UI and limited support. **Options availability is
unclear from current sources** — some 2026 reviews describe stock *and* options API trading, others
state options are unsupported. Verify directly before relying on it; not urgent, since options are a
deferred track.

**Upgrade path: Interactive Brokers**, if capital exceeds ~$50k or options become central. Superior
execution, margin rates, and options coverage; meaningfully more complex API; market data costs extra.

**Ruled out:** Fidelity (no retail API), Robinhood (no official API). Schwab has an API but a rocky
post-TD-Ameritrade migration.

**Do not open an account before checking §12.**

---

## 11. Open items before hypothesis writing

1. **Employer personal-trading policy** (§12) — blocking. Determines holding period and universe.
2. Approved-broker list, if one exists — determines broker choice.

---

## 12. Employer compliance constraint (BLOCKING)

The operator is a **branch banker**. Financial institutions routinely impose personal securities trading
policies on employees. Provisions to verify before hypothesis design, since several would invalidate the
current specification:

| Provision | Impact if applicable |
| --- | --- |
| **Minimum holding period** (30 days is common) | **Fatal to the 2–5 day design.** Forces a multi-week horizon and a different strategy family. |
| **Pre-clearance requirement** | Survivable — inserts a compliance step between screen output and order entry. The platform can generate the request. |
| **Approved broker list** | Overrides §10 entirely. |
| **Duplicate statements / account disclosure** | Administrative only; no design impact. |
| **Restricted list** (employer's own securities, client companies) | Implemented as a universe exclusion filter. |

**Likely mitigation.** Broad-based ETFs are commonly exempt from pre-clearance and holding-period
requirements, since index instruments cannot be front-run. If individual securities are restricted but
ETFs are exempt, the universe becomes ~50–150 liquid sector and index ETFs.

This is **not a downgrade for swing trading**: deeper liquidity, no single-name earnings-gap risk,
cleaner sector-rotation signals, and a smaller universe permits faster research iteration. Several of
the operator's SMC concepts port at least as well — SMT divergence is natively an index-pair construct
(§5), and liquidity sweeps on index ETFs are well defined.

**No policy outcome identified so far kills the project.** The outcome determines universe and holding
period, both of which are inputs to hypothesis design, which is why it is resolved first.

---

## 13. Approval

This profile is a draft. Correct anything that doesn't read like you — particularly §1.2, which is
built from your own words but is still an interpretation of them. Nothing proceeds to hypothesis design
until you approve or amend it.
