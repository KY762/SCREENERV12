"""Budget enforcement.

The point of these tests is that the budget cannot be exceeded by an ordinary
mistake -- forgetting how many configurations were already tried is exactly the
mistake it exists to prevent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from screener.backtest.budget import (
    BudgetExceeded,
    NotPreregistered,
    check,
    config_hash,
    record,
    status,
)
from screener.backtest.preregistration import Preregistration, Registry
from screener.backtest.splits import DEVELOPMENT, TEST, VALIDATION
from tests.unit.ingest.conftest import session  # noqa: F401

CONFIG_A = {"r_multiple": 2.0, "time_limit": 10}
CONFIG_B = {"r_multiple": 1.5, "time_limit": 10}
CONFIG_C = {"r_multiple": 2.5, "time_limit": 20}
CONFIG_D = {"r_multiple": 3.0, "time_limit": 5}

# The count-limit tests below are about counting, so every configuration they
# use is registered. Registration authorizes a run; it never lifts the count.
_ALL = [CONFIG_A, CONFIG_B, CONFIG_C, CONFIG_D]
REGISTERED = Registry(tuple(
    Preregistration(h, "signed", Path(f"{h}.md"), "test", "2026-09-18",
                    {"validation": _ALL, "test": _ALL})
    for h in ("h2", "h3", "h4")
))


def test_config_hash_ignores_key_order():
    assert config_hash({"a": 1, "b": 2}) == config_hash({"b": 2, "a": 1})


def test_config_hash_changes_with_any_value():
    assert config_hash({"r": 2.0}) != config_hash({"r": 2.5})


def test_development_split_is_unlimited(session):  # noqa: F811
    for config in (CONFIG_A, CONFIG_B, CONFIG_C, CONFIG_D):
        check(session, "h2", DEVELOPMENT, config)
        record(session, hypothesis="h2", split=DEVELOPMENT, config=config)
    assert status(session, "h2", DEVELOPMENT, CONFIG_A).limit is None


def test_validation_allows_three_configurations_then_stops(session):  # noqa: F811
    for config in (CONFIG_A, CONFIG_B, CONFIG_C):
        check(session, "h2", VALIDATION, config, registry=REGISTERED)
        record(session, hypothesis="h2", split=VALIDATION, config=config)

    with pytest.raises(BudgetExceeded, match="already spent 3"):
        check(session, "h2", VALIDATION, CONFIG_D, registry=REGISTERED)


def test_rerunning_an_identical_configuration_is_free(session):  # noqa: F811
    """A reproduction is not a second look at the data."""
    for config in (CONFIG_A, CONFIG_B, CONFIG_C):
        record(session, hypothesis="h2", split=VALIDATION, config=config)

    check(session, "h2", VALIDATION, CONFIG_A, registry=REGISTERED)          # must not raise
    assert status(session, "h2", VALIDATION, CONFIG_A).already_run


def test_test_split_allows_exactly_one_configuration(session):  # noqa: F811
    check(session, "h3", TEST, CONFIG_A, registry=REGISTERED)
    record(session, hypothesis="h3", split=TEST, config=CONFIG_A)

    with pytest.raises(BudgetExceeded, match="already spent 1"):
        check(session, "h3", TEST, CONFIG_B, registry=REGISTERED)


def test_budget_is_tracked_per_hypothesis(session):  # noqa: F811
    record(session, hypothesis="h2", split=TEST, config=CONFIG_A)
    check(session, "h3", TEST, CONFIG_A, registry=REGISTERED)                # h3 has its own budget


def test_spending_survives_a_new_session(session):  # noqa: F811
    """The budget lives in the database precisely so it outlives the process
    that spent it."""
    record(session, hypothesis="h4", split=TEST, config=CONFIG_A)
    session.commit()
    session.expunge_all()

    assert status(session, "h4", TEST, CONFIG_B).spent == 1
    with pytest.raises(BudgetExceeded):
        check(session, "h4", TEST, CONFIG_B, registry=REGISTERED)


def test_infinite_profit_factor_is_stored_as_null_not_a_number(session):  # noqa: F811
    run = record(
        session, hypothesis="h2", split=DEVELOPMENT, config=CONFIG_A,
        profit_factor=float("inf"),
    )
    assert run.profit_factor is None


# --------------------------------------------------------------------------
# Pre-registration
#
# The count limit stopped a hypothesis looking at validation a fourth time. It
# did not stop the three looks being aimed after the fact.
# --------------------------------------------------------------------------

def test_an_unregistered_configuration_cannot_touch_validation(session):  # noqa: F811
    with pytest.raises(NotPreregistered, match="no signed pre-registration"):
        check(session, "h1", VALIDATION, CONFIG_A, registry=Registry())


def test_refusal_is_still_a_budget_refusal(session):  # noqa: F811
    """Every caller that already handles BudgetExceeded handles this too, so
    no path can catch one and let the other through."""
    with pytest.raises(BudgetExceeded):
        check(session, "h1", TEST, CONFIG_A, registry=Registry())


def test_a_draft_authorizes_nothing(session):  # noqa: F811
    """Anyone may draft. Only the operator signs."""
    draft = Registry((Preregistration("h1", "draft", Path("H1.md"),
                                      configurations={"validation": [CONFIG_A]}),))
    with pytest.raises(NotPreregistered, match="draft"):
        check(session, "h1", VALIDATION, CONFIG_A, registry=draft)


def test_a_signed_registration_authorizes_exactly_its_configurations(session):  # noqa: F811
    signed = Registry((Preregistration("h1", "signed", Path("H1.md"), "op", "2026-09-18",
                                       {"validation": [CONFIG_A]}),))
    check(session, "h1", VALIDATION, CONFIG_A, registry=signed)       # must not raise
    with pytest.raises(NotPreregistered):
        check(session, "h1", VALIDATION, CONFIG_B, registry=signed)


def test_registration_is_per_hypothesis(session):  # noqa: F811
    signed = Registry((Preregistration("h1", "signed", Path("H1.md"), "op", "2026-09-18",
                                       {"validation": [CONFIG_A]}),))
    with pytest.raises(NotPreregistered):
        check(session, "h2", VALIDATION, CONFIG_A, registry=signed)


def test_development_needs_no_registration(session):  # noqa: F811
    check(session, "h1", DEVELOPMENT, CONFIG_A, registry=Registry())
