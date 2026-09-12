"""F87A-R9 bounded, ruleset-agnostic Western terminal discovery control."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generic_chess.benchmark.qualification import semantic_tape_games

try:
    from scripts.f87a_ruleset_qualification import _controls, _semantic_compiled
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from f87a_ruleset_qualification import _controls, _semantic_compiled


BASELINE_SHA = "178b06b04e1ee47f03fe12688ca6067e75721135"
ARTIFACT_DIR = Path("artifacts/f87a_r9_western_dynamic_discovery")
SEEDS = (9011, 9012, 9013)
PAIR_COUNT = 1
MAX_PLY = 256
TAPE_LENGTH = 256
POLICY_ID = "canonical_common_tape_random"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(root: Path = Path("."), output_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    controls = _controls(root)
    control = controls[-2]
    compiled = _semantic_compiled(control)
    reports = {
        str(seed): semantic_tape_games(
            compiled,
            policy_id=POLICY_ID,
            pair_count=PAIR_COUNT,
            max_ply=MAX_PLY,
            seed=seed,
            tape_length=TAPE_LENGTH,
        )
        for seed in SEEDS
    }
    terminal_counts = {}
    for report in reports.values():
        for status, count in report["terminal_counts"].items():
            terminal_counts[status] = terminal_counts.get(status, 0) + count
    terminal_discovery_count = sum(
        count for status, count in terminal_counts.items() if status != "CENSORED"
    )
    game_count = sum(report["game_count"] for report in reports.values())
    result = {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-R9-WESTERN-DYNAMIC-DISCOVERY",
        "status": "RESULT_COMPLETE",
        "baseline_sha": BASELINE_SHA,
        "ruleset_name": control["name"],
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "policy_id": POLICY_ID,
        "seeds": list(SEEDS),
        "pair_count": PAIR_COUNT,
        "game_count": game_count,
        "max_ply": MAX_PLY,
        "tape_length": TAPE_LENGTH,
        "terminal_counts": dict(sorted(terminal_counts.items())),
        "terminal_discovery_count": terminal_discovery_count,
        "censored_count": terminal_counts.get("CENSORED", 0),
        "dynamic_viability_pass": False,
        "qualification_effect": (
            "DYNAMIC_TERMINAL_DISCOVERY_EVIDENCE_BUT_VIABILITY_STILL_DEFERRED"
        ),
        "external_engine_used": False,
        "training_steps": 0,
        "reports": reports,
    }
    _write_json(output_dir / "manifest.json", {
        "schema_version": 1,
        "experiment": result["experiment"],
        "status": "PREP_FROZEN",
        "baseline_sha": BASELINE_SHA,
        "ruleset_name": control["name"],
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "policy_id": POLICY_ID,
        "seeds": list(SEEDS),
        "pair_count": PAIR_COUNT,
        "max_ply": MAX_PLY,
        "tape_length": TAPE_LENGTH,
        "ruleset_specific_opening_or_tape": False,
        "dynamic_viability_pass": False,
    })
    _write_json(output_dir / "results.json", result)
    return json.loads(json.dumps(result))


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
