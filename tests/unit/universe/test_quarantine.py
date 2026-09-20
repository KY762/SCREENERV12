"""The quarantine: symbols excluded from every universe, and why.

What breaks if these fail: a backtest silently trades a series belonging to a
different company than the one that was in the index (BBBY holds Overstock's
2013-2015 prices), or -- the opposite failure, and the one that cost an hour on
2026-09-19 -- a regeneration throws away correct history for a company that had
simply just left the index.
"""

from __future__ import annotations

from datetime import date

import pytest

from screener.universe import quarantine
from screener.universe.quarantine import Excluded

from .conftest import REAL_QUARANTINE_FILE


def excluded(symbol, reason="not_a_stock", holder="", detail=""):
    return Excluded(
        symbol=symbol, reason=reason, holder=holder,
        recorded_on=date(2026, 9, 19), detail=detail,
    )


@pytest.fixture
def quarantine_file(tmp_path):
    """A quarantine of our own. The cache is cleared around every test by the
    autouse fixture in conftest -- `symbols` is lru_cached on the path, so a
    leaked entry would let one test's list apply to the next."""
    return tmp_path / "universe_quarantine.csv"


def test_a_missing_file_excludes_nothing(quarantine_file):
    """A vault with no quarantine yet must not exclude the whole universe."""
    assert quarantine.load(quarantine_file) == []
    assert quarantine.symbols(quarantine_file) == frozenset()


def test_what_is_written_is_what_comes_back(quarantine_file):
    quarantine.write(
        [excluded("BBBY", "outlived_its_security", "Bed Bath & Beyond, Inc.")],
        quarantine_file,
    )

    (back,) = quarantine.load(quarantine_file)
    assert back.symbol == "BBBY"
    assert back.reason == "outlived_its_security"
    assert back.holder == "Bed Bath & Beyond, Inc."
    assert back.recorded_on == date(2026, 9, 19)


def test_the_file_is_written_sorted(quarantine_file):
    """A regeneration should produce a readable diff, not a reshuffle: nobody
    reviews a 14-line diff that is really a re-ordering."""
    quarantine.write([excluded("SPLS"), excluded("CA"), excluded("JAVA")], quarantine_file)

    assert [e.symbol for e in quarantine.load(quarantine_file)] == ["CA", "JAVA", "SPLS"]


def test_symbols_is_just_the_tickers(quarantine_file):
    quarantine.write([excluded("FB"), excluded("EMC")], quarantine_file)

    assert quarantine.symbols(quarantine_file) == {"FB", "EMC"}


def test_rewriting_invalidates_the_cache(quarantine_file):
    """The cache exists because a backtest asks once per trading day. If a
    rewrite did not clear it, `--write` would report a new list while every
    backtest in the same process kept filtering on the old one."""
    quarantine.write([excluded("FB")], quarantine_file)
    assert quarantine.symbols(quarantine_file) == {"FB"}

    quarantine.write([excluded("FB"), excluded("EMC")], quarantine_file)

    assert quarantine.symbols(quarantine_file) == {"FB", "EMC"}


# --- merge -----------------------------------------------------------------


def test_regeneration_keeps_hand_entered_rows():
    """BBT reads 'Beacon Financial Corporation' and CPWR 'Ocean Thermal Energy
    Corp' -- both listed common stock, both continuous, both invisible to every
    rule here. A --write that dropped them would un-quarantine exactly the
    cases that needed a person to find."""
    existing = [excluded("BBT", "manual", "Beacon Financial Corporation")]
    generated = [excluded("FB", "not_a_stock", "ProShares Trust")]

    merged = quarantine.merge(generated, existing)

    assert {e.symbol for e in merged} == {"BBT", "FB"}


def test_regeneration_drops_rule_found_rows_that_no_longer_conflict():
    """The rule is the authority on its own reasons. When AVB stopped being
    flagged, its row had to go -- otherwise a fixed rule leaves its false
    positives quarantined forever."""
    existing = [excluded("AVB", "outlived_its_security", "AvalonBay Communities Inc")]

    merged = quarantine.merge([], existing)

    assert merged == []


def test_a_hand_entered_row_wins_over_the_rule():
    """The person read the holder name; the rule read a vendor flag."""
    existing = [excluded("BBT", "manual", "Beacon Financial Corporation", "verified by volume")]
    generated = [excluded("BBT", "not_a_stock", "Something Else")]

    merged = quarantine.merge(generated, existing)

    assert [(e.symbol, e.reason) for e in merged] == [("BBT", "manual")]


def test_absent_is_not_a_contaminating_reason():
    """A series that starts after the ticker left has no bars during the
    membership, so there is nothing to get wrong. Excluding it would also
    remove the successor company's legitimate later membership -- DNB left in
    2017 and Dun & Bradstreet Holdings listed again in 2020."""
    assert "absent" in quarantine.GENERATED_REASONS
    assert "absent" not in quarantine.CONTAMINATING_REASONS


# --- the committed file ----------------------------------------------------


def test_the_committed_quarantine_parses():
    """The file ships in the repo and every backtest reads it. A malformed row
    would silently stop excluding a contaminated symbol."""
    entries = quarantine.load(REAL_QUARANTINE_FILE)

    assert entries, "the committed quarantine should not be empty"
    for e in entries:
        assert e.symbol == e.symbol.upper().strip()
        assert e.reason, f"{e.symbol} has no reason"
        assert e.recorded_on != date.min, f"{e.symbol} has no usable date"


def test_the_companies_that_only_just_left_the_index_are_not_quarantined():
    """Pinned because the rule DID quarantine them on 2026-09-19. AVB, EA and
    EQR left the index within weeks of the data ending and EODHD's unreliable
    delisted flag marked all three dead. Their history is correct; excluding it
    destroys clean data to protect against contamination that is not there."""
    quarantined = quarantine.symbols(REAL_QUARANTINE_FILE)

    assert not ({"AVB", "EA", "EQR"} & quarantined)
