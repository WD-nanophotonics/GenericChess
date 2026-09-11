"""F87A-R5 search-budget fallback and trajectory-independence evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from generic_chess.benchmark.qualification import STATUS_DEFER, semantic_search_games

try:
    from scripts.f87a_r4_termination_viability import MAX_PLY, POSITIVE_PAIR_COUNT, SEARCH_NODE_CAP, _termination_viability
    from scripts.f87a_ruleset_qualification import _compiled, _controls, _semantic_compiled
except ModuleNotFoundError:  # direct ``python scripts/...`` execution
    from f87a_r4_termination_viability import MAX_PLY, POSITIVE_PAIR_COUNT, SEARCH_NODE_CAP, _termination_viability
    from f87a_ruleset_qualification import _compiled, _controls, _semantic_compiled


BASELINE_SHA = "a42e38f9f8aeb6edacdb51c809fbdbe001a212d7"
ARTIFACT_DIR = Path("artifacts/f87a_r5_search_budget_evidence")
PREP_PATH = ARTIFACT_DIR / "manifest.json"
SEARCH_DEPTH = 1


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_prep(root: Path, output: Path = PREP_PATH) -> dict[str, Any]:
    controls = []
    for control in _controls(root)[-2:]:
        legacy = _compiled(control)
        semantic = _semantic_compiled(control)
        if legacy.ruleset_fingerprint != semantic.ruleset_fingerprint:
            raise RuntimeError(f"R5 fingerprint mismatch for {control['name']}")
        controls.append({"name": control["name"], "source_kind": control["source_kind"], "ruleset_fingerprint": semantic.ruleset_fingerprint})
    prep = {
        "schema_version": 1,
        "experiment": "GENERICCHESS-F87A-R5-SEARCH-BUDGET-EVIDENCE",
        "status": "PREP_FROZEN",
        "baseline_sha": BASELINE_SHA,
        "controls": controls,
        "inherited_r4": {"scope": "R4 termination results remain historical; R5 measures corrected budget/trajectory evidence"},
        "policy": {
            "policy_id": "deterministic_semantic_shallow_search",
            "max_ply": MAX_PLY,
            "search_depth": SEARCH_DEPTH,
            "pair_count": POSITIVE_PAIR_COUNT,
            "game_count": 8,
            "search_node_cap_per_game": SEARCH_NODE_CAP,
            "fallback": "if budget prevents full root action evaluation, choose first canonical action and record BUDGET_FALLBACK",
            "terminal_utility": "winner +/-1; terminal without winner 0.0; CENSORED null",
        },
        "required_evidence": [
            "unique_action_sequence_count",
            "role_swap_distinct_pair_count",
            "first_budget_exhausted_ply",
            "searched_ply_count",
            "fallback_ply_count",
            "terminal_utility",
        ],
        "prohibited_compute": ["R2 rerun", "R3 rerun", "Arena", "training", "Heavy", "C2", "F85"],
    }
    _write_json(output, prep)
    return prep


def _load_prep(path: Path) -> dict[str, Any]:
    prep = json.loads(path.read_text(encoding="utf-8"))
    if prep.get("status") != "PREP_FROZEN" or prep.get("baseline_sha") != BASELINE_SHA:
        raise RuntimeError("F87A-R5 PREP manifest is not frozen at the authorized baseline")
    return prep


def run(root: Path, prep_path: Path = PREP_PATH, result_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    prep = _load_prep(prep_path)
    controls = {control["name"]: control for control in _controls(root)[-2:]}
    reports = {}
    for identity in prep["controls"]:
        control = controls[identity["name"]]
        semantic = _semantic_compiled(control)
        if semantic.ruleset_fingerprint != identity["ruleset_fingerprint"]:
            raise RuntimeError(f"F87A-R5 fingerprint drift for {identity['name']}")
        dynamic = semantic_search_games(
            semantic,
            pair_count=POSITIVE_PAIR_COUNT,
            max_ply=MAX_PLY,
            node_cap=SEARCH_NODE_CAP,
            search_depth=SEARCH_DEPTH,
        )
        viability = _termination_viability(dynamic)
        reports[identity["name"]] = {
            "ruleset_fingerprint": semantic.ruleset_fingerprint,
            "termination_viability": viability,
            "trajectory_independence": dynamic["trajectory_independence"],
            "search_budget": {
                "node_cap_per_game": SEARCH_NODE_CAP,
                "total_search_nodes": dynamic["search_nodes"],
                "first_budget_exhausted_plies": [row["first_budget_exhausted_ply"] for row in dynamic["records"]],
                "searched_ply_count": sum(row["searched_ply_count"] for row in dynamic["records"]),
                "fallback_ply_count": sum(row["fallback_ply_count"] for row in dynamic["records"]),
                "fallback_fraction": sum(row["fallback_ply_count"] for row in dynamic["records"]) / sum(row["plies"] for row in dynamic["records"]),
            },
            "terminal_utility_policy": dynamic["terminal_utility_policy"],
            "dynamic": dynamic,
        }
    summary = {
        "schema_version": 1,
        "experiment": prep["experiment"],
        "status": "RESULT_COMPLETE",
        "baseline_sha": BASELINE_SHA,
        "controls": list(reports),
        "termination_viability": {name: report["termination_viability"]["status"] for name, report in reports.items()},
        "trajectory_independence": {name: report["trajectory_independence"]["status"] for name, report in reports.items()},
        "compute_usage": {"new_games": 8, "search_nodes": sum(report["dynamic"]["search_nodes"] for report in reports.values()), "search_node_cap_per_game": SEARCH_NODE_CAP, "arena_games": 0, "training_steps": 0, "heavy_jobs": 0},
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
        run(root, args.manifest_output or (root / PREP_PATH), args.result_dir or (root / ARTIFACT_DIR))
    if not args.prep and not args.result:
        parser.error("choose --prep or --result")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
