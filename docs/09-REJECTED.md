# Rejected — things deliberately not built, and why

A fresh session sees the code but not the arguments. Everything below looks
like an obvious improvement to someone who was not here, which is exactly why
each one needs a written reason.

**If you want to revisit any of these, that is legitimate.** Argue with the
reason given. What is not legitimate is reintroducing one silently because it
looked like an oversight.

---

## Data

**Yahoo as an ingestion source.** It has decades of free history and we already
use it for verification, which makes it tempting. Two problems: it serves
split-adjusted prices only, which contradicts the raw-storage policy in
`db/models.py` and would make stored history mutate at every future split; and
using the verification source as the ingestion source makes the Phase 1 gate
circular. It stays a reference source only. See ADR 0002.

**Alpaca's paid tier ($99/mo).** Solves the history problem outright. Rejected
on arithmetic: roughly 12% of a $10,000 account per year, against a strategy
with no demonstrated edge. Revisit if the account grows or something passes
validation.

**Storing one row per reporting period in `fundamentals`.** Simpler and smaller.
Rejected because it destroys the ability to ask what was known on a past date:
restatements would overwrite the figure that was actually public. Every version
is kept, keyed on accession number.

**Using the original filing when a restatement exists.** Sounds like the
conservative choice. It is wrong: a restatement filed before the screen date
was public knowledge, and ignoring it uses less information than the market
had. The rule is `filed <= as_of`, most recent version — which handles both
directions with one condition.

## Strategy

**Sector-specific parameters.** Different thresholds per sector divides the
sample by eight and multiplies tunable numbers by eight. That is the
confluence-stacking pathology from `docs/05` §1.4 — the operator's own journal
shows win rate climbing from 52% to 82% as conditions were added, which is what
selection bias looks like when a dataset is sliced thinner. Sector as a ranking
input or a correlation control is fine. Sector-specific *rules* are not.

**Adding hypotheses after Round 1 failed, chosen from what looked least bad.**
Round 2 exists, but h5/h6/h7 were selected for having published evidence
behind them, not for scoring well in our own failed sweeps. Mining a null
search for its most promising corner manufactures false positives.

**Removing the mandatory stop from `calc/sizing.py`.** The strongest research
result so far says a price stop set inside normal noise costs more than it
protects (`docs/07`). That is one development-split measurement with a known
confound. The mandatory stop stays until something survives validation — the
profile's documented losses came from having *no exit at all* on leveraged
futures, which is not what any of this tested.

**Optimising for the best cell on a parameter surface.** `backtest/surface.py`
selects the plateau centre and refuses to select a spike at all. Choosing the
maximum is fitting to noise by construction; the peak's margin over its
neighbours is precisely the part that does not survive out of sample.

## Scope

**React and FastAPI for the interface.** The original Phase 5 plan. For one
operator on one machine it means two codebases, two languages, a build step and
a deployment story, for no capability that matters yet. Streamlit imports the
existing package and calls the same functions the CLI does. React earns its
place if this ever needs to run somewhere other than the operator's machine.

**Footprint, DOM, heat maps, volume profile, TPO.** Excluded on two independent
grounds in `docs/05` §2.1: the data is intraday-only and expensive, and — more
decisively — the documented predictive horizon of order-flow imbalance is
seconds to minutes. It decays before a 2–5 day hold begins. Not revisitable
within this project; relevant again only if the operator pursues intraday
trading, which is a separate discipline.

**Fibonacci retracements.** Not objectively definable — they require
discretionary swing-point selection, so two people reading the same chart get
different levels. Fails the mechanization criterion outright (`docs/04` Tier 4).

**RSI, MACD, stochastics, Bollinger %B, Ichimoku, OBV.** Each rejected in
`docs/04` Tier 4 on parameter cost exceeding expected informational
contribution, given what is already computed. None of these is a claim that the
indicator does not work.

## Method

**Moving a pre-registered threshold after seeing a result.** The criteria in
`backtest/performance.py` are module constants rather than arguments
specifically so this requires editing the file and explaining it in a commit.

**Sweeping parameters on the validation or test split.** Refused by the CLI. A
sweep would spend a three-configuration budget in a single command without
anyone deciding to spend it.

**Reporting only the experiments that found something.** The battery reports
every experiment in declaration order, including the empty-handed ones. A
report containing only the interesting results is a report of a search, not of
a result.

---

## Hypotheses, retired 2026-09-22

The first seven hypotheses are archived here with their verdicts. This is not a
clean slate: four of them were rejected on evidence, and that is a result worth
keeping. **Re-proposing any of them requires arguing with the reason below, not
noticing a gap.**

All seven shared one flaw beyond their individual ones: they were tested as
whole strategies — an indicator plus a hold plus a stop plus sizing plus
portfolio limits — so a failure could never be attributed to any single part.
588 configurations were spent that way before `screener diagnose predictive`
asked the prior question directly.

### Rejected on evidence

**H2 — Daily-bar fair value gap continuation.** NONE across every experiment in
every battery, including on the unrestricted universe where survivorship bias
was helping it. Its exit-isolated arm also failed isolation at 29% trade-count
divergence, so even its exit comparison measured a confound.

**H3 — Liquidity sweep reversal.** NONE, and below random on the date-matched
benchmark in all four of its experiments on the 2026-09-20 battery. The ICT
framing was tested against a plain-pullback control by design; it did not beat
it.

**H4 — Inverse fair value gap.** NONE. Overlapped H3 heavily by construction
(`docs/05` §1.3 anticipated this), so it was never independent evidence.

**H7 — Volatility squeeze into range expansion.** NONE across all three of its
experiments. `h7_compression_depth` reached the 16th percentile; `h7_no_stop`
the 50th at best and the 3rd at worst.

These four were rejected **with the bias helping them**, which is the strongest
form of rejection this project can produce. Their signals were real and
frequent — `docs/06` measured thousands of occurrences — they simply did not
predict returns.

### Retired for a different reason

**H1 — Relative-strength continuation (the control). NOT RETIRED — see the
correction below.** An earlier version of this section archived H1 and claimed
the date-matched random benchmark could take over as the control. That was
wrong, and the operator caught it.

The two are different tests and only one of them was ever the benchmark:

| | Question it answers |
| --- | --- |
| Date-matched random benchmark | Does this rule have any selection skill? |
| **H1, the control** | Is this complexity worth anything over a simple momentum rotation? |

A strategy can clear the first and fail the second — beat random while being
worse than buying strong stocks and holding three weeks. The second test is
what made rejecting H2, H3 and H4 mean something, and deleting H1 would have
silently removed it.

What IS wrong with H1 is only its specification: it ranked on 63-day relative
strength, which `diagnose predictive` measures at IC +0.017 (t = 0.81) —
noise. A control built on a noise indicator is a bar not worth clearing. It is
respecified on the twelve-month variant in `docs/10`, and it keeps its role.

Also recorded: H1 spent four rounds looking like the project's one positive
result, which was survivorship channel 2 rather than the rule — 97.7th
percentile on all stored symbols, 49.8th on point-in-time membership.

**H5 — Canonical 12-1 momentum.** Never given a fair test. Its last numbers
predate the split fix, the quarantine and the ranking fix. The indicator it
rests on is the strongest thing measured here (IC +0.033 at 20 days, 59%
positive), so the idea survives even though this specification does not — it
was written for a large-cap universe and rebalances monthly on a hold the
2026-09-20 battery scored at the 0th percentile.

**H6 — Post-earnings drift.** Never had the sample size to answer: its tightest
filter produced 96 trades against a 200-effective floor. Two specific problems,
both fixable rather than fatal — it has no earnings-surprise measure and uses
the size of the price reaction as a proxy, which is a different variable; and
its filter was tight enough to starve itself. Its event dates were checked on
2026-09-22 and are sound: the largest move clusters on the filing day and the
next (788 and 797 of 4,573 filings, against a ~220 baseline), so the ingest is
catching the earnings release rather than a late 10-Q.

### What replaces them

A universe of US mid and small caps constructed per date from liquidity rather
than from anyone's index membership, and an indicator-first method: measure
predictive content before building a strategy on it, then test selection, exit,
sizing and costs as separate questions rather than as one bundle.
