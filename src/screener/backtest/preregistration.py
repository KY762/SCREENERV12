"""Pre-registration: which configurations an evidential split may be spent on.

`budget.py` limits HOW MANY configurations a hypothesis may run on validation
(3) and test (1). Until 2026-09-18 nothing limited WHICH ones, so a slot could
be spent on a configuration chosen after looking -- the budget counted the
looks but did not stop them being aimed. A pre-registration fixes the
configurations in a committed file before the split is touched, and
`budget.check` refuses any evidential run whose configuration is not in a
SIGNED one.

Each hypothesis's pre-registration is a Markdown file in `preregistrations/`
at the repository root. The prose is the reasoning; the first fenced ```toml
block is the part the code binds to:

    hypothesis = "h1"
    status = "draft"        # "draft" authorizes nothing; only "signed" does
    signed_by = ""
    signed_on = ""

    [[validation]]          # at most the split's budget
    hold = 10
    stop_atr = 2.5

Configuration keys are the `screener backtest run` options. Anything omitted
takes that command's default, and every value goes through the same
`evidential_config` the command hashes, so the file and the run cannot disagree
about what was registered.

Signing is the operator's act. A draft written by anyone else authorizes
nothing until the operator changes its status and commits it.
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .budget import config_hash
from .splits import Split, get_split

# repository root / preregistrations
PREREGISTRATION_DIR = Path(__file__).resolve().parents[3] / "preregistrations"

# The `screener backtest run` defaults. A pre-registration that omits a key
# gets exactly what the command would have used.
RUN_DEFAULTS: dict[str, Any] = {
    "symbols": None,
    "universe": None,
    "equity": 10_000.0,
    "r_multiple": None,
    "time_limit": None,
    "slippage_bps": 5.0,
    "trend_filter": True,
    "use_stop": True,
    "displacement": None,
    "hold": None,
    "top_pct": 0.10,
    "stop_atr": 2.0,
    "rs_lookback": 63,
}

EVIDENTIAL_SPLITS = ("validation", "test")


def evidential_config(hypothesis: str, **options: Any) -> dict[str, Any]:
    """The identity of a run, as hashed for budget and written to config_json.

    Every value is RESOLVED before hashing, because two spellings of one run
    must not produce two hashes, and two different runs must not produce one:

      - `hold`: omitted resolves to the hypothesis's own horizon. Hashed raw it
        gave `--hold 5` and no `--hold` different hashes for the identical H1
        run -- the budget would count one configuration twice.
      - `equity`: hashed at all. It was not, so a second validation run at a
        different account size hashed as a reproduction of the first and cost
        nothing -- unlimited looks at the split by changing one number.
      - `r_multiple`, `time_limit`: through RunConfig.resolved(), as before.
    """
    from .runner import RunConfig

    unknown = set(options) - set(RUN_DEFAULTS)
    if unknown:
        raise ValueError(f"not a backtest run option: {sorted(unknown)}")
    opts = {**RUN_DEFAULTS, **options}
    key = hypothesis.strip().lower()

    spec = RunConfig(
        hypothesis=key, r_multiple=opts["r_multiple"],
        time_limit=opts["time_limit"], hold=opts["hold"],
    ).resolved()

    return {
        "hypothesis": key,
        "symbols": opts["symbols"] or "all",
        "universe": opts["universe"],
        "equity": float(opts["equity"]),
        # Resolved values, as they are. The CLI this replaced wrote
        # `r_multiple or None`, which turns the canonical "no target" 0.0 back
        # into None -- the value that re-resolves to h2-h4's 2R default -- so
        # the logged config again described a run that did not happen.
        # `time_limit or None` did the same to 0, "no time exit". Caught by
        # test_resolving_twice_changes_nothing on the day this was written.
        "r_multiple": spec.r_multiple,
        "time_limit": spec.time_limit,
        "slippage_bps": float(opts["slippage_bps"]),
        "trend_filter": bool(opts["trend_filter"]),
        "use_stop": bool(opts["use_stop"]),
        "displacement": opts["displacement"],
        "hold": spec.hold,
        "top_pct": float(opts["top_pct"]),
        "stop_atr": float(opts["stop_atr"]) if key == "h1" else None,
        "rs_lookback": int(opts["rs_lookback"]) if key == "h1" else None,
    }


class PreregistrationError(ValueError):
    """A pre-registration file that cannot be trusted to mean what it says."""


@dataclass(frozen=True)
class Preregistration:
    hypothesis: str
    status: str
    path: Path
    signed_by: str = ""
    signed_on: str = ""
    configurations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    # Bars the registration adds on top of performance.py's criteria. Applied
    # by `screener backtest run` to any run this registration authorizes, and
    # counted in its pass/fail -- written here, not passed in, for the same
    # reason the criteria are constants.
    min_date_matched_percentile: float | None = None

    @property
    def signed(self) -> bool:
        return self.status == "signed"

    def hashes(self, split: str) -> set[str]:
        return {config_hash(c) for c in self.configurations.get(split, [])}


_TOML_BLOCK = re.compile(r"^```toml\s*\n(.*?)^```", re.S | re.M)


def parse(path: Path) -> Preregistration:
    """Read one pre-registration, refusing anything ambiguous."""
    text = path.read_text(encoding="utf-8")
    match = _TOML_BLOCK.search(text)
    if not match:
        raise PreregistrationError(f"{path.name}: no ```toml block")
    try:
        data = tomllib.loads(match.group(1))
    except tomllib.TOMLDecodeError as exc:
        raise PreregistrationError(f"{path.name}: {exc}") from exc

    hypothesis = str(data.get("hypothesis", "")).strip().lower()
    if not hypothesis:
        raise PreregistrationError(f"{path.name}: no hypothesis")
    status = str(data.get("status", "")).strip().lower()
    if status not in ("draft", "signed"):
        raise PreregistrationError(f"{path.name}: status must be 'draft' or 'signed'")
    signed_by = str(data.get("signed_by", "")).strip()
    signed_on = str(data.get("signed_on", "")).strip()
    if status == "signed" and not (signed_by and signed_on):
        raise PreregistrationError(
            f"{path.name}: a signed pre-registration names who signed it and when"
        )

    configurations: dict[str, list[dict[str, Any]]] = {}
    for split_name in EVIDENTIAL_SPLITS:
        entries = data.get(split_name, [])
        split: Split = get_split(split_name)
        if split.config_budget is not None and len(entries) > split.config_budget:
            raise PreregistrationError(
                f"{path.name}: {len(entries)} {split_name} configuration(s) registered "
                f"against a budget of {split.config_budget}"
            )
        built = []
        for entry in entries:
            options = {k: v for k, v in entry.items() if k != "label"}
            try:
                built.append(evidential_config(hypothesis, **options))
            except ValueError as exc:
                raise PreregistrationError(f"{path.name}: {exc}") from exc
        configurations[split_name] = built

    decision = data.get("decision", {})
    unknown = set(decision) - {"min_date_matched_percentile"}
    if unknown:
        # A misspelt bar would otherwise be silently ignored -- the rule the
        # operator signed would not be the rule that ran.
        raise PreregistrationError(f"{path.name}: unknown decision key(s) {sorted(unknown)}")
    floor = decision.get("min_date_matched_percentile")
    if floor is not None and not 0 <= float(floor) <= 100:
        raise PreregistrationError(f"{path.name}: a percentile is between 0 and 100")

    return Preregistration(
        hypothesis, status, path, signed_by, signed_on, configurations,
        None if floor is None else float(floor),
    )


@dataclass(frozen=True)
class Registry:
    entries: tuple[Preregistration, ...] = ()

    def authorizing(
        self, hypothesis: str, split: Split, config: dict[str, Any]
    ) -> Preregistration | None:
        """The signed pre-registration naming this run, if there is one."""
        digest = config_hash(config)
        for p in self.entries:
            if p.signed and p.hypothesis == hypothesis and digest in p.hashes(split.name):
                return p
        return None

    def authorizes(self, hypothesis: str, split: Split, config: dict[str, Any]) -> bool:
        return self.authorizing(hypothesis, split, config) is not None

    def for_hypothesis(self, hypothesis: str) -> list[Preregistration]:
        return [p for p in self.entries if p.hypothesis == hypothesis]


def load(directory: Path | None = None) -> Registry:
    """Every pre-registration on disk. A malformed file raises rather than
    being skipped: a registration that silently fails to load is a budget
    guard that silently fails open.

    SCREENER_PREREGISTRATION_DIR relocates the directory -- for tests that
    spend an evidential split through the CLI. It changes WHERE registrations
    are read, not WHETHER one is required: an empty or missing directory
    registers nothing and every evidential run is refused.
    """
    override = os.environ.get("SCREENER_PREREGISTRATION_DIR")
    root = directory or (Path(override) if override else PREREGISTRATION_DIR)
    if not root.exists():
        return Registry()
    entries = tuple(parse(p) for p in sorted(root.glob("*.md")))

    # One per hypothesis. Two files could otherwise register past the budget
    # between them, and "which one did the operator sign" would have two
    # answers.
    seen: dict[str, Path] = {}
    for p in entries:
        if p.hypothesis in seen:
            raise PreregistrationError(
                f"{p.path.name} and {seen[p.hypothesis].name} both pre-register "
                f"{p.hypothesis}; amend one file instead"
            )
        seen[p.hypothesis] = p.path
    return Registry(entries)
