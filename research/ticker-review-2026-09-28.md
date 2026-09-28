# Ticker review, 2026-09-28

**For the operator.** Tickers whose stored prices match an EODHD `_OLD` record
under a different company's name, with no trading hole for the 60-day gap rule
to cut at. Only the 14 that were ever in `swing_small_mid` during 2010-2019
are listed: those are the ones that can change a development or validation
result. 25 more matter only for the sealed test split (2020 onward) and can
wait.

How the list was built: 96 tickers match their `_OLD` twin on price. 24 are
already cut in two by the gap rule where the twin ends, 3 are quarantined, 33
carry the same company name on both records, and 39 have a name mismatch
with no hole. Of those 39, these 14 were universe members before 2020.

**The "price on the date" column is the stored close as actually traded.**
Compare it with what the named company really traded at on that day. The
"likely" column is Claude's recollection of each company's history, which is
exactly the kind of claim that should be checked, not trusted: it is there to
make the check quick.

| ticker | stored as | `_OLD` record says | price on the date | universe days dev / val | likely | suggested |
| --- | --- | --- | --- | --- | --- | --- |
| TTE | TotalEnergies ADR | a Treasury futures ETF | $44.95, 2012-06-29 | 1510 / 1006 | Total's own history (ticker was TOT until 2021); `_OLD` record mislabelled | keep |
| AD | Array Digital Infrastructure | Ahold Delhaize | $38.62, 2012-06-29 | 1493 / 1006 | US Cellular's history (renamed Array Digital 2025); `_OLD` mislabelled | keep |
| ZD | Ziff Davis | (no name) | $22.96, 2012-06-29 | 1510 / 948 | j2 Global's history (renamed Ziff Davis 2021) | keep |
| CCE | Coca-Cola European Partners | Coca-Cola Enterprises | $28.04, 2012-06-29 | 1510 / 721 | Coca-Cola Enterprises to 2016, then the merged CCEP; the 2016 merger paid cash as well as shares | **look**: a real corporate event, not a rename |
| OAS | Oasis Petroleum | (no name) | $24.18, 2012-06-29 | 1145 / 861 | Oasis throughout, but the 2020 bankruptcy cancelled the old shares; a 199x jump on 2020-11-20 | **cut at 2020-10-09** (42-day hole, under the 60-day rule) |
| COR | Cencora | CoreSite Realty | $39.35, 2012-06-29 | 1215 / 213 | AmerisourceBergen's history (renamed Cencora 2023); `_OLD` mislabelled | keep |
| TEN | Tsakos Energy Navigation | Tenneco | $4.87, 2012-06-29 | 822 / 162 | Tsakos's history (ticker was TNP); Tenneco traded far higher; `_OLD` mislabelled | keep |
| POL | Polished.com | PolyOne | $43.22, 2018-06-29 | 0 / 744 | **PolyOne** in 2016-2020 (PolyOne became Avient in 2020), Polished.com later: a handover with no hole | **cut at 2020-07-22** |
| PENG | Penguin Solutions | Prima Energy | $31.87, 2018-06-29 | 0 / 405 | SMART Global's history from its 2017 IPO (renamed Penguin 2024); `_OLD` mislabelled | keep |
| SOL | Emeren Group | ReneSola | $1.26, 2012-06-29 | 377 / 0 | ReneSola, renamed Emeren; same company | keep |
| HHH | Howard Hughes Holdings | a real-estate ETF | $61.64, 2012-06-29 | 335 / 0 | Howard Hughes's own history; `_OLD` mislabelled | keep |
| LGF | Lions Gate | (no name) | **$0.66 on 4,000 shares**, 2018-06-18 | 0 / 236 | Lions Gate until its December 2016 share-class split, then something else; already cut into 7 pieces | **quarantine the post-2016 series**; the $5 price floor keeps it out of the universe already |
| ID | PARTS iD | Onyx Enterprises (its former name) | $9.62, 2018-06-29 | 0 / 59 | the SPAC shell that became PARTS iD; same listed entity | keep |
| STEL | Stellar Bancorp | StellarOne | $33.05, 2018-06-29 | 0 / 33 | CBTX's history (CBTX was the legal survivor of the 2022 merger that formed Stellar) | keep |

**If these readings hold:** 10 are renames, where the vendor filed the
company's own history under its new ticker. Those are harmless for price
research. Four need something done:

- **POL and OAS need a manual cut date.** The gap rule cannot see them, and
  there is no mechanism yet for a hand-entered cut. It would be a small
  reference file read by the same code that makes the 60-day cuts.
- **LGF** fits the existing quarantine.
- **CCE** is a judgement: the merger was a real event, and whether to treat it
  as one security depends on whether a strategy could have held through it.

Evidence behind the table: `ticker-review-2026-09-28.json` beside this file,
one record per price-matched ticker (both names and ranges, shared days,
pieces after the gap rule, largest adjusted one-day move, universe days by
split). The twin-matching method is described in the 2026-09-24 commits on
`diagnostics/stale_series.py`.
