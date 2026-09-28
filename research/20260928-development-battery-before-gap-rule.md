# Development-split battery — development

**Generated:** 2026-09-28 00:06 Eastern Daylight Time
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
| `h1_exits` | parameter | 10 | **none** | -0.229R | 0th ⚠ below random | 1st ⚠ below random | — |
| `h1_no_stop` | structural | 3 | **none** | -0.430R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h1_selection` | parameter | 12 | **spike** | +0.181R | 82nd | 58th | — |
| `h1_entry_delay` | structural | 3 | **none** | -0.288R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h1_trend_filter` | structural | 2 | **none** | -0.275R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h2_exits` | parameter | 20 | **none** | -0.204R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h2_no_stop` | structural | 4 | **spike** | +0.796R | 73rd | 53rd | — |
| `h2_displacement` | structural | 4 | **spike** | +0.037R | 61st | 41st ⚠ below random | — |
| `h3_exits` | parameter | 20 | **none** | -0.186R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h3_no_stop` | structural | 4 | **none** | +1.053R | 39th ⚠ below random | 26th ⚠ below random | — |
| `h3_lookback` | structural | 4 | **none** | -0.005R | 60th | 29th ⚠ below random | — |
| `h1_exit_isolated` | structural | 2 | **none** | -0.077R | 1st ⚠ below random | 0th ⚠ below random | — |
| `h2_exit_isolated` | structural | 2 | **indistinct** | +0.133R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h3_exit_isolated` | structural | 2 | **indistinct** | +0.433R | 5th ⚠ below random | 0th ⚠ below random | — |
| `h4_exit_isolated` | structural | 2 | **indistinct** | +0.148R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h5_exit_isolated` | structural | 2 | **indistinct** | +0.032R | 33rd ⚠ below random | 1st ⚠ below random | — |
| `h4_exits` | parameter | 20 | **none** | -0.240R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h4_no_stop` | structural | 4 | **spike** | +1.216R | 34th ⚠ below random | 27th ⚠ below random | — |
| `h5_momentum_canonical` | parameter | 9 | **none** | +0.367R | 29th ⚠ below random | 28th ⚠ below random | — |
| `h5_skip_matters` | structural | 4 | **none** | -0.090R | 14th ⚠ below random | 22nd ⚠ below random | — |
| `h5_no_stop` | structural | 3 | **spike** | +2.233R | 87th | 89th | — |
| `h5_rebalance` | structural | 2 | **none** | -0.528R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h7_squeeze_exits` | parameter | 20 | **none** | -0.190R | 3rd ⚠ below random | 3rd ⚠ below random | — |
| `h7_compression_depth` | parameter | 4 | **spike** | +0.091R | 69th | 50th ⚠ below random | — |
| `h7_no_stop` | structural | 4 | **none** | -0.193R | 1st ⚠ below random | 2nd ⚠ below random | — |
| `h6_drift_exits` | parameter | 5 | **plateau** | +0.921R | 67th | 56th | `time_limit=60` |
| `h6_reaction_size` | parameter | 5 | **plateau** | +0.596R | 89th | 66th | `reaction_pct=0.03` |
| `h6_entry_delay` | parameter | 4 | **plateau** | +0.618R | 95th | 63rd | `entry_delay=2` |

## `h1_exits` — H1

**Question:** Is there any hold horizon and stop width at which momentum rotation is profitable?

**Verdict — NONE:** no configuration of 10 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | stop_atr | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 3.0 | 548 | 51% | -0.229R | 0th ⚠ below random | 1st ⚠ below random | 0.83 | 30.8% | -24.0% | time 454, stop 85, stop_gap 9 |
| 20 | 3.0 | 267 | 46% | -0.288R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 29.1% | -21.0% | time 179, stop 81, stop_gap 7 |
| 10 | 2.5 | 527 | 49% | -0.304R | 0th ⚠ below random | 1st ⚠ below random | 0.81 | 37.2% | -29.3% | time 396, stop 114, stop_gap 17 |
| 20 | 2.5 | 253 | 43% | -0.411R | 0th ⚠ below random | 0th ⚠ below random | 0.74 | 37.3% | -29.1% | time 145, stop 94, stop_gap 14 |
| 10 | 2.0 | 476 | 46% | -0.454R | 0th ⚠ below random | 0th ⚠ below random | 0.75 | 41.0% | -39.4% | time 306, stop 153, stop_gap 17 |
| 10 | 1.5 | 532 | 42% | -0.520R | 0th ⚠ below random | 1st ⚠ below random | 0.83 | 36.2% | -31.1% | time 287, stop 209, stop_gap 36 |
| 20 | 2.0 | 235 | 39% | -0.562R | 0th ⚠ below random | 0th ⚠ below random | 0.72 | 37.7% | -32.0% | time 116, stop 104, stop_gap 15 |
| 20 | 1.5 | 262 | 35% | -0.626R | 1st ⚠ below random | 0th ⚠ below random | 0.79 | 33.3% | -24.6% | stop 134, time 109, stop_gap 19 |
| 10 | 1.0 | 528 | 33% | -0.805R | 0th ⚠ below random | 1st ⚠ below random | 0.81 | 37.6% | -32.9% | stop 245, time 209, stop_gap 74 |
| 20 | 1.0 | 261 | 28% | -0.944R | 2nd ⚠ below random | 1st ⚠ below random | 0.74 | 33.9% | -26.9% | stop 140, time 79, stop_gap 42 |

## `h1_no_stop` — H1

**Question:** Is the STOP what loses the money? Same entries, no stop.

**Held fixed:** `use_stop=False`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 475 | 50% | -0.430R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 48.0% | -38.9% | time 475 |
| 20 | 236 | 51% | -0.442R | 0th ⚠ below random | 1st ⚠ below random | 0.86 | 37.2% | -17.9% | time 236 |
| 40 | 115 | 52% | -0.894R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 38.0% | -18.3% | time 115 |

## `h1_selection` — H1

**Question:** Does the momentum lookback or the selection cutoff matter, holding exits fixed?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — SPIKE:** 3 of 12 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| rs_lookback | top_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 0.05 | 246 | 52% | +0.181R | 82nd | 58th | 1.56 | 9.2% | +51.4% | time 194, stop 49, stop_gap 3 |
| 21 | 0.2 | 266 | 52% | +0.171R | 58th | 49th ⚠ below random | 1.54 | 11.5% | +53.3% | time 212, stop 50, stop_gap 4 |
| 21 | 0.1 | 258 | 52% | +0.171R | 65th | 51st | 1.54 | 11.5% | +51.5% | time 204, stop 51, stop_gap 3 |
| 126 | 0.2 | 275 | 52% | +0.098R | 32nd ⚠ below random | 30th ⚠ below random | 1.29 | 11.9% | +29.6% | time 199, stop 67, stop_gap 9 |
| 126 | 0.1 | 271 | 51% | +0.096R | 34th ⚠ below random | 24th ⚠ below random | 1.28 | 11.3% | +28.5% | time 196, stop 66, stop_gap 9 |
| 126 | 0.05 | 259 | 51% | +0.078R | 42nd ⚠ below random | 17th ⚠ below random | 1.22 | 13.3% | +21.6% | time 185, stop 65, stop_gap 9 |
| 252 | 0.1 | 300 | 54% | +0.069R | 14th ⚠ below random | 9th ⚠ below random | 1.16 | 10.6% | +19.7% | time 210, stop 82, stop_gap 8 |
| 252 | 0.2 | 300 | 54% | +0.056R | 9th ⚠ below random | 9th ⚠ below random | 1.13 | 11.3% | +16.0% | time 209, stop 83, stop_gap 8 |
| 252 | 0.05 | 284 | 53% | +0.037R | 9th ⚠ below random | 5th ⚠ below random | 1.08 | 11.0% | +9.5% | time 196, stop 80, stop_gap 8 |
| 63 | 0.1 | 267 | 46% | -0.288R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 29.1% | -21.0% | time 179, stop 81, stop_gap 7 |
| 63 | 0.2 | 272 | 47% | -0.288R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 29.7% | -21.9% | time 182, stop 82, stop_gap 8 |
| 63 | 0.05 | 255 | 47% | -0.302R | 0th ⚠ below random | 1st ⚠ below random | 0.78 | 32.9% | -22.7% | time 170, stop 78, stop_gap 7 |

## `h1_entry_delay` — H1

**Question:** Does waiting after the ranking help? Momentum's return is reported absent in the weeks after ranking (Jegadeesh & Titman 1993). Delayed names are re-checked at the last close before the buy and dropped if they no longer rank or trend, so this measures waiting AND re-selection together.

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| entry_delay | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 267 | 46% | -0.288R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 29.1% | -21.0% | time 179, stop 81, stop_gap 7 |
| 3 | 259 | 48% | -0.371R | 0th ⚠ below random | 0th ⚠ below random | 0.73 | 36.7% | -29.2% | time 175, stop 70, stop_gap 14 |
| 6 | 249 | 43% | -0.503R | 0th ⚠ below random | 0th ⚠ below random | 0.59 | 45.0% | -41.5% | time 156, stop 78, stop_gap 15 |

## `h1_trend_filter` — H1

**Question:** Does requiring an uptrend help, or is it just fewer trades?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — NONE:** neither arm produced positive expectancy -- trend_filter=False at -0.275R versus trend_filter=True at -0.288R, a gap of +0.013R. The comparison still says which is less bad, but nothing here is selectable.

| trend_filter | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 277 | 47% | -0.275R | 0th ⚠ below random | 0th ⚠ below random | 0.82 | 30.4% | -20.1% | time 183, stop 85, stop_gap 9 |
| True | 267 | 46% | -0.288R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 29.1% | -21.0% | time 179, stop 81, stop_gap 7 |

## `h2_exits` — H2

**Question:** Is there a target and holding period at which the FVG continuation is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 10 | 1292 | 35% | -0.204R | 0th ⚠ below random | 0th ⚠ below random | 0.82 | 55.5% | -52.7% | stop 510, time 373, stop_gap 222, target 187 |
| 1.5 | 15 | 1377 | 43% | -0.208R | 3rd ⚠ below random | 1st ⚠ below random | 0.90 | 44.8% | -38.0% | stop 508, target 481, stop_gap 212, time 176 |
| 3.0 | 5 | 1947 | 39% | -0.210R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 72.7% | -71.4% | time 829, stop 618, stop_gap 308, target 192 |
| 2.5 | 10 | 1359 | 36% | -0.215R | 0th ⚠ below random | 0th ⚠ below random | 0.79 | 65.5% | -61.9% | stop 535, time 351, target 248, stop_gap 225 |
| 3.0 | 15 | 1059 | 34% | -0.216R | 0th ⚠ below random | 0th ⚠ below random | 0.84 | 55.6% | -46.4% | stop 438, time 230, stop_gap 209, target 182 |
| 1.5 | 5 | 2246 | 43% | -0.220R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 74.9% | -74.0% | time 704, stop 658, target 560, stop_gap 324 |
| 2.5 | 20 | 980 | 34% | -0.221R | 7th ⚠ below random | 5th ⚠ below random | 0.88 | 44.1% | -33.0% | stop 431, target 214, stop_gap 174, time 161 |
| 1.5 | 10 | 1631 | 42% | -0.223R | 0th ⚠ below random | 0th ⚠ below random | 0.77 | 71.0% | -67.1% | stop 593, target 502, time 297, stop_gap 238, no_volume 1 |
| 1.5 | 20 | 1263 | 42% | -0.227R | 0th ⚠ below random | 1st ⚠ below random | 0.86 | 54.0% | -44.4% | stop 482, target 449, stop_gap 210, time 122 |
| 2.0 | 5 | 2094 | 40% | -0.233R | 0th ⚠ below random | 0th ⚠ below random | 0.73 | 77.2% | -76.3% | time 772, stop 649, target 360, stop_gap 313 |
| 2.5 | 15 | 1112 | 35% | -0.238R | 0th ⚠ below random | 0th ⚠ below random | 0.85 | 54.1% | -44.5% | stop 461, target 230, time 219, stop_gap 202 |
| 2.5 | 5 | 1993 | 39% | -0.238R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 74.1% | -72.4% | time 817, stop 611, stop_gap 322, target 243 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h2_no_stop` — H2

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 166 | 61% | +0.796R | 73rd | 53rd | 1.76 | 21.7% | +113.6% | time 166 |
| 20 | 320 | 53% | +0.343R | 7th ⚠ below random | 6th ⚠ below random | 1.15 | 23.6% | +23.9% | time 320 |
| 10 | 475 | 52% | +0.116R | 14th ⚠ below random | 14th ⚠ below random | 1.03 | 19.1% | +6.3% | time 475 |
| 5 | 1205 | 50% | +0.008R | 7th ⚠ below random | 4th ⚠ below random | 0.96 | 25.5% | -14.3% | time 1205 |

## `h2_displacement` — H2

**Question:** Does the displacement filter contribute anything? 'off' is the null the specification leaves live.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| displacement | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 376 | 42% | +0.037R | 61st | 41st ⚠ below random | 1.11 | 15.7% | +18.4% | time 162, stop 146, target 37, stop_gap 31 |
| 1.0 | 743 | 35% | -0.119R | 1st ⚠ below random | 1st ⚠ below random | 0.89 | 42.1% | -26.9% | stop 330, time 175, target 126, stop_gap 112 |
| 1.5 | 549 | 37% | -0.130R | 15th ⚠ below random | 8th ⚠ below random | 0.97 | 31.5% | -7.8% | stop 237, time 183, target 69, stop_gap 60 |
| None | 917 | 32% | -0.260R | 1st ⚠ below random | 3rd ⚠ below random | 0.86 | 47.5% | -36.6% | stop 419, stop_gap 171, time 170, target 157 |

## `h3_exits` — H3

**Question:** Is there a target and holding period at which sweep-reclaim is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 5 | 1683 | 39% | -0.186R | 0th ⚠ below random | 0th ⚠ below random | 0.78 | 63.2% | -62.1% | time 666, stop 516, stop_gap 308, target 193 |
| 2.5 | 5 | 1736 | 40% | -0.202R | 0th ⚠ below random | 0th ⚠ below random | 0.77 | 67.0% | -66.2% | time 625, stop 548, stop_gap 301, target 262 |
| 2.5 | 10 | 1347 | 37% | -0.205R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 58.1% | -55.6% | stop 511, target 283, time 278, stop_gap 275 |
| 2.0 | 5 | 1815 | 41% | -0.212R | 0th ⚠ below random | 0th ⚠ below random | 0.78 | 66.6% | -65.5% | time 598, stop 540, target 364, stop_gap 313 |
| 2.5 | 20 | 1017 | 35% | -0.217R | 0th ⚠ below random | 0th ⚠ below random | 0.82 | 47.7% | -45.0% | stop 424, target 257, stop_gap 212, time 124 |
| 3.0 | 10 | 1299 | 34% | -0.234R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 65.9% | -64.0% | stop 503, time 294, stop_gap 285, target 217 |
| 2.0 | 20 | 1147 | 37% | -0.238R | 0th ⚠ below random | 0th ⚠ below random | 0.82 | 53.5% | -50.6% | stop 466, target 351, stop_gap 228, time 102 |
| 2.0 | 10 | 1424 | 39% | -0.239R | 0th ⚠ below random | 0th ⚠ below random | 0.79 | 62.2% | -59.0% | stop 519, target 373, stop_gap 277, time 255 |
| 1.5 | 5 | 1963 | 43% | -0.245R | 0th ⚠ below random | 0th ⚠ below random | 0.74 | 74.6% | -73.8% | stop 578, target 538, time 519, stop_gap 328 |
| 1.5 | 10 | 1605 | 42% | -0.247R | 0th ⚠ below random | 0th ⚠ below random | 0.77 | 66.0% | -64.7% | target 555, stop 550, stop_gap 300, time 200 |
| 1.5 | 20 | 1320 | 42% | -0.247R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 58.8% | -57.2% | target 499, stop 491, stop_gap 250, time 80 |
| 1.5 | 15 | 1418 | 42% | -0.261R | 0th ⚠ below random | 0th ⚠ below random | 0.78 | 63.1% | -61.9% | stop 514, target 512, stop_gap 269, time 123 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h3_no_stop` — H3

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 156 | 54% | +1.053R | 39th ⚠ below random | 26th ⚠ below random | 1.59 | 22.3% | +70.9% | time 155, no_volume 1 |
| 20 | 286 | 56% | +0.582R | 17th ⚠ below random | 7th ⚠ below random | 1.15 | 19.3% | +24.7% | time 286 |
| 10 | 547 | 53% | +0.181R | 11th ⚠ below random | 10th ⚠ below random | 1.08 | 18.9% | +18.4% | time 547 |
| 5 | 1027 | 51% | +0.092R | 14th ⚠ below random | 16th ⚠ below random | 1.02 | 27.3% | +6.1% | time 1027 |

## `h3_lookback` — H3

**Question:** Which liquidity reference is swept? Varying the lookback is the cheapest version of that question.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| sweep_lookback | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 44 | 43% | -0.005R | 60th | 29th ⚠ below random | 0.95 | 6.6% | -0.7% | time 27, stop 14, target 2, stop_gap 1 |
| 20 | 603 | 37% | -0.139R | 1st ⚠ below random | 7th ⚠ below random | 0.94 | 22.7% | -12.0% | stop 241, stop_gap 127, target 124, time 111 |
| 5 | 1020 | 32% | -0.256R | 0th ⚠ below random | 0th ⚠ below random | 0.83 | 47.8% | -46.4% | stop 424, stop_gap 242, target 212, time 142 |
| 10 | 1017 | 31% | -0.268R | 0th ⚠ below random | 0th ⚠ below random | 0.74 | 61.2% | -59.9% | stop 466, stop_gap 216, target 210, time 124, no_volume 1 |

## `h1_exit_isolated` — H1

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — NONE:** neither arm produced positive expectancy -- use_stop=False at -0.077R versus use_stop=True at -0.146R, a gap of +0.068R. The comparison still says which is less bad, but nothing here is selectable.

**Isolation held:** arms differ by 0.2% in trade count (1,272 vs 1,274), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 1272 | 51% | -0.077R | 1st ⚠ below random | 0th ⚠ below random | 0.96 | 1.3% | -0.3% | time 1272 |
| True | 1274 | 40% | -0.146R | 0th ⚠ below random | 0th ⚠ below random | 0.85 | 1.0% | -0.9% | time 632, stop 557, stop_gap 85 |

## `h2_exit_isolated` — H2

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.133R versus use_stop=True at -0.160R, a gap of +0.294R, but the arms differ by 27.8% in trade count (11,549 vs 15,995). They did not take the same signals, so this measures exit design and selection together and the gap is not attributable to the exit rule.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 27.8% in trade count (11,549 vs 15,995). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 11549 | 54% | +0.133R | 0th ⚠ below random | 0th ⚠ below random | 1.10 | 8.2% | +5.0% | time 11545, no_volume 4 |
| True | 15995 | 26% | -0.160R | 0th ⚠ below random | 0th ⚠ below random | 0.89 | 8.0% | -5.3% | stop 8491, time 4497, stop_gap 3003, no_volume 4 |

## `h3_exit_isolated` — H3

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.433R versus use_stop=True at -0.095R, a gap of +0.528R, but the arms differ by 30.3% in trade count (5,986 vs 8,588). They did not take the same signals, so this measures exit design and selection together and the gap is not attributable to the exit rule.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 30.3% in trade count (5,986 vs 8,588). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 5986 | 55% | +0.433R | 5th ⚠ below random | 0th ⚠ below random | 1.21 | 4.0% | +5.8% | time 5983, no_volume 3 |
| True | 8588 | 25% | -0.095R | 0th ⚠ below random | 0th ⚠ below random | 0.90 | 3.0% | -2.8% | stop 4584, time 2348, stop_gap 1653, no_volume 3 |

## `h4_exit_isolated` — H4

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.148R versus use_stop=True at -0.187R, a gap of +0.334R, but that gap is 1.5 standard errors on mean per-trade return (paired over 5,884 shared signals, month-clustered) -- under the 2 required.

**Isolation held:** arms differ by 19.2% in trade count (5,964 vs 7,383), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 5964 | 53% | +0.148R | 0th ⚠ below random | 0th ⚠ below random | 1.06 | 4.8% | +1.5% | time 5960, no_volume 4 |
| True | 7383 | 24% | -0.187R | 0th ⚠ below random | 0th ⚠ below random | 0.84 | 4.8% | -3.8% | stop 3945, time 1884, stop_gap 1551, no_volume 3 |

## `h5_exit_isolated` — H5

**Question:** H5 shows +0.055R yet ranks below random selection. With portfolio competition removed so both arms take the same signals, is that the entries or the exit?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=21`

**Verdict — INDISTINCT:** use_stop=False at +0.032R versus use_stop=True at -0.054R, a gap of +0.086R, but that gap is 1.3 standard errors on mean per-trade return (paired over 1,098 shared signals, month-clustered) -- under the 2 required.

**Isolation held:** arms differ by 5.1% in trade count (1,104 vs 1,163), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 1104 | 56% | +0.032R | 33rd ⚠ below random | 1st ⚠ below random | 1.18 | 1.5% | +1.0% | time 1102, no_volume 2 |
| True | 1163 | 43% | -0.054R | 5th ⚠ below random | 0th ⚠ below random | 1.04 | 1.4% | +0.2% | time 565, stop 528, stop_gap 68, no_volume 2 |

## `h4_exits` — H4

**Question:** Is there a target and holding period at which the inverted gap is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 15 | 1172 | 32% | -0.240R | 0th ⚠ below random | 0th ⚠ below random | 0.81 | 55.9% | -55.3% | stop 506, stop_gap 259, target 242, time 165 |
| 3.0 | 10 | 1366 | 34% | -0.259R | 0th ⚠ below random | 0th ⚠ below random | 0.79 | 62.3% | -59.9% | stop 537, stop_gap 311, time 282, target 236 |
| 3.0 | 5 | 1401 | 37% | -0.259R | 0th ⚠ below random | 0th ⚠ below random | 0.71 | 69.9% | -69.3% | time 511, stop 461, stop_gap 267, target 162 |
| 1.5 | 5 | 1569 | 43% | -0.260R | 0th ⚠ below random | 0th ⚠ below random | 0.70 | 71.4% | -71.1% | stop 448, target 434, time 406, stop_gap 281 |
| 2.0 | 5 | 1606 | 40% | -0.265R | 0th ⚠ below random | 0th ⚠ below random | 0.74 | 66.4% | -66.1% | time 495, stop 494, target 317, stop_gap 300 |
| 2.0 | 20 | 1311 | 36% | -0.268R | 1st ⚠ below random | 0th ⚠ below random | 0.85 | 55.5% | -50.7% | stop 533, target 415, stop_gap 291, time 72 |
| 2.0 | 15 | 1430 | 37% | -0.269R | 0th ⚠ below random | 0th ⚠ below random | 0.79 | 65.1% | -63.8% | stop 563, target 440, stop_gap 309, time 118 |
| 2.5 | 10 | 1471 | 35% | -0.274R | 0th ⚠ below random | 0th ⚠ below random | 0.77 | 66.2% | -64.0% | stop 566, stop_gap 331, target 314, time 260 |
| 2.5 | 15 | 964 | 34% | -0.282R | 0th ⚠ below random | 0th ⚠ below random | 0.78 | 58.0% | -54.6% | stop 397, target 234, stop_gap 216, time 117 |
| 2.0 | 10 | 1583 | 38% | -0.287R | 0th ⚠ below random | 0th ⚠ below random | 0.79 | 66.0% | -63.6% | stop 587, target 420, stop_gap 344, time 232 |
| 2.5 | 5 | 1449 | 37% | -0.287R | 0th ⚠ below random | 0th ⚠ below random | 0.72 | 70.4% | -70.0% | time 488, stop 469, stop_gap 276, target 216 |
| 1.5 | 10 | 1275 | 41% | -0.306R | 0th ⚠ below random | 0th ⚠ below random | 0.74 | 64.5% | -64.1% | stop 430, target 425, stop_gap 264, time 156 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h4_no_stop` — H4

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 150 | 59% | +1.216R | 34th ⚠ below random | 27th ⚠ below random | 1.52 | 24.1% | +72.4% | time 150 |
| 20 | 301 | 56% | +0.429R | 45th ⚠ below random | 25th ⚠ below random | 1.28 | 40.0% | +49.9% | time 301 |
| 10 | 588 | 59% | +0.362R | 78th | 51st | 1.29 | 25.1% | +85.0% | time 588 |
| 5 | 1140 | 51% | -0.058R | 6th ⚠ below random | 5th ⚠ below random | 0.94 | 41.1% | -19.1% | time 1140 |

## `h5_momentum_canonical` — H5

**Question:** Does 12-1 momentum -- the version with decades of replication -- work where H1's 63-day no-skip variant did not?

**Held fixed:** `monthly_rebalance=True`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 9 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | top_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 126 | 0.05 | 56 | 38% | +0.367R | 29th ⚠ below random | 28th ⚠ below random | 1.24 | 40.1% | +14.3% | stop 26, time 23, stop_gap 6, no_volume 1 |
| 126 | 0.1 | 63 | 33% | +0.162R | 15th ⚠ below random | 16th ⚠ below random | 1.06 | 40.5% | +4.2% | stop 31, time 23, stop_gap 8, no_volume 1 |
| 126 | 0.2 | 55 | 33% | -0.007R | 8th ⚠ below random | 18th ⚠ below random | 0.92 | 39.5% | -4.1% | stop 30, time 22, stop_gap 3 |
| 63 | 0.05 | 83 | 47% | -0.111R | 7th ⚠ below random | 11th ⚠ below random | 0.86 | 35.0% | -8.5% | time 41, stop 36, stop_gap 6 |
| 63 | 0.2 | 72 | 39% | -0.377R | 0th ⚠ below random | 2nd ⚠ below random | 0.61 | 34.3% | -22.8% | stop 40, time 30, stop_gap 2 |
| 63 | 0.1 | 66 | 36% | -0.528R | 0th ⚠ below random | 0th ⚠ below random | 0.51 | 34.8% | -27.9% | stop 36, time 26, stop_gap 4 |
| 21 | 0.2 | 140 | 49% | -0.665R | 0th ⚠ below random | 0th ⚠ below random | 0.64 | 36.9% | -25.5% | time 88, stop 42, stop_gap 10 |
| 21 | 0.1 | 133 | 47% | -0.719R | 0th ⚠ below random | 0th ⚠ below random | 0.60 | 37.3% | -27.6% | time 83, stop 41, stop_gap 9 |
| 21 | 0.05 | 126 | 48% | -0.729R | 0th ⚠ below random | 0th ⚠ below random | 0.65 | 35.1% | -24.0% | time 78, stop 39, stop_gap 9 |

## `h5_skip_matters` — H5

**Question:** Is the skip month load-bearing, or decoration? skip=0 is H1's formation; skip=21 is the literature's.

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| mom_skip | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 83 | 47% | -0.090R | 14th ⚠ below random | 22nd ⚠ below random | 0.92 | 27.7% | -4.6% | time 42, stop 39, stop_gap 2 |
| 0 | 84 | 44% | -0.184R | 2nd ⚠ below random | 8th ⚠ below random | 0.80 | 31.7% | -12.6% | time 41, stop 37, stop_gap 6 |
| 42 | 65 | 38% | -0.504R | 0th ⚠ below random | 1st ⚠ below random | 0.49 | 38.0% | -27.8% | stop 34, time 26, stop_gap 5 |
| 21 | 66 | 36% | -0.528R | 0th ⚠ below random | 0th ⚠ below random | 0.51 | 34.8% | -27.9% | stop 36, time 26, stop_gap 4 |

## `h5_no_stop` — H5

**Question:** Does momentum survive without a stop, as the literature's version has none at all?

**Held fixed:** `top_pct=0.1`, `use_stop=False`

**Verdict — SPIKE:** 1 of 3 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| hold | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 126 | 29 | 76% | +2.233R | 87th | 89th | 6.97 | 14.0% | +80.5% | time 28, no_volume 1 |
| 63 | 41 | 66% | +0.444R | 27th ⚠ below random | 34th ⚠ below random | 1.40 | 18.3% | +15.2% | time 41 |
| 21 | 100 | 54% | -1.272R | 1st ⚠ below random | 4th ⚠ below random | 0.75 | 38.2% | -16.8% | time 100 |

## `h5_rebalance` — H5

**Question:** Monthly versus daily rebalancing -- does the documented frequency matter, or is it convention?

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — NONE:** neither arm produced positive expectancy -- monthly_rebalance=True at -0.528R versus monthly_rebalance=False at -0.896R, a gap of +0.368R. The comparison still says which is less bad, but nothing here is selectable.

| monthly_rebalance | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| True | 66 | 36% | -0.528R | 0th ⚠ below random | 0th ⚠ below random | 0.51 | 34.8% | -27.9% | stop 36, time 26, stop_gap 4 |
| False | 110 | 34% | -0.896R | 0th ⚠ below random | 0th ⚠ below random | 0.69 | 35.9% | -24.7% | stop 59, time 43, stop_gap 8 |

## `h7_squeeze_exits` — H7

**Question:** Is there a target and holding period where range expansion after compression is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 5 | 777 | 50% | -0.190R | 3rd ⚠ below random | 3rd ⚠ below random | 0.76 | 29.2% | -26.1% | time 756, stop 18, stop_gap 2, target 1 |
| 1.5 | 5 | 777 | 50% | -0.190R | 3rd ⚠ below random | 2nd ⚠ below random | 0.76 | 29.2% | -26.4% | time 756, stop 18, stop_gap 2, target 1 |
| 1.0 | 5 | 782 | 49% | -0.193R | 1st ⚠ below random | 2nd ⚠ below random | 0.76 | 28.3% | -27.2% | time 746, stop 18, target 16, stop_gap 2 |
| 2.5 | 5 | 778 | 50% | -0.193R | 2nd ⚠ below random | 2nd ⚠ below random | 0.75 | 29.2% | -27.9% | time 757, stop 19, stop_gap 2 |
| 3.0 | 5 | 778 | 50% | -0.193R | 2nd ⚠ below random | 2nd ⚠ below random | 0.75 | 29.2% | -27.9% | time 757, stop 19, stop_gap 2 |
| 1.5 | 10 | 431 | 50% | -0.315R | 2nd ⚠ below random | 1st ⚠ below random | 0.81 | 25.9% | -17.2% | time 393, stop 24, target 12, stop_gap 2 |
| 2.0 | 10 | 428 | 50% | -0.315R | 2nd ⚠ below random | 1st ⚠ below random | 0.83 | 24.9% | -15.5% | time 401, stop 21, target 4, stop_gap 2 |
| 3.0 | 10 | 424 | 47% | -0.318R | 2nd ⚠ below random | 1st ⚠ below random | 0.81 | 27.1% | -17.1% | time 401, stop 19, stop_gap 3, target 1 |
| 2.5 | 10 | 426 | 48% | -0.325R | 1st ⚠ below random | 1st ⚠ below random | 0.80 | 25.5% | -18.5% | time 399, stop 22, stop_gap 3, target 2 |
| 1.0 | 10 | 435 | 49% | -0.326R | 0th ⚠ below random | 2nd ⚠ below random | 0.79 | 25.4% | -20.4% | time 385, target 24, stop 23, stop_gap 2, no_volume 1 |
| 1.5 | 20 | 311 | 55% | -0.371R | 16th ⚠ below random | 13th ⚠ below random | 1.02 | 28.7% | +1.2% | time 257, stop 37, target 14, stop_gap 3 |
| 3.0 | 20 | 303 | 56% | -0.376R | 13th ⚠ below random | 8th ⚠ below random | 1.05 | 27.0% | +3.7% | time 265, stop 34, stop_gap 4 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h7_compression_depth` — H7

**Question:** How quiet must it get first? A threshold that only works at one depth is a threshold fitted to noise.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| squeeze_percentile | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.3 | 223 | 58% | +0.091R | 69th | 50th ⚠ below random | 1.47 | 7.3% | +25.2% | time 190, stop 27, stop_gap 5, no_volume 1 |
| 0.4 | 254 | 54% | +0.041R | 40th ⚠ below random | 19th ⚠ below random | 1.18 | 11.2% | +11.2% | time 218, stop 32, stop_gap 4 |
| 0.2 | 303 | 56% | -0.376R | 13th ⚠ below random | 8th ⚠ below random | 1.05 | 27.0% | +3.7% | time 265, stop 34, stop_gap 4 |
| 0.1 | 327 | 52% | -0.382R | 3rd ⚠ below random | 2nd ⚠ below random | 0.92 | 27.1% | -8.1% | time 273, stop 46, stop_gap 7, no_volume 1 |

## `h7_no_stop` — H7

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 766 | 49% | -0.193R | 1st ⚠ below random | 2nd ⚠ below random | 0.76 | 26.8% | -25.7% | time 766 |
| 10 | 497 | 50% | -0.266R | 1st ⚠ below random | 2nd ⚠ below random | 0.86 | 29.8% | -14.5% | time 496, no_volume 1 |
| 20 | 289 | 59% | -0.351R | 48th ⚠ below random | 24th ⚠ below random | 1.18 | 27.3% | +14.5% | time 289 |
| 40 | 146 | 62% | -0.686R | 46th ⚠ below random | 34th ⚠ below random | 1.21 | 30.1% | +15.1% | time 146 |

## `h6_drift_exits` — H6

**Question:** Does price drift after an earnings filing, and over what horizon?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 3 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (time_limit=60, +0.921R) rather than the peak (time_limit=60, +0.921R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 60 | 75 | 69% | +0.921R | 67th | 56th | 2.24 | 17.8% | +78.6% | time 75 |
| 40 | 89 | 61% | +0.544R | 94th | 52nd | 1.97 | 20.3% | +51.5% | time 89 |
| 5 | 117 | 62% | +0.103R | 76th | 69th | 1.39 | 6.7% | +10.9% | time 117 |
| 20 | 104 | 57% | +0.061R | 33rd ⚠ below random | 14th ⚠ below random | 1.06 | 19.6% | +3.0% | time 104 |
| 10 | 112 | 54% | +0.052R | 37th ⚠ below random | 23rd ⚠ below random | 1.11 | 10.9% | +4.6% | time 112 |

## `h6_reaction_size` — H6

**Question:** Does the size of the reaction sort the drift? The literature sorts on surprise; this substitutes the market's response.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 3 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (reaction_pct=0.03, +0.544R) rather than the peak (reaction_pct=0.05, +0.596R) -- the peak's margin over its neighbours is the part least likely to survive.

| reaction_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.05 | 43 | 63% | +0.596R | 89th | 66th | 2.46 | 6.3% | +27.1% | time 43 |
| 0.03 | 89 | 61% | +0.544R | 94th | 52nd | 1.97 | 20.3% | +51.5% | time 89 |
| 0.02 | 92 | 59% | +0.318R | 57th | 21st ⚠ below random | 1.39 | 23.5% | +23.2% | time 92 |
| 0.0 | 108 | 51% | +0.152R | 29th ⚠ below random | 9th ⚠ below random | 1.20 | 22.5% | +13.2% | time 108 |
| 0.08 | 10 | 50% | -0.475R | 18th ⚠ below random | 4th ⚠ below random | 0.37 | 7.2% | -4.7% | time 10 |

## `h6_entry_delay` — H6

**Question:** How much of the drift is gone by the time we could act? A day-one edge that vanishes by day three is not tradeable.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 4 of 4 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (entry_delay=2, +0.618R) rather than the peak (entry_delay=2, +0.618R) -- the peak's margin over its neighbours is the part least likely to survive.

| entry_delay | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 89 | 61% | +0.618R | 95th | 63rd | 2.27 | 19.9% | +60.8% | time 89 |
| 1 | 89 | 61% | +0.544R | 94th | 52nd | 1.97 | 20.3% | +51.5% | time 89 |
| 3 | 89 | 57% | +0.439R | 81st | 31st ⚠ below random | 1.82 | 19.9% | +38.9% | time 89 |
| 5 | 90 | 61% | +0.340R | 74th | 24th ⚠ below random | 1.55 | 20.5% | +27.5% | time 90 |

## Caveats attached to every number above

- The universe is **today's** large caps. No delisted company is present, so every result is inflated by an unknown amount (ADR 0002).
- Ambiguous bars resolve to the stop, gaps fill at the open, and slippage is charged both ways. Those understate results.
- Random-selection percentiles, where present, are the comparison that matters: beating zero is not the test, beating random long exposure is.
