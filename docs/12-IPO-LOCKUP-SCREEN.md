# H9 — the IPO lock-up expiry screen

**Written 2026-10-03.** Like H8, this does not try to pick winners. It asks
whether a name recently freed from its IPO lock-up underperforms the market
in the days right after, which would make it a name to avoid or trim rather
than one to buy.

> In the trading days right after an IPO's lock-up expires, does the stock
> underperform a same-day pool of other names, net of costs?

## 0. Why this is askable now, and why it was not before

A research pass across this vault found that `calc/fundamentals.py`'s
`net_share_issuance` signal -- the project's existing dilution screen --
requires a `shares_outstanding` filing from roughly one year before the
signal date (`_paired`/`year_earlier`, `YEAR_TOLERANCE_DAYS = 100`). A stock
that IPO'd within the trailing twelve months has no such filing and
structurally returns no signal there. That leaves the lock-up-expiry
literature -- which is specifically ABOUT a stock's first year -- genuinely
untested in this project. It is not a variant of anything H1-H8 already ran.

## 1. The literature

- **Loughran & Ritter (1995)**, *Journal of Finance*: 4,753 US IPOs,
  1970-1990, underperform over a 5-year holding period. Long-horizon; not
  what this module tests (see section 2), but the reason to expect an
  IPO's shares to be systematically mispriced in the first place.
- **Field & Hanka (2001)**, *Journal of Finance*, "The Expiration of IPO
  Share Lockups": 1,948 lock-up expirations, 1988-1997. A roughly -1.5%
  abnormal return over the THREE trading days around expiry, trading
  volume up about 40% permanently afterward, the effect larger for
  VC-backed firms. This is the effect this module tests, on its own
  horizon.

**Where this project's use differs from the papers' own.** Both studied the
whole US market; this project's universe is whatever is in its own
database (see section 3). Field & Hanka's sample is 1988-1997, a different
regulatory and market-structure regime from this project's 2010-2015
development split (Reg NMS, decimalization, and a lock-up convention that
had mostly standardized on 180 days by 2010, against the 90-180-day mix
their sample saw). L&R's 5-year holding period is not tested here at all --
testing it would need bars years past each IPO, most of which this
project's development split does not contain for a 2010-2015-era IPO.

## 2. Feasibility: is a lock-up expiry date actually obtainable here?

**Checked 2026-10-03, before any code was written against it.** Two routes
were evaluated, as the task required:

- **Jay Ritter's IPO data** (site.warrington.ufl.edu/ritter). Fetched and
  read directly: it lists IPO dates, offer prices, first-day closes and
  some underwriter data. **It does not list lock-up terms at all** -- not
  the length, not the expiry date. Confirmed absent, not merely unread.
- **SEC EDGAR full text search** (`efts.sec.gov`). Works, is free, and
  needs no key beyond the fair-access User-Agent this project already
  sets (`SEC_USER_AGENT`). A lock-up's length in days is disclosed in the
  IPO prospectus itself (424B1 through 424B5, whichever Rule 424(b)
  paragraph applies) under "Underwriting," stated as an explicit number of
  days -- not assumed. Confirmed against real filings, not just the API
  shape: Textura Corp's 2013-06-06 424B4 states "180 days after the date
  of this prospectus"; Terreno Realty's 2010-02-10 424B1 and Generac's and
  Ironwood Pharmaceuticals' and QuinStreet's 2010-02 filings all state
  their own lengths the same way, each independently confirmed against the
  live document.

**So: feasible, but not cheaply, and not from a free structured dataset.**
It needed a purpose-built extraction pipeline (`src/screener/ingest/
lockups.py`), not a download. Two identification methods were tried, in
order, because the first one failed on this project's own data:

1. **By company name**, searching EDGAR's historical registrant index
   (`browse-edgar?action=getcompany`), which -- unlike
   `EdgarProvider.cik_for`'s CURRENT ticker-to-CIK map -- finds a filer
   whether or not it still exists today. This still was not enough: a
   15-candidate pilot found `symbols.name` empty for 13 of 15 in this
   database. Project-wide, only 1,050 of 11,868 stored symbols have a
   name at all -- essentially the original EODHD load, not the
   2026-09-24 expansion most of this hypothesis's candidates come from.
2. **By ticker, in EDGAR's full text search index**, as a quoted phrase,
   restricted to 424B1-424B5 filings within 15 days of the candidate's
   first stored bar. This needs nothing from this database but the ticker
   itself, so it is not exposed to the missing-name gap. This is what the
   pipeline actually uses.

Every candidate is required to clear a second check before being
confirmed: the filing's OWN cover page must state the SAME ticker, read
from the document, not assumed. This catches a ticker that is also an
ordinary word or abbreviation turning up in an unrelated company's filing
by coincidence (measured: `ROI`, `NB`, `ST`, `KBL` all hit more than one
company's filings in their windows and are excluded as ambiguous rather
than guessed at). Full method, every exclusion reason, and the real bugs
this extraction found and fixed (legacy Windows-1252 quote entities,
unquoted cover pages, a period inside "Inc." breaking a proximity regex)
are documented in `src/screener/ingest/lockups.py`'s own docstrings --
each was found on a real filing, not invented defensively.

**What this does not capture.** The lock-up length used is the
CONTRACTUAL BASE figure from the prospectus. Many underwriting agreements
also carry an earnings-blackout extension (sometimes called a "booster
shot"): if the issuer releases earnings or material news in roughly the
last 17 days of the lock-up, the expiry pushes out to let the information
digest first. This extraction does not model that clause -- it was found
as a confusion risk in Textura Corp's own filing and specifically
excluded from the day-count regex (see `extract_lockup_days`), but the
extension's own effect on the ACTUAL expiry date is not applied. For an
affected IPO the date used here is a few days too early, which understates
rather than invents an effect: an early "expiry" still sits inside what
was actually the live lock-up, so if anything this biases the measured
gap toward zero, not toward finding one.

## 3. The construction method and universe

Candidates: every symbol in this project's database with `asset_type =
'equity'` whose first stored bar falls in `(2010-02-01, 2015-06-30]`.
That window, not the full development split, leaves room for a 180-day
lock-up plus the event window to land inside or just past
2015-12-31 for even the latest candidate, and leaves a month of margin at
the start against the ingest-batch artifact dated exactly 2010-01-04 (101
symbols on that single day, measured 2026-10-03 -- an ingest-start
artifact, not 101 companies IPO'ing the same morning).

**This window is NOT point-in-time index membership** -- it is this
project's own stored first-bar date, which is itself noisy (confirmed:
large single-day spikes at 2009-01-02, 2009-01-05, 2010-01-04 and
2016-01-04 are ingest-batch starts, not listing dates; dates inside the
chosen window show no comparable spike, the largest being 9 symbols on
2014-07-31, consistent with 2013-2014 being the hottest IPO years of the
period rather than an artifact). A candidate that is actually a pre-2010
company with a data gap, not a new listing, is expected and is caught
downstream: EDGAR has no IPO-shaped filing for it near that date, so it is
excluded as `no_filing_found`, not silently counted.

Each candidate is run through `ingest/lockups.py`'s pipeline
(`screener ingest-lockups --start 2010-02-01 --end 2015-06-30`), which
writes `data/reference/ipo_lockups.csv` with a status for every candidate
-- `confirmed`, or the exact step it failed at. Nothing is silently
dropped. **The exact confirmed count is stated in section 6, after the
pipeline ran; it is a property of the data, not a choice made before
running it, and finding it out is data construction, not looking at any
outcome this hypothesis is about.**

## 4. The signal, and the entry/exit mechanics

> Avoid or trim a position in a name within **3 trading days** after its
> lock-up expiry date.

**N = 3, from Field & Hanka's own event window, not picked arbitrarily.**
Their measured effect IS the three-day abnormal return around expiry; a
different N would be testing a different, unstudied window. (A secondary,
non-pre-registered N = 20 reading is reported alongside for context only --
same horizon as H8 and this project's other hypotheses -- and does not
count toward the bar in section 5.)

Mechanics, reusing the project's own engine rather than a new one:

- **Signal**: the lock-up expires on date E (a calendar date, from the
  prospectus clause, not a trading date).
- **Entry**: the next session's open after E -- non-negotiable 1, applied
  the same way H8 applies it. `diagnostics/lockup_screen._entry_index`
  finds the bar on or immediately before E; `diagnostics.screen.
  trade_return` (H8's own function, imported unchanged) does the fill,
  refusing entry on a zero-volume bar.
- **Exit**: the open 3 sessions later, a zero-volume bar's open, or a
  series' last close -- again `trade_return`, unchanged.
- **Cost**: each name's own measured spread as of the signal date
  (`calc/spread.spread_table`), one full spread per round trip, with a
  date's cross-sectional median as the fallback for a name missing its own
  estimate -- H8's convention, reused exactly.
- **Comparison pool**: the SAME full equity universe the candidates were
  drawn from (`load_symbol_bars`, point-in-time, quarantine and the
  impossible-bar cleaning applied by construction), on the SAME calendar
  entry dates. This is a real, stated difference from H8, which compares
  against `swing_small_mid`: a stock in its first months of trading has
  often not yet cleared `swing_small_mid`'s own $2M ADV floor, so
  filtering the pool to it but not the events would be comparing an
  unfiltered group against a filtered one.
- **Statistic**: per event, the event's own net return minus the same-day
  pool's mean net return. Mean of that gap across events, its t-statistic,
  and the one-sided p-value for the gap being NEGATIVE (underperformance;
  the mirror of H8's test, which reads a POSITIVE gap as its hypothesis).

## 5. The bar -- written before looking at any result

**To earn a pass on development** (clean data, 2010-02-01 through roughly
2016, the window the 3-day post-expiry events actually fall in):

1. Net gap one-sided p ≤ 0.05 (testing for a negative gap).
2. Negative in at least 2 of the split's 3 regime buckets
   (`chop_2011`, `bull_2013_2014`, `chop_2015`).
3. The 10%-trimmed version of the gap negative too, so the result is not a
   handful of extreme events.

This mirrors `docs/11` section 4's three-part bar exactly, with the sign
flipped to match H9's opposite-direction hypothesis (H8 tests for
outperformance of a screened pool; H9 tests for underperformance after an
event). It is written down and committed (`preregistrations/H9.md`)
BEFORE `screener ingest-lockups` or the return measurement has been run,
per CHARTER section 5 ("the pass mark is written before looking"). Section
5 above is settled first for the same reason H8's own bar was settled
before its development numbers existed.

**What this bar does NOT authorize.** Per CHARTER section 5 and section 9,
clearing it would make this hypothesis eligible to be PROPOSED for a
validation run -- it does not spend validation or test budget, which
remains the operator's to authorize, exactly as H8's validation run
needed the operator's signature on `preregistrations/H8.md` even after
its own development bar was cleared. Running on development needs no such
sign-off (CHARTER section 5: "Agents may draft, commit and run a pass mark
on historical data"), which is as far as this hypothesis goes without the
operator.

**Known sample-size caveat, stated before the number is known.** The
3-day pre-registered window is short by construction (Field & Hanka's own
design, not a weakness introduced here), so each confirmed event
contributes only one observation regardless of how liquid or long-running
the stock later became. If the confirmed count from section 3's pipeline
turns out to be in the low hundreds or fewer, this test has materially
less power than H8's 78 non-overlapping 20-session windows drawn from a
multi-thousand-name pool, and a null result would be a weaker statement
than H8's. This is recorded now so it cannot be invoked afterward as an
excuse for either a pass or a fail.

## 6. Results

*Filled in after `screener ingest-lockups` and the development measurement
have both run -- see `preregistrations/H9.md` and the project log for the
dated result. Nothing in this section existed when sections 0-5 were
committed.*
