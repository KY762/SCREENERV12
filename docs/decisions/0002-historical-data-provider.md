# ADR 0002 — Tiingo for historical bars, Alpaca for execution

**Date:** 2026-08-20
**Status:** Accepted
**Context:** Measured during Phase 1 verification on the operator's machine.

---

## The finding

A request for `SPY` from `2010-01-01` returned a first bar of **2020-07-27**. All three
ingested symbols showed the same first date and identical bar counts (1,525), which
makes it a provider-side limit rather than a per-symbol quirk.

**Alpaca's free tier serves roughly the most recent six years.**

## Why that broke the research design

[`docs/03-HYPOTHESES.md`](../03-HYPOTHESES.md) §0.4 splits history three ways:

| Split | Window | Purpose |
| --- | --- | --- |
| Development | 2010–2015 | Unlimited exploration; carries no evidential weight |
| Validation | 2016–2019 | 3 configurations per hypothesis |
| Test | 2020–2026 | 1 configuration, once |

With six years of data, only the **test** window exists — and the sealed window is
precisely the one that must never be explored. The whole structure depends on having
somewhere to make mistakes that costs nothing, and there was nowhere.

The available window is also missing 2020-01 through 2020-07, which contains the
COVID crash: the single most informative stress period in recent history.

## Options considered

| Option | Verdict |
| --- | --- |
| Alpaca paid tier (~$99/mo) | Rejected. ~12% of a $10,000 account per year. |
| Accept six years, compress the splits | Rejected. Leaves ~2 years of out-of-sample test — a verdict reached faster on materially weaker evidence. |
| Yahoo (already used for verification) | Rejected as a *source*. Serves split-adjusted prices only, which contradicts the raw-storage policy, and using the verification source for ingestion would make the Phase 1 gate circular. |
| **Tiingo free tier** | **Accepted.** |

## Decision

**Historical bars come from Tiingo. Alpaca stays for execution and paper trading.**

Tiingo returns raw and adjusted prices as separate fields on every row
(`open`/`adjOpen`, `splitFactor`, `divCash`), which is exactly what
`price_daily`'s raw-storage policy requires: raw bars stored, corporate actions
recorded separately, adjusted series derived on demand. Sources that serve only
adjusted history would silently rewrite stored history at every future split.

### Consequences

- `screener ingest --provider auto` prefers Tiingo when `TIINGO_API_KEY` is set,
  and falls back to Alpaca.
- One request per symbol — Tiingo has no multi-symbol daily endpoint — so the
  initial backfill is slow on the free tier. Ingestion is idempotent, so a run
  stopped by a rate limit resumes by re-running the same command.
- A rate-limit response raises immediately rather than backing off. The free
  tier's window is measured in hours; retrying inside one command would hang
  for longer than anyone waits at a terminal.
- Bars already stored from Alpaca are **overwritten** where the two disagree,
  because re-ingesting the same range updates changed rows. After a full-range
  Tiingo backfill, each symbol's history comes from one source, with no seam
  where the provider changed.
- Verification remains independent: the Phase 1 gate compares against Yahoo and
  Stooq, neither of which is now the ingestion path. Alpaca's overlap window is
  available as a third check.
- The split windows in `03-HYPOTHESES.md` §0.4 stand unchanged. They were only
  ever unreachable for want of data.

### What this does not fix

Alpaca's thin delisted-ticker coverage was already documented as a survivorship
risk. Tiingo's delisted coverage on the free tier is **unverified** — it must be
measured before any universe-wide claim rests on it, and until then every
backtest report continues to state the survivorship caveat.
