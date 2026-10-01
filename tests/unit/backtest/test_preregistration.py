"""Pre-registration files, and the run identity they bind to.

A registration that silently fails to parse, or that hashes differently from
the run that spends it, is a budget guard that fails open. These tests are
about the ways that could happen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from screener.backtest import budget
from screener.backtest.budget import BudgetExceeded, NotPreregistered, config_hash
from screener.backtest.preregistration import (
    Preregistration,
    PreregistrationError,
    Registry,
    evidential_config,
    load,
    parse,
    screen_diagnostic_config,
)
from screener.backtest.splits import VALIDATION
from tests.unit.ingest.conftest import session  # noqa: F401


def write(tmp: Path, body: str, name: str = "H1.md") -> Path:
    path = tmp / name
    path.write_text(f"# H1\n\nReasoning.\n\n```toml\n{body}\n```\n", encoding="utf-8")
    return path


SIGNED = """
hypothesis = "h1"
status = "signed"
signed_by = "operator"
signed_on = "2026-09-18"

[[validation]]
label = "plateau centre"
hold = 10
stop_atr = 2.5
"""

DIAGNOSTIC_SIGNED = """
hypothesis = "h8"
kind = "diagnose_screen"
status = "signed"
signed_by = "operator"
signed_on = "2026-09-28"

[[validation]]
label = "docs/11 section 2 configuration, unchanged"
pool = "swing_small_mid"
horizon = 20
"""


# -- the run identity -------------------------------------------------------

def test_an_omitted_hold_and_its_default_are_one_configuration():
    """The CLI hashed `hold` as typed, so `--hold N` and no `--hold` -- the
    same H1 run when N is the default -- spent two budget slots. Written
    against the constant, not a literal, because the default has moved once."""
    from screener.backtest.runner import HOLD_DEFAULTS

    default = HOLD_DEFAULTS["h1"]
    explicit = evidential_config("h1", hold=default)
    assert config_hash(evidential_config("h1")) == config_hash(explicit)


def test_entry_delay_is_always_part_of_an_h1_identity():
    """Including it only when it differs from 1 would keep old hashes, but the
    moment the default moved, two different runs would share one."""
    assert evidential_config("h1")["entry_delay"] == 1
    assert config_hash(evidential_config("h1", entry_delay=1)) != config_hash(
        evidential_config("h1", entry_delay=3)
    )
    assert evidential_config("h2")["entry_delay"] is None, "h2 never reads it"


def test_account_size_is_part_of_the_identity():
    """It was not hashed at all, so a second validation run at a different
    equity counted as a free reproduction of the first."""
    assert config_hash(evidential_config("h1", equity=10_000)) != config_hash(
        evidential_config("h1", equity=25_000)
    )


def test_explicit_no_target_and_resolved_no_target_are_one_configuration():
    assert config_hash(evidential_config("h2", r_multiple=0)) == config_hash(
        evidential_config("h2", r_multiple=-1.0)
    )


def test_resolving_twice_changes_nothing():
    """The CLI resolves before calling this and this resolves again -- the
    double pass that once gave h2-h4 a target they were told not to have."""
    once = evidential_config("h4", r_multiple=0, use_stop=False, time_limit=20)
    twice = evidential_config(
        "h4", r_multiple=once["r_multiple"], use_stop=False, time_limit=once["time_limit"]
    )
    assert once == twice


def test_a_misspelt_option_is_refused_not_ignored():
    with pytest.raises(ValueError, match="not a backtest run option"):
        evidential_config("h1", stop_art=2.5)


# -- the file ---------------------------------------------------------------

def test_a_signed_file_binds_its_configuration(tmp_path):
    p = parse(write(tmp_path, SIGNED))

    assert p.signed
    assert p.hashes("validation") == {config_hash(evidential_config("h1", hold=10, stop_atr=2.5))}


def test_the_registry_authorizes_the_run_the_cli_would_build(tmp_path):
    write(tmp_path, SIGNED)
    registry = load(tmp_path)
    run = evidential_config("h1", hold=10, stop_atr=2.5)   # what `backtest run` hashes

    assert registry.authorizes("h1", VALIDATION, run)
    assert not registry.authorizes("h1", VALIDATION, evidential_config("h1", hold=10))


def test_more_configurations_than_the_budget_is_refused(tmp_path):
    body = SIGNED + "\n".join(f"\n[[validation]]\nhold = {h}" for h in (3, 5, 20))
    with pytest.raises(PreregistrationError, match="budget of 3"):
        parse(write(tmp_path, body))


def test_signed_without_a_signer_is_refused(tmp_path):
    body = SIGNED.replace('signed_by = "operator"', 'signed_by = ""')
    with pytest.raises(PreregistrationError, match="names who signed"):
        parse(write(tmp_path, body))


def test_a_misspelt_decision_bar_is_refused(tmp_path):
    """Ignored silently, the rule that ran would not be the rule signed."""
    body = SIGNED + '\n[decision]\nmin_date_matched_percentle = 95\n'
    with pytest.raises(PreregistrationError, match="unknown decision"):
        parse(write(tmp_path, body))


def test_the_decision_bar_is_read(tmp_path):
    body = SIGNED + "\n[decision]\nmin_date_matched_percentile = 95\n"
    assert parse(write(tmp_path, body)).min_date_matched_percentile == 95.0


def test_a_file_without_a_toml_block_is_refused(tmp_path):
    path = tmp_path / "H1.md"
    path.write_text("# H1\n\nJust prose.\n", encoding="utf-8")
    with pytest.raises(PreregistrationError, match="no ```toml"):
        parse(path)


def test_one_malformed_file_fails_the_whole_load(tmp_path):
    """Skipping it would leave its hypothesis looking unregistered at best --
    or, if a later edit fixed the TOML, registered without anyone noticing."""
    write(tmp_path, SIGNED)
    write(tmp_path, 'hypothesis = "h2"\nstatus = "maybe"', name="H2.md")
    with pytest.raises(PreregistrationError, match="status"):
        load(tmp_path)


def test_no_directory_means_nothing_is_registered(tmp_path):
    assert load(tmp_path / "absent").entries == ()


def test_the_real_preregistrations_parse():
    """Whatever is committed must load, or every evidential run is blocked
    for a reason nobody will see until they try."""
    load()


def test_two_files_for_one_hypothesis_are_refused(tmp_path):
    """Between them they could register past the budget."""
    write(tmp_path, SIGNED, name="H1.md")
    write(tmp_path, SIGNED, name="H1-amended.md")
    with pytest.raises(PreregistrationError, match="both pre-register"):
        load(tmp_path)


# -- diagnostic (kind = "diagnose_screen") configurations ------------------

def test_a_file_without_kind_defaults_to_backtest_run(tmp_path):
    p = parse(write(tmp_path, SIGNED))
    assert p.kind == "backtest_run"


def test_a_misspelt_diagnostic_option_is_refused():
    with pytest.raises(ValueError, match="not a diagnose screen option"):
        screen_diagnostic_config("h8", pol="swing_small_mid")


def test_an_unknown_kind_is_refused(tmp_path):
    body = DIAGNOSTIC_SIGNED.replace('kind = "diagnose_screen"', 'kind = "something_else"')
    with pytest.raises(PreregistrationError, match="unknown kind"):
        parse(write(tmp_path, body, name="H8.md"))


def test_a_diagnostic_file_parses_with_its_own_shape(tmp_path):
    p = parse(write(tmp_path, DIAGNOSTIC_SIGNED, name="H8.md"))

    assert p.kind == "diagnose_screen"
    assert p.hashes("validation") == {
        config_hash(screen_diagnostic_config("h8", pool="swing_small_mid", horizon=20))
    }


def test_the_registry_authorizes_the_diagnostic_run_the_cli_would_build(tmp_path):
    write(tmp_path, DIAGNOSTIC_SIGNED, name="H8.md")
    registry = load(tmp_path)
    run = screen_diagnostic_config("h8", pool="swing_small_mid", horizon=20)

    assert registry.authorizes("h8", VALIDATION, run)
    assert not registry.authorizes("h8", VALIDATION, screen_diagnostic_config("h8", horizon=10))


def test_an_unsigned_diagnostic_draft_still_refuses(tmp_path):
    body = (
        DIAGNOSTIC_SIGNED
        .replace('status = "signed"', 'status = "draft"')
        .replace('signed_by = "operator"', 'signed_by = ""')
        .replace('signed_on = "2026-09-28"', 'signed_on = ""')
    )
    write(tmp_path, body, name="H8.md")
    registry = load(tmp_path)
    run = screen_diagnostic_config("h8", pool="swing_small_mid", horizon=20)

    assert not registry.authorizes("h8", VALIDATION, run)


def test_backtest_run_shaped_registrations_are_unaffected_by_diagnostic_support(tmp_path):
    """H1-H7's shape, parsed after the diagnostic support was added, must
    produce exactly the same hash it always did."""
    p = parse(write(tmp_path, SIGNED))
    assert p.hashes("validation") == {config_hash(evidential_config("h1", hold=10, stop_atr=2.5))}


DIAG_A = screen_diagnostic_config("h8", horizon=10)
DIAG_B = screen_diagnostic_config("h8", horizon=20)
DIAG_C = screen_diagnostic_config("h8", horizon=30)
DIAG_D = screen_diagnostic_config("h8", horizon=40)
DIAG_REGISTERED = Registry((
    Preregistration(
        "h8", "signed", Path("H8.md"), "test", "2026-09-18",
        configurations={"validation": [DIAG_A, DIAG_B, DIAG_C, DIAG_D]},
        kind="diagnose_screen",
    ),
))


def test_a_signed_diagnostic_registration_authorizes_a_run(session):  # noqa: F811
    budget.check(session, "h8", VALIDATION, DIAG_A, registry=DIAG_REGISTERED)  # must not raise


def test_an_unsigned_diagnostic_draft_refuses_via_budget_check(session):  # noqa: F811
    draft = Registry((Preregistration(
        "h8", "draft", Path("H8.md"), configurations={"validation": [DIAG_A]},
        kind="diagnose_screen",
    ),))
    with pytest.raises(NotPreregistered, match="draft"):
        budget.check(session, "h8", VALIDATION, DIAG_A, registry=draft)


def test_budget_exceeded_still_raises_for_diagnostics(session):  # noqa: F811
    for config in (DIAG_A, DIAG_B, DIAG_C):
        budget.check(session, "h8", VALIDATION, config, registry=DIAG_REGISTERED)
        budget.record(session, hypothesis="h8", split=VALIDATION, config=config)

    with pytest.raises(BudgetExceeded, match="already spent 3"):
        budget.check(session, "h8", VALIDATION, DIAG_D, registry=DIAG_REGISTERED)
