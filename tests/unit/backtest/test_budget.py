"""Budget enforcement.

The point of these tests is that the budget cannot be exceeded by an ordinary
mistake -- forgetting how many configurations were already tried is exactly the
mistake it exists to prevent.
"""

from __future__ import annotations

import pytest

from screener.backtest.budget import BudgetExceeded, check, config_hash, record, status
from screener.backtest.splits import DEVELOPMENT, TEST, VALIDATION
from tests.unit.ingest.conftest import session  # noqa: F401

CONFIG_A = {"r_multiple": 2.0, "time_limit": 10}
CONFIG_B = {"r_multiple": 1.5, "time_limit": 10}
CONFIG_C = {"r_multiple": 2.5, "time_limit": 20}
CONFIG_D = {"r_multiple": 3.0, "time_limit": 5}


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
        check(session, "h2", VALIDATION, config)
        record(session, hypothesis="h2", split=VALIDATION, config=config)

    with pytest.raises(BudgetExceeded, match="already spent 3"):
        check(session, "h2", VALIDATION, CONFIG_D)


def test_rerunning_an_identical_configuration_is_free(session):  # noqa: F811
    """A reproduction is not a second look at the data."""
    for config in (CONFIG_A, CONFIG_B, CONFIG_C):
        record(session, hypothesis="h2", split=VALIDATION, config=config)

    check(session, "h2", VALIDATION, CONFIG_A)          # must not raise
    assert status(session, "h2", VALIDATION, CONFIG_A).already_run


def test_test_split_allows_exactly_one_configuration(session):  # noqa: F811
    check(session, "h3", TEST, CONFIG_A)
    record(session, hypothesis="h3", split=TEST, config=CONFIG_A)

    with pytest.raises(BudgetExceeded, match="already spent 1"):
        check(session, "h3", TEST, CONFIG_B)


def test_budget_is_tracked_per_hypothesis(session):  # noqa: F811
    record(session, hypothesis="h2", split=TEST, config=CONFIG_A)
    check(session, "h3", TEST, CONFIG_A)                # h3 has its own budget


def test_spending_survives_a_new_session(session):  # noqa: F811
    """The budget lives in the database precisely so it outlives the process
    that spent it."""
    record(session, hypothesis="h4", split=TEST, config=CONFIG_A)
    session.commit()
    session.expunge_all()

    assert status(session, "h4", TEST, CONFIG_B).spent == 1
    with pytest.raises(BudgetExceeded):
        check(session, "h4", TEST, CONFIG_B)


def test_infinite_profit_factor_is_stored_as_null_not_a_number(session):  # noqa: F811
    run = record(
        session, hypothesis="h2", split=DEVELOPMENT, config=CONFIG_A,
        profit_factor=float("inf"),
    )
    assert run.profit_factor is None
