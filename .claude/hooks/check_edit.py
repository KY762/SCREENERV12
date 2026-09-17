"""Gate an edit on ruff and the two no-lookahead tests.

Deterministic checks belong to the machine, not to anyone's memory. The
no-lookahead tests are named explicitly because non-negotiable #1 is the one
whose breakage is invisible: a lookahead bug produces better numbers, not an
error.

Blocks (exit 2, stderr back to Claude) on a ruff violation or a genuine test
failure. Does NOT block when the environment itself is broken -- a missing
dependency is not evidence about the edit, and a hook that blocks every write
because pandas is absent gets switched off, which costs more than it saves.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

NO_LOOKAHEAD_TESTS = (
    "tests/unit/calc/test_no_lookahead.py",
    "tests/unit/backtest/test_no_lookahead_backtest.py",
)

# pytest's own codes: 1 = tests failed, 2 = interrupted, 3 = internal error,
# 4 = usage error, 5 = no tests collected. Only 1 is a statement about the code.
PYTEST_TESTS_FAILED = 1


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    return Path(__file__).resolve().parents[2]


def edited_file(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    response = payload.get("tool_response") or {}
    for value in (tool_input.get("file_path"), response.get("filePath")):
        if isinstance(value, str) and value:
            return value
    return None


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=300, check=False
    )


def tool_cmd(module: str) -> list[str] | None:
    """How to invoke a checker, or None if it is not installed anywhere.

    Prefers `sys.executable -m <module>` so a venv's own version runs, and
    PROVES it is importable first. Skipping that probe is how the first version
    of this hook reported a no-lookahead failure it had never observed: `python
    -m pytest` with pytest absent exits 1, the same code pytest uses for "tests
    failed". A checker that reports a result it did not measure is the bug this
    file exists to catch, so it may not be the bug inside this file.
    """
    probe = subprocess.run(
        [sys.executable, "-m", module, "--version"],
        capture_output=True, text=True, check=False,
    )
    if probe.returncode == 0:
        return [sys.executable, "-m", module]
    found = shutil.which(module)
    return [found] if found else None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    path = edited_file(payload)
    if not path or not path.endswith(".py"):
        return 0

    root = project_root()
    try:
        target = str(Path(path).resolve().relative_to(root))
    except ValueError:
        return 0                      # edited outside the project; not ours
    if not (target.startswith("src") or target.startswith("tests")):
        return 0

    notes: list[str] = []

    ruff = tool_cmd("ruff")
    if ruff is None:
        notes.append("ruff is not installed for this interpreter; lint skipped")
    else:
        result = run([*ruff, "check", target], root)
        if result.returncode != 0:
            sys.stderr.write(
                "ruff check failed on the file just edited:\n\n"
                + (result.stdout or result.stderr)
            )
            return 2

    pytest_exe = tool_cmd("pytest")
    if pytest_exe is None:
        notes.append(
            "pytest is not installed for this interpreter, so the no-lookahead "
            "tests did NOT run and this edit was not gated"
        )
        print(json.dumps({"systemMessage": "; ".join(notes)}))
        return 0

    tests = run([*pytest_exe, "-q", *NO_LOOKAHEAD_TESTS], root)
    if tests.returncode == PYTEST_TESTS_FAILED:
        sys.stderr.write(
            "A no-lookahead test failed after this edit. Non-negotiable #1: a "
            "signal completes at a bar's close and fills at the NEXT bar's "
            "open. Fix the edit; do not change what the test asserts.\n\n"
            + (tests.stdout or tests.stderr)
        )
        return 2
    if tests.returncode != 0:
        notes.append(
            f"no-lookahead tests could not run (pytest exit {tests.returncode}) "
            "-- environment problem, not a finding; the edit was not gated"
        )

    if notes:
        print(json.dumps({"systemMessage": "; ".join(notes)}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired:
        sys.exit(0)
