"""Tell a starting session two things it cannot see for itself.

1. Whether this clone is behind origin. On 2026-09-17 a session came up six
   commits stale and read a superseded CLAUDE.md as if it were current -- it
   reported the exit-isolated experiments as unrun when they had been run and
   the results committed. A stale brief is worse than none: it is confidently
   wrong.

2. What the research log already contains. `screener status` was written for
   exactly this reader, so it is called rather than reimplemented -- one query
   in one place, per the arithmetic-lives-in-one-module convention.

Never fails a session. Every check degrades to a printed note.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).is_dir():
        return Path(env)
    return Path(__file__).resolve().parents[2]


def git(root: Path, *args: str, timeout: int = 25) -> tuple[int, str]:
    try:
        done = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return done.returncode, (done.stdout or "").strip()


def freshness(root: Path) -> list[str]:
    code, branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0:
        return ["Not a git checkout, or git unavailable."]

    code, _ = git(root, "fetch", "--quiet", "origin", branch)
    if code != 0:
        return [
            f"On {branch}. Could not reach origin, so whether this clone is "
            "current is UNKNOWN -- treat CLAUDE.md as possibly stale."
        ]

    code, counts = git(root, "rev-list", "--left-right", "--count", f"HEAD...origin/{branch}")
    if code != 0 or not counts:
        return [f"On {branch}. No upstream to compare against."]

    ahead, behind = (counts.split() + ["0", "0"])[:2]
    if behind != "0":
        return [
            f"*** This clone is {behind} commit(s) BEHIND origin/{branch}. ***",
            "CLAUDE.md, docs/ and research/ may all be superseded. Run",
            f"    git pull origin {branch}",
            "before believing anything in them or starting work.",
        ]
    if ahead != "0":
        return [f"On {branch}, {ahead} commit(s) ahead of origin, in sync otherwise."]
    return [f"On {branch}, level with origin."]


def research_status(root: Path) -> list[str]:
    exe = shutil.which("screener")
    cmd = [exe, "status"] if exe else [sys.executable, "-m", "screener.cli", "status"]
    try:
        done = subprocess.run(
            cmd, cwd=root, capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return ["Could not run `screener status`."]
    if done.returncode != 0:
        return [
            "`screener status` did not run (database down, or the package is "
            "not installed in this interpreter). Budget state is UNKNOWN -- "
            "check it before spending validation or test budget."
        ]
    return (done.stdout or "").strip().splitlines()


def main() -> int:
    root = project_root()
    lines = ["=== SCREENERV12 session check ===", *freshness(root), "", *research_status(root)]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
