# The swing strategy

**Written 2026-09-22.** One strategy, derived from measurement rather than from
an idea, replacing the seven hypotheses archived in `docs/09`.

> Own US mid and small caps that have been rising for a year, bought at the
> next open, cut quickly if they turn, and held with a trailing stop and no
> time limit so the winners are allowed to run.

Nothing below is proven. This is the specification; whether it has an edge is
what the testing answers.

## The rules

```
UNIVERSE      US common stock, NYSE / NASDAQ / AMEX
              price $5 to $80
              50-day average dollar volume >= $2,000,000
              >= 252 bars of history
              not on the quarantine list

FILTER        close > SMA(50) > SMA(200)
              SMA(200) today > SMA(200) 21 sessions ago

RANK          raw 12-month return, skipping the most recent 21 sessions
              ret(252) shifted 21 -- NOT volatility-adjusted

BUY           top 10% of the ranked universe
              at the NEXT session's open

STOP          entry - 3 x ATR(14), trailing UP only, never down

TARGET        none

SIZE          risk 0.5% of equity per position
              maximum 10 concurrent positions
              total open risk capped at 5%
```

## Why each line, and what it cost to learn

**The price ceiling** is arithmetic, not preference. At 0.5% risk on $10,000
with a 3 × ATR stop, a $100 name buys five whole shares and takes 90% of the
intended risk; a $200 name buys two and takes 72%. Without a ceiling those
trades still happen, they are just silently under-risked. Measured 2026-09-22.

**The $5 floor and $2M volume floor** keep the spread survivable. Estimated
from daily ranges (`calc/spread.py`), NBR sits at 36.5bp — 4.6% a year of drag
at a 20-day hold against 1.5% at 63. On a thin name the cost model becomes the
entire result.

**Raw 12-month return, not volatility-adjusted.** Measured on large caps: raw
`ret(252)` holds 16.5% of the biggest subsequent movers against
volatility-adjusted `RS_adj(252)`'s 13.3%. Dividing by volatility penalises
exactly the high-volatility names that produce large winners, which is the
wrong transform for a strategy whose returns come from the right tail. The
previous seven hypotheses all ranked on the adjusted version.

**Skipping the most recent month** follows Jegadeesh & Titman (1993), who find
the momentum return absent in the month immediately after ranking.

**The trailing stop with no target** is what produces the payoff shape. A
target and a trailing stop answer the same question and whichever fires first
wins: a near target always fires first and caps the right tail, a far one never
binds. Since the whole strategy depends on rare large winners paying for
frequent small losses, the target is the thing that would break it.

**0.5% risk** survives the losing streaks this shape produces. At an expected
win rate near a third, ten losses in a row is an ordinary event; at 0.5% that
is a 5% drawdown. It also lets ten positions fit inside the 5% open-risk cap,
where 1% allows only five — which is what held the trade count to 305 and
failed the effective-sample floor on the last attempt.

## What is expected to be uncomfortable

A win rate around a third. Six or seven losses out of ten, with the return
carried by a handful of trades. The operator's documented losses came from
execution rather than strategy — missing stops, size escalation after a losing
run — and this is the payoff shape that tests that discipline hardest. The stop
being mechanical is the whole reason this platform exists.

Selecting names capable of large moves also maximises gap risk, and gaps are
what defeat stops. Expect occasional −2R and −3R losses rather than a clean −1R
floor. The engine models this correctly (non-negotiable 6: gaps fill at the
open), so the backtest will not flatter it.

## The stopping rule, declared before the test

**If the best indicator's top decile holds less than 15% of the biggest
subsequent movers on the small-cap universe — a lift below 1.5× — the convex
thesis is dead and this stops.**

Large caps already give 1.65× on `ret(252)`, so this is a low bar and failing
it means small caps are worse than the universe already rejected. Operator
decision, 2026-09-22, recorded before the measurement existed.

## What is not yet decided

- **A partial exit.** Taking some off at a target and trailing the rest raises
  the win rate and costs part of the right tail. A real technique with a real
  price; the fraction would be swept rather than chosen.
- **The cost model.** Still the 5bp constant. `calc/spread.py` can now measure
  it per symbol, and the strategy should use the measured figure rather than
  a constant.
- **Entry timing.** The rule buys at the next open after ranking. Whether
  waiting for a pullback helps was tested on the old universe and hurt at every
  delay, but that was a different universe and a different ranking variable.

## How this gets tested

In this order, and no further than the first failure:

1. **Does the ranking hold the big movers?** Lift on the small-cap universe,
   against the 1.5× stopping rule above.
2. **Does it beat random names bought on the same days?** The date-matched
   benchmark, with the benchmark drawn from the same universe.
3. **Does it survive the measured spread** at the holding period the trailing
   stop actually produces?
4. **Does it hold up on data not used to build it?** Validation, once, with a
   signed pre-registration.
