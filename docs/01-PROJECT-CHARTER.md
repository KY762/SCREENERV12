# Project Charter — What We Are Building, and Why

**Date:** 2026-08-17
**Status:** Synthesis of `00`, `02`, `03`, `04`, `05`. Written before Phase 1 code begins.
**Purpose:** The document to re-read when the project feels complicated, or to hand someone who asks
what this is.

---

## 1. The one-paragraph version

We are building a personal market intelligence and trading operations platform for a single operator: a
full-time branch banker with $10,000 in side capital, 30–60 minutes on a weekday evening, a background
in ICT/Smart Money Concepts and order flow, and no validated trading strategy. The platform's job is to
compute every number deterministically, enforce risk rules that cannot be overridden in the moment, test
whether the operator's existing trading concepts carry any real signal, and produce evidence rather than
opinion. **Its primary product over the next two years is a validated process and an honest track record
— not income.**

## 2. The mistake this project is designed to avoid

Nearly everyone in this position believes the binding constraint is *"I need a profitable strategy."* So
they buy a course, learn a framework, and start trading. The strategy is treated as the missing piece.

**The evidence says otherwise.** The operator's own trading journal — 2025-12-09 to 2026-03-20, roughly
six documented trades on a funded futures account — contains a written plan specifying 0.25–0.5% risk per
trade and a 0.5–1% daily loss limit. Those are disciplined, well-chosen numbers. The journal then
documents, in his own words:

> "KYLER, START PUTTING STOP LOSSES! … I'm stupid and don't want to use a SL"
> "I decided I needed to get it back so I could make my $100 profit for the day"
> "This is where I started gambling to reclaim my lost profits—and luckily it worked"
> "I switched to NQ—fuck micros—and started balling"
> "Was at work trying to multi-task and manage the trade"

**Every documented loss traces to one of four causes: no predefined stop, a self-imposed daily profit
quota, divided attention during the session, or size escalation after a loss.** None of these are
strategy problems. A profitable strategy executed this way still loses money; an unprofitable one loses
it faster.

The rules were not wrong. **Nothing enforced them.** That is a software problem, and it is the reason
this project is a platform rather than a spreadsheet.

## 3. Three findings that shaped everything

### Finding 1 — The failure mode is execution, and it is fixable by design
See §2. The system therefore computes position size with no manual override, requires a stop
simultaneous with entry, never displays a "profit needed today" figure anywhere, and logs a rule
violation regardless of whether the trade made money. A profitable rule-break is still a rule-break —
arguably worse, since chance rewards the behaviour.

**The encouraging half:** the operator diagnosed all of this himself, accurately, in writing, within days
of it happening. Most traders cannot see this pattern in their own behaviour for years. That is the single
most useful trait for quantitative work, and it is why a rules-based system is likely to help this
operator specifically.

### Finding 2 — There is no strategy yet, and that is a clean starting point
The operator states plainly that entry criteria still require research. The journal corroborates it: the
ICT model is written down in detail, and the documented trades were entered on *"intuition and market
experience."*

This is better than a false starting point. We design from hypotheses instead of reverse-engineering a
process that was never consistently applied.

### Finding 3 — The operator's expertise is real but timeframe-mismatched
His knowledge is intraday-futures order flow: footprint, DOM, heat maps, volume profile, TPO, NY-open
kill zones. Two independent problems:

1. **Structural.** Trading the 09:30–11:00 session requires attention he does not have, and the journal
   attributes specific losses to exactly that conflict.
2. **Evidential.** The microstructure literature finds order-flow imbalance effects strongest *within
   tens of seconds*, dissipating almost entirely *within one second*, informative for *at most several
   minutes*, and decaying rapidly *beyond one day*. His target hold is 2–5 days. **Even with an
   institutional data feed and unlimited budget, the signal would have decayed before the hold begins.**

The constraint is not cost. Order flow is a genuinely powerful discipline operating on a timescale that
does not reach swing positioning. That is a reframe, not a consolation: he is not settling for inferior
tools, he is matching tools to timeframe.

**What does transfer:** Fair Value Gaps, Inverse FVGs, liquidity sweeps, break of structure, and SMT
divergence all have crisp *geometric* definitions and port cleanly to daily bars. Most discretionary
traders arrive with concepts that resist formalization. These largely don't — which is a genuine
advantage.

## 4. What we are therefore building

Three jobs, in dependency order.

### Job 1 — Externalize the decisions that get made worst under pressure
Screens run after the close. Candidates arrive ranked, with entry, stop, and size already computed.
Portfolio risk, sector concentration, and correlated exposure are visible before the order is placed.
**No decision is ever required during working hours.** This directly removes the most frequently cited
cause of loss in the operator's own record.

### Job 2 — Find out whether his concepts carry signal
Four hypotheses at Stage B, specified in `03` and `05`:

| | Hypothesis | Role |
| --- | --- | --- |
| **H1** | Volatility-adjusted relative-strength continuation | **Control — built to be beaten** |
| **H2** | Daily-bar Fair Value Gap continuation | His framework, mechanized |
| **H3** | Liquidity sweep + reclaim | His framework, mechanized |
| **H4** | Inverse FVG | His framework, mechanized (pending overlap check) |

H1 is the most important and it is not his. It is the simplest thing that could plausibly work, built
from the most replicated factor in the literature. Without it, a positive H2 result is uninterpretable —
we would not know whether the FVG did the work or whether we merely bought strong stocks in a bull
market.

### Job 3 — Build the evidence machine
Every future question — a new indicator, a different holding period, an options overlay — gets answered
with data instead of opinion. This is the part that compounds. A one-off backtest answers one question;
infrastructure answers them repeatedly, at declining marginal cost.

## 5. The governing principle

Adopted after the operator identified that an earlier draft had hard-coded `1.5 × ATR` and a `10`-day
lookback as though they were derived, when they were assumed:

> **Every constant is either derived from evidence, conventional and declared as such, or itself a
> hypothesis under test. No third category exists.**

This is the difference between a quantitative system and a system that merely *looks* quantitative.
Attaching arbitrary numbers to ICT terminology produces the latter, and it rests on exactly the same
unexamined folklore as the win-rate tables we rejected.

## 6. Division of labour: code versus AI

| Deterministic code owns | AI owns |
| --- | --- |
| Prices, indicators, position sizing, stops | Summarizing what the platform computed |
| P&L, R multiples, returns, correlations | Explaining why a candidate qualified |
| Portfolio weights, concentration, risk | Comparing original thesis against current conditions |
| Statistical metrics, ranking, backtesting | Morning and post-market briefings |
| | Journal pattern analysis |

**AI never invents a price, an indicator, a news item, or a calculation.** Where data is unavailable, the
system says so. Every AI call is logged with its input payload hash, model, output, and cost, so any
claim traces back to the rows that produced it. The AI layer can be deleted and the platform still works
— which is the correct dependency direction.

## 7. The honesty machinery

Retail quantitative research fails in a predictable way: test many variants, keep the one that looks
good, discard the rest, and mistake a beautiful backtest of noise for an edge. It is indistinguishable
from success until real money is deployed. Five defences, all pre-committed:

1. **Three-way data split.** Development (2010–2015) permits unlimited exploration because nothing there
   counts as evidence. Validation (2016–2019) allows three configurations per hypothesis. Test
   (2020–2026) is sealed and opened once.
2. **Pre-registered success criteria.** ≥200 trades, profit factor >1.20, above the 75th percentile of a
   1,000-iteration random-selection distribution, drawdown <25%, positive in ≥3 of 5 regime buckets.
   **Failing a criterion rejects the hypothesis; thresholds do not move.**
3. **Stability surfaces, not best points.** Parameters are chosen at the *centre of a plateau*, never at
   the peak — choosing the maximum is fitting to noise by construction. A parameter with no plateau is
   evidence against the hypothesis, not an invitation to search harder.
4. **The random-selection benchmark.** Same universe, same trade count, same holding period, 1,000
   iterations. If a strategy cannot beat randomly chosen stocks held for the same duration, it has no
   selection edge — it has market beta wearing a costume. This is the most commonly omitted test in
   retail backtesting.
5. **Internal controls.** H3 runs against a plain-pullback variant. If sweep-and-reclaim cannot beat
   "buy dips in uptrends," the ICT framing is decorative — an uncomfortable finding, and precisely why
   the control exists.

Every reported result states how many configurations preceded it. A profit factor selected from 50 trials
is weaker evidence than the same number from 3, and the reader is entitled to know which they are
looking at.

## 8. Validation gates

No strategy touches real capital before Stage F. Current position: **Stage B on all four hypotheses.**

| Stage | Meaning | Status |
| --- | --- | --- |
| A — Idea | Interesting, unproven | ✓ passed |
| B — Objective specification | Rules fully defined | **← we are here** |
| C — Historical test | Initial backtest complete | |
| D — Robustness | Overfitting and fragility probed | |
| E — Out-of-sample | Sealed data, one run | |
| F — Forward test | Prospective, on paper | |
| G — Small capital | Limited real money | |
| H — Scaling review | Increased allocation | |

**The $10,000 stays uninvested until Stage E clears.** Nothing is lost by waiting; no validated strategy
will exist for months regardless.

## 9. What success looks like — realistic, not aspirational

| Horizon | Realistic outcome |
| --- | --- |
| 3 months | Data pipeline verified to the penny. Indicators tested against golden values. First honest answers on H1–H4. |
| 6 months | Screener in daily use. Regime and breadth engines running. At least one hypothesis through Stage D, or honestly rejected. |
| 12 months | Positions, portfolio risk, journal, and analytics live. Something at Stage F on paper. A real track record beginning. |
| 24 months | Validated process, documented evidence, and a track record that would justify deploying larger capital — from savings, not from trading returns. |

**Honest arithmetic, stated once so it is not forgotten:** at $10,000, a sustained and genuinely
excellent 20%/year is $2,000. Exceptional and rare — 30% — is $3,000. Neither is income. The operator
ranked *long-term wealth building* and *learning quantitative research* alongside *eventual significant
trading income*; the first two are exactly right for this capital, and they are what make the third
reachable later. The edge is what makes larger capital worth deploying. Anyone claiming a small account
can be traded into a living is selling something, and the mechanism is always leverage — which is
precisely what would breach the 25% drawdown limit.

## 10. Why "no edge found" is a successful outcome

If we test H2, H3, and H4 honestly and find they carry no signal beyond H1, **that is a win worth
thousands of dollars and several years.** The operator currently believes, on the strength of unsourced
win-rate tables, that a four-confluence ICT model wins 70–82% of the time. Discovering that daily-bar
FVGs add nothing over simple momentum saves him from building a trading life on it.

The failure mode this project is designed to prevent is not "the strategies don't work." It is
"the strategies don't work and we convinced ourselves otherwise."

## 11. What we are deliberately not building

| Not building | Why |
| --- | --- |
| Autonomous trading | The operator makes every decision. The platform informs; it does not act. |
| Price prediction | Nothing here forecasts. It measures conditions and manages risk. |
| Order flow / footprint / DOM / TPO | Requires tick or L2 data, and decays before a 2–5 day hold begins (§3, Finding 3). Permanently closed for this project. |
| Options — for now | Deferred until a share-based signal clears Stage E. Validating a signal and an options expression at once gives two sets of free parameters and no way to attribute the result. The contract-selection tool is planned, later. |
| Futures module | No funded account is held. Removed from scope. |
| Automated parameter optimization | Not until the overfitting protections in §7 are proven in practice. |

## 12. Current state and next action

**Complete:** repository assessment (`00`), trader profile (`02`), four specified hypotheses (`03`, `05`),
indicator pre-screening (`04`), and this charter. Approved: universe, sizing, cost model, data splits,
success criteria, indicator set, and hypothesis specifications.

**Next: Phase 1.** Repository skeleton, configuration, database schema, provider abstraction, Alpaca
ingestion, validation layer, and the pure-function calculation engine with golden-value tests.

**Phase 1 gate:** SPY, AAPL, and QQQ daily bars for five years match an independent reference to the
penny; every validation rule passes; re-running ingestion is idempotent; every indicator matches a
hand-computed golden value.

Then two diagnostics that cost minutes and could send us straight back to revise the specifications —
the **indicator redundancy matrix** and the **signal-frequency and overlap counts**. H2 with displacement
optional may fire so often it has no selectivity; H4 may prove to be H3 wearing a different name. Learning
either in minutes rather than after a full backtest is the entire point of running them first.

That outcome is expected and desirable. Specifications that survive contact with data unchanged are
usually specifications that were never tested against it.
