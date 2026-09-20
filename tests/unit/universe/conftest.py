"""Unit tests get an empty quarantine unless they ask for one.

`universe_members` filters against a committed CSV of contaminated symbols, so
without this a unit test using a real ticker would pass or fail depending on
which companies EODHD currently mislabels. Two tests in `test_quarantine.py`
read the committed file on purpose, by explicit path.
"""

from __future__ import annotations

import pytest

from screener.universe import quarantine

#: The real, committed list, captured before anything patches it.
REAL_QUARANTINE_FILE = quarantine.QUARANTINE_FILE


@pytest.fixture(autouse=True)
def empty_quarantine(tmp_path, monkeypatch):
    """Point the quarantine at a file that does not exist, and clear the cache
    on both sides -- `symbols` is lru_cached, so a leaked entry would make one
    test's list apply to the next."""
    quarantine.symbols.cache_clear()
    monkeypatch.setattr(quarantine, "QUARANTINE_FILE", tmp_path / "no-quarantine.csv")
    yield
    quarantine.symbols.cache_clear()
