# Development-split battery — development

**Generated:** 2026-09-22 21:08 Eastern Daylight Time
**Window:** 2010-01-01 → 2015-12-31
**Symbols:** 1020  
**Configurations tested:** 180
**Universe:** `sp500_pit` — point-in-time membership  
**Quarantined and excluded:** 25 (ACS, AYE, BBBY, BBT, CA, CAM, CPWR, CSRA, EMC, EP, FB, GENZ, GR, INFO, JAVA, KG, NFX, PARA, PBG, PCL, RX, SHLD, SII, SPLS, UST)  

Those symbols' stored series is not the company that was in the index — see `data/reference/universe_quarantine.csv` for the reason on each. Results generated before 2026-09-19 did not exclude them and are not comparable.

Development-split results carry **no evidential weight** (docs/03-HYPOTHESES.md §0.4). Nothing here confirms a hypothesis; it can only rule things out and suggest what to confirm elsewhere.

## Summary

| Experiment | Kind | Configs | Shape | Best expectancy | vs random (same days) | vs random (any day) | Selected |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `h1_exits` | parameter | 10 | **none** | -0.205R | 3rd ⚠ below random | 2nd ⚠ below random | — |
| `h1_no_stop` | structural | 3 | **none** | -0.378R | 0th ⚠ below random | 1st ⚠ below random | — |
| `h1_selection` | parameter | 12 | **spike** | +0.204R | 89th | 70th | — |
| `h1_entry_delay` | structural | 3 | **none** | -0.257R | 0th ⚠ below random | 1st ⚠ below random | — |
| `h1_trend_filter` | structural | 2 | **none** | -0.247R | 1st ⚠ below random | 1st ⚠ below random | — |
| `h2_exits` | parameter | 20 | **none** | -0.111R | 7th ⚠ below random | 4th ⚠ below random | — |
| `h2_no_stop` | structural | 4 | **spike** | +1.236R | 82nd | 66th | — |
| `h2_displacement` | structural | 4 | **spike** | +0.066R | 86th | 62nd | — |
| `h3_exits` | parameter | 20 | **none** | -0.063R | 1st ⚠ below random | 9th ⚠ below random | — |
| `h3_no_stop` | structural | 4 | **spike** | +0.754R | 25th ⚠ below random | 17th ⚠ below random | — |
| `h3_lookback` | structural | 4 | **spike** | +0.040R | 72nd | 34th ⚠ below random | — |
| `h1_exit_isolated` | structural | 2 | **none** | -0.034R | 17th ⚠ below random | 0th ⚠ below random | — |
| `h2_exit_isolated` | structural | 2 | **indistinct** | +0.252R | 23rd ⚠ below random | 0th ⚠ below random | — |
| `h3_exit_isolated` | structural | 2 | **indistinct** | +0.602R | 71st | 0th ⚠ below random | — |
| `h4_exit_isolated` | structural | 2 | **indistinct** | +0.270R | 7th ⚠ below random | 0th ⚠ below random | — |
| `h5_exit_isolated` | structural | 2 | **indistinct** | +0.070R | 61st | 4th ⚠ below random | — |
| `h4_exits` | parameter | 20 | **none** | -0.111R | 9th ⚠ below random | 4th ⚠ below random | — |
| `h4_no_stop` | structural | 4 | **plateau** | +1.806R | 90th | 62nd | `time_limit=5` |
| `h5_momentum_canonical` | parameter | 9 | **none** | +0.344R | 29th ⚠ below random | 28th ⚠ below random | — |
| `h5_skip_matters` | structural | 4 | **none** | -0.012R | 27th ⚠ below random | 39th ⚠ below random | — |
| `h5_no_stop` | structural | 3 | **none** | +1.103R | 40th ⚠ below random | 43rd ⚠ below random | — |
| `h5_rebalance` | structural | 2 | **none** | -0.507R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h7_squeeze_exits` | parameter | 20 | **none** | -0.190R | 37th ⚠ below random | 20th ⚠ below random | — |
| `h7_compression_depth` | parameter | 4 | **plateau** | +0.114R | 63rd | 48th ⚠ below random | `squeeze_percentile=0.4` |
| `h7_no_stop` | structural | 4 | **none** | -0.200R | 15th ⚠ below random | 10th ⚠ below random | — |
| `h6_drift_exits` | parameter | 5 | **plateau** | +0.951R | 72nd | 60th | `time_limit=5` |
| `h6_reaction_size` | parameter | 5 | **plateau** | +0.633R | 92nd | 71st | `reaction_pct=0.03` |
| `h6_entry_delay` | parameter | 4 | **plateau** | +0.637R | 99th | 62nd | `entry_delay=2` |

## `h1_exits` — H1

**Question:** Is there any hold horizon and stop width at which momentum rotation is profitable?

**Verdict — NONE:** no configuration of 10 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | stop_atr | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 3.0 | 548 | 52% | -0.205R | 3rd ⚠ below random | 2nd ⚠ below random | 0.92 | 28.5% | -12.4% | time 454, stop 84, stop_gap 10 |
| 20 | 3.0 | 267 | 48% | -0.257R | 0th ⚠ below random | 1st ⚠ below random | 0.87 | 28.5% | -14.6% | time 182, stop 77, stop_gap 8 |
| 10 | 2.5 | 530 | 50% | -0.274R | 1st ⚠ below random | 1st ⚠ below random | 0.89 | 32.9% | -17.0% | time 401, stop 115, stop_gap 14 |
| 20 | 2.5 | 257 | 45% | -0.363R | 1st ⚠ below random | 1st ⚠ below random | 0.82 | 31.4% | -20.5% | time 148, stop 97, stop_gap 12 |
| 10 | 2.0 | 478 | 47% | -0.413R | 0th ⚠ below random | 1st ⚠ below random | 0.82 | 33.0% | -28.2% | time 309, stop 154, stop_gap 15 |
| 10 | 1.5 | 533 | 44% | -0.455R | 1st ⚠ below random | 5th ⚠ below random | 0.95 | 32.4% | -9.0% | time 294, stop 204, stop_gap 35 |
| 20 | 2.0 | 237 | 40% | -0.531R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 33.8% | -27.4% | time 117, stop 105, stop_gap 15 |
| 20 | 1.5 | 262 | 37% | -0.572R | 3rd ⚠ below random | 2nd ⚠ below random | 0.86 | 33.6% | -16.3% | stop 131, time 111, stop_gap 20 |
| 10 | 1.0 | 528 | 36% | -0.700R | 2nd ⚠ below random | 5th ⚠ below random | 0.94 | 28.5% | -11.5% | stop 242, time 218, stop_gap 68 |
| 20 | 1.0 | 261 | 29% | -0.850R | 15th ⚠ below random | 4th ⚠ below random | 0.85 | 32.0% | -15.7% | stop 137, time 82, stop_gap 42 |

## `h1_no_stop` — H1

**Question:** Is the STOP what loses the money? Same entries, no stop.

**Held fixed:** `use_stop=False`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 479 | 52% | -0.378R | 0th ⚠ below random | 1st ⚠ below random | 0.86 | 38.2% | -22.5% | time 479 |
| 20 | 237 | 53% | -0.411R | 0th ⚠ below random | 1st ⚠ below random | 0.91 | 36.1% | -12.1% | time 237 |
| 40 | 115 | 53% | -0.905R | 0th ⚠ below random | 0th ⚠ below random | 0.79 | 37.5% | -19.0% | time 115 |

## `h1_selection` — H1

**Question:** Does the momentum lookback or the selection cutoff matter, holding exits fixed?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — SPIKE:** 6 of 12 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| rs_lookback | top_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 0.05 | 247 | 53% | +0.204R | 89th | 70th | 1.65 | 8.8% | +60.0% | time 196, stop 46, stop_gap 5 |
| 21 | 0.1 | 258 | 52% | +0.196R | 74th | 63rd | 1.63 | 10.8% | +60.2% | time 206, stop 47, stop_gap 5 |
| 21 | 0.2 | 266 | 53% | +0.194R | 66th | 61st | 1.61 | 10.8% | +61.1% | time 213, stop 48, stop_gap 5 |
| 126 | 0.2 | 275 | 53% | +0.121R | 53rd | 41st ⚠ below random | 1.37 | 11.3% | +37.8% | time 199, stop 67, stop_gap 9 |
| 126 | 0.1 | 271 | 53% | +0.120R | 52nd | 38th ⚠ below random | 1.36 | 10.4% | +36.5% | time 196, stop 66, stop_gap 9 |
| 126 | 0.05 | 259 | 52% | +0.110R | 69th | 36th ⚠ below random | 1.33 | 10.8% | +32.4% | time 186, stop 64, stop_gap 9 |
| 252 | 0.1 | 300 | 55% | +0.089R | 29th ⚠ below random | 17th ⚠ below random | 1.22 | 10.1% | +27.2% | time 210, stop 81, stop_gap 9 |
| 252 | 0.2 | 300 | 54% | +0.077R | 22nd ⚠ below random | 18th ⚠ below random | 1.18 | 11.0% | +22.9% | time 209, stop 82, stop_gap 9 |
| 252 | 0.05 | 284 | 54% | +0.058R | 19th ⚠ below random | 9th ⚠ below random | 1.13 | 10.7% | +15.5% | time 196, stop 79, stop_gap 9 |
| 63 | 0.2 | 273 | 48% | -0.256R | 0th ⚠ below random | 0th ⚠ below random | 0.86 | 29.1% | -15.8% | time 186, stop 79, stop_gap 8 |
| 63 | 0.1 | 267 | 48% | -0.257R | 0th ⚠ below random | 1st ⚠ below random | 0.87 | 28.5% | -14.6% | time 182, stop 77, stop_gap 8 |
| 63 | 0.05 | 256 | 48% | -0.271R | 1st ⚠ below random | 1st ⚠ below random | 0.85 | 30.8% | -16.0% | time 174, stop 74, stop_gap 8 |

## `h1_entry_delay` — H1

**Question:** Does waiting after the ranking help? Momentum's return is reported absent in the weeks after ranking (Jegadeesh & Titman 1993). Delayed names are re-checked at the last close before the buy and dropped if they no longer rank or trend, so this measures waiting AND re-selection together.

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| entry_delay | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 267 | 48% | -0.257R | 0th ⚠ below random | 1st ⚠ below random | 0.87 | 28.5% | -14.6% | time 182, stop 77, stop_gap 8 |
| 3 | 258 | 49% | -0.352R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 33.9% | -25.5% | time 174, stop 70, stop_gap 14 |
| 6 | 250 | 44% | -0.481R | 0th ⚠ below random | 0th ⚠ below random | 0.63 | 42.2% | -37.8% | time 157, stop 77, stop_gap 16 |

## `h1_trend_filter` — H1

**Question:** Does requiring an uptrend help, or is it just fewer trades?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — NONE:** neither arm produced positive expectancy -- trend_filter=False at -0.247R versus trend_filter=True at -0.257R, a gap of +0.010R. The comparison still says which is less bad, but nothing here is selectable.

| trend_filter | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 277 | 48% | -0.247R | 1st ⚠ below random | 1st ⚠ below random | 0.88 | 29.0% | -13.7% | time 186, stop 81, stop_gap 10 |
| True | 267 | 48% | -0.257R | 0th ⚠ below random | 1st ⚠ below random | 0.87 | 28.5% | -14.6% | time 182, stop 77, stop_gap 8 |

## `h2_exits` — H2

**Question:** Is there a target and holding period at which the FVG continuation is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 10 | 1291 | 37% | -0.111R | 7th ⚠ below random | 4th ⚠ below random | 0.92 | 36.9% | -27.0% | stop 501, time 364, stop_gap 222, target 204 |
| 2.5 | 10 | 1358 | 38% | -0.112R | 1st ⚠ below random | 2nd ⚠ below random | 0.90 | 42.5% | -34.2% | stop 497, time 359, target 266, stop_gap 236 |
| 2.0 | 10 | 1484 | 40% | -0.117R | 9th ⚠ below random | 6th ⚠ below random | 0.92 | 36.8% | -29.1% | stop 542, target 386, time 316, stop_gap 240 |
| 3.0 | 15 | 1065 | 34% | -0.119R | 4th ⚠ below random | 5th ⚠ below random | 0.94 | 35.9% | -19.9% | stop 449, time 224, stop_gap 196, target 196 |
| 3.0 | 5 | 1940 | 41% | -0.122R | 1st ⚠ below random | 4th ⚠ below random | 0.91 | 43.8% | -37.2% | time 816, stop 602, stop_gap 317, target 205 |
| 2.5 | 5 | 2014 | 42% | -0.126R | 2nd ⚠ below random | 3rd ⚠ below random | 0.90 | 46.8% | -39.3% | time 789, stop 629, stop_gap 310, target 286 |
| 3.0 | 20 | 916 | 34% | -0.126R | 7th ⚠ below random | 3rd ⚠ below random | 0.95 | 34.5% | -14.2% | stop 397, target 176, time 172, stop_gap 171 |
| 2.0 | 5 | 2107 | 43% | -0.136R | 3rd ⚠ below random | 4th ⚠ below random | 0.92 | 44.3% | -35.8% | time 748, stop 627, target 402, stop_gap 330 |
| 2.0 | 20 | 1135 | 38% | -0.138R | 8th ⚠ below random | 5th ⚠ below random | 0.94 | 38.4% | -19.7% | stop 467, target 336, stop_gap 195, time 137 |
| 2.5 | 20 | 1017 | 36% | -0.140R | 9th ⚠ below random | 8th ⚠ below random | 0.93 | 41.0% | -21.0% | stop 426, target 238, stop_gap 194, time 159 |
| 2.0 | 15 | 1235 | 39% | -0.145R | 5th ⚠ below random | 4th ⚠ below random | 0.93 | 36.5% | -24.1% | stop 480, target 341, stop_gap 221, time 193 |
| 2.5 | 15 | 1089 | 37% | -0.145R | 4th ⚠ below random | 2nd ⚠ below random | 0.91 | 45.7% | -28.0% | stop 430, target 235, time 219, stop_gap 205 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h2_no_stop` — H2

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 168 | 62% | +1.236R | 82nd | 66th | 1.88 | 21.4% | +128.3% | time 168 |
| 20 | 318 | 53% | +0.298R | 8th ⚠ below random | 8th ⚠ below random | 1.16 | 23.7% | +26.7% | time 318 |
| 10 | 471 | 52% | +0.157R | 19th ⚠ below random | 19th ⚠ below random | 1.08 | 24.8% | +16.4% | time 471 |
| 5 | 1194 | 51% | +0.090R | 37th ⚠ below random | 22nd ⚠ below random | 1.07 | 18.7% | +27.5% | time 1194 |

## `h2_displacement` — H2

**Question:** Does the displacement filter contribute anything? 'off' is the null the specification leaves live.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| displacement | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 380 | 43% | +0.066R | 86th | 62nd | 1.21 | 13.2% | +36.5% | time 166, stop 147, target 36, stop_gap 31 |
| 1.5 | 550 | 39% | -0.010R | 35th ⚠ below random | 22nd ⚠ below random | 1.07 | 30.5% | +14.6% | stop 237, time 177, target 78, stop_gap 58 |
| 1.0 | 707 | 37% | -0.034R | 20th ⚠ below random | 15th ⚠ below random | 1.02 | 30.7% | +5.5% | stop 306, time 178, target 120, stop_gap 103 |
| None | 916 | 34% | -0.126R | 7th ⚠ below random | 3rd ⚠ below random | 0.95 | 34.5% | -14.2% | stop 397, target 176, time 172, stop_gap 171 |

## `h3_exits` — H3

**Question:** Is there a target and holding period at which sweep-reclaim is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 5 | 1670 | 41% | -0.063R | 1st ⚠ below random | 9th ⚠ below random | 0.96 | 34.2% | -15.0% | time 645, stop 525, stop_gap 285, target 215 |
| 2.5 | 20 | 1019 | 37% | -0.063R | 11th ⚠ below random | 12th ⚠ below random | 1.02 | 21.5% | +5.5% | stop 416, target 277, stop_gap 205, time 121 |
| 2.5 | 5 | 1729 | 43% | -0.072R | 1st ⚠ below random | 11th ⚠ below random | 0.95 | 32.0% | -18.3% | time 616, stop 535, stop_gap 290, target 288 |
| 3.0 | 20 | 985 | 33% | -0.083R | 0th ⚠ below random | 0th ⚠ below random | 0.92 | 35.9% | -22.1% | stop 436, target 231, stop_gap 201, time 117 |
| 2.0 | 5 | 1817 | 44% | -0.086R | 3rd ⚠ below random | 12th ⚠ below random | 0.96 | 29.3% | -18.2% | time 569, stop 532, target 405, stop_gap 311 |
| 2.5 | 10 | 1330 | 38% | -0.092R | 4th ⚠ below random | 6th ⚠ below random | 0.95 | 37.7% | -18.0% | stop 498, target 296, time 280, stop_gap 256 |
| 3.0 | 10 | 1281 | 36% | -0.092R | 1st ⚠ below random | 2nd ⚠ below random | 0.92 | 41.6% | -25.2% | stop 486, time 293, stop_gap 272, target 230 |
| 2.0 | 10 | 1437 | 41% | -0.103R | 2nd ⚠ below random | 8th ⚠ below random | 0.94 | 36.6% | -21.1% | stop 520, target 412, stop_gap 264, time 241 |
| 1.5 | 5 | 1968 | 47% | -0.104R | 0th ⚠ below random | 13th ⚠ below random | 0.93 | 35.4% | -30.3% | target 594, stop 558, time 510, stop_gap 306 |
| 2.5 | 15 | 1158 | 36% | -0.105R | 0th ⚠ below random | 1st ⚠ below random | 0.93 | 30.6% | -21.1% | stop 471, target 285, stop_gap 229, time 173 |
| 1.5 | 10 | 1590 | 45% | -0.108R | 3rd ⚠ below random | 7th ⚠ below random | 0.95 | 36.0% | -18.5% | target 588, stop 525, stop_gap 276, time 201 |
| 3.0 | 15 | 1057 | 33% | -0.113R | 0th ⚠ below random | 2nd ⚠ below random | 0.92 | 33.3% | -24.1% | stop 441, target 224, stop_gap 221, time 171 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h3_no_stop` — H3

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 153 | 56% | +0.754R | 25th ⚠ below random | 17th ⚠ below random | 1.44 | 22.2% | +46.9% | time 153 |
| 10 | 535 | 56% | +0.333R | 26th ⚠ below random | 22nd ⚠ below random | 1.19 | 19.2% | +42.8% | time 535 |
| 20 | 289 | 58% | +0.304R | 9th ⚠ below random | 11th ⚠ below random | 1.14 | 19.0% | +21.2% | time 289 |
| 5 | 1024 | 54% | +0.162R | 63rd | 51st | 1.15 | 24.1% | +55.1% | time 1024 |

## `h3_lookback` — H3

**Question:** Which liquidity reference is swept? Varying the lookback is the cheapest version of that question.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| sweep_lookback | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 44 | 43% | +0.040R | 72nd | 34th ⚠ below random | 1.06 | 5.7% | +0.9% | time 27, stop 14, target 2, stop_gap 1 |
| 20 | 627 | 37% | -0.025R | 9th ⚠ below random | 25th ⚠ below random | 1.06 | 21.6% | +14.6% | stop 255, target 137, stop_gap 126, time 109 |
| 5 | 1034 | 35% | -0.039R | 10th ⚠ below random | 10th ⚠ below random | 1.04 | 23.1% | +15.1% | stop 421, target 248, stop_gap 230, time 135 |
| 10 | 985 | 33% | -0.083R | 0th ⚠ below random | 0th ⚠ below random | 0.92 | 35.9% | -22.1% | stop 436, target 231, stop_gap 201, time 117 |

## `h1_exit_isolated` — H1

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — NONE:** neither arm produced positive expectancy -- use_stop=False at -0.034R versus use_stop=True at -0.099R, a gap of +0.065R. The comparison still says which is less bad, but nothing here is selectable.

**Isolation held:** arms differ by 0.1% in trade count (1,272 vs 1,273), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 1272 | 53% | -0.034R | 17th ⚠ below random | 0th ⚠ below random | 1.03 | 1.2% | +0.2% | time 1272 |
| True | 1273 | 41% | -0.099R | 1st ⚠ below random | 0th ⚠ below random | 0.93 | 0.8% | -0.4% | time 642, stop 552, stop_gap 79 |

## `h2_exit_isolated` — H2

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.252R versus use_stop=True at -0.068R, a gap of +0.320R, but the arms differ by 27.5% in trade count (11,432 vs 15,777). They did not take the same signals, so this measures exit design and selection together and the gap is not attributable to the exit rule.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 27.5% in trade count (11,432 vs 15,777). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 11432 | 55% | +0.252R | 23rd ⚠ below random | 0th ⚠ below random | 1.17 | 7.8% | +8.8% | time 11432 |
| True | 15777 | 26% | -0.068R | 0th ⚠ below random | 0th ⚠ below random | 0.98 | 6.3% | -0.7% | stop 8392, time 4475, stop_gap 2910 |

## `h3_exit_isolated` — H3

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.602R versus use_stop=True at +0.043R, a gap of +0.560R, but the arms differ by 29.7% in trade count (5,954 vs 8,468). They did not take the same signals, so this measures exit design and selection together and the gap is not attributable to the exit rule.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 29.7% in trade count (5,954 vs 8,468). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 5954 | 56% | +0.602R | 71st | 0th ⚠ below random | 1.31 | 4.0% | +8.0% | time 5954 |
| True | 8468 | 26% | +0.043R | 0th ⚠ below random | 0th ⚠ below random | 1.02 | 2.7% | +0.5% | stop 4530, time 2350, stop_gap 1588 |

## `h4_exit_isolated` — H4

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.270R versus use_stop=True at -0.072R, a gap of +0.342R, but that gap is 1.4 standard errors on mean per-trade return (paired over 5,805 shared signals, month-clustered) -- under the 2 required.

**Isolation held:** arms differ by 19.0% in trade count (5,884 vs 7,260), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 5884 | 55% | +0.270R | 7th ⚠ below random | 0th ⚠ below random | 1.12 | 4.4% | +3.2% | time 5884 |
| True | 7260 | 24% | -0.072R | 0th ⚠ below random | 0th ⚠ below random | 0.92 | 3.8% | -1.7% | stop 3899, time 1881, stop_gap 1480 |

## `h5_exit_isolated` — H5

**Question:** H5 shows +0.055R yet ranks below random selection. With portfolio competition removed so both arms take the same signals, is that the entries or the exit?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=21`

**Verdict — INDISTINCT:** use_stop=False at +0.070R versus use_stop=True at -0.002R, a gap of +0.073R, but that gap is 1.1 standard errors on mean per-trade return (paired over 1,098 shared signals, month-clustered) -- under the 2 required.

**Isolation held:** arms differ by 4.9% in trade count (1,103 vs 1,160), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 1103 | 57% | +0.070R | 61st | 4th ⚠ below random | 1.25 | 1.4% | +1.4% | time 1103 |
| True | 1160 | 44% | -0.002R | 27th ⚠ below random | 4th ⚠ below random | 1.12 | 1.3% | +0.7% | time 578, stop 515, stop_gap 67 |

## `h4_exits` — H4

**Question:** Is there a target and holding period at which the inverted gap is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 5 | 1505 | 39% | -0.111R | 9th ⚠ below random | 4th ⚠ below random | 0.90 | 40.7% | -32.1% | time 541, stop 495, stop_gap 276, target 193 |
| 2.5 | 15 | 1292 | 35% | -0.132R | 1st ⚠ below random | 2nd ⚠ below random | 0.88 | 48.9% | -38.0% | stop 526, target 356, stop_gap 278, time 132 |
| 2.5 | 5 | 1525 | 40% | -0.134R | 3rd ⚠ below random | 2nd ⚠ below random | 0.88 | 43.4% | -39.4% | time 516, stop 477, stop_gap 282, target 250 |
| 3.0 | 15 | 1215 | 32% | -0.159R | 0th ⚠ below random | 0th ⚠ below random | 0.82 | 53.5% | -51.9% | stop 535, target 266, stop_gap 258, time 156 |
| 3.0 | 10 | 1382 | 35% | -0.162R | 0th ⚠ below random | 0th ⚠ below random | 0.87 | 45.6% | -42.2% | stop 552, stop_gap 303, time 273, target 254 |
| 2.0 | 15 | 1413 | 38% | -0.169R | 2nd ⚠ below random | 3rd ⚠ below random | 0.91 | 42.2% | -33.0% | stop 555, target 448, stop_gap 288, time 122 |
| 1.5 | 5 | 1600 | 44% | -0.172R | 0th ⚠ below random | 0th ⚠ below random | 0.81 | 55.5% | -54.4% | stop 465, target 462, time 403, stop_gap 270 |
| 2.5 | 20 | 1174 | 33% | -0.172R | 0th ⚠ below random | 1st ⚠ below random | 0.88 | 49.1% | -38.1% | stop 504, target 321, stop_gap 264, time 85 |
| 2.5 | 10 | 1463 | 37% | -0.176R | 2nd ⚠ below random | 3rd ⚠ below random | 0.88 | 45.0% | -39.2% | stop 553, target 326, stop_gap 318, time 266 |
| 2.0 | 5 | 1610 | 41% | -0.181R | 0th ⚠ below random | 1st ⚠ below random | 0.84 | 49.0% | -48.4% | stop 494, time 488, target 335, stop_gap 293 |
| 2.0 | 20 | 1312 | 37% | -0.190R | 2nd ⚠ below random | 3rd ⚠ below random | 0.91 | 42.5% | -32.3% | stop 535, target 423, stop_gap 277, time 77 |
| 1.5 | 15 | 1276 | 42% | -0.193R | 1st ⚠ below random | 1st ⚠ below random | 0.85 | 46.3% | -45.7% | target 488, stop 459, stop_gap 254, time 75 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h4_no_stop` — H4

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 3 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (time_limit=5, +0.064R) rather than the peak (time_limit=40, +1.806R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 131 | 67% | +1.806R | 90th | 62nd | 2.08 | 25.5% | +121.2% | time 131 |
| 10 | 586 | 59% | +0.372R | 74th | 51st | 1.29 | 26.6% | +90.3% | time 586 |
| 20 | 298 | 51% | +0.162R | 10th ⚠ below random | 9th ⚠ below random | 1.10 | 38.7% | +18.3% | time 298 |
| 5 | 1136 | 54% | +0.064R | 84th | 53rd | 1.15 | 30.0% | +55.8% | time 1136 |

## `h5_momentum_canonical` — H5

**Question:** Does 12-1 momentum -- the version with decades of replication -- work where H1's 63-day no-skip variant did not?

**Held fixed:** `monthly_rebalance=True`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 9 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | top_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 126 | 0.05 | 55 | 36% | +0.344R | 29th ⚠ below random | 28th ⚠ below random | 1.24 | 39.2% | +13.9% | stop 27, time 23, stop_gap 5 |
| 126 | 0.1 | 62 | 32% | +0.130R | 17th ⚠ below random | 17th ⚠ below random | 1.02 | 40.1% | +2.2% | stop 32, time 23, stop_gap 7 |
| 63 | 0.05 | 83 | 47% | -0.072R | 12th ⚠ below random | 17th ⚠ below random | 0.91 | 34.4% | -5.6% | time 41, stop 37, stop_gap 5 |
| 63 | 0.1 | 66 | 36% | -0.507R | 0th ⚠ below random | 0th ⚠ below random | 0.53 | 34.3% | -26.8% | stop 37, time 26, stop_gap 3 |
| 63 | 0.2 | 66 | 35% | -0.531R | 0th ⚠ below random | 0th ⚠ below random | 0.50 | 34.1% | -27.4% | stop 38, time 26, stop_gap 2 |
| 126 | 0.2 | 51 | 24% | -0.540R | 0th ⚠ below random | 1st ⚠ below random | 0.53 | 39.0% | -24.1% | stop 31, time 15, stop_gap 5 |
| 21 | 0.2 | 136 | 46% | -0.709R | 0th ⚠ below random | 0th ⚠ below random | 0.60 | 35.6% | -28.0% | time 86, stop 41, stop_gap 9 |
| 21 | 0.05 | 121 | 50% | -0.709R | 1st ⚠ below random | 0th ⚠ below random | 0.70 | 33.5% | -19.2% | time 77, stop 37, stop_gap 7 |
| 21 | 0.1 | 134 | 44% | -0.714R | 0th ⚠ below random | 0th ⚠ below random | 0.61 | 36.5% | -27.4% | time 83, stop 42, stop_gap 9 |

## `h5_skip_matters` — H5

**Question:** Is the skip month load-bearing, or decoration? skip=0 is H1's formation; skip=21 is the literature's.

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| mom_skip | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 78 | 47% | -0.012R | 27th ⚠ below random | 39th ⚠ below random | 1.05 | 27.0% | +2.7% | time 40, stop 36, stop_gap 2 |
| 0 | 84 | 43% | -0.188R | 3rd ⚠ below random | 12th ⚠ below random | 0.78 | 31.4% | -13.7% | stop 42, time 39, stop_gap 3 |
| 42 | 65 | 35% | -0.488R | 0th ⚠ below random | 1st ⚠ below random | 0.52 | 37.7% | -27.4% | stop 37, time 25, stop_gap 3 |
| 21 | 66 | 36% | -0.507R | 0th ⚠ below random | 0th ⚠ below random | 0.53 | 34.3% | -26.8% | stop 37, time 26, stop_gap 3 |

## `h5_no_stop` — H5

**Question:** Does momentum survive without a stop, as the literature's version has none at all?

**Held fixed:** `top_pct=0.1`, `use_stop=False`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 126 | 20 | 70% | +1.103R | 40th ⚠ below random | 43rd ⚠ below random | 5.21 | 14.0% | +23.4% | time 20 |
| 63 | 41 | 61% | +0.235R | 6th ⚠ below random | 14th ⚠ below random | 1.11 | 18.1% | +4.6% | time 41 |
| 21 | 97 | 57% | -1.257R | 3rd ⚠ below random | 6th ⚠ below random | 0.82 | 35.6% | -11.8% | time 97 |

## `h5_rebalance` — H5

**Question:** Monthly versus daily rebalancing -- does the documented frequency matter, or is it convention?

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — NONE:** neither arm produced positive expectancy -- monthly_rebalance=True at -0.507R versus monthly_rebalance=False at -0.757R, a gap of +0.250R. The comparison still says which is less bad, but nothing here is selectable.

| monthly_rebalance | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| True | 66 | 36% | -0.507R | 0th ⚠ below random | 0th ⚠ below random | 0.53 | 34.3% | -26.8% | stop 37, time 26, stop_gap 3 |
| False | 104 | 40% | -0.757R | 3rd ⚠ below random | 7th ⚠ below random | 0.86 | 38.0% | -10.4% | stop 48, time 47, stop_gap 9 |

## `h7_squeeze_exits` — H7

**Question:** Is there a target and holding period where range expansion after compression is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 672 | 53% | -0.190R | 37th ⚠ below random | 20th ⚠ below random | 0.88 | 24.9% | -11.9% | time 655, stop 15, stop_gap 1, target 1 |
| 2.5 | 5 | 670 | 53% | -0.192R | 35th ⚠ below random | 16th ⚠ below random | 0.87 | 24.9% | -12.8% | time 654, stop 15, stop_gap 1 |
| 3.0 | 5 | 670 | 53% | -0.192R | 35th ⚠ below random | 16th ⚠ below random | 0.87 | 24.9% | -12.8% | time 654, stop 15, stop_gap 1 |
| 1.5 | 5 | 670 | 53% | -0.192R | 29th ⚠ below random | 14th ⚠ below random | 0.86 | 25.0% | -13.1% | time 651, stop 16, target 2, stop_gap 1 |
| 1.0 | 5 | 680 | 52% | -0.195R | 21st ⚠ below random | 12th ⚠ below random | 0.85 | 24.2% | -15.2% | time 649, stop 16, target 14, stop_gap 1 |
| 2.0 | 10 | 429 | 51% | -0.293R | 4th ⚠ below random | 3rd ⚠ below random | 0.89 | 24.4% | -10.3% | time 400, stop 24, target 3, stop_gap 2 |
| 1.5 | 10 | 431 | 52% | -0.295R | 2nd ⚠ below random | 3rd ⚠ below random | 0.87 | 24.3% | -12.2% | time 393, stop 26, target 10, stop_gap 2 |
| 2.5 | 10 | 428 | 50% | -0.298R | 4th ⚠ below random | 3rd ⚠ below random | 0.87 | 24.3% | -11.8% | time 399, stop 23, stop_gap 4, target 2 |
| 1.0 | 10 | 439 | 50% | -0.303R | 5th ⚠ below random | 3rd ⚠ below random | 0.82 | 24.2% | -16.9% | time 384, target 28, stop 26, stop_gap 1 |
| 3.0 | 10 | 425 | 49% | -0.311R | 2nd ⚠ below random | 2nd ⚠ below random | 0.81 | 25.3% | -17.4% | time 400, stop 22, stop_gap 3 |
| 2.5 | 20 | 303 | 58% | -0.343R | 21st ⚠ below random | 17th ⚠ below random | 1.12 | 26.3% | +10.2% | time 264, stop 34, stop_gap 4, target 1 |
| 2.0 | 20 | 307 | 55% | -0.345R | 12th ⚠ below random | 12th ⚠ below random | 1.10 | 27.2% | +8.5% | time 261, stop 37, target 5, stop_gap 4 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h7_compression_depth` — H7

**Question:** How quiet must it get first? A threshold that only works at one depth is a threshold fitted to noise.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — PLATEAU:** 1 of 2 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (squeeze_percentile=0.4, +0.089R) rather than the peak (squeeze_percentile=0.3, +0.114R) -- the peak's margin over its neighbours is the part least likely to survive.

| squeeze_percentile | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.3 | 294 | 59% | +0.114R | 63rd | 48th ⚠ below random | 1.51 | 10.1% | +37.5% | time 254, stop 34, stop_gap 6 |
| 0.4 | 326 | 57% | +0.089R | 74th | 32nd ⚠ below random | 1.42 | 8.2% | +32.6% | time 283, stop 39, stop_gap 4 |
| 0.2 | 304 | 56% | -0.355R | 13th ⚠ below random | 11th ⚠ below random | 1.08 | 26.3% | +6.4% | time 264, stop 35, stop_gap 5 |
| 0.1 | 326 | 52% | -0.360R | 3rd ⚠ below random | 3rd ⚠ below random | 0.96 | 26.6% | -4.0% | time 274, stop 44, stop_gap 8 |

## `h7_no_stop` — H7

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 659 | 51% | -0.200R | 15th ⚠ below random | 10th ⚠ below random | 0.84 | 25.4% | -16.1% | time 659 |
| 10 | 496 | 53% | -0.240R | 7th ⚠ below random | 7th ⚠ below random | 0.95 | 28.6% | -5.7% | time 496 |
| 20 | 289 | 60% | -0.315R | 64th | 34th ⚠ below random | 1.29 | 26.4% | +23.7% | time 289 |
| 40 | 131 | 66% | -0.652R | 88th | 66th | 1.45 | 30.1% | +27.8% | time 131 |

## `h6_drift_exits` — H6

**Question:** Does price drift after an earnings filing, and over what horizon?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 2 of 4 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (time_limit=5, +0.137R) rather than the peak (time_limit=60, +0.951R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 60 | 75 | 69% | +0.951R | 72nd | 60th | 2.30 | 17.9% | +82.7% | time 75 |
| 40 | 90 | 64% | +0.592R | 96th | 59th | 2.10 | 19.9% | +58.7% | time 90 |
| 5 | 117 | 65% | +0.137R | 87th | 80th | 1.57 | 6.6% | +15.2% | time 117 |
| 20 | 104 | 57% | +0.098R | 40th ⚠ below random | 17th ⚠ below random | 1.14 | 18.9% | +6.9% | time 104 |
| 10 | 111 | 56% | +0.090R | 53rd | 33rd ⚠ below random | 1.23 | 10.1% | +9.0% | time 111 |

## `h6_reaction_size` — H6

**Question:** Does the size of the reaction sort the drift? The literature sorts on surprise; this substitutes the market's response.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 3 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (reaction_pct=0.03, +0.592R) rather than the peak (reaction_pct=0.05, +0.633R) -- the peak's margin over its neighbours is the part least likely to survive.

| reaction_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.05 | 43 | 67% | +0.633R | 92nd | 71st | 2.62 | 6.3% | +29.1% | time 43 |
| 0.03 | 90 | 64% | +0.592R | 96th | 59th | 2.10 | 19.9% | +58.7% | time 90 |
| 0.02 | 92 | 59% | +0.347R | 65th | 24th ⚠ below random | 1.44 | 23.3% | +26.4% | time 92 |
| 0.0 | 108 | 52% | +0.188R | 36th ⚠ below random | 10th ⚠ below random | 1.25 | 22.1% | +16.7% | time 108 |
| 0.08 | 10 | 50% | -0.433R | 20th ⚠ below random | 5th ⚠ below random | 0.40 | 7.0% | -4.3% | time 10 |

## `h6_entry_delay` — H6

**Question:** How much of the drift is gone by the time we could act? A day-one edge that vanishes by day three is not tradeable.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 4 of 4 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (entry_delay=2, +0.637R) rather than the peak (entry_delay=2, +0.637R) -- the peak's margin over its neighbours is the part least likely to survive.

| entry_delay | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 88 | 61% | +0.637R | 99th | 62nd | 2.32 | 19.5% | +62.4% | time 88 |
| 1 | 90 | 64% | +0.592R | 96th | 59th | 2.10 | 19.9% | +58.7% | time 90 |
| 3 | 89 | 57% | +0.469R | 86th | 36th ⚠ below random | 1.90 | 19.6% | +42.2% | time 89 |
| 5 | 90 | 61% | +0.374R | 79th | 29th ⚠ below random | 1.62 | 20.2% | +30.9% | time 90 |

## Caveats attached to every number above

- The universe is **today's** large caps. No delisted company is present, so every result is inflated by an unknown amount (ADR 0002).
- Ambiguous bars resolve to the stop, gaps fill at the open, and slippage is charged both ways. Those understate results.
- Random-selection percentiles, where present, are the comparison that matters: beating zero is not the test, beating random long exposure is.
