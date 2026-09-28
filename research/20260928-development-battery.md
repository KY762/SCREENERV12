# Development-split battery — development

**Generated:** 2026-09-28 03:26 Eastern Daylight Time
**Window:** 2010-01-01 → 2015-12-31
**Symbols:** 1046  
**Configurations tested:** 180
**Universe:** `sp500_pit` — point-in-time membership  
**Quarantined and excluded:** 25 (ACS, AYE, BBBY, BBT, CA, CAM, CPWR, CSRA, EMC, EP, FB, GENZ, GR, INFO, JAVA, KG, NFX, PARA, PBG, PCL, RX, SHLD, SII, SPLS, UST)  

Those symbols' stored series is not the company that was in the index — see `data/reference/universe_quarantine.csv` for the reason on each. Results generated before 2026-09-19 did not exclude them and are not comparable.

Development-split results carry **no evidential weight** (docs/03-HYPOTHESES.md §0.4). Nothing here confirms a hypothesis; it can only rule things out and suggest what to confirm elsewhere.

## Summary

| Experiment | Kind | Configs | Shape | Best expectancy | vs random (same days) | vs random (any day) | Selected |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `h1_exits` | parameter | 10 | **none** | +0.015R | 2nd ⚠ below random | 3rd ⚠ below random | — |
| `h1_no_stop` | structural | 3 | **none** | +0.185R | 0th ⚠ below random | 2nd ⚠ below random | — |
| `h1_selection` | parameter | 12 | **spike** | +0.122R | 32nd ⚠ below random | 30th ⚠ below random | — |
| `h1_entry_delay` | structural | 3 | **none** | +0.015R | 2nd ⚠ below random | 3rd ⚠ below random | — |
| `h1_trend_filter` | structural | 2 | **indistinct** | +0.015R | 2nd ⚠ below random | 3rd ⚠ below random | — |
| `h2_exits` | parameter | 20 | **none** | -0.196R | 4th ⚠ below random | 4th ⚠ below random | — |
| `h2_no_stop` | structural | 4 | **spike** | +0.796R | 73rd | 48th ⚠ below random | — |
| `h2_displacement` | structural | 4 | **spike** | +0.029R | 67th | 46th ⚠ below random | — |
| `h3_exits` | parameter | 20 | **none** | -0.186R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h3_no_stop` | structural | 4 | **none** | +1.053R | 40th ⚠ below random | 25th ⚠ below random | — |
| `h3_lookback` | structural | 4 | **none** | -0.005R | 60th | 28th ⚠ below random | — |
| `h1_exit_isolated` | structural | 2 | **indistinct** | +0.017R | 6th ⚠ below random | 0th ⚠ below random | — |
| `h2_exit_isolated` | structural | 2 | **indistinct** | +0.167R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h3_exit_isolated` | structural | 2 | **indistinct** | +0.434R | 6th ⚠ below random | 0th ⚠ below random | — |
| `h4_exit_isolated` | structural | 2 | **indistinct** | +0.147R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h5_exit_isolated` | structural | 2 | **indistinct** | +0.160R | 49th ⚠ below random | 1st ⚠ below random | — |
| `h4_exits` | parameter | 20 | **none** | -0.214R | 0th ⚠ below random | 0th ⚠ below random | — |
| `h4_no_stop` | structural | 4 | **none** | +1.216R | 34th ⚠ below random | 29th ⚠ below random | — |
| `h5_momentum_canonical` | parameter | 9 | **spike** | +0.547R | 67th | 38th ⚠ below random | — |
| `h5_skip_matters` | structural | 4 | **plateau** | +0.433R | 80th | 72nd | `mom_skip=0` |
| `h5_no_stop` | structural | 3 | **plateau** | +2.300R | 95th | 88th | `hold=63` |
| `h5_rebalance` | structural | 2 | **indistinct** | +0.199R | 26th ⚠ below random | 25th ⚠ below random | — |
| `h7_squeeze_exits` | parameter | 20 | **spike** | +0.101R | 60th | 40th ⚠ below random | — |
| `h7_compression_depth` | parameter | 4 | **spike** | +0.092R | 54th | 35th ⚠ below random | — |
| `h7_no_stop` | structural | 4 | **plateau** | +0.291R | 91st | 65th | `time_limit=40` |
| `h6_drift_exits` | parameter | 5 | **plateau** | +0.921R | 65th | 56th | `time_limit=60` |
| `h6_reaction_size` | parameter | 5 | **plateau** | +0.596R | 89th | 66th | `reaction_pct=0.03` |
| `h6_entry_delay` | parameter | 4 | **plateau** | +0.618R | 95th | 64th | `entry_delay=2` |

## `h1_exits` — H1

**Question:** Is there any hold horizon and stop width at which momentum rotation is profitable?

**Verdict — NONE:** no configuration of 10 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | stop_atr | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 3.0 | 340 | 48% | +0.015R | 2nd ⚠ below random | 3rd ⚠ below random | 1.01 | 12.4% | +1.3% | time 227, stop 100, stop_gap 9, series_end 4 |
| 20 | 1.5 | 280 | 38% | +0.013R | 18th ⚠ below random | 13th ⚠ below random | 1.03 | 14.8% | +5.2% | stop 140, time 119, stop_gap 19, series_end 2 |
| 10 | 3.0 | 690 | 51% | -0.003R | 1st ⚠ below random | 1st ⚠ below random | 0.97 | 17.3% | -6.0% | time 566, stop 108, stop_gap 13, series_end 3 |
| 20 | 1.0 | 279 | 29% | -0.010R | 37th ⚠ below random | 14th ⚠ below random | 1.01 | 14.1% | +2.3% | stop 150, time 84, stop_gap 43, series_end 2 |
| 10 | 2.5 | 669 | 49% | -0.018R | 0th ⚠ below random | 2nd ⚠ below random | 0.93 | 20.8% | -13.3% | time 497, stop 145, stop_gap 24, series_end 3 |
| 20 | 2.5 | 330 | 44% | -0.022R | 0th ⚠ below random | 1st ⚠ below random | 0.94 | 18.5% | -7.6% | time 192, stop 115, stop_gap 20, series_end 3 |
| 10 | 1.5 | 567 | 43% | -0.023R | 1st ⚠ below random | 5th ⚠ below random | 0.97 | 21.1% | -6.5% | time 307, stop 220, stop_gap 38, series_end 2 |
| 10 | 2.0 | 622 | 47% | -0.031R | 0th ⚠ below random | 1st ⚠ below random | 0.91 | 20.9% | -17.9% | time 405, stop 192, stop_gap 22, series_end 3 |
| 20 | 2.0 | 309 | 41% | -0.031R | 0th ⚠ below random | 2nd ⚠ below random | 0.93 | 17.4% | -9.1% | time 157, stop 129, stop_gap 20, series_end 3 |
| 10 | 1.0 | 564 | 34% | -0.068R | 2nd ⚠ below random | 6th ⚠ below random | 0.93 | 22.6% | -12.7% | stop 263, time 223, stop_gap 76, series_end 2 |

## `h1_no_stop` — H1

**Question:** Is the STOP what loses the money? Same entries, no stop.

**Held fixed:** `use_stop=False`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| hold | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 150 | 53% | +0.185R | 0th ⚠ below random | 2nd ⚠ below random | 1.10 | 22.7% | +15.0% | time 146, series_end 4 |
| 20 | 307 | 52% | +0.106R | 6th ⚠ below random | 5th ⚠ below random | 1.15 | 21.8% | +24.0% | time 303, series_end 4 |
| 10 | 619 | 52% | +0.030R | 4th ⚠ below random | 3rd ⚠ below random | 1.03 | 23.1% | +6.7% | time 616, series_end 3 |

## `h1_selection` — H1

**Question:** Does the momentum lookback or the selection cutoff matter, holding exits fixed?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — SPIKE:** 1 of 12 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| rs_lookback | top_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 0.1 | 343 | 51% | +0.122R | 32nd ⚠ below random | 30th ⚠ below random | 1.32 | 13.1% | +45.8% | time 257, stop 76, stop_gap 7, series_end 3 |
| 21 | 0.2 | 351 | 51% | +0.120R | 33rd ⚠ below random | 28th ⚠ below random | 1.31 | 14.3% | +46.0% | time 263, stop 77, stop_gap 8, series_end 3 |
| 21 | 0.05 | 322 | 50% | +0.113R | 44th ⚠ below random | 29th ⚠ below random | 1.29 | 13.7% | +38.9% | time 239, stop 74, stop_gap 6, series_end 3 |
| 126 | 0.2 | 333 | 53% | +0.101R | 41st ⚠ below random | 29th ⚠ below random | 1.28 | 11.9% | +36.8% | time 238, stop 81, stop_gap 11, series_end 3 |
| 126 | 0.1 | 329 | 53% | +0.100R | 45th ⚠ below random | 29th ⚠ below random | 1.28 | 11.0% | +35.8% | time 235, stop 80, stop_gap 11, series_end 3 |
| 126 | 0.05 | 312 | 52% | +0.088R | 51st | 29th ⚠ below random | 1.25 | 14.8% | +29.3% | time 222, stop 76, stop_gap 11, series_end 3 |
| 252 | 0.1 | 300 | 54% | +0.069R | 14th ⚠ below random | 14th ⚠ below random | 1.16 | 10.6% | +19.7% | time 210, stop 82, stop_gap 8 |
| 252 | 0.2 | 304 | 54% | +0.066R | 11th ⚠ below random | 12th ⚠ below random | 1.16 | 11.3% | +19.6% | time 212, stop 83, stop_gap 8, series_end 1 |
| 252 | 0.05 | 284 | 53% | +0.037R | 9th ⚠ below random | 7th ⚠ below random | 1.08 | 11.0% | +9.5% | time 196, stop 80, stop_gap 8 |
| 63 | 0.1 | 340 | 48% | +0.015R | 2nd ⚠ below random | 3rd ⚠ below random | 1.01 | 12.4% | +1.3% | time 227, stop 100, stop_gap 9, series_end 4 |
| 63 | 0.2 | 345 | 48% | +0.009R | 2nd ⚠ below random | 2nd ⚠ below random | 1.00 | 12.4% | -0.2% | time 230, stop 101, stop_gap 10, series_end 4 |
| 63 | 0.05 | 319 | 47% | -0.004R | 2nd ⚠ below random | 2nd ⚠ below random | 0.96 | 15.6% | -4.4% | time 211, stop 95, stop_gap 9, series_end 4 |

## `h1_entry_delay` — H1

**Question:** Does waiting after the ranking help? Momentum's return is reported absent in the weeks after ranking (Jegadeesh & Titman 1993). Delayed names are re-checked at the last close before the buy and dropped if they no longer rank or trend, so this measures waiting AND re-selection together.

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — NONE:** no configuration of 3 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| entry_delay | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 328 | 50% | +0.015R | 2nd ⚠ below random | 3rd ⚠ below random | 1.02 | 15.3% | +1.3% | time 222, stop 89, stop_gap 14, series_end 3 |
| 1 | 340 | 48% | +0.015R | 2nd ⚠ below random | 3rd ⚠ below random | 1.01 | 12.4% | +1.3% | time 227, stop 100, stop_gap 9, series_end 4 |
| 6 | 317 | 47% | -0.042R | 0th ⚠ below random | 0th ⚠ below random | 0.88 | 23.9% | -14.4% | time 203, stop 95, stop_gap 17, series_end 2 |

## `h1_trend_filter` — H1

**Question:** Does requiring an uptrend help, or is it just fewer trades?

**Held fixed:** `hold=20`, `stop_atr=3.0`

**Verdict — INDISTINCT:** trend_filter=True at +0.015R versus trend_filter=False at +0.004R, a gap of +0.011R, but that gap is 0.0 standard errors on mean per-trade return (unpaired, month-clustered) -- under the 2 required.

| trend_filter | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| True | 340 | 48% | +0.015R | 2nd ⚠ below random | 3rd ⚠ below random | 1.01 | 12.4% | +1.3% | time 227, stop 100, stop_gap 9, series_end 4 |
| False | 351 | 48% | +0.004R | 2nd ⚠ below random | 2nd ⚠ below random | 1.00 | 14.0% | -0.4% | time 231, stop 105, stop_gap 11, series_end 4 |

## `h2_exits` — H2

**Question:** Is there a target and holding period at which the FVG continuation is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.5 | 20 | 1001 | 35% | -0.196R | 4th ⚠ below random | 4th ⚠ below random | 0.88 | 42.9% | -33.0% | stop 433, target 227, stop_gap 180, time 161 |
| 3.0 | 10 | 1288 | 35% | -0.197R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 60.5% | -56.8% | stop 504, time 378, stop_gap 219, target 187 |
| 1.5 | 15 | 1377 | 43% | -0.208R | 3rd ⚠ below random | 3rd ⚠ below random | 0.90 | 44.8% | -38.0% | stop 508, target 481, stop_gap 212, time 176 |
| 3.0 | 5 | 1936 | 39% | -0.213R | 0th ⚠ below random | 0th ⚠ below random | 0.78 | 70.5% | -68.7% | time 829, stop 606, stop_gap 313, target 188 |
| 2.5 | 10 | 1359 | 36% | -0.215R | 0th ⚠ below random | 0th ⚠ below random | 0.79 | 65.5% | -61.9% | stop 535, time 351, target 248, stop_gap 225 |
| 2.0 | 5 | 2090 | 41% | -0.216R | 0th ⚠ below random | 0th ⚠ below random | 0.74 | 75.8% | -74.8% | time 767, stop 645, target 367, stop_gap 311 |
| 2.0 | 15 | 1195 | 38% | -0.219R | 0th ⚠ below random | 1st ⚠ below random | 0.82 | 55.9% | -50.0% | stop 471, target 316, stop_gap 206, time 202 |
| 2.5 | 5 | 1994 | 40% | -0.221R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 72.5% | -71.1% | time 809, stop 620, stop_gap 315, target 250 |
| 1.5 | 20 | 1237 | 43% | -0.222R | 7th ⚠ below random | 4th ⚠ below random | 0.90 | 46.3% | -34.8% | stop 473, target 440, stop_gap 201, time 123 |
| 1.5 | 5 | 2263 | 43% | -0.226R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 74.6% | -73.7% | time 693, stop 670, target 567, stop_gap 333 |
| 1.5 | 10 | 1627 | 42% | -0.236R | 0th ⚠ below random | 0th ⚠ below random | 0.78 | 70.4% | -66.4% | stop 591, target 499, time 297, stop_gap 240 |
| 2.5 | 15 | 1115 | 35% | -0.238R | 0th ⚠ below random | 1st ⚠ below random | 0.85 | 54.6% | -44.8% | stop 459, target 233, time 218, stop_gap 205 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h2_no_stop` — H2

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 166 | 61% | +0.796R | 73rd | 48th ⚠ below random | 1.76 | 21.7% | +113.6% | time 166 |
| 20 | 320 | 53% | +0.343R | 7th ⚠ below random | 6th ⚠ below random | 1.15 | 23.6% | +23.9% | time 320 |
| 10 | 619 | 55% | +0.136R | 32nd ⚠ below random | 22nd ⚠ below random | 1.12 | 32.7% | +30.9% | time 618, series_end 1 |
| 5 | 1205 | 50% | +0.008R | 5th ⚠ below random | 6th ⚠ below random | 0.96 | 28.0% | -15.1% | time 1205 |

## `h2_displacement` — H2

**Question:** Does the displacement filter contribute anything? 'off' is the null the specification leaves live.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| displacement | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2.0 | 376 | 42% | +0.029R | 67th | 46th ⚠ below random | 1.12 | 15.8% | +20.6% | time 164, stop 148, target 35, stop_gap 29 |
| 1.5 | 546 | 38% | -0.093R | 7th ⚠ below random | 8th ⚠ below random | 0.96 | 33.0% | -8.4% | stop 230, time 184, target 69, stop_gap 63 |
| 1.0 | 746 | 36% | -0.172R | 1st ⚠ below random | 0th ⚠ below random | 0.83 | 45.6% | -40.6% | stop 335, time 178, target 120, stop_gap 112, series_end 1 |
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
| 40 | 156 | 54% | +1.053R | 40th ⚠ below random | 25th ⚠ below random | 1.59 | 22.3% | +70.9% | time 155, no_volume 1 |
| 20 | 286 | 56% | +0.582R | 17th ⚠ below random | 11th ⚠ below random | 1.15 | 19.3% | +24.7% | time 286 |
| 10 | 547 | 53% | +0.181R | 11th ⚠ below random | 8th ⚠ below random | 1.08 | 18.9% | +18.4% | time 547 |
| 5 | 1027 | 51% | +0.092R | 14th ⚠ below random | 15th ⚠ below random | 1.02 | 27.3% | +6.1% | time 1027 |

## `h3_lookback` — H3

**Question:** Which liquidity reference is swept? Varying the lookback is the cheapest version of that question.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| sweep_lookback | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 44 | 43% | -0.005R | 60th | 28th ⚠ below random | 0.95 | 6.6% | -0.7% | time 27, stop 14, target 2, stop_gap 1 |
| 20 | 732 | 37% | -0.102R | 1st ⚠ below random | 5th ⚠ below random | 0.94 | 22.7% | -13.7% | stop 294, target 159, stop_gap 150, time 128, series_end 1 |
| 5 | 1020 | 32% | -0.256R | 0th ⚠ below random | 0th ⚠ below random | 0.83 | 47.8% | -46.4% | stop 424, stop_gap 242, target 212, time 142 |
| 10 | 1017 | 31% | -0.268R | 0th ⚠ below random | 0th ⚠ below random | 0.74 | 61.2% | -59.9% | stop 466, stop_gap 216, target 210, time 124, no_volume 1 |

## `h1_exit_isolated` — H1

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.017R versus use_stop=True at -0.051R, a gap of +0.068R, but that gap is 0.8 standard errors on mean per-trade return (paired over 1,275 shared signals, month-clustered) -- under the 2 required.

**Isolation held:** arms differ by 0.1% in trade count (1,275 vs 1,276), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 1275 | 52% | +0.017R | 6th ⚠ below random | 0th ⚠ below random | 0.99 | 1.1% | -0.1% | time 1271, series_end 4 |
| True | 1276 | 40% | -0.051R | 0th ⚠ below random | 0th ⚠ below random | 0.88 | 0.9% | -0.7% | time 631, stop 557, stop_gap 85, series_end 3 |

## `h2_exit_isolated` — H2

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.167R versus use_stop=True at -0.136R, a gap of +0.302R, but the arms differ by 27.7% in trade count (11,554 vs 15,990). They did not take the same signals, so this measures exit design and selection together and the gap is not attributable to the exit rule.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 27.7% in trade count (11,554 vs 15,990). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 11554 | 54% | +0.167R | 0th ⚠ below random | 0th ⚠ below random | 1.10 | 8.1% | +5.3% | time 11535, series_end 15, no_volume 4 |
| True | 15990 | 26% | -0.136R | 0th ⚠ below random | 0th ⚠ below random | 0.90 | 7.8% | -5.1% | stop 8486, time 4493, stop_gap 2998, series_end 9, no_volume 4 |

## `h3_exit_isolated` — H3

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.434R versus use_stop=True at -0.094R, a gap of +0.528R, but the arms differ by 30.2% in trade count (5,993 vs 8,590). They did not take the same signals, so this measures exit design and selection together and the gap is not attributable to the exit rule.

**ISOLATION FAILED — do not read this as an exit-rule result.** The arms differ by 30.2% in trade count (5,993 vs 8,590). A stop frees its slot early, so the arms took different signals and this measures exit design and selection together -- the confound of docs/07. Raise `max_positions` until the counts converge.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 5993 | 55% | +0.434R | 6th ⚠ below random | 0th ⚠ below random | 1.21 | 4.0% | +5.8% | time 5982, series_end 8, no_volume 3 |
| True | 8590 | 25% | -0.094R | 0th ⚠ below random | 0th ⚠ below random | 0.90 | 3.0% | -2.8% | stop 4582, time 2348, stop_gap 1653, series_end 4, no_volume 3 |

## `h4_exit_isolated` — H4

**Question:** With portfolio competition removed so both arms take the same signals, does the stop help or cost?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=20`

**Verdict — INDISTINCT:** use_stop=False at +0.147R versus use_stop=True at -0.186R, a gap of +0.334R, but that gap is 1.5 standard errors on mean per-trade return (paired over 5,885 shared signals, month-clustered) -- under the 2 required.

**Isolation held:** arms differ by 19.2% in trade count (5,963 vs 7,377), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 5963 | 53% | +0.147R | 0th ⚠ below random | 0th ⚠ below random | 1.06 | 4.8% | +1.5% | time 5956, no_volume 4, series_end 3 |
| True | 7377 | 24% | -0.186R | 0th ⚠ below random | 0th ⚠ below random | 0.84 | 4.8% | -3.8% | stop 3943, time 1882, stop_gap 1548, no_volume 3, series_end 1 |

## `h5_exit_isolated` — H5

**Question:** H5 shows +0.055R yet ranks below random selection. With portfolio competition removed so both arms take the same signals, is that the entries or the exit?

**Held fixed:** `equity=5000000.0`, `max_open_risk_pct=0.6`, `max_position_pct=0.002`, `max_positions=400`, `r_multiple=0.0`, `risk_pct_per_trade=0.0005`, `time_limit=21`

**Verdict — INDISTINCT:** use_stop=False at +0.160R versus use_stop=True at +0.069R, a gap of +0.092R, but that gap is 1.3 standard errors on mean per-trade return (paired over 1,106 shared signals, month-clustered) -- under the 2 required.

**Isolation held:** arms differ by 5.0% in trade count (1,112 vs 1,171), so both took substantially the same signals and the difference is the exit rule.

| use_stop | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 1112 | 56% | +0.160R | 49th ⚠ below random | 1st ⚠ below random | 1.22 | 1.3% | +1.2% | time 1100, series_end 10, no_volume 2 |
| True | 1171 | 43% | +0.069R | 12th ⚠ below random | 1st ⚠ below random | 1.08 | 1.2% | +0.4% | time 563, stop 528, stop_gap 68, series_end 10, no_volume 2 |

## `h4_exits` — H4

**Question:** Is there a target and holding period at which the inverted gap is profitable?

**Verdict — NONE:** no configuration of 20 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3.0 | 5 | 1905 | 37% | -0.214R | 0th ⚠ below random | 0th ⚠ below random | 0.75 | 73.1% | -71.3% | time 663, stop 615, stop_gap 381, target 246 |
| 2.5 | 5 | 1971 | 38% | -0.230R | 0th ⚠ below random | 0th ⚠ below random | 0.76 | 73.1% | -71.2% | time 631, stop 625, stop_gap 392, target 323 |
| 3.0 | 15 | 1163 | 32% | -0.240R | 0th ⚠ below random | 0th ⚠ below random | 0.82 | 53.9% | -52.3% | stop 500, stop_gap 256, target 242, time 165 |
| 2.5 | 15 | 1283 | 33% | -0.249R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 60.7% | -58.4% | stop 535, target 328, stop_gap 283, time 137 |
| 3.0 | 10 | 1368 | 34% | -0.263R | 0th ⚠ below random | 0th ⚠ below random | 0.79 | 62.3% | -59.9% | stop 538, stop_gap 312, time 282, target 236 |
| 2.0 | 5 | 2093 | 39% | -0.264R | 0th ⚠ below random | 0th ⚠ below random | 0.72 | 79.0% | -78.0% | stop 655, time 590, target 445, stop_gap 403 |
| 3.0 | 20 | 1061 | 31% | -0.266R | 0th ⚠ below random | 0th ⚠ below random | 0.84 | 55.8% | -48.2% | stop 471, stop_gap 251, target 229, time 110 |
| 2.0 | 10 | 1579 | 38% | -0.267R | 0th ⚠ below random | 0th ⚠ below random | 0.81 | 62.7% | -59.4% | stop 579, target 430, stop_gap 338, time 232 |
| 2.0 | 20 | 1311 | 36% | -0.268R | 1st ⚠ below random | 0th ⚠ below random | 0.85 | 55.5% | -50.7% | stop 533, target 415, stop_gap 291, time 72 |
| 2.0 | 15 | 1426 | 37% | -0.274R | 0th ⚠ below random | 0th ⚠ below random | 0.80 | 64.6% | -63.3% | stop 560, target 436, stop_gap 312, time 118 |
| 1.5 | 5 | 2243 | 42% | -0.276R | 0th ⚠ below random | 0th ⚠ below random | 0.68 | 84.9% | -84.6% | stop 665, target 642, time 515, stop_gap 420, series_end 1 |
| 2.5 | 10 | 1465 | 35% | -0.278R | 0th ⚠ below random | 0th ⚠ below random | 0.77 | 66.1% | -64.0% | stop 563, stop_gap 330, target 310, time 262 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h4_no_stop` — H4

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — NONE:** no configuration of 4 was positive and beat random on the same days. Per docs/03 0.7 rule 4 this is evidence against the hypothesis, not an invitation to widen the search.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 150 | 59% | +1.216R | 34th ⚠ below random | 29th ⚠ below random | 1.52 | 24.1% | +72.4% | time 150 |
| 20 | 301 | 57% | +0.546R | 28th ⚠ below random | 14th ⚠ below random | 1.18 | 37.9% | +35.4% | time 301 |
| 10 | 587 | 57% | +0.235R | 35th ⚠ below random | 21st ⚠ below random | 1.14 | 26.7% | +39.3% | time 587 |
| 5 | 1139 | 51% | -0.056R | 8th ⚠ below random | 7th ⚠ below random | 0.94 | 38.8% | -18.8% | time 1139 |

## `h5_momentum_canonical` — H5

**Question:** Does 12-1 momentum -- the version with decades of replication -- work where H1's 63-day no-skip variant did not?

**Held fixed:** `monthly_rebalance=True`, `stop_atr=3.0`

**Verdict — SPIKE:** 2 of 9 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| hold | top_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 126 | 0.05 | 91 | 40% | +0.547R | 67th | 38th ⚠ below random | 1.71 | 17.1% | +53.7% | stop 40, time 31, stop_gap 13, series_end 6, no_volume 1 |
| 126 | 0.1 | 91 | 40% | +0.528R | 52nd | 34th ⚠ below random | 1.72 | 18.9% | +56.0% | stop 41, time 31, stop_gap 12, series_end 6, no_volume 1 |
| 126 | 0.2 | 94 | 38% | +0.487R | 46th ⚠ below random | 36th ⚠ below random | 1.72 | 19.2% | +54.0% | stop 46, time 32, stop_gap 9, series_end 6, no_volume 1 |
| 63 | 0.05 | 140 | 45% | +0.233R | 34th ⚠ below random | 25th ⚠ below random | 1.40 | 17.2% | +36.2% | time 59, stop 59, stop_gap 14, series_end 7, no_volume 1 |
| 63 | 0.1 | 148 | 45% | +0.199R | 26th ⚠ below random | 25th ⚠ below random | 1.37 | 18.1% | +30.3% | time 64, stop 64, stop_gap 12, series_end 7, no_volume 1 |
| 63 | 0.2 | 151 | 45% | +0.185R | 26th ⚠ below random | 19th ⚠ below random | 1.33 | 19.6% | +27.3% | stop 66, time 65, stop_gap 12, series_end 7, no_volume 1 |
| 21 | 0.2 | 284 | 52% | +0.087R | 13th ⚠ below random | 17th ⚠ below random | 1.21 | 12.5% | +22.4% | time 191, stop 73, stop_gap 12, series_end 7, no_volume 1 |
| 21 | 0.1 | 278 | 51% | +0.079R | 16th ⚠ below random | 13th ⚠ below random | 1.19 | 13.0% | +20.0% | time 185, stop 73, stop_gap 12, series_end 7, no_volume 1 |
| 21 | 0.05 | 259 | 51% | +0.062R | 23rd ⚠ below random | 9th ⚠ below random | 1.14 | 13.0% | +13.7% | time 168, stop 71, stop_gap 12, series_end 7, no_volume 1 |

## `h5_skip_matters` — H5

**Question:** Is the skip month load-bearing, or decoration? skip=0 is H1's formation; skip=21 is the literature's.

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — PLATEAU:** 1 of 2 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (mom_skip=0, +0.331R) rather than the peak (mom_skip=5, +0.433R) -- the peak's margin over its neighbours is the part least likely to survive.

| mom_skip | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5 | 147 | 50% | +0.433R | 80th | 72nd | 1.84 | 10.3% | +76.8% | time 68, stop 59, stop_gap 11, series_end 8, no_volume 1 |
| 0 | 146 | 48% | +0.331R | 59th | 46th ⚠ below random | 1.63 | 12.6% | +53.1% | time 67, stop 59, stop_gap 11, series_end 8, no_volume 1 |
| 21 | 148 | 45% | +0.199R | 26th ⚠ below random | 25th ⚠ below random | 1.37 | 18.1% | +30.3% | time 64, stop 64, stop_gap 12, series_end 7, no_volume 1 |
| 42 | 154 | 42% | +0.109R | 11th ⚠ below random | 9th ⚠ below random | 1.17 | 21.0% | +14.6% | stop 73, time 60, stop_gap 12, series_end 8, no_volume 1 |

## `h5_no_stop` — H5

**Question:** Does momentum survive without a stop, as the literature's version has none at all?

**Held fixed:** `top_pct=0.1`, `use_stop=False`

**Verdict — PLATEAU:** 3 of 3 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (hold=63, +0.942R) rather than the peak (hold=126, +2.300R) -- the peak's margin over its neighbours is the part least likely to survive.

| hold | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 126 | 54 | 80% | +2.300R | 95th | 88th | 6.64 | 16.8% | +181.1% | time 47, series_end 6, no_volume 1 |
| 63 | 102 | 70% | +0.942R | 82nd | 72nd | 2.32 | 18.3% | +117.5% | time 96, series_end 5, no_volume 1 |
| 21 | 238 | 61% | +0.334R | 90th | 72nd | 1.89 | 20.2% | +98.8% | time 230, series_end 7, no_volume 1 |

## `h5_rebalance` — H5

**Question:** Monthly versus daily rebalancing -- does the documented frequency matter, or is it convention?

**Held fixed:** `hold=63`, `stop_atr=3.0`

**Verdict — INDISTINCT:** monthly_rebalance=True at +0.199R versus monthly_rebalance=False at +0.135R, a gap of +0.064R, but that gap is 0.4 standard errors on mean per-trade return (unpaired, month-clustered) -- under the 2 required.

| monthly_rebalance | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| True | 148 | 45% | +0.199R | 26th ⚠ below random | 25th ⚠ below random | 1.37 | 18.1% | +30.3% | time 64, stop 64, stop_gap 12, series_end 7, no_volume 1 |
| False | 206 | 38% | +0.135R | 3rd ⚠ below random | 6th ⚠ below random | 1.21 | 17.4% | +27.7% | stop 98, time 85, stop_gap 16, series_end 7 |

## `h7_squeeze_exits` — H7

**Question:** Is there a target and holding period where range expansion after compression is profitable?

**Verdict — SPIKE:** 1 of 20 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| r_multiple | time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 20 | 411 | 57% | +0.101R | 60th | 40th ⚠ below random | 1.45 | 8.3% | +47.6% | time 278, target 76, stop 44, stop_gap 9, series_end 3, no_volume 1 |
| 3.0 | 20 | 372 | 56% | +0.091R | 30th ⚠ below random | 21st ⚠ below random | 1.37 | 9.0% | +35.6% | time 317, stop 46, stop_gap 6, series_end 2, target 1 |
| 2.0 | 20 | 376 | 55% | +0.089R | 16th ⚠ below random | 16th ⚠ below random | 1.36 | 8.5% | +34.6% | time 314, stop 48, target 7, stop_gap 5, series_end 2 |
| 2.5 | 20 | 371 | 55% | +0.082R | 16th ⚠ below random | 17th ⚠ below random | 1.35 | 9.6% | +32.6% | time 318, stop 44, stop_gap 5, series_end 2, target 2 |
| 1.5 | 20 | 383 | 55% | +0.076R | 27th ⚠ below random | 25th ⚠ below random | 1.31 | 10.4% | +30.6% | time 304, stop 50, target 18, stop_gap 8, series_end 3 |
| 1.5 | 15 | 489 | 57% | +0.069R | 45th ⚠ below random | 28th ⚠ below random | 1.32 | 13.0% | +37.6% | time 417, stop 44, target 17, stop_gap 7, series_end 4 |
| 1.0 | 15 | 501 | 55% | +0.065R | 48th ⚠ below random | 27th ⚠ below random | 1.30 | 16.0% | +36.2% | time 385, target 60, stop 49, series_end 3, stop_gap 3, no_volume 1 |
| 2.0 | 15 | 485 | 56% | +0.052R | 26th ⚠ below random | 19th ⚠ below random | 1.23 | 12.8% | +26.2% | time 417, stop 47, stop_gap 10, target 7, series_end 4 |
| 3.0 | 15 | 484 | 54% | +0.045R | 19th ⚠ below random | 12th ⚠ below random | 1.18 | 12.4% | +21.0% | time 423, stop 47, stop_gap 8, series_end 5, target 1 |
| 2.5 | 15 | 486 | 54% | +0.039R | 19th ⚠ below random | 12th ⚠ below random | 1.15 | 12.4% | +17.7% | time 419, stop 50, stop_gap 8, series_end 5, target 4 |
| 2.0 | 10 | 679 | 52% | +0.035R | 31st ⚠ below random | 19th ⚠ below random | 1.15 | 14.6% | +22.7% | time 623, stop 42, target 7, series_end 3, stop_gap 3, no_volume 1 |
| 3.0 | 10 | 674 | 51% | +0.033R | 29th ⚠ below random | 13th ⚠ below random | 1.14 | 15.9% | +20.4% | time 627, stop 41, series_end 3, stop_gap 2, no_volume 1 |

*8 further configuration(s) omitted from this table; all are present in the JSON.*

## `h7_compression_depth` — H7

**Question:** How quiet must it get first? A threshold that only works at one depth is a threshold fitted to noise.

**Held fixed:** `r_multiple=3.0`, `time_limit=20`

**Verdict — SPIKE:** 1 of 4 cells were positive and beat random on the same days, but none has neighbours that also were. One value working while its neighbours fail is what noise looks like. Per docs/03 0.7 rule 3, the peak is not selectable.

| squeeze_percentile | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.3 | 377 | 58% | +0.092R | 54th | 35th ⚠ below random | 1.42 | 12.6% | +41.0% | time 322, stop 45, stop_gap 6, series_end 3, no_volume 1 |
| 0.2 | 372 | 56% | +0.091R | 30th ⚠ below random | 21st ⚠ below random | 1.37 | 9.0% | +35.6% | time 317, stop 46, stop_gap 6, series_end 2, target 1 |
| 0.1 | 370 | 52% | +0.070R | 19th ⚠ below random | 16th ⚠ below random | 1.25 | 10.6% | +26.8% | time 310, stop 52, stop_gap 5, series_end 1, target 1, no_volume 1 |
| 0.4 | 384 | 54% | +0.045R | 38th ⚠ below random | 18th ⚠ below random | 1.21 | 13.3% | +19.7% | time 325, stop 48, stop_gap 8, series_end 2, target 1 |

## `h7_no_stop` — H7

**Question:** Same entries with no stop -- entry rule or exit design?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 2 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (time_limit=40, +0.291R) rather than the peak (time_limit=40, +0.291R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 40 | 182 | 65% | +0.291R | 91st | 65th | 1.86 | 16.2% | +59.6% | time 178, series_end 4 |
| 20 | 352 | 58% | +0.149R | 74th | 48th ⚠ below random | 1.60 | 11.9% | +57.0% | time 350, series_end 2 |
| 10 | 661 | 52% | +0.042R | 40th ⚠ below random | 24th ⚠ below random | 1.21 | 11.7% | +28.8% | time 657, series_end 3, no_volume 1 |
| 5 | 1196 | 49% | -0.002R | 11th ⚠ below random | 5th ⚠ below random | 0.98 | 10.8% | -4.3% | time 1193, series_end 3 |

## `h6_drift_exits` — H6

**Question:** Does price drift after an earnings filing, and over what horizon?

**Held fixed:** `r_multiple=0.0`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 3 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (time_limit=60, +0.921R) rather than the peak (time_limit=60, +0.921R) -- the peak's margin over its neighbours is the part least likely to survive.

| time_limit | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 60 | 75 | 69% | +0.921R | 65th | 56th | 2.24 | 17.8% | +78.6% | time 75 |
| 40 | 89 | 61% | +0.544R | 93rd | 54th | 1.97 | 20.3% | +51.5% | time 89 |
| 5 | 117 | 62% | +0.103R | 76th | 72nd | 1.39 | 6.7% | +10.9% | time 117 |
| 20 | 104 | 57% | +0.061R | 32nd ⚠ below random | 12th ⚠ below random | 1.06 | 19.6% | +3.0% | time 104 |
| 10 | 112 | 54% | +0.052R | 37th ⚠ below random | 25th ⚠ below random | 1.11 | 10.9% | +4.6% | time 112 |

## `h6_reaction_size` — H6

**Question:** Does the size of the reaction sort the drift? The literature sorts on surprise; this substitutes the market's response.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 1 of 3 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (reaction_pct=0.03, +0.544R) rather than the peak (reaction_pct=0.05, +0.596R) -- the peak's margin over its neighbours is the part least likely to survive.

| reaction_pct | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.05 | 43 | 63% | +0.596R | 89th | 66th | 2.46 | 6.3% | +27.1% | time 43 |
| 0.03 | 89 | 61% | +0.544R | 93rd | 54th | 1.97 | 20.3% | +51.5% | time 89 |
| 0.02 | 92 | 59% | +0.318R | 57th | 19th ⚠ below random | 1.39 | 23.5% | +23.2% | time 92 |
| 0.0 | 108 | 51% | +0.152R | 29th ⚠ below random | 10th ⚠ below random | 1.20 | 22.5% | +13.2% | time 108 |
| 0.08 | 10 | 50% | -0.475R | 18th ⚠ below random | 7th ⚠ below random | 0.37 | 7.2% | -4.7% | time 10 |

## `h6_entry_delay` — H6

**Question:** How much of the drift is gone by the time we could act? A day-one edge that vanishes by day three is not tradeable.

**Held fixed:** `r_multiple=0.0`, `time_limit=40`, `use_stop=False`

**Verdict — PLATEAU:** 4 of 4 qualifying cells sit inside a qualifying neighbourhood (positive and beat random on the same days). Selected the plateau centre (entry_delay=2, +0.618R) rather than the peak (entry_delay=2, +0.618R) -- the peak's margin over its neighbours is the part least likely to survive.

| entry_delay | Trades | Win% | Expectancy | vs random (same days) | vs random (any day) | PF | MaxDD | Return | Exits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 89 | 61% | +0.618R | 95th | 64th | 2.27 | 19.9% | +60.8% | time 89 |
| 1 | 89 | 61% | +0.544R | 93rd | 54th | 1.97 | 20.3% | +51.5% | time 89 |
| 3 | 89 | 57% | +0.439R | 82nd | 32nd ⚠ below random | 1.82 | 19.9% | +38.9% | time 89 |
| 5 | 90 | 61% | +0.340R | 73rd | 20th ⚠ below random | 1.55 | 20.5% | +27.5% | time 90 |

## Caveats attached to every number above

- The universe is **today's** large caps. No delisted company is present, so every result is inflated by an unknown amount (ADR 0002).
- Ambiguous bars resolve to the stop, gaps fill at the open, and slippage is charged both ways. Those understate results.
- Random-selection percentiles, where present, are the comparison that matters: beating zero is not the test, beating random long exposure is.
