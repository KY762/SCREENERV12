# Development-split battery — development

**Generated:** 2026-09-17 20:11 Eastern Daylight Time
**Window:** 2010-01-01 → 2015-12-31
**Symbols:** 307  
**Configurations tested:** 188

Development-split results carry **no evidential weight** (docs/03-HYPOTHESES.md §0.4). Nothing here confirms a hypothesis; it can only rule things out and suggest what to confirm elsewhere.

## Summary

| Experiment | Kind | Configs | Shape | Best expectancy | vs random | Selected |
| --- | --- | --- | --- | --- | --- | --- |
| `h1_exits` | parameter | 20 | **plateau** | +0.194R | 94th | `hold=10`, `stop_atr=2.5` |
| `h1_no_stop` | structural | 4 | **plateau** | +0.298R | 64th | `hold=10` |
| `h1_selection` | parameter | 12 | **plateau** | +0.146R | 95th | `rs_lookback=126`, `top_pct=0.2` |
| `h1_trend_filter` | structural | 2 | **plateau** | +0.073R | 89th | `trend_filter=True` |
| `h2_exits` | parameter | 20 | **none** | -0.052R | 61st | — |
| `h2_no_stop` | structural | 4 | **spike** | +0.457R | 69th | — |
| `h2_displacement` | structural | 4 | **spike** | +0.077R | 74th | — |
| `h3_exits` | parameter | 20 | **none** | -0.048R | 30th ⚠ below random | — |
| `h3_no_stop` | structural | 4 | **spike** | +0.033R | 3rd ⚠ below random | — |
| `h3_lookback` | structural | 4 | **none** | -0.009R | 15th ⚠ below random | — |
| `h1_exit_isolated` | structural | 2 | **spike** | +0.088R | 80th | — |
| `h2_exit_isolated` | structural | 2 | **spike** | +0.150R | 23rd ⚠ below random | — |
| `h3_exit_isolated` | structural | 2 | **spike** | +0.265R | 13th ⚠ below random | — |
| `h4_exit_isolated` | structural | 2 | **spike** | +0.294R | 11th ⚠ below random | — |
| `h5_exit_isolated` | structural | 2 | **plateau** | +0.249R | 73rd | `use_stop=True` |
| `h4_exits` | parameter | 20 | **none** | -0.049R | 35th ⚠ below random | — |
| `h4_no_stop` | structural | 4 | **plateau** | +2.837R | 96th | `time_limit=20` |
| `h5_momentum_canonical` | parameter | 9 | **spike** | +0.099R | 54th | — |
| `h5_skip_matters` | structural | 4 | **spike** | +0.113R | 45th ⚠ below random | — |
| `h5_no_stop` | structural | 3 | **plateau** | +1.368R | 52nd | `hold=63` |
| `h5_rebalance` | structural | 2 | **spike** | +0.126R | 45th ⚠ below random | — |
| `h7_squeeze_exits` | parameter | 20 | **spike** | +0.049R | 26th ⚠ below random | — |
| `h7_compression_depth` | parameter | 4 | **plateau** | +0.049R | 26th ⚠ below random | `squeeze_percentile=0.2` |
| `h7_no_stop` | structural | 4 | **plateau** | +0.030R | 20th ⚠ below random | `time_limit=40` |
| `h6_drift_exits` | parameter | 5 | **plateau** | +0.161R | 26th ⚠ below random | `time_limit=20` |
| `h6_reaction_size` | parameter | 5 | **plateau** | +0.661R | 89th | `reaction_pct=0.03` |
| `h6_entry_delay` | parameter | 4 | **plateau** | +0.255R | 31st ⚠ below random | `entry_delay=2` |

## `h1_exits` — H1

**Question:** Is there any hold horizon and stop width at which momentum rotation is profitable?

**Verdict — PLATEAU:** 7 of 12 positive cells sit inside a positive neighbourhood. Selected the plateau centre (hold=10, stop_atr=2.5, +0.067R) rather than the peak (hold=20, stop_atr=1.0, +0.194R) -- the peak's margin over its neighbours is the part least likely to survive.

| hold | stop_atr | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 1.0 | 235 | 29% | +0.194R | 94th | 1.31 | 21.2% | +42.5% | stop 135, time 70, stop_gap 30 |
| 20 | 1.5 | 247 | 40% | +0.176R | 95th | 1.34 | 17.2% | +49.3% | stop 128, time 101, stop_gap 18 |
| 20 | 2.5 | 277 | 52% | +0.112R | 91st | 1.27 | 17.1% | +41.3% | time 167, stop 100, stop_gap 10 |
| 20 | 2.0 | 274 | 46% | +0.094R | 86th | 1.23 | 16.9% | +38.3% | time 140, stop 124, stop_gap 10 |
| 20 | 3.0 | 278 | 53% | +0.069R | 82nd | 1.22 | 14.9% | +27.2% | time 187, stop 81, stop_gap 10 |
| 10 | 2.5 | 566 | 52% | +0.067R | 96th | 1.23 | 24.0% | +52.9% | time 436, stop 113, stop_gap 17 |
| 10 | 1.0 | 476 | 35% | +0.067R | 89th | 1.13 | 39.1% | +29.9% | stop 231, time 181, stop_gap 64 |
| 10 | 2.0 | 556 | 49% | +0.055R | 93rd | 1.15 | 31.5% | +42.1% | time 369, stop 161, stop_gap 26 |
| 10 | 1.5 | 510 | 42% | +0.053R | 89th | 1.15 | 39.0% | +34.9% | time 271, stop 205, stop_gap 34 |
| 10 | 3.0 | 568 | 52% | +0.038R | 93rd | 1.13 | 21.9% | +25.2% | time 463, stop 89, stop_gap 16 |
| 5 | 3.0 | 1141 | 50% | +0.002R | 69th | 1.07 | 25.6% | +16.7% | time 1052, stop 77, stop_gap 12 |
| 5 | 2.5 | 1139 | 50% | +0.002R | 71st | 1.06 | 30.4% | +16.4% | time 997, stop 120, stop_gap 22 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h1_no_stop` — H1

**Question:** Is the STOP what loses the money? Same entries, no stop.

**Held fixed:** `use_stop=False`

**Verdict — PLATEAU:** 4 of 4 positive cells sit inside a positive neighbourhood. Selected the plateau centre (hold=10, +0.005R) rather than the peak (hold=40, +0.298R) -- the peak's margin over its neighbours is the part least likely to survive.

| hold | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 129 | 46% | +0.298R | 64th | 1.33 | 27.1% | +36.4% | time 129 |
| 20 | 273 | 58% | +0.122R | 65th | 1.17 | 29.2% | +34.0% | time 273 |
| 10 | 555 | 53% | +0.005R | 88th | 1.09 | 33.2% | +25.7% | time 555 |
| 5 | 1112 | 50% | +0.001R | 66th | 1.06 | 39.2% | +20.3% | time 1112 |

## `h1_selection` — H1

**Question:** Does the momentum lookback or the selection cutoff matter, holding exits fixed?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — PLATEAU:** 3 of 9 positive cells sit inside a positive neighbourhood. Selected the plateau centre (rs_lookback=126, top_pct=0.2, +0.028R) rather than the peak (rs_lookback=252, top_pct=0.1, +0.146R) -- the peak's margin over its neighbours is the part least likely to survive.

| rs_lookback | top_pct | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 252 | 0.1 | 268 | 53% | +0.146R | 95th | 1.36 | 12.4% | +42.1% | time 181, stop 75, stop_gap 12 |
| 252 | 0.2 | 298 | 53% | +0.126R | 91st | 1.28 | 14.5% | +40.4% | time 198, stop 85, stop_gap 15 |
| 252 | 0.05 | 195 | 51% | +0.114R | 94th | 1.30 | 11.5% | +23.4% | time 129, stop 57, stop_gap 9 |
| 63 | 0.05 | 204 | 51% | +0.083R | 90th | 1.26 | 17.2% | +20.6% | time 131, stop 65, stop_gap 8 |
| 63 | 0.1 | 278 | 53% | +0.069R | 82nd | 1.22 | 14.9% | +27.2% | time 187, stop 81, stop_gap 10 |
| 63 | 0.2 | 305 | 52% | +0.055R | 78th | 1.18 | 16.6% | +26.5% | time 202, stop 89, stop_gap 14 |
| 126 | 0.2 | 308 | 52% | +0.028R | 86th | 1.10 | 22.6% | +15.4% | time 204, stop 79, stop_gap 25 |
| 21 | 0.05 | 204 | 51% | +0.020R | 70th | 1.10 | 13.1% | +9.1% | time 135, stop 61, stop_gap 8 |
| 126 | 0.1 | 280 | 52% | +0.007R | 84th | 1.06 | 22.7% | +8.5% | time 183, stop 76, stop_gap 21 |
| 126 | 0.05 | 204 | 50% | -0.053R | 76th | 0.94 | 22.9% | -6.2% | time 131, stop 58, stop_gap 15 |
| 21 | 0.1 | 278 | 49% | -0.064R | 36th ⚠ below random | 0.90 | 29.1% | -11.3% | time 187, stop 77, stop_gap 14 |
| 21 | 0.2 | 305 | 48% | -0.066R | 33rd ⚠ below random | 0.90 | 30.7% | -11.5% | time 201, stop 86, stop_gap 18 |

## `h1_trend_filter` — H1

**Question:** Does requiring an uptrend help, or is it just fewer trades?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — PLATEAU:** 2 of 2 positive cells sit inside a positive neighbourhood. Selected the plateau centre (trend_filter=True, +0.069R) rather than the peak (trend_filter=False, +0.073R) -- the peak's margin over its neighbours is the part least likely to survive.

| trend_filter | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 349 | 51% | +0.073R | 89th | 1.27 | 14.8% | +40.6% | time 233, stop 98, stop_gap 18 |
| True | 278 | 53% | +0.069R | 82nd | 1.22 | 14.9% | +27.2% | time 187, stop 81, stop_gap 10 |

## `h2_exits` — H2

**Question:** Is there a target and holding period at which the FVG continuation is profitable?

**Verdict — NONE:** no configuration of 20 produced positive expectancy. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 15 | 943 | 36% | -0.052R | 61st | 0.99 | 40.8% | -2.3% | stop 399, target 189, time 188, stop_gap 167 |
| 2.5 | 15 | 1039 | 37% | -0.077R | 37th ⚠ below random | 0.94 | 44.7% | -20.7% | stop 432, target 248, stop_gap 180, time 179 |
| 3.0 | 5 | 1650 | 41% | -0.100R | 30th ⚠ below random | 0.91 | 42.9% | -37.0% | time 676, stop 524, stop_gap 253, target 197 |
| 2.5 | 5 | 1719 | 42% | -0.105R | 23rd ⚠ below random | 0.89 | 51.0% | -43.5% | time 659, stop 523, stop_gap 269, target 268 |
| 2.5 | 10 | 1206 | 37% | -0.120R | 49th ⚠ below random | 0.93 | 45.4% | -28.0% | stop 465, time 294, target 245, stop_gap 202 |
| 1.5 | 10 | 1463 | 43% | -0.123R | 36th ⚠ below random | 0.91 | 49.8% | -33.9% | stop 504, target 503, time 228, stop_gap 228 |
| 1.5 | 5 | 1917 | 45% | -0.125R | 13th ⚠ below random | 0.85 | 58.6% | -54.6% | time 565, stop 555, target 520, stop_gap 277 |
| 2.0 | 20 | 987 | 38% | -0.126R | 29th ⚠ below random | 0.92 | 37.2% | -27.5% | stop 398, target 302, stop_gap 175, time 112 |
| 3.0 | 10 | 1170 | 34% | -0.126R | 18th ⚠ below random | 0.92 | 48.5% | -33.9% | stop 483, time 300, stop_gap 196, target 191 |
| 2.0 | 10 | 1299 | 39% | -0.131R | 34th ⚠ below random | 0.89 | 47.1% | -39.2% | stop 495, target 338, time 257, stop_gap 209 |
| 2.0 | 5 | 1818 | 43% | -0.133R | 15th ⚠ below random | 0.84 | 59.6% | -56.2% | time 626, stop 550, target 368, stop_gap 274 |
| 1.5 | 20 | 1180 | 43% | -0.137R | 12th ⚠ below random | 0.86 | 52.0% | -45.7% | target 449, stop 442, stop_gap 200, time 89 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h2_no_stop` — H2

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 2 of 4 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 144 | 59% | +0.457R | 69th | 1.22 | 33.7% | +27.2% | time 144 |
| 10 | 538 | 52% | +0.165R | 78th | 1.12 | 39.8% | +43.8% | time 538 |
| 5 | 1037 | 55% | -0.003R | 85th | 1.11 | 25.9% | +44.7% | time 1037 |
| 20 | 284 | 52% | -0.295R | 75th | 1.12 | 27.3% | +28.7% | time 284 |

## `h2_displacement` — H2

**Question:** Does the displacement filter contribute anything? 'off' is the null the specification leaves live.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — SPIKE:** 1 of 4 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| displacement | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 222 | 39% | +0.077R | 74th | 1.18 | 20.3% | +19.2% | stop 92, time 77, target 32, stop_gap 21 |
| 1.5 | 406 | 34% | -0.130R | 8th ⚠ below random | 0.81 | 43.9% | -37.2% | stop 190, time 107, target 63, stop_gap 46 |
| 1.0 | 625 | 31% | -0.152R | 9th ⚠ below random | 0.82 | 44.6% | -40.0% | stop 311, time 120, target 107, stop_gap 87 |
| None | 854 | 31% | -0.156R | 21st ⚠ below random | 0.91 | 48.0% | -31.6% | stop 405, target 176, stop_gap 147, time 126 |

## `h3_exits` — H3

**Question:** Is there a target and holding period at which sweep-reclaim is profitable?

**Verdict — NONE:** no configuration of 20 produced positive expectancy. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 5 | 1251 | 40% | -0.048R | 30th ⚠ below random | 0.94 | 38.3% | -19.7% | time 492, stop 396, stop_gap 199, target 164 |
| 3.0 | 10 | 1011 | 35% | -0.075R | 9th ⚠ below random | 0.89 | 46.4% | -34.8% | stop 415, time 218, target 193, stop_gap 185 |
| 2.5 | 5 | 1284 | 40% | -0.097R | 11th ⚠ below random | 0.88 | 49.2% | -38.2% | time 464, stop 413, target 204, stop_gap 203 |
| 2.0 | 5 | 1347 | 41% | -0.106R | 18th ⚠ below random | 0.91 | 46.5% | -32.9% | time 433, stop 414, target 286, stop_gap 214 |
| 1.5 | 5 | 1445 | 45% | -0.113R | 14th ⚠ below random | 0.91 | 47.4% | -33.1% | stop 427, target 423, time 381, stop_gap 214 |
| 2.0 | 10 | 1130 | 39% | -0.129R | 8th ⚠ below random | 0.88 | 47.7% | -39.8% | stop 438, target 315, stop_gap 197, time 180 |
| 2.5 | 20 | 864 | 33% | -0.138R | 1st ⚠ below random | 0.84 | 56.7% | -44.9% | stop 393, target 216, stop_gap 165, time 90 |
| 2.5 | 10 | 1066 | 36% | -0.140R | 6th ⚠ below random | 0.85 | 57.1% | -47.5% | stop 428, target 222, time 221, stop_gap 195 |
| 3.0 | 20 | 765 | 32% | -0.145R | 2nd ⚠ below random | 0.85 | 54.4% | -42.1% | stop 349, target 164, stop_gap 147, time 105 |
| 2.0 | 15 | 1035 | 38% | -0.154R | 11th ⚠ below random | 0.86 | 54.5% | -43.0% | stop 422, target 309, stop_gap 189, time 115 |
| 1.5 | 10 | 1253 | 42% | -0.156R | 5th ⚠ below random | 0.85 | 58.0% | -49.1% | stop 464, target 433, stop_gap 199, time 157 |
| 2.5 | 15 | 961 | 34% | -0.164R | 3rd ⚠ below random | 0.83 | 57.4% | -48.2% | stop 431, target 226, stop_gap 177, time 127 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h3_no_stop` — H3

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 1 of 4 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 466 | 49% | +0.033R | 3rd ⚠ below random | 0.84 | 43.5% | -34.6% | time 466 |
| 5 | 805 | 50% | -0.037R | 29th ⚠ below random | 0.98 | 33.6% | -4.9% | time 805 |
| 40 | 140 | 54% | -0.121R | 9th ⚠ below random | 0.83 | 47.7% | -25.7% | time 140 |
| 20 | 253 | 52% | -0.271R | 6th ⚠ below random | 0.85 | 50.6% | -29.3% | time 253 |

## `h3_lookback` — H3

**Question:** Which liquidity reference is swept? Varying the lookback is the cheapest version of that question.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — NONE:** no configuration of 4 produced positive expectancy. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| sweep_lookback | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 526 | 33% | -0.009R | 15th ⚠ below random | 0.95 | 25.8% | -10.2% | stop 255, target 120, stop_gap 85, time 66 |
| 5 | 892 | 33% | -0.053R | 2nd ⚠ below random | 0.91 | 39.0% | -28.0% | stop 412, target 202, stop_gap 162, time 116 |
| 10 | 765 | 32% | -0.145R | 2nd ⚠ below random | 0.85 | 54.4% | -42.1% | stop 349, target 164, stop_gap 147, time 105 |
| 40 | 9 | 44% | -0.242R | 10th ⚠ below random | 0.46 | 3.0% | -2.5% | time 5, stop 4 |

## `h1_exit_isolated` — H1

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — SPIKE:** 1 of 2 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

**Isolation held:** arms differ by 11.8% in trade count (760 vs 862), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 760 | 54% | +0.088R | 80th | 1.33 | 1.1% | +1.7% | time 760 |
| True | 862 | 41% | -0.011R | 37th ⚠ below random | 1.11 | 1.1% | +0.7% | time 413, stop 378, stop_gap 71 |

## `h2_exit_isolated` — H2

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — SPIKE:** 1 of 2 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 27.3% in trade count (3,980 vs 5,475). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 3980 | 55% | +0.150R | 23rd ⚠ below random | 1.22 | 3.5% | +4.9% | time 3980 |
| True | 5475 | 25% | -0.111R | 0th ⚠ below random | 0.98 | 2.5% | -0.3% | stop 2927, time 1537, stop_gap 1011 |

## `h3_exit_isolated` — H3

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — SPIKE:** 1 of 2 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 28.9% in trade count (2,069 vs 2,909). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 2069 | 53% | +0.265R | 13th ⚠ below random | 1.14 | 1.9% | +1.6% | time 2069 |
| True | 2909 | 24% | -0.091R | 0th ⚠ below random | 0.89 | 1.9% | -1.3% | stop 1600, time 761, stop_gap 548 |

## `h4_exit_isolated` — H4

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — SPIKE:** 1 of 2 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

**Isolation held:** arms differ by 19.1% in trade count (2,079 vs 2,571), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 2079 | 54% | +0.294R | 11th ⚠ below random | 1.14 | 2.2% | +1.7% | time 2079 |
| True | 2571 | 23% | -0.105R | 0th ⚠ below random | 0.93 | 1.7% | -0.7% | stop 1365, time 645, stop_gap 561 |

## `h5_exit_isolated` — H5

**Question:** H5 shows +0.055R yet ranks below random selection. With portfolio competition removed so both arms take the same signals, is that the entries or the exit?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=21`

**Verdict — PLATEAU:** 2 of 2 positive cells sit inside a positive neighbourhood. Selected the plateau centre (use_stop=True, +0.126R) rather than the peak (use_stop=False, +0.249R) -- the peak's margin over its neighbours is the part least likely to survive.

**Isolation held:** arms differ by 4.3% in trade count (355 vs 371), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 355 | 55% | +0.249R | 73rd | 1.37 | 0.5% | +0.9% | time 355 |
| True | 371 | 42% | +0.126R | 60th | 1.16 | 0.5% | +0.4% | time 173, stop 172, stop_gap 26 |

## `h4_exits` — H4

**Question:** Is there a target and holding period at which the inverted gap is profitable?

**Verdict — NONE:** no configuration of 20 produced positive expectancy. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 20 | 805 | 33% | -0.049R | 35th ⚠ below random | 0.99 | 46.6% | -1.9% | stop 357, target 186, stop_gap 170, time 92 |
| 3.0 | 15 | 885 | 33% | -0.073R | 18th ⚠ below random | 0.93 | 44.9% | -23.4% | stop 379, stop_gap 189, target 187, time 130 |
| 3.0 | 10 | 1010 | 35% | -0.078R | 6th ⚠ below random | 0.87 | 50.2% | -38.2% | stop 402, time 207, stop_gap 207, target 194 |
| 2.5 | 15 | 965 | 35% | -0.121R | 12th ⚠ below random | 0.88 | 50.3% | -36.5% | stop 412, target 236, stop_gap 195, time 122 |
| 2.0 | 20 | 997 | 37% | -0.122R | 10th ⚠ below random | 0.89 | 46.3% | -33.1% | stop 424, target 321, stop_gap 192, time 60 |
| 2.5 | 20 | 880 | 34% | -0.127R | 9th ⚠ below random | 0.89 | 50.0% | -33.2% | stop 393, target 225, stop_gap 179, time 83 |
| 3.0 | 5 | 1352 | 37% | -0.141R | 3rd ⚠ below random | 0.83 | 55.4% | -50.9% | time 475, stop 461, stop_gap 255, target 161 |
| 2.0 | 10 | 1174 | 38% | -0.152R | 3rd ⚠ below random | 0.84 | 54.1% | -47.2% | stop 450, target 325, stop_gap 230, time 169 |
| 2.0 | 15 | 1058 | 36% | -0.154R | 4th ⚠ below random | 0.85 | 50.4% | -43.8% | stop 439, target 316, stop_gap 209, time 94 |
| 2.0 | 5 | 1445 | 40% | -0.171R | 0th ⚠ below random | 0.79 | 60.7% | -57.9% | stop 467, time 403, target 303, stop_gap 272 |
| 2.5 | 10 | 1091 | 36% | -0.171R | 1st ⚠ below random | 0.79 | 61.5% | -57.4% | stop 446, target 230, stop_gap 219, time 196 |
| 2.5 | 5 | 1393 | 37% | -0.174R | 1st ⚠ below random | 0.79 | 59.4% | -57.8% | stop 472, time 440, stop_gap 268, target 213 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h4_no_stop` — H4

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 2 of 3 positive cells sit inside a positive neighbourhood. Selected the plateau centre (time_limit=20, +0.788R) rather than the peak (time_limit=40, +2.837R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 130 | 69% | +2.837R | 96th | 3.19 | 29.8% | +217.6% | time 130 |
| 20 | 249 | 56% | +0.788R | 50th | 1.22 | 34.9% | +46.2% | time 249 |
| 10 | 484 | 51% | +0.045R | 11th ⚠ below random | 0.91 | 48.3% | -24.2% | time 484 |
| 5 | 889 | 49% | -0.106R | 7th ⚠ below random | 0.85 | 44.9% | -39.2% | time 889 |

## `h5_momentum_canonical` — H5

**Question:** Does 12-1 momentum -- the version with decades of replication -- work where H1's 63-day no-skip variant did not?

**Held fixed:** `monthly_rebalance=True`, `stop_atr=3.0`

**Verdict — SPIKE:** 4 of 9 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| hold | top_pct | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 0.1 | 204 | 48% | +0.099R | 54th | 1.20 | 14.4% | +18.6% | time 134, stop 56, stop_gap 14 |
| 21 | 0.2 | 220 | 50% | +0.097R | 52nd | 1.22 | 14.8% | +20.8% | time 147, stop 60, stop_gap 13 |
| 126 | 0.05 | 77 | 30% | +0.075R | 13th ⚠ below random | 1.03 | 25.4% | +2.8% | stop 44, time 23, stop_gap 10 |
| 21 | 0.05 | 160 | 46% | +0.037R | 29th ⚠ below random | 1.06 | 11.8% | +4.4% | time 103, stop 46, stop_gap 11 |
| 63 | 0.05 | 105 | 32% | -0.015R | 9th ⚠ below random | 0.99 | 21.3% | +0.4% | stop 52, time 40, stop_gap 13 |
| 63 | 0.2 | 125 | 34% | -0.015R | 10th ⚠ below random | 0.99 | 22.6% | +0.2% | stop 64, time 49, stop_gap 12 |
| 126 | 0.1 | 82 | 29% | -0.029R | 16th ⚠ below random | 0.92 | 24.8% | -3.7% | stop 46, time 25, stop_gap 11 |
| 126 | 0.2 | 86 | 29% | -0.070R | 7th ⚠ below random | 0.85 | 28.6% | -9.4% | stop 49, time 26, stop_gap 11 |
| 63 | 0.1 | 118 | 31% | -0.075R | 5th ⚠ below random | 0.90 | 25.4% | -6.2% | stop 62, time 44, stop_gap 12 |

## `h5_skip_matters` — H5

**Question:** Is the skip month load-bearing, or decoration? skip=0 is H1's formation; skip=21 is the literature's.

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — SPIKE:** 2 of 4 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| mom_skip | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 117 | 37% | +0.113R | 45th ⚠ below random | 1.17 | 22.0% | +13.7% | stop 60, time 49, stop_gap 8 |
| 5 | 120 | 33% | +0.028R | 15th ⚠ below random | 1.05 | 21.0% | +4.8% | stop 58, time 49, stop_gap 13 |
| 0 | 125 | 33% | -0.030R | 4th ⚠ below random | 0.96 | 22.6% | -2.4% | stop 68, time 46, stop_gap 11 |
| 21 | 118 | 31% | -0.075R | 5th ⚠ below random | 0.90 | 25.4% | -6.2% | stop 62, time 44, stop_gap 12 |

## `h5_no_stop` — H5

**Question:** Does momentum survive without a stop, as the literature's version has none at all?

**Held fixed:** `top_pct=0.1`, `use_stop=False`

**Verdict — PLATEAU:** 3 of 3 positive cells sit inside a positive neighbourhood. Selected the plateau centre (hold=63, +0.697R) rather than the peak (hold=126, +1.368R) -- the peak's margin over its neighbours is the part least likely to survive.

| hold | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 126 | 42 | 64% | +1.368R | 52nd | 1.78 | 32.3% | +51.8% | time 42 |
| 63 | 82 | 59% | +0.697R | 55th | 1.66 | 23.7% | +64.7% | time 82 |
| 21 | 185 | 51% | +0.171R | 42nd ⚠ below random | 1.28 | 24.7% | +32.6% | time 185 |

## `h5_rebalance` — H5

**Question:** Monthly versus daily rebalancing -- does the documented frequency matter, or is it convention?

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — SPIKE:** 1 of 2 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| monthly_rebalance | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 161 | 40% | +0.126R | 45th ⚠ below random | 1.19 | 20.0% | +22.1% | stop 73, time 72, stop_gap 16 |
| True | 118 | 31% | -0.075R | 5th ⚠ below random | 0.90 | 25.4% | -6.2% | stop 62, time 44, stop_gap 12 |

## `h7_squeeze_exits` — H7

**Question:** Is there a target and holding period where range expansion after compression is profitable?

**Verdict — SPIKE:** 4 of 20 cells positive, but no positive cell has positive neighbours. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 20 | 306 | 53% | +0.049R | 26th ⚠ below random | 1.12 | 10.8% | +10.6% | time 253, stop 41, stop_gap 10, target 2 |
| 2.5 | 20 | 309 | 54% | +0.034R | 27th ⚠ below random | 1.08 | 10.9% | +6.9% | time 252, stop 40, stop_gap 12, target 5 |
| 1.5 | 20 | 312 | 55% | +0.025R | 21st ⚠ below random | 1.06 | 11.7% | +4.9% | time 238, stop 42, target 23, stop_gap 9 |
| 2.0 | 20 | 309 | 52% | +0.003R | 19th ⚠ below random | 1.00 | 12.0% | -0.9% | time 240, stop 47, target 11, stop_gap 11 |
| 2.5 | 5 | 883 | 50% | -0.011R | 10th ⚠ below random | 0.92 | 20.4% | -9.8% | time 859, stop 18, stop_gap 4, target 2 |
| 3.0 | 5 | 882 | 49% | -0.012R | 10th ⚠ below random | 0.92 | 20.4% | -10.8% | time 859, stop 18, stop_gap 4, target 1 |
| 2.0 | 5 | 883 | 49% | -0.012R | 9th ⚠ below random | 0.91 | 20.4% | -11.1% | time 858, stop 18, stop_gap 4, target 3 |
| 1.0 | 20 | 330 | 53% | -0.013R | 11th ⚠ below random | 0.93 | 13.8% | -7.0% | time 212, target 60, stop 47, stop_gap 11 |
| 1.5 | 5 | 883 | 49% | -0.014R | 10th ⚠ below random | 0.90 | 20.7% | -12.6% | time 855, stop 19, target 6, stop_gap 3 |
| 1.0 | 15 | 397 | 53% | -0.014R | 20th ⚠ below random | 0.94 | 22.5% | -5.9% | time 303, target 43, stop 41, stop_gap 10 |
| 1.0 | 10 | 543 | 50% | -0.017R | 8th ⚠ below random | 0.91 | 19.8% | -10.0% | time 463, target 38, stop 37, stop_gap 5 |
| 1.0 | 5 | 886 | 49% | -0.021R | 5th ⚠ below random | 0.86 | 21.0% | -17.1% | time 845, stop 20, target 18, stop_gap 3 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h7_compression_depth` — H7

**Question:** How quiet must it get first? A threshold that only works at one depth is a threshold fitted to noise.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — PLATEAU:** 2 of 3 positive cells sit inside a positive neighbourhood. Selected the plateau centre (squeeze_percentile=0.2, +0.049R) rather than the peak (squeeze_percentile=0.2, +0.049R) -- the peak's margin over its neighbours is the part least likely to survive.

| squeeze_percentile | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.2 | 306 | 53% | +0.049R | 26th ⚠ below random | 1.12 | 10.8% | +10.6% | time 253, stop 41, stop_gap 10, target 2 |
| 0.1 | 295 | 48% | +0.031R | 17th ⚠ below random | 1.10 | 11.3% | +8.8% | time 243, stop 41, stop_gap 9, target 2 |
| 0.3 | 310 | 55% | +0.016R | 19th ⚠ below random | 1.02 | 11.5% | +1.4% | time 255, stop 46, stop_gap 8, target 1 |
| 0.4 | 332 | 52% | -0.024R | 6th ⚠ below random | 0.96 | 19.1% | -5.0% | time 260, stop 58, stop_gap 10, target 4 |

## `h7_no_stop` — H7

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 2 positive cells sit inside a positive neighbourhood. Selected the plateau centre (time_limit=40, +0.014R) rather than the peak (time_limit=20, +0.030R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 282 | 54% | +0.030R | 20th ⚠ below random | 1.09 | 10.5% | +6.2% | time 282 |
| 40 | 145 | 53% | +0.014R | 18th ⚠ below random | 0.98 | 13.7% | -1.5% | time 145 |
| 5 | 873 | 49% | -0.014R | 10th ⚠ below random | 0.93 | 18.6% | -9.2% | time 873 |
| 10 | 514 | 50% | -0.026R | 9th ⚠ below random | 0.87 | 22.8% | -13.0% | time 514 |

## `h6_drift_exits` — H6

**Question:** Does price drift after an earnings filing, and over what horizon?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 3 of 4 positive cells sit inside a positive neighbourhood. Selected the plateau centre (time_limit=20, +0.051R) rather than the peak (time_limit=40, +0.161R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 96 | 60% | +0.161R | 26th ⚠ below random | 1.08 | 30.8% | +7.6% | time 96 |
| 10 | 172 | 55% | +0.072R | 65th | 1.12 | 23.9% | +9.9% | time 172 |
| 5 | 197 | 55% | +0.057R | 82nd | 1.12 | 19.8% | +8.8% | time 197 |
| 20 | 124 | 55% | +0.051R | 40th ⚠ below random | 1.01 | 23.3% | +1.0% | time 124 |
| 60 | 82 | 56% | -0.038R | 18th ⚠ below random | 0.91 | 39.3% | -8.1% | time 82 |

## `h6_reaction_size` — H6

**Question:** Does the size of the reaction sort the drift? The literature sorts on surprise; this substitutes the market's response.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 5 of 5 positive cells sit inside a positive neighbourhood. Selected the plateau centre (reaction_pct=0.03, +0.161R) rather than the peak (reaction_pct=0.05, +0.661R) -- the peak's margin over its neighbours is the part least likely to survive.

| reaction_pct | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.05 | 72 | 67% | +0.661R | 89th | 2.86 | 12.3% | +55.8% | time 72 |
| 0.0 | 115 | 60% | +0.516R | 86th | 1.73 | 18.2% | +62.4% | time 115 |
| 0.08 | 41 | 61% | +0.489R | 81st | 1.95 | 9.7% | +20.9% | time 41 |
| 0.03 | 96 | 60% | +0.161R | 26th ⚠ below random | 1.08 | 30.8% | +7.6% | time 96 |
| 0.02 | 99 | 59% | +0.126R | 14th ⚠ below random | 1.03 | 28.4% | +2.5% | time 99 |

## `h6_entry_delay` — H6

**Question:** How much of the drift is gone by the time we could act? A day-one edge that vanishes by day three is not tradeable.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 2 of 3 positive cells sit inside a positive neighbourhood. Selected the plateau centre (entry_delay=2, +0.255R) rather than the peak (entry_delay=2, +0.255R) -- the peak's margin over its neighbours is the part least likely to survive.

| entry_delay | Trades | Win% | Expectancy | vs random | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 96 | 54% | +0.255R | 31st ⚠ below random | 1.30 | 23.8% | +20.4% | time 96 |
| 3 | 95 | 53% | +0.226R | 34th ⚠ below random | 1.29 | 24.4% | +17.6% | time 95 |
| 1 | 96 | 60% | +0.161R | 26th ⚠ below random | 1.08 | 30.8% | +7.6% | time 96 |
| 5 | 96 | 52% | -0.149R | 7th ⚠ below random | 0.79 | 24.1% | -16.4% | time 96 |

## Caveats attached to every number above

- The universe is **today's** large caps. No delisted company is present, so every result is inflated by an unknown amount (ADR 0002).
- Ambiguous bars resolve to the stop, gaps fill at the open, and slippage is charged both ways. Those understate results.
- Random-selection percentiles, where present, are the comparison that matters: beating zero is not the test, beating random long exposure is.
