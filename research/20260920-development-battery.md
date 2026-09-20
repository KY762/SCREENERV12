# Development-split battery — development

**Generated:** 2026-09-20 12:58 Eastern Daylight Time
**Window:** 2010-01-01 → 2015-12-31
**Symbols:** 1020  
**Configurations tested:** 180
**Quarantined and excluded:** 25 (ACS, AYE, BBBY, BBT, CA, CAM, CPWR, CSRA, EMC, EP, FB, GENZ, GR, INFO, JAVA, KG, NFX, PARA, PBG, PCL, RX, SHLD, SII, SPLS, UST)  

Those symbols' stored series is not the company that was in the index — see `data/reference/universe_quarantine.csv` for the reason on each. Results generated before 2026-09-19 did not exclude them and are not comparable.

Development-split results carry **no evidential weight** (docs/03-HYPOTHESES.md §0.4). Nothing here confirms a hypothesis; it can only rule things out and suggest what to confirm elsewhere.

## Summary

| Experiment | Kind | Configs | Shape | Best expectancy | vs random (same days) | vs random (any day) | Selected |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `h1_exits` | parameter | 10 | **none** | -0.135R | 83rd | 79th | — |
| `h1_no_stop` | structural | 3 | **none** | -0.243R | 95th | 83rd | — |
| `h1_selection` | parameter | 12 | **plateau** | +0.179R | 62nd | 86th | `rs_lookback=252`, `top_pct=0.1` |
| `h1_entry_delay` | structural | 3 | **none** | -0.135R | 83rd | 79th | — |
| `h1_trend_filter` | structural | 2 | **none** | -0.135R | 83rd | 79th | — |
| `h2_exits` | parameter | 20 | **none** | -0.080R | 20th ⚠ below random | 21st ⚠ below random | — |
| `h2_no_stop` | structural | 4 | **spike** | +1.195R | 94th | 89th | — |
| `h2_displacement` | structural | 4 | **spike** | +0.115R | 86th | 84th | — |
| `h3_exits` | parameter | 20 | **none** | -0.017R | 9th ⚠ below random | 13th ⚠ below random | — |
| `h3_no_stop` | structural | 4 | **plateau** | +0.754R | 96th | 93rd | `time_limit=40` |
| `h3_lookback` | structural | 4 | **none** | +0.033R | 16th ⚠ below random | 18th ⚠ below random | — |
| `h1_exit_isolated` | structural | 2 | **indistinct** | +0.065R | 76th | 1st ⚠ below random | — |
| `h2_exit_isolated` | structural | 2 | **indistinct** | +0.371R | 29th ⚠ below random | 0th ⚠ below random | — |
| `h3_exit_isolated` | structural | 2 | **indistinct** | +0.643R | 40th ⚠ below random | 4th ⚠ below random | — |
| `h4_exit_isolated` | structural | 2 | **indistinct** | +0.477R | 29th ⚠ below random | 0th ⚠ below random | — |
| `h5_exit_isolated` | structural | 2 | **separated** | +0.255R | 97th | 78th | `use_stop=False` |
| `h4_exits` | parameter | 20 | **none** | -0.106R | 1st ⚠ below random | 1st ⚠ below random | — |
| `h4_no_stop` | structural | 4 | **spike** | +1.545R | 74th | 74th | — |
| `h5_momentum_canonical` | parameter | 9 | **none** | -0.133R | 0th ⚠ below random | 7th ⚠ below random | — |
| `h5_skip_matters` | structural | 4 | **none** | -0.092R | 2nd ⚠ below random | 16th ⚠ below random | — |
| `h5_no_stop` | structural | 3 | **none** | +0.754R | 38th ⚠ below random | 51st | — |
| `h5_rebalance` | structural | 2 | **none** | -0.170R | 0th ⚠ below random | 3rd ⚠ below random | — |
| `h7_squeeze_exits` | parameter | 20 | **none** | -0.135R | 62nd | 36th ⚠ below random | — |
| `h7_compression_depth` | parameter | 4 | **none** | -0.347R | 16th ⚠ below random | 13th ⚠ below random | — |
| `h7_no_stop` | structural | 4 | **none** | -0.144R | 50th ⚠ below random | 25th ⚠ below random | — |
| `h6_drift_exits` | parameter | 5 | **plateau** | +0.694R | 84th | 74th | `time_limit=20` |
| `h6_reaction_size` | parameter | 5 | **plateau** | +0.674R | 95th | 90th | `reaction_pct=0.05` |
| `h6_entry_delay` | parameter | 4 | **plateau** | +0.426R | 73rd | 54th | `entry_delay=2` |

## `h1_exits` — H1

**Question:** Is there any hold horizon and stop width at which momentum rotation is profitable?

**Verdict — NONE:** no configuration of 10 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | stop_atr | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 3.0 | 275 | 51% | -0.135R | 83rd | 79th | 1.22 | 22.1% | +26.1% | time 194, stop 72, stop_gap 9 |
| 10 | 3.0 | 558 | 52% | -0.179R | 75th | 61st | 1.08 | 23.5% | +13.4% | time 453, stop 91, stop_gap 14 |
| 20 | 2.5 | 273 | 48% | -0.190R | 88th | 82nd | 1.22 | 22.2% | +29.2% | time 168, stop 96, stop_gap 9 |
| 10 | 2.5 | 553 | 52% | -0.211R | 85th | 75th | 1.14 | 25.6% | +27.6% | time 416, stop 123, stop_gap 14 |
| 10 | 2.0 | 535 | 49% | -0.286R | 89th | 75th | 1.14 | 25.0% | +33.0% | time 349, stop 164, stop_gap 22 |
| 20 | 2.0 | 263 | 43% | -0.297R | 82nd | 69th | 1.16 | 25.5% | +22.5% | time 137, stop 113, stop_gap 13 |
| 10 | 1.5 | 590 | 43% | -0.317R | 87th | 86th | 1.17 | 34.0% | +51.0% | time 318, stop 227, stop_gap 45 |
| 20 | 1.5 | 290 | 36% | -0.375R | 83rd | 57th | 1.11 | 33.0% | +17.5% | stop 141, time 120, stop_gap 29 |
| 20 | 1.0 | 264 | 28% | -0.676R | 90th | 58th | 1.10 | 30.5% | +13.7% | stop 147, time 80, stop_gap 37 |
| 10 | 1.0 | 538 | 34% | -0.678R | 16th ⚠ below random | 23rd ⚠ below random | 0.96 | 36.2% | -8.7% | stop 264, time 205, stop_gap 69 |

## `h1_no_stop` — H1

**Question:** Is the STOP what loses the money? Same entries, no stop.

**Held fixed:** `use_stop=False`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 537 | 53% | -0.243R | 95th | 83rd | 1.22 | 29.8% | +58.4% | time 537 |
| 20 | 247 | 54% | -0.269R | 61st | 50th | 1.17 | 24.6% | +31.3% | time 247 |
| 40 | 124 | 50% | -0.559R | 21st ⚠ below random | 17th ⚠ below random | 1.17 | 31.3% | +20.6% | time 124 |

## `h1_selection` — H1

**Question:** Does the momentum lookback or the selection cutoff matter, holding exits fixed?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — PLATEAU:** 3 of 8 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (rs_lookback=252, top_pct=0.1, +0.146R) rather than the peak (rs_lookback=21, top_pct=0.1, +0.179R) -- the peak's margin over its neighbours is the part least likely to survive.

| rs_lookback | top_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 0.1 | 271 | 53% | +0.179R | 62nd | 86th | 1.70 | 12.5% | +69.1% | time 208, stop 56, stop_gap 7 |
| 21 | 0.2 | 276 | 52% | +0.166R | 48th ⚠ below random | 76th | 1.63 | 12.5% | +64.7% | time 209, stop 59, stop_gap 8 |
| 21 | 0.05 | 270 | 52% | +0.156R | 59th | 80th | 1.60 | 12.5% | +60.9% | time 206, stop 57, stop_gap 7 |
| 252 | 0.05 | 300 | 56% | +0.147R | 98th | 88th | 1.37 | 13.7% | +51.9% | time 208, stop 85, stop_gap 7 |
| 252 | 0.1 | 305 | 56% | +0.146R | 97th | 89th | 1.37 | 13.4% | +52.5% | time 212, stop 86, stop_gap 7 |
| 252 | 0.2 | 310 | 55% | +0.141R | 95th | 85th | 1.36 | 12.7% | +50.6% | time 215, stop 88, stop_gap 7 |
| 126 | 0.2 | 279 | 52% | +0.132R | 91st | 86th | 1.38 | 13.8% | +48.5% | time 189, stop 77, stop_gap 13 |
| 126 | 0.1 | 275 | 51% | +0.131R | 91st | 84th | 1.38 | 14.1% | +47.9% | time 186, stop 76, stop_gap 13 |
| 126 | 0.05 | 275 | 50% | +0.104R | 87th | 80th | 1.30 | 16.6% | +38.3% | time 183, stop 79, stop_gap 13 |
| 63 | 0.2 | 277 | 52% | -0.130R | 86th | 84th | 1.23 | 22.1% | +27.4% | time 196, stop 72, stop_gap 9 |
| 63 | 0.1 | 275 | 51% | -0.135R | 83rd | 79th | 1.22 | 22.1% | +26.1% | time 194, stop 72, stop_gap 9 |
| 63 | 0.05 | 272 | 51% | -0.150R | 81st | 79th | 1.18 | 26.1% | +20.9% | time 192, stop 71, stop_gap 9 |

## `h1_entry_delay` — H1

**Question:** Does waiting after the ranking help? Momentum's return is reported absent in the weeks after ranking (Jegadeesh & Titman 1993). Delayed names are re-checked at the last close before the buy and dropped if they no longer rank or trend, so this measures waiting AND re-selection together.

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| entry_delay | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 275 | 51% | -0.135R | 83rd | 79th | 1.22 | 22.1% | +26.1% | time 194, stop 72, stop_gap 9 |
| 3 | 274 | 51% | -0.217R | 19th ⚠ below random | 34th ⚠ below random | 1.02 | 29.4% | +1.7% | time 187, stop 74, stop_gap 13 |
| 6 | 272 | 49% | -0.249R | 11th ⚠ below random | 27th ⚠ below random | 1.06 | 28.1% | +6.3% | time 188, stop 74, stop_gap 10 |

## `h1_trend_filter` — H1

**Question:** Does requiring an uptrend help, or is it just fewer trades?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — NONE:** neither arm produced positive expectancy -- trend_filter=True at -0.135R versus trend_filter=False at -0.206R, a gap of +0.071R. The comparison still says which is less bad, but nothing here is selectable.

| trend_filter | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| True | 275 | 51% | -0.135R | 83rd | 79th | 1.22 | 22.1% | +26.1% | time 194, stop 72, stop_gap 9 |
| False | 275 | 49% | -0.206R | 87th | 77th | 1.12 | 22.7% | +13.1% | time 191, stop 75, stop_gap 9 |

## `h2_exits` — H2

**Question:** Is there a target and holding period at which the FVG continuation is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 5 | 2034 | 42% | -0.080R | 20th ⚠ below random | 21st ⚠ below random | 0.95 | 34.3% | -23.8% | time 894, stop 599, stop_gap 311, target 230 |
| 3.0 | 20 | 919 | 35% | -0.082R | 18th ⚠ below random | 24th ⚠ below random | 0.99 | 38.7% | -2.1% | stop 401, time 185, target 174, stop_gap 159 |
| 2.0 | 20 | 1165 | 39% | -0.104R | 22nd ⚠ below random | 21st ⚠ below random | 0.98 | 37.1% | -9.1% | stop 474, target 347, stop_gap 199, time 145 |
| 1.5 | 15 | 1410 | 45% | -0.115R | 47th ⚠ below random | 38th ⚠ below random | 1.02 | 28.3% | +7.7% | target 509, stop 481, stop_gap 217, time 203 |
| 2.5 | 5 | 2096 | 42% | -0.119R | 5th ⚠ below random | 6th ⚠ below random | 0.91 | 48.7% | -39.8% | time 873, stop 637, stop_gap 307, target 279 |
| 2.0 | 10 | 1521 | 41% | -0.126R | 3rd ⚠ below random | 3rd ⚠ below random | 0.89 | 50.0% | -40.2% | stop 545, time 372, target 369, stop_gap 235 |
| 2.5 | 10 | 1395 | 39% | -0.127R | 4th ⚠ below random | 8th ⚠ below random | 0.91 | 40.2% | -32.1% | stop 503, time 420, target 251, stop_gap 221 |
| 1.5 | 5 | 2371 | 46% | -0.128R | 5th ⚠ below random | 8th ⚠ below random | 0.92 | 48.9% | -39.6% | time 790, stop 647, target 601, stop_gap 333 |
| 2.0 | 5 | 2212 | 44% | -0.130R | 1st ⚠ below random | 2nd ⚠ below random | 0.91 | 50.6% | -44.2% | time 850, stop 637, target 400, stop_gap 325 |
| 1.5 | 20 | 1296 | 44% | -0.135R | 12th ⚠ below random | 9th ⚠ below random | 0.95 | 36.6% | -19.7% | stop 488, target 475, stop_gap 199, time 134 |
| 3.0 | 10 | 1353 | 37% | -0.137R | 2nd ⚠ below random | 3rd ⚠ below random | 0.88 | 46.9% | -40.5% | stop 502, time 425, stop_gap 232, target 194 |
| 1.5 | 10 | 1687 | 44% | -0.142R | 5th ⚠ below random | 7th ⚠ below random | 0.91 | 52.5% | -36.7% | stop 556, target 534, time 348, stop_gap 249 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h2_no_stop` — H2

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 2 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 167 | 63% | +1.195R | 94th | 89th | 2.52 | 25.4% | +194.0% | time 167 |
| 20 | 335 | 58% | +0.475R | 32nd ⚠ below random | 38th ⚠ below random | 1.45 | 23.2% | +103.7% | time 335 |
| 10 | 645 | 56% | +0.311R | 87th | 80th | 1.36 | 25.7% | +131.0% | time 645 |
| 5 | 1251 | 53% | +0.076R | 49th ⚠ below random | 49th ⚠ below random | 1.12 | 18.0% | +58.0% | time 1251 |

## `h2_displacement` — H2

**Question:** Does the displacement filter contribute anything? 'off' is the null the specification leaves live.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| displacement | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 471 | 44% | +0.115R | 86th | 84th | 1.24 | 19.8% | +61.7% | time 193, stop 175, target 60, stop_gap 43 |
| 1.5 | 632 | 39% | -0.009R | 47th ⚠ below random | 35th ⚠ below random | 1.09 | 32.0% | +29.6% | stop 265, time 199, target 91, stop_gap 77 |
| None | 919 | 35% | -0.082R | 18th ⚠ below random | 24th ⚠ below random | 0.99 | 38.7% | -2.1% | stop 401, time 185, target 174, stop_gap 159 |
| 1.0 | 786 | 35% | -0.143R | 4th ⚠ below random | 1st ⚠ below random | 0.90 | 39.3% | -29.1% | stop 345, time 201, stop_gap 124, target 116 |

## `h3_exits` — H3

**Question:** Is there a target and holding period at which sweep-reclaim is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 15 | 1042 | 36% | -0.017R | 9th ⚠ below random | 13th ⚠ below random | 1.02 | 25.0% | +9.4% | stop 423, target 218, time 206, stop_gap 195 |
| 3.0 | 5 | 1731 | 41% | -0.038R | 1st ⚠ below random | 10th ⚠ below random | 0.99 | 35.5% | -6.6% | time 714, stop 520, stop_gap 275, target 222 |
| 2.5 | 5 | 1801 | 43% | -0.047R | 4th ⚠ below random | 20th ⚠ below random | 0.98 | 36.9% | -7.7% | time 674, stop 544, target 300, stop_gap 283 |
| 3.0 | 20 | 904 | 35% | -0.060R | 2nd ⚠ below random | 5th ⚠ below random | 0.97 | 31.4% | -9.8% | stop 382, target 191, stop_gap 174, time 157 |
| 2.5 | 15 | 1110 | 38% | -0.070R | 6th ⚠ below random | 12th ⚠ below random | 0.98 | 25.3% | -5.5% | stop 427, target 265, stop_gap 213, time 205 |
| 2.0 | 5 | 1913 | 44% | -0.083R | 1st ⚠ below random | 14th ⚠ below random | 0.95 | 30.7% | -20.5% | time 625, stop 555, target 421, stop_gap 312 |
| 3.0 | 10 | 1237 | 37% | -0.086R | 3rd ⚠ below random | 6th ⚠ below random | 0.94 | 36.1% | -19.9% | stop 462, time 333, stop_gap 231, target 211 |
| 2.0 | 10 | 1464 | 41% | -0.093R | 2nd ⚠ below random | 4th ⚠ below random | 0.93 | 39.5% | -28.3% | stop 513, target 417, time 277, stop_gap 257 |
| 2.5 | 10 | 1333 | 38% | -0.099R | 1st ⚠ below random | 4th ⚠ below random | 0.92 | 38.5% | -28.4% | stop 504, time 312, target 283, stop_gap 234 |
| 2.0 | 15 | 1202 | 40% | -0.115R | 6th ⚠ below random | 13th ⚠ below random | 0.98 | 27.1% | -7.2% | stop 443, target 354, stop_gap 225, time 180 |
| 1.5 | 5 | 2052 | 46% | -0.126R | 0th ⚠ below random | 5th ⚠ below random | 0.91 | 41.7% | -36.9% | stop 583, time 583, target 578, stop_gap 308 |
| 2.5 | 20 | 986 | 36% | -0.134R | 0th ⚠ below random | 0th ⚠ below random | 0.86 | 49.5% | -40.1% | stop 425, target 236, stop_gap 182, time 143 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h3_no_stop` — H3

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 2 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (time_limit=40, +0.754R) rather than the peak (time_limit=40, +0.754R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 161 | 63% | +0.754R | 96th | 93rd | 1.81 | 35.5% | +121.3% | time 161 |
| 20 | 317 | 59% | +0.417R | 92nd | 88th | 1.70 | 20.7% | +157.2% | time 317 |
| 10 | 600 | 54% | +0.195R | 40th ⚠ below random | 31st ⚠ below random | 1.17 | 27.8% | +47.1% | time 600 |
| 5 | 1077 | 52% | +0.099R | 34th ⚠ below random | 47th ⚠ below random | 1.12 | 22.4% | +49.6% | time 1077 |

## `h3_lookback` — H3

**Question:** Which liquidity reference is swept? Varying the lookback is the cheapest version of that question.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| sweep_lookback | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 82 | 44% | +0.033R | 16th ⚠ below random | 18th ⚠ below random | 1.03 | 6.8% | +0.8% | time 54, stop 24, target 3, stop_gap 1 |
| 10 | 904 | 35% | -0.060R | 2nd ⚠ below random | 5th ⚠ below random | 0.97 | 31.4% | -9.8% | stop 382, target 191, stop_gap 174, time 157 |
| 5 | 1111 | 33% | -0.063R | 2nd ⚠ below random | 2nd ⚠ below random | 0.95 | 32.4% | -18.3% | stop 492, target 261, stop_gap 216, time 142 |
| 20 | 652 | 34% | -0.080R | 1st ⚠ below random | 10th ⚠ below random | 0.96 | 23.7% | -9.1% | stop 283, target 132, stop_gap 128, time 109 |

## `h1_exit_isolated` — H1

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.065R versus use_stop=True at -0.033R, a gap of +0.098R, but that gap is 1.5 standard errors on mean per-trade return (paired over 2,259 shared signals, month-clustered) -- under the 2 required.

**Isolation held:** arms differ by 0.2% in trade count (2,259 vs 2,263), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 2259 | 54% | +0.065R | 76th | 1st ⚠ below random | 1.21 | 1.7% | +2.7% | time 2259 |
| True | 2263 | 41% | -0.033R | 1st ⚠ below random | 0th ⚠ below random | 1.05 | 1.3% | +0.6% | time 1135, stop 992, stop_gap 136 |

## `h2_exit_isolated` — H2

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.371R versus use_stop=True at -0.045R, a gap of +0.415R, but the arms differ by 29.0% in trade count (19,269 vs 27,146). They did not take the same signals, so this measures exit design and selection together and the gap is not attributable to the exit rule.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 29.0% in trade count (19,269 vs 27,146). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 19269 | 56% | +0.371R | 29th ⚠ below random | 0th ⚠ below random | 1.26 | 12.9% | +25.6% | time 19269 |
| True | 27146 | 26% | -0.045R | 0th ⚠ below random | 0th ⚠ below random | 1.02 | 9.1% | +2.1% | stop 14375, time 7807, stop_gap 4964 |

## `h3_exit_isolated` — H3

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.643R versus use_stop=True at +0.077R, a gap of +0.565R, but the arms differ by 29.4% in trade count (10,390 vs 14,712). They did not take the same signals, so this measures exit design and selection together and the gap is not attributable to the exit rule.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 29.4% in trade count (10,390 vs 14,712). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 10390 | 56% | +0.643R | 40th ⚠ below random | 4th ⚠ below random | 1.37 | 7.8% | +19.1% | time 10390 |
| True | 14712 | 26% | +0.077R | 0th ⚠ below random | 0th ⚠ below random | 1.07 | 4.0% | +3.4% | stop 7916, time 4196, stop_gap 2600 |

## `h4_exit_isolated` — H4

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.477R versus use_stop=True at +0.005R, a gap of +0.472R. But the winning arm sits at the 29th percentile against random selection on its own entry dates, so beating the other arm is not evidence of an edge -- both are losing to a coin toss and one loses by less.

**Isolation held:** arms differ by 19.2% in trade count (10,144 vs 12,561), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 10144 | 55% | +0.477R | 29th ⚠ below random | 0th ⚠ below random | 1.23 | 7.3% | +12.0% | time 10144 |
| True | 12561 | 24% | +0.005R | 0th ⚠ below random | 0th ⚠ below random | 0.99 | 5.9% | -0.5% | stop 6741, time 3291, stop_gap 2529 |

## `h5_exit_isolated` — H5

**Question:** H5 shows +0.055R yet ranks below random selection. With portfolio competition removed so both arms take the same signals, is that the entries or the exit?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=21`

**Verdict — SEPARATED:** use_stop=False at +0.255R versus use_stop=True at +0.100R, a gap of +0.155R at 2.7 standard errors (paired over 1,918 shared signals, month-clustered), and the winning arm beats random selection on its own entry dates at the 97th percentile. Development split: a question worth pre-registering, not a settled result.

**Isolation held:** arms differ by 4.9% in trade count (1,931 vs 2,030), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 1931 | 57% | +0.255R | 97th | 78th | 1.48 | 1.5% | +5.0% | time 1931 |
| True | 2030 | 44% | +0.100R | 68th | 22nd ⚠ below random | 1.21 | 1.7% | +2.3% | time 996, stop 893, stop_gap 141 |

## `h4_exits` — H4

**Question:** Is there a target and holding period at which the inverted gap is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.5 | 15 | 1332 | 36% | -0.106R | 1st ⚠ below random | 1st ⚠ below random | 0.91 | 44.0% | -33.5% | stop 554, target 371, stop_gap 269, time 138 |
| 3.0 | 5 | 2021 | 39% | -0.113R | 0th ⚠ below random | 3rd ⚠ below random | 0.89 | 52.2% | -49.1% | time 724, stop 658, stop_gap 371, target 268 |
| 2.5 | 20 | 1238 | 34% | -0.126R | 3rd ⚠ below random | 1st ⚠ below random | 0.90 | 50.5% | -37.3% | stop 541, target 346, stop_gap 251, time 100 |
| 2.0 | 10 | 1663 | 40% | -0.130R | 4th ⚠ below random | 4th ⚠ below random | 0.91 | 45.6% | -35.7% | stop 616, target 490, stop_gap 319, time 238 |
| 2.5 | 5 | 2100 | 40% | -0.131R | 0th ⚠ below random | 0th ⚠ below random | 0.86 | 60.2% | -58.5% | time 686, stop 684, stop_gap 379, target 351 |
| 3.0 | 20 | 1067 | 32% | -0.134R | 0th ⚠ below random | 0th ⚠ below random | 0.88 | 54.2% | -43.2% | stop 486, target 252, stop_gap 222, time 107 |
| 2.5 | 10 | 1545 | 36% | -0.135R | 0th ⚠ below random | 0th ⚠ below random | 0.85 | 54.5% | -51.3% | stop 617, target 355, stop_gap 304, time 269 |
| 2.0 | 15 | 1462 | 38% | -0.136R | 0th ⚠ below random | 1st ⚠ below random | 0.88 | 48.9% | -44.6% | stop 594, target 468, stop_gap 283, time 117 |
| 3.0 | 10 | 1403 | 35% | -0.138R | 2nd ⚠ below random | 1st ⚠ below random | 0.90 | 47.4% | -38.8% | stop 587, time 294, stop_gap 271, target 251 |
| 2.0 | 20 | 1341 | 38% | -0.142R | 0th ⚠ below random | 1st ⚠ below random | 0.92 | 42.3% | -33.4% | stop 551, target 450, stop_gap 261, time 79 |
| 2.0 | 5 | 2207 | 42% | -0.143R | 0th ⚠ below random | 1st ⚠ below random | 0.85 | 60.9% | -58.3% | stop 685, time 639, target 491, stop_gap 392 |
| 3.0 | 15 | 1178 | 32% | -0.153R | 0th ⚠ below random | 1st ⚠ below random | 0.88 | 54.4% | -42.3% | stop 522, target 247, stop_gap 239, time 170 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h4_no_stop` — H4

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 2 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 156 | 57% | +1.545R | 74th | 74th | 2.24 | 18.4% | +175.8% | time 156 |
| 20 | 307 | 57% | +0.486R | 8th ⚠ below random | 13th ⚠ below random | 1.12 | 36.8% | +26.9% | time 307 |
| 10 | 603 | 56% | +0.380R | 54th | 48th ⚠ below random | 1.26 | 24.0% | +87.1% | time 603 |
| 5 | 1184 | 53% | -0.028R | 20th ⚠ below random | 19th ⚠ below random | 1.01 | 35.6% | +2.1% | time 1184 |

## `h5_momentum_canonical` — H5

**Question:** Does 12-1 momentum -- the version with decades of replication -- work where H1's 63-day no-skip variant did not?

**Held fixed:** `monthly_rebalance=True`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 9 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | top_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 63 | 0.2 | 98 | 42% | -0.133R | 0th ⚠ below random | 7th ⚠ below random | 0.81 | 39.4% | -13.7% | time 45, stop 43, stop_gap 10 |
| 63 | 0.1 | 99 | 40% | -0.170R | 0th ⚠ below random | 3rd ⚠ below random | 0.77 | 39.4% | -16.9% | stop 45, time 44, stop_gap 10 |
| 126 | 0.1 | 70 | 33% | -0.201R | 1st ⚠ below random | 4th ⚠ below random | 0.78 | 35.9% | -12.8% | stop 36, time 25, stop_gap 9 |
| 126 | 0.2 | 70 | 33% | -0.201R | 1st ⚠ below random | 4th ⚠ below random | 0.78 | 35.9% | -12.8% | stop 36, time 25, stop_gap 9 |
| 63 | 0.05 | 92 | 36% | -0.229R | 2nd ⚠ below random | 3rd ⚠ below random | 0.74 | 37.6% | -18.9% | stop 42, time 37, stop_gap 13 |
| 126 | 0.05 | 69 | 30% | -0.247R | 0th ⚠ below random | 1st ⚠ below random | 0.71 | 40.2% | -16.9% | stop 36, time 24, stop_gap 9 |
| 21 | 0.1 | 172 | 48% | -0.460R | 3rd ⚠ below random | 6th ⚠ below random | 0.83 | 37.8% | -14.4% | time 113, stop 47, stop_gap 12 |
| 21 | 0.2 | 174 | 47% | -0.480R | 0th ⚠ below random | 3rd ⚠ below random | 0.79 | 39.8% | -18.1% | time 113, stop 49, stop_gap 12 |
| 21 | 0.05 | 168 | 47% | -0.497R | 2nd ⚠ below random | 2nd ⚠ below random | 0.79 | 38.8% | -18.0% | time 109, stop 47, stop_gap 12 |

## `h5_skip_matters` — H5

**Question:** Is the skip month load-bearing, or decoration? skip=0 is H1's formation; skip=21 is the literature's.

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| mom_skip | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 98 | 40% | -0.092R | 2nd ⚠ below random | 16th ⚠ below random | 0.86 | 35.7% | -10.4% | time 45, stop 44, stop_gap 9 |
| 42 | 93 | 41% | -0.122R | 1st ⚠ below random | 7th ⚠ below random | 0.86 | 34.3% | -9.3% | time 44, stop 42, stop_gap 7 |
| 5 | 92 | 41% | -0.136R | 2nd ⚠ below random | 10th ⚠ below random | 0.83 | 32.7% | -11.3% | time 42, stop 41, stop_gap 9 |
| 21 | 99 | 40% | -0.170R | 0th ⚠ below random | 3rd ⚠ below random | 0.77 | 39.4% | -16.9% | stop 45, time 44, stop_gap 10 |

## `h5_no_stop` — H5

**Question:** Does momentum survive without a stop, as the literature's version has none at all?

**Held fixed:** `top_pct=0.1`, `use_stop=False`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 63 | 60 | 63% | +0.754R | 38th ⚠ below random | 51st | 1.71 | 22.9% | +39.5% | time 60 |
| 126 | 29 | 55% | +0.427R | 0th ⚠ below random | 2nd ⚠ below random | 1.13 | 21.1% | +5.5% | time 29 |
| 21 | 149 | 54% | -0.745R | 2nd ⚠ below random | 6th ⚠ below random | 0.95 | 41.4% | -4.3% | time 149 |

## `h5_rebalance` — H5

**Question:** Monthly versus daily rebalancing -- does the documented frequency matter, or is it convention?

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — NONE:** neither arm produced positive expectancy -- monthly_rebalance=True at -0.170R versus monthly_rebalance=False at -0.785R, a gap of +0.615R. The comparison still says which is less bad, but nothing here is selectable.

| monthly_rebalance | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| True | 99 | 40% | -0.170R | 0th ⚠ below random | 3rd ⚠ below random | 0.77 | 39.4% | -16.9% | stop 45, time 44, stop_gap 10 |
| False | 136 | 32% | -0.785R | 0th ⚠ below random | 0th ⚠ below random | 0.62 | 46.1% | -33.8% | stop 75, time 51, stop_gap 10 |

## `h7_squeeze_exits` — H7

**Question:** Is there a target and holding period where range expansion after compression is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 5 | 852 | 53% | -0.135R | 62nd | 36th ⚠ below random | 1.00 | 24.9% | -0.4% | time 815, target 21, stop 13, stop_gap 3 |
| 3.0 | 5 | 842 | 53% | -0.135R | 68th | 40th ⚠ below random | 1.00 | 24.0% | -0.4% | time 825, stop 14, target 2, stop_gap 1 |
| 1.5 | 5 | 848 | 53% | -0.136R | 61st | 37th ⚠ below random | 1.00 | 23.6% | +0.2% | time 823, stop 14, target 8, stop_gap 3 |
| 2.0 | 5 | 844 | 53% | -0.137R | 66th | 40th ⚠ below random | 0.99 | 24.0% | -1.0% | time 825, stop 13, target 4, stop_gap 2 |
| 2.5 | 5 | 843 | 53% | -0.138R | 58th | 35th ⚠ below random | 0.98 | 24.3% | -2.7% | time 825, stop 15, target 2, stop_gap 1 |
| 1.0 | 10 | 455 | 54% | -0.241R | 47th ⚠ below random | 36th ⚠ below random | 1.04 | 24.8% | +3.4% | time 411, target 26, stop 17, stop_gap 1 |
| 3.0 | 10 | 448 | 54% | -0.259R | 24th ⚠ below random | 16th ⚠ below random | 0.99 | 24.3% | -0.8% | time 421, stop 21, stop_gap 4, target 2 |
| 2.5 | 10 | 448 | 54% | -0.260R | 20th ⚠ below random | 13th ⚠ below random | 0.99 | 24.3% | -1.2% | time 422, stop 20, stop_gap 4, target 2 |
| 1.5 | 10 | 447 | 55% | -0.272R | 21st ⚠ below random | 16th ⚠ below random | 0.91 | 24.7% | -7.9% | time 420, stop 20, target 4, stop_gap 3 |
| 2.0 | 10 | 393 | 54% | -0.305R | 12th ⚠ below random | 13th ⚠ below random | 0.94 | 23.3% | -5.0% | time 368, stop 19, target 5, stop_gap 1 |
| 1.5 | 15 | 313 | 58% | -0.340R | 38th ⚠ below random | 30th ⚠ below random | 1.09 | 25.2% | +7.5% | time 270, stop 23, target 15, stop_gap 5 |
| 1.0 | 15 | 328 | 58% | -0.348R | 39th ⚠ below random | 31st ⚠ below random | 0.94 | 27.8% | -4.5% | time 253, target 43, stop 27, stop_gap 5 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h7_compression_depth` — H7

**Question:** How quiet must it get first? A threshold that only works at one depth is a threshold fitted to noise.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| squeeze_percentile | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.1 | 298 | 58% | -0.347R | 16th ⚠ below random | 13th ⚠ below random | 1.06 | 26.7% | +5.3% | time 252, stop 39, stop_gap 4, target 3 |
| 0.4 | 298 | 60% | -0.349R | 59th | 41st ⚠ below random | 1.10 | 26.8% | +8.6% | time 260, stop 31, stop_gap 5, target 2 |
| 0.2 | 243 | 55% | -0.495R | 12th ⚠ below random | 12th ⚠ below random | 0.91 | 27.9% | -6.1% | time 205, stop 32, stop_gap 5, target 1 |
| 0.3 | 243 | 58% | -0.509R | 7th ⚠ below random | 6th ⚠ below random | 0.84 | 29.2% | -10.7% | time 209, stop 28, stop_gap 5, target 1 |

## `h7_no_stop` — H7

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 833 | 52% | -0.144R | 50th ⚠ below random | 25th ⚠ below random | 0.96 | 24.3% | -4.9% | time 833 |
| 10 | 577 | 55% | -0.190R | 28th ⚠ below random | 24th ⚠ below random | 1.03 | 27.7% | +3.9% | time 577 |
| 20 | 287 | 55% | -0.338R | 19th ⚠ below random | 13th ⚠ below random | 1.20 | 28.8% | +16.0% | time 287 |
| 40 | 134 | 60% | -0.885R | 3rd ⚠ below random | 10th ⚠ below random | 0.92 | 31.0% | -5.3% | time 134 |

## `h6_drift_exits` — H6

**Question:** Does price drift after an earnings filing, and over what horizon?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 5 of 5 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (time_limit=20, +0.092R) rather than the peak (time_limit=60, +0.694R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 60 | 103 | 64% | +0.694R | 84th | 74th | 1.71 | 18.7% | +85.4% | time 103 |
| 40 | 115 | 60% | +0.426R | 73rd | 54th | 1.63 | 21.7% | +54.1% | time 115 |
| 10 | 206 | 54% | +0.093R | 71st | 45th ⚠ below random | 1.23 | 14.2% | +18.4% | time 206 |
| 5 | 240 | 55% | +0.093R | 95th | 90th | 1.30 | 11.8% | +21.8% | time 240 |
| 20 | 150 | 55% | +0.092R | 61st | 23rd ⚠ below random | 1.14 | 21.5% | +10.5% | time 150 |

## `h6_reaction_size` — H6

**Question:** Does the size of the reaction sort the drift? The literature sorts on surprise; this substitutes the market's response.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 2 of 4 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (reaction_pct=0.05, +0.674R) rather than the peak (reaction_pct=0.05, +0.674R) -- the peak's margin over its neighbours is the part least likely to survive.

| reaction_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.05 | 86 | 66% | +0.674R | 95th | 90th | 2.92 | 14.7% | +72.6% | time 86 |
| 0.08 | 43 | 63% | +0.592R | 99th | 88th | 2.19 | 10.7% | +27.4% | time 43 |
| 0.0 | 134 | 63% | +0.562R | 98th | 93rd | 1.81 | 19.7% | +88.7% | time 134 |
| 0.03 | 115 | 60% | +0.426R | 73rd | 54th | 1.63 | 21.7% | +54.1% | time 115 |
| 0.02 | 121 | 61% | +0.363R | 41st ⚠ below random | 24th ⚠ below random | 1.41 | 23.8% | +42.0% | time 121 |

## `h6_entry_delay` — H6

**Question:** How much of the drift is gone by the time we could act? A day-one edge that vanishes by day three is not tradeable.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 2 of 3 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (entry_delay=2, +0.396R) rather than the peak (entry_delay=1, +0.426R) -- the peak's margin over its neighbours is the part least likely to survive.

| entry_delay | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 115 | 60% | +0.426R | 73rd | 54th | 1.63 | 21.7% | +54.1% | time 115 |
| 2 | 116 | 58% | +0.396R | 56th | 44th ⚠ below random | 1.55 | 21.4% | +48.7% | time 116 |
| 3 | 115 | 57% | +0.331R | 59th | 40th ⚠ below random | 1.48 | 22.1% | +39.1% | time 115 |
| 5 | 115 | 58% | +0.160R | 26th ⚠ below random | 8th ⚠ below random | 1.16 | 22.2% | +13.4% | time 115 |

## Caveats attached to every number above

- The universe is **today's** large caps. No delisted company is present, so every result is inflated by an unknown amount (ADR 0002).
- Ambiguous bars resolve to the stop, gaps fill at the open, and slippage is charged both ways. Those understate results.
- Random-selection percentiles, where present, are the comparison that matters: beating zero is not the test, beating random long exposure is.
