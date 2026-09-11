"""F87A-R6 bounded termination control with complete-root budgeting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from generic_chess.benchmark.qualification import semantic_termination_control_games

try:
    from scripts.f87a_ruleset_qualification import _controls, _semantic_compiled
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from f87a_ruleset_qualification import _controls, _semantic_compiled


BASELINE_SHA = "2d7db69c470ec7e56ec595799b0bef198715b2d3"
ARTIFACT_DIR = Path("artifacts/f87a_r6_termination_control")
PREP_PATH = ARTIFACT_DIR / "manifest.json"
POLICIES = (
    "deterministic_material_capture_greedy",
    "deterministic_complete_root_material_search",
)
PAIR_COUNT = 2
MAX_PLY = 128
ROOT_NODE_CAP_PER_PLY = 64


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_prep(root: Path, output: Path = PREP_PATH) -> dict[str, Any]:
    controls = []
    for control in _controls(root)[-2:]:
        semantic = _semantic_compiled(control)
        controls.append({"name": control["name"], "source_kind": control["source_kind"], "ruleset_fingerprint": semantic.ruleset_fingerprint})
    prep = {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-R6-TERMINATION-CONTROL",
        "status": "PREP_FROZEN",
        "baseline_sha": BASELINE_SHA,
        "controls": controls,
        "inherited_r5": {"scope": "budget evidence only; R5 full-game fallback is not rerun"},
        "runtime": "production semantic_engine_for via initial_state/apply_action",
        "policies": list(POLICIES),
        "pair_count": PAIR_COUNT,
        "max_ply": MAX_PLY,
        "root_node_cap_per_ply": ROOT_NODE_CAP_PER_PLY,
        "budget_rule": "complete root set required; exhaustion terminates trajectory as SEARCH_BUDGET_CENSORED",
        "digest_rule": "pure move sequence digest is separate from execution trace digest",
        "prohibited_compute": ["R2 rerun", "R3 rerun", "R5 full-game fallback", "Arena", "training", "Heavy", "C2", "F85"],
    }
    _write_json(output, prep)
    return prep


def _load_prep(path: Path) -> dict[str, Any]:
    prep = json.loads(path.read_text(encoding="utf-8"))
    if prep.get("status") != "PREP_FROZEN" or prep.get("baseline_sha") != BASELINE_SHA:
        raise RuntimeError("F87A-R6 PREP manifest is not frozen at the authorized baseline")
    return prep


def _viability(dynamic: dict[str, Any]) -> dict[str, Any]:
    terminal_statuses = {"checkmate", "stalemate", "repetition", "perpetual_check", "no_contest"}
    terminal_count = sum(dynamic["terminal_counts"].get(status, 0) for status in terminal_statuses)
    budget_censored = dynamic["search_budget_censored_count"]
    return {
        "status": "PASS" if terminal_count and budget_censored == 0 else "DEFER",
        "terminal_trajectory_count": terminal_count,
        "search_budget_censored_count": budget_censored,
        "reason": "terminal trajectory with complete root-set coverage" if terminal_count and budget_censored == 0 else "termination evidence remains censored or budget-limited",
    }


def run(root: Path, prep_path: Path = PREP_PATH, result_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    prep = _load_prep(prep_path)
    controls = {control["name"]: control for control in _controls(root)[-2:]}
    reports = {}
    for identity in prep["controls"]:
        semantic = _semantic_compiled(controls[identity["name"]])
        if semantic.ruleset_fingerprint != identity["ruleset_fingerprint"]:
            raise RuntimeError(f"F87A-R6 fingerprint drift for {identity['name']}")
        dynamic = semantic_termination_control_games(
            semantic,
            policy_ids=POLICIES,
            pair_count=PAIR_COUNT,
            max_ply=MAX_PLY,
            root_node_cap_per_ply=ROOT_NODE_CAP_PER_PLY,
        )
        reports[identity["name"]] = {
            "ruleset_fingerprint": semantic.ruleset_fingerprint,
            "termination_viability": {policy_id: _viability(dynamic["policies"][policy_id]) for policy_id in POLICIES},
            "pure_sequence_diversity": {
                "unique_action_sequence_count": dynamic["unique_action_sequence_count"],
                "control_distinct_sequence_count": dynamic["control_distinct_sequence_count"],
            },
            "search_coverage": {policy_id: dynamic["policies"][policy_id]["search_coverage"] for policy_id in POLICIES},
            "search_budget_censorship": {policy_id: dynamic["policies"][policy_id]["search_budget_censored_count"] for policy_id in POLICIES},
            "semantic_terminal": {policy_id: dynamic["policies"][policy_id]["terminal_counts"] for policy_id in POLICIES},
            "dynamic": dynamic,
        }
    summary = {
        "schema_version": 1,
        "experiment": prep["experiment"],
        "status": "RESULT_COMPLETE",
        "baseline_sha": BASELINE_SHA,
        "controls": list(reports),
        "pure_sequence_diversity": {name: report["pure_sequence_diversity"] for name, report in reports.items()},
        "termination_viability": {name: report["termination_viability"] for name, report in reports.items()},
        "compute_usage": {"new_games": sum(report["dynamic"]["game_count"] for report in reports.values()), "root_node_cap_per_ply": ROOT_NODE_CAP_PER_PLY, "search_nodes": sum(policy["search_nodes"] for report in reports.values() for policy in report["dynamic"]["policies"].values()), "arena_games": 0, "training_steps": 0, "heavy_jobs": 0},
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
    prep_path = args.manifest_output or (root / PREP_PATH)
    if args.prep:
        build_prep(root, prep_path)
    if args.result:
        run(root, prep_path, args.result_dir or (root / ARTIFACT_DIR))
    if not args.prep and not args.result:
        parser.error("choose --prep or --result")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
