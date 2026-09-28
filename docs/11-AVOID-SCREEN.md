# H8 — the avoid screen

**Written 2026-09-28.** A different kind of hypothesis from H1–H7 and `docs/10`:
it does not try to pick winners. It asks whether leaving out the names the
market is known to overprice makes a random pick from what remains better than
a random pick from everything.

> Leave out the pool's most volatile fifth and the fifth with the largest
> one-day gain in the past month. Draw from the rest.

## 1. Why this, after "no edge found"

Measured by the Obscura vault on Ken French's data library (CRSP, delisting-
adjusted, the whole US market, 202607 vintage), against a random stock from the
same pool, since 2005:

- **No published signal's buy side beats random.** Twelve-month momentum's top
  decile +0.01% a month (t 0.04); value, profitability, low volatility,
  reversal, issuance, accruals, asset growth — none significant.
- **Several avoid sides still lose.** Heavy share issuers −0.99% a month
  (t −4.84); the most volatile fifth of small caps −0.91% (t −3.56).

That is the shape Stambaugh, Yu and Yuan (2012) predict: mispricing is mostly
overpricing, because shorting is hard. A long-only account cannot short it. It
can decline to own it. The lottery reading is Bali, Cakici and Whitelaw (2011):
the decile with last month's largest one-day gain trails the lowest by about 1%
a month, 1962–2005, and the whole effect sits in the top three deciles — an
exclusion result, not a selection one.

It also names a likely reason `docs/10` lost: momentum in small caps selects
volatility (see "No edge found"), which is the fifth this screen removes.
Inference, not measured.

## 2. The configuration

```
POOL        swing_small_mid, point-in-time, as built
SCREEN      leave out names in the pool's top 20% on the date by EITHER
              vol60   standard deviation of daily returns, 60 sessions
              max21   largest daily return, 21 sessions
HORIZON     20 sessions, windows 20 sessions apart (no overlap)
TRADE       the engine's rules: next open, refused on a zero-volume bar;
            exit at the open 20 sessions later, a zero-volume bar's open, or
            a series' last close
COST        each name's own measured spread (calc/spread.spread_table)
STATISTIC   per window, mean net return of the screened pool minus the full
            pool's; mean of that across windows, and its t
```

`screener diagnose screen` computes it (`diagnostics/screen.py`).

**How it was chosen, stated plainly.** The 2026-09-25 proposal named three
variables, the third being last month's return. On development (2026-09-28,
before the data cleaning below) that one did nothing, t 0.64, and was dropped.
**This configuration was therefore chosen after seeing development**, which is
what development is for, and why its development numbers are not evidence.

## 3. Decisions taken 2026-09-28

The operator's instruction on 2026-09-28 was "do it all", given in reply to the
four decisions this platform had put to the operator. They were taken by Claude
under that instruction,
before any validation or test result for H8 exists, and **each can be overridden
by the operator before the first validation run**:

| # | Decision | Taken |
| --- | --- | --- |
| 1 | Clean the impossible bars | Done: `calc/validity.py`, see `CLAUDE.md` |
| 2 | The bar the screen must clear | §4 below |
| 3 | Does `docs/10`'s 1.5× tail-lift stopping rule govern H8? | **No.** That rule stops the convex *ranking* thesis, which `docs/10` tested and rejected. H8 asks what every `docs/03` criterion asks — does selection beat random on the same days — and a volatility screen lowers lift by construction, so judging it by lift would reject it for doing what it is meant to do. |
| 4 | Does a pool definition spend a hypothesis's budget? | **H8 is its own hypothesis with its own budget**: 3 validation configurations, 1 test, as every hypothesis. The §2 configuration is one of them; changing any line of it is another. It joins Holm's family, which has not closed because no validation run exists. A later *strategy* trading from the screened pool is a separate hypothesis and does not inherit H8's evidence. |

## 4. The bar

**To earn a validation run** (development, clean data):

1. Net statistic one-sided p ≤ 0.05.
2. Positive in at least 2 of the split's 3 regime buckets.
3. The 10%-trimmed version positive too, so the result is not a handful of
   extreme names.

**To pass validation** (2016–2019, once per configuration, signed
pre-registration): the same statistic at one-sided p ≤ 0.05 **after Holm**
across the registered validation family, and positive in at least 2 of the
split's regime buckets.

**Test** (2020–2026): the same, once.

Validation and test cannot be run yet, deliberately. `diagnose screen` refuses
every split but development, because it keeps no budget and non-negotiable 5
says budgets are enforced against the database. Spending validation needs two
things first: an operator-signed `preregistrations/H8.md`, and the diagnostic
writing and checking `research_runs` the way `backtest run` does.

## 5. Results — development only; it proves nothing

`screener diagnose screen`, 2026-09-28, after the impossible-bar cleaning and
the `swing_small_mid` rebuild (`research/h8-development.txt`):

| | per 20-session window |
| --- | --- |
| windows | 78, median 2,343 names, 28% left out |
| **screened minus full pool, net of spread** | **+0.174%** (t 2.22, one-sided p 0.013) |
| gross | +0.111% (t 1.43) |
| 10%-trimmed | +0.138% |
| chop 2011 / bull 2013–14 / chop 2015, net | +0.284% / +0.096% / +0.438% |

**It clears the §4 development bar**: p 0.013, 3 of 3 regimes positive, trimmed
positive. About +2.2% a year net against a random pick from the same pool.

**Why that is weaker than it reads.** The bar was written on 2026-09-28, after a
development measurement of a near-identical screen already existed (the vault's,
before cleaning: +0.15% net, t 1.8–2.0), and the configuration dropped a third
variable on that same data. Clearing a bar set that way was likely. It earns a
validation run under §4; it is not evidence that the screen works. Roughly a
third of the net figure is spread saved by not trading the dearest names, which
is mechanical rather than statistical.

**What it does not do.** It does not make the pool beat the market. On the
same grid a random pick from the unscreened pool made about +0.54% per 20
sessions gross, roughly 7% a year, against SPY's +81.2% over the six years,
roughly 10% a year; +2.2% a year does not close that. It is a better pool to
draw from, not a strategy.

## 6. Draft pre-registration — DRAFT, authorizes nothing

Not in `preregistrations/`, deliberately. That registry binds to `backtest run`
options and raises on anything else, so an H8 file there would stop every
hypothesis's validation runs from loading. Moving this there needs the registry
extended to diagnostics, and `diagnose screen` writing and checking
`research_runs` — both engineering, neither done.

```
hypothesis    h8
status        draft            # only the operator signs
split         validation (2016-01-01 to 2019-12-31), once
config        docs/11 section 2, unchanged
passes if     net statistic one-sided p <= 0.05 after Holm across the
              registered validation family, AND positive in >= 2 of
              bull_2017, correction_2018q4, bull_2019
spends        1 of H8's 3 validation configurations
```

**Drafter's recommendation:** worth one validation slot once the two
engineering items exist, because it is the first hypothesis here whose
direction was predicted by independent, survivorship-free data before it was
measured on this project's. It is also the first whose honest best case is
modest — a couple of percent a year better than drawing at random from a pool
that itself trailed the index.
