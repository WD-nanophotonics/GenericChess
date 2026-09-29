"""Bounded material-control check against frozen R5 exact root-action labels."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import legal_successors
from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23n_preference_corpus_r5 as f23n
from scripts.audit_chess_mate2_qsearch import _python_search


FIXTURE = ROOT / "tests/fixtures/evaluator_v2_corpus_v7.json"
FIXTURE_SHA256 = "57d0d40ad4e74815ca1c542c2fa680750ea8a6411e47249a3892f23954dd064b"
ROOT_IDS = (
    "generic-f23n-legacy_capture_recapture-1",
    "generic-f23n-legacy_capture_recapture-2",
)
PROFILES = {
    "rook_high": {"K": 0, "R": 4, "D": 1},
    "d_high": {"K": 0, "R": 1, "D": 4},
}


def run_probe() -> dict:
    if hashlib.sha256(FIXTURE.read_bytes()).hexdigest() != FIXTURE_SHA256:
        raise RuntimeError("frozen R5 fixture changed")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = {}
    for root_id in ROOT_IDS:
        exact = next(
            row for row in fixture["effective_preference_representatives"]
            if row["id"] == root_id
        )
        if exact["planned_split"] != "DEVELOPMENT":
            raise RuntimeError("selected root is not in R5 DEVELOPMENT")
        plan = f23n._plan_entry(exact["construction_family"])
        compiled, state = f23n._build_candidate(
            f23c._imports(), plan, tuple(exact["parameter"])
        )
        labels = {
            json.dumps(item["action"], sort_keys=True): item["value"]
            for item in exact["root_action_values"]
        }
        selections = {}
        for profile_name, values in PROFILES.items():
            for depth in (1, 2):
                search = _python_search(compiled, state, values, depth, 0)
                if search["completed_depth"] != depth:
                    raise RuntimeError("bounded search did not complete")
                key = json.dumps(search["action"], sort_keys=True)
                if key not in labels:
                    raise RuntimeError("selected action absent from exact certificate")
                selections[f"{profile_name}_d{depth}"] = {
                    **search,
                    "exact_wdl": labels[key],
                }
        rows[root_id] = {
            "parameter": exact["parameter"],
            "wdl_partition": exact["wdl_partition"],
            "max_ply_dependence": exact["max_ply_dependence"],
            "selections": selections,
        }
        if root_id == ROOT_IDS[1]:
            losing = selections["d_high_d2"]["action"]
            matches = [
                child for action, child in legal_successors(state, compiled)
                if action_to_dict(action) == losing
            ]
            if len(matches) != 1:
                raise RuntimeError("losing capture is not uniquely legal")
            target = losing["to"]
            victim = state.position.board[target[1] * compiled.board_size + target[0]]
            rows[root_id]["losing_action_is_d_capture_to_hand"] = (
                victim is not None
                and victim.owner == 1
                and victim.current_type_id == "D"
                and matches[0].position.hands[0].count("D") == 1
            )
            qsearch_control = {}
            for profile_name, values in PROFILES.items():
                for depth in (1, 2):
                    search = _python_search(compiled, state, values, depth, 4)
                    if search["completed_depth"] != depth:
                        raise RuntimeError("bounded qsearch control did not complete")
                    key = json.dumps(search["action"], sort_keys=True)
                    if key not in labels:
                        raise RuntimeError("qsearch action absent from exact certificate")
                    qsearch_control[f"{profile_name}_d{depth}"] = {
                        **search, "exact_wdl": labels[key]
                    }
            rows[root_id]["qsearch_control"] = qsearch_control
    first = rows[ROOT_IDS[0]]["selections"]
    second = rows[ROOT_IDS[1]]["selections"]
    valid = (
        all(item["exact_wdl"] == "DRAW" for item in first.values())
        and second["rook_high_d1"]["exact_wdl"] == "LOSS"
        and second["d_high_d1"]["exact_wdl"] == "LOSS"
        and second["rook_high_d2"]["exact_wdl"] == "DRAW"
        and second["d_high_d2"]["exact_wdl"] == "LOSS"
        and rows[ROOT_IDS[1]]["losing_action_is_d_capture_to_hand"]
        and all(
            item["exact_wdl"] == "LOSS" and item["qnodes"] > 0
            for name, item in rows[ROOT_IDS[1]]["qsearch_control"].items()
            if name.endswith("_d1")
        )
        and all(
            item["exact_wdl"] == "DRAW" and item["qnodes"] > 0
            for name, item in rows[ROOT_IDS[1]]["qsearch_control"].items()
            if name.endswith("_d2")
        )
    )
    return {
        "classification": "R5_MATERIAL_CONTROL_WDL_SPLIT" if valid else "OBSERVATION_CHANGED",
        "fixture_sha256": FIXTURE_SHA256,
        "profiles": PROFILES,
        "search_contract": "Python depth 1/2, qdepth 0; root -2 also qdepth 4; 2000 nodes, 5 seconds, TT/order disabled",
        "roots": rows,
    }


if __name__ == "__main__":
    result = run_probe()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["classification"] == "R5_MATERIAL_CONTROL_WDL_SPLIT" else 1)
