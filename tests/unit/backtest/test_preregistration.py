"""Pre-registration files, and the run identity they bind to.

A registration that silently fails to parse, or that hashes differently from
the run that spends it, is a budget guard that fails open. These tests are
about the ways that could happen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from screener.backtest.budget import config_hash
from screener.backtest.preregistration import (
    PreregistrationError,
    evidential_config,
    load,
    parse,
)
from screener.backtest.splits import VALIDATION


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


# -- the run identity -------------------------------------------------------

def test_an_omitted_hold_and_its_default_are_one_configuration():
    """The CLI hashed `hold` as typed, so `--hold 5` and no `--hold` -- the
    same H1 run -- spent two budget slots."""
    assert config_hash(evidential_config("h1")) == config_hash(evidential_config("h1", hold=5))


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
