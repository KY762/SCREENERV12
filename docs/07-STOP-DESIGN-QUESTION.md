# The stop is costing more than it protects — provisionally

**Date:** 2026-08-21
**Status:** OPEN QUESTION. One measurement, on the development split, with a confound
identified below. Nothing here is settled, and nothing here changes how anyone trades.

---

## 1. What was measured

H3 (sweep-and-reclaim), development split 2010–2015, identical entry signals, identical
position sizing. The only change was removing the price stop:

| | Stop at swing low − 0.1 ATR | No price stop, 20-day time exit |
| --- | --- | --- |
| Expectancy | −0.121R | **+0.485R** |
| Win rate | 40.4% | 56.7% |
| Return | −33.4% | **+8.9%** |
| Max drawdown | 45.9% | **28.9%** |
| Trades | 651 | 203 |
| Exits | mixed | **100% time** |

Not one trade in the unstopped arm reached a profit target. Every position closed on the
clock.

Across the earlier parameter surfaces the same gradient appeared twice, independently:
in H1, wider stops were monotonically less bad (−0.553R at 1.0 ATR → −0.042R at 3.0 ATR);
in H3, larger targets were monotonically less bad (−0.224R at 1R → −0.019R at 3R).
**Three separate measurements point the same way: cutting sooner loses more.**

## 2. The confound, stated before the finding is used

The trade count fell from 651 to 203, and cash rejections rose from 239 to 605. Positions
held 20 days occupy the five available slots for 20 days, so **the two arms did not take
the same signals.** The comparison measures the exit rule *and* which trades there was room
for, mixed together.

Sizing was identical (both arms size off the same stop distance; only the exit differs), so
that much is clean. Selection is not.

`h1_exit_isolated` … `h4_exit_isolated` in the battery remove the confound by shrinking
per-trade risk until nearly every signal fits, so both arms take the same trades. **Until
those run, §1 is suggestive, not established.**

### A related discovery about the sizing rules

Making that isolation work surfaced something about the specification itself. At 1% risk
per trade with a 2-ATR stop:

| Price | ATR% | Stop distance | Position as % of equity |
| --- | --- | --- | --- |
| $100 | 1.5% | $3.00 | **33%** |
| $100 | 2.0% | $4.00 | **25%** |
| $300 | 1.8% | $10.80 | **27%** |

The 25% concentration cap therefore binds on **almost every trade**, and four positions
exhaust a $10,000 cash account. "Max 5 concurrent positions" and "max 5% total open risk"
are never the constraint that stops anything — the concentration cap and the cash balance
are. The portfolio in practice is roughly four names at a quarter of the account each,
which is a materially more concentrated design than the profile reads as describing.

That is an operator decision, not a bug, and it is recorded in §5.

## 3. The uncomfortable part

The trader profile is explicit that missing stops caused the documented losses. The
platform was built so that a stop is mandatory and cannot be overridden. And the first
measurement says the stop is what loses the money.

**These do not actually contradict each other, and the difference matters:**

| Journal | Backtest |
| --- | --- |
| Leveraged futures | Unleveraged long equity |
| **No exit at all** — position held through unbounded loss | Exit at 20 days, guaranteed |
| Risk of account destruction | Risk bounded by position size and time |
| Size escalated after losses | Size fixed by rule |

The unstopped arm is **not** "no risk management." It has a hard time exit, fixed position
sizing, a concentration cap, and no leverage. Risk is bounded by *time and size* instead of
by *price*. The finding is narrow and should be stated narrowly:

> On unleveraged long equity positions in a rising market, a price stop set inside the
> instrument's normal noise converts recoverable drawdowns into realised losses, and a
> time-based exit did better over 2010–2015.

That is a claim about **which kind** of risk control, not **whether** to have one. Nothing
here supports holding a losing leveraged position and hoping.

## 4. Why the mechanism is plausible

A 2-ATR stop on a stock whose daily range is 1 ATR is roughly two average days of adverse
movement. Ordinary noise reaches it regularly. Each time it does, a paper loss becomes a
real one, and equity drops, and the next position is sized off the smaller equity.

Meanwhile the target caps the winners. The combination — cut the losers early, cap the
winners — inverts the asymmetry that makes long equity profitable over multi-day horizons
in a rising market. That the unstopped arm ALSO had a lower maximum drawdown (28.9% vs
45.9%) is the tell: the stops were not reducing risk, they were realising it and adding
churn.

**Also unresolved:** the unstopped arm still landed at the 5.7th percentile of random
selection. Removing the stop made it profitable in absolute terms and still worse than
picking at random. Two independent problems — a costly exit design and an entry rule that
does not select well — and fixing one does not fix the other.

## 5. What must happen before any of this is believed

1. **Run the isolation experiments.** Same signals in both arms. If the effect survives, it
   is about exits. If it collapses, §1 was measuring slot competition.
2. **Reconcile the sizing rules** (§2). Three options, all defensible, and the choice is
   the operator's: cut risk per trade to ~0.5% so five positions fit; cut the concentration
   cap to 20% so 5 × 20% = 100%; or accept ~4 concentrated positions and correct the
   profile to say so.
3. **Do not act on this.** It is one development-split measurement. Development results
   carry no evidential weight by construction (`03` §0.4) — that is the whole reason it is
   safe to explore there.
4. **If it survives validation**, the specification changes to a *time-stop-primary* design
   with a wide catastrophic price stop, and that change is recorded as what it is: a
   revision made on evidence, on a split where evidence counts.

## 6. What does not change

The mandatory-stop rule stays in `calc.sizing` until something survives validation. A
research finding on six years of one universe does not get to remove the control that
exists because of documented, repeated, real losses — and the profile's failure mode was
*no exit at all*, which is not what any of this tests.
