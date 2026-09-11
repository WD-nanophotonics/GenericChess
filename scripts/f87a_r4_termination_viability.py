"""F87A-R4 termination-viability calibration.

R4 inherits R3's semantic runtime/nondegeneracy evidence and measures only a
small deterministic semantic-search control at a longer horizon.  It does not
rerun R2 controls or R3 random/greedy games.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from generic_chess.benchmark.qualification import STATUS_DEFER, STATUS_PASS, semantic_search_games
try:
    from scripts.f87a_ruleset_qualification import _compiled, _controls, _semantic_compiled
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from f87a_ruleset_qualification import _compiled, _controls, _semantic_compiled


BASELINE_SHA = "4b26e51f4a5dfcace639cb5a1572a90a4c80632e"
ARTIFACT_DIR = Path("artifacts/f87a_r4_termination_viability")
PREP_PATH = ARTIFACT_DIR / "manifest.json"
POSITIVE_PAIR_COUNT = 2
MAX_PLY = 128
SEARCH_NODE_CAP = 256


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _termination_viability(dynamic: dict[str, Any]) -> dict[str, Any]:
    records = dynamic["records"]
    if all(row["completion"] == "CENSORED" for row in records):
        return {
            "status": STATUS_DEFER,
            "reason": "ALL_TRAJECTORIES_CENSORED",
            "terminal_trajectory_count": 0,
            "abnormal_recurrence": False,
            "abnormal_collapse": False,
        }
    abnormal_recurrence = any(row["max_position_multiplicity"] >= 8 for row in records)
    abnormal_collapse = dynamic["legal_action_collapse_fraction"] >= 0.95
    terminal_trajectory_count = sum(row["completion"] != "CENSORED" for row in records)
    status = STATUS_PASS if terminal_trajectory_count and not abnormal_recurrence and not abnormal_collapse else STATUS_DEFER
    return {
        "status": status,
        "reason": "REPRODUCIBLE_TERMINAL_WITHOUT_ABNORMAL_RECURRENCE_OR_COLLAPSE" if status == STATUS_PASS else "TERMINATION_VIABILITY_REQUIRES_MORE_EVIDENCE",
        "terminal_trajectory_count": terminal_trajectory_count,
        "abnormal_recurrence": abnormal_recurrence,
        "abnormal_collapse": abnormal_collapse,
    }


def build_prep(root: Path, output: Path = PREP_PATH) -> dict[str, Any]:
    controls = []
    for control in _controls(root)[-2:]:
        compiled = _compiled(control)
        semantic = _semantic_compiled(control)
        if compiled.ruleset_fingerprint != semantic.ruleset_fingerprint:
            raise RuntimeError(f"R4 fingerprint mismatch for {control['name']}")
        controls.append({
            "name": control["name"],
            "source_kind": control["source_kind"],
            "source_path": control["source_path"],
            "ruleset_fingerprint": semantic.ruleset_fingerprint,
        })
    prep = {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-R4-TERMINATION-VIABILITY-CALIBRATION",
        "status": "PREP_FROZEN",
        "baseline_sha": BASELINE_SHA,
        "controls": controls,
        "inherited_r3": {
            "source_experiment": "GENERICCHESS-F87A-R3-LAYER-C-DYNAMIC-PLAYABILITY-CALIBRATION",
            "scope": "semantic nondegeneracy evidence only; no R3 games rerun",
        },
        "runtime": "production semantic_engine_for via initial_state/apply_action",
        "policy": {
            "policy_id": "deterministic_semantic_shallow_search",
            "depth": 2,
            "max_ply": MAX_PLY,
            "pair_count": POSITIVE_PAIR_COUNT,
            "game_count": 8,
            "search_node_cap_per_game": SEARCH_NODE_CAP,
        },
        "definitions": {
            "position_identity": "exact position_identity_key including semantic auxiliary state",
            "recurrence": "exact identity return counts; separate from terminal status",
            "censored": "ongoing/max_ply at horizon; never a draw",
            "termination_viability": "PASS only with a reproducible terminal trajectory and no abnormal recurrence/collapse",
        },
        "prohibited_compute": ["R2 rerun", "R3 rerun", "Arena", "training", "Heavy", "C2", "F85"],
    }
    _write_json(output, prep)
    return prep


def _load_prep(path: Path) -> dict[str, Any]:
    prep = json.loads(path.read_text(encoding="utf-8"))
    if prep.get("status") != "PREP_FROZEN" or prep.get("baseline_sha") != BASELINE_SHA:
        raise RuntimeError("F87A-R4 PREP manifest is not frozen at the authorized baseline")
    if prep.get("policy", {}).get("game_count") != 8 or prep.get("policy", {}).get("search_node_cap_per_game") != SEARCH_NODE_CAP:
        raise RuntimeError("F87A-R4 compute cap drift")
    return prep


def run(root: Path, prep_path: Path = PREP_PATH, result_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    prep = _load_prep(prep_path)
    controls = {control["name"]: control for control in _controls(root)[-2:]}
    reports = {}
    for identity in prep["controls"]:
        control = controls[identity["name"]]
        semantic = _semantic_compiled(control)
        if semantic.ruleset_fingerprint != identity["ruleset_fingerprint"]:
            raise RuntimeError(f"F87A-R4 fingerprint drift for {identity['name']}")
        dynamic = semantic_search_games(
            semantic,
            pair_count=POSITIVE_PAIR_COUNT,
            max_ply=MAX_PLY,
            node_cap=SEARCH_NODE_CAP,
        )
        viability = _termination_viability(dynamic)
        reports[identity["name"]] = {
            "ruleset_fingerprint": semantic.ruleset_fingerprint,
            "inherited_r3": {"dynamic_nondegeneracy": STATUS_PASS, "termination_viability": STATUS_DEFER},
            "runtime_contract": "production semantic runtime",
            "layer_c": {
                "dynamic_nondegeneracy": STATUS_PASS,
                "termination_viability": viability["status"],
                "status": viability["status"],
            },
            "termination_viability": viability,
            "dynamic": dynamic,
        }
    summary = {
        "schema_version": 1,
        "experiment": prep["experiment"],
        "status": "RESULT_COMPLETE",
        "baseline_sha": BASELINE_SHA,
        "controls": list(reports),
        "termination_viability": {name: report["termination_viability"]["status"] for name, report in reports.items()},
        "layer_c": {name: report["layer_c"]["status"] for name, report in reports.items()},
        "compute_usage": {
            "new_games": 8,
            "search_nodes": sum(report["dynamic"]["search_nodes"] for report in reports.values()),
            "search_node_cap_per_game": SEARCH_NODE_CAP,
            "arena_games": 0,
            "training_steps": 0,
            "heavy_jobs": 0,
        },
        "reports": reports,
    }
    _write_json(result_dir / "summary.json", summary)
    _write_json(result_dir / "reports.json", reports)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--prep", action="store_true")
    parser.add_argument("--manifest-output", type=Path, default=None)
    parser.add_argument("--result", action="store_true")
    parser.add_argument("--result-dir", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.prep:
        build_prep(root, args.manifest_output or (root / PREP_PATH))
    if args.result:
        run(root, root / PREP_PATH, args.result_dir or (root / ARTIFACT_DIR))
    if not args.prep and not args.result:
        parser.error("choose --prep or --result")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
