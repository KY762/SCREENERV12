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
