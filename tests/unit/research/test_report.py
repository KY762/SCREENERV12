"""How the battery report renders the random-selection benchmark.

The report's own caveat calls percentiles "the comparison that matters:
beating zero is not the test, beating random long exposure is" -- and for the
first several batteries no table printed one. Expectancy was shown alone, so
H6 read as +0.255R rather than as +0.255R at the 31st percentile, which is the
same finding with the opposite meaning.
"""

from __future__ import annotations

from types import SimpleNamespace

from screener.research.report import _fmt_percentile


def cell(percentile):
    return SimpleNamespace(outcome=SimpleNamespace(random_percentile=percentile))


def test_a_configuration_that_lost_to_a_coin_toss_says_so():
    """This is the number that has to survive skimming. A positive expectancy
    below the 50th percentile is long exposure in a rising market, not
    selection -- H5 at 38.5 and H6 at 31.3 were both read as results first."""
    rendered = _fmt_percentile(cell(31.3))

    assert rendered.startswith("31st")
    assert "below random" in rendered


def test_ordinals_are_english():
    """The report is a document a person reads; '3th' and '31th' say it was
    assembled by something that was not paying attention, which is the last
    impression a research log should give."""
    rendered = {p: _fmt_percentile(cell(p)) for p in (1, 2, 3, 4, 11, 12, 13, 21, 52, 93)}

    assert rendered[1].startswith("1st")
    assert rendered[2].startswith("2nd")
    assert rendered[3].startswith("3rd")
    assert rendered[4].startswith("4th")
    # The teens are the exception every naive implementation gets wrong.
    assert rendered[11].startswith("11th")
    assert rendered[12].startswith("12th")
    assert rendered[13].startswith("13th")
    assert rendered[21].startswith("21st")
    assert rendered[52].startswith("52nd")
    assert rendered[93].startswith("93rd")


def test_beating_random_is_not_decorated():
    assert "below random" not in _fmt_percentile(cell(88.7))
    assert "89th" in _fmt_percentile(cell(88.7))


def test_the_boundary_belongs_to_random():
    """At the 50th percentile the strategy matched a coin toss. Only above it
    has it done anything."""
    assert "below random" in _fmt_percentile(cell(49.9))
    assert "below random" not in _fmt_percentile(cell(50.0))


def test_a_benchmark_that_did_not_run_is_not_a_bad_rank():
    """--random-iterations 0, or no closed trades, means the comparison was
    never made. Rendering that as a low percentile would invent a result."""
    assert _fmt_percentile(cell(None)) == "—"
    assert _fmt_percentile(SimpleNamespace()) == "—"
