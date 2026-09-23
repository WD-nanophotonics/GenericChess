"""Check score-event visibility of the three already-recorded F153 divergences.

This probe consumes the saved F153 search decisions and reconstructs only its
two F151 roots. It performs no AlphaBeta search and enumerates each root's
legal actions once.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession
from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f151_shogi_material_paired_score_microprobe as f151
from scripts import f153_shogi_material_mutation_root_sensitivity as f153
from scripts.f144_shogi_material_only_arena_evolution import GEN0_SEED, gen0_vector

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "5c365efde06c8fd39dc3eab8b312933c4a39492e"
F153_RESULT_SHA256 = "F70CD249F2B68086BE670F6839704891CC21234EBA285E405AEC24969BA4EB55"
F151_SEED = 1_510_101
ROOT_A_ID = "5738e1f589b8096372ce9c369692937123c13a383f70ceb44ec4f6a19a9bfd2b"
ROOT_B_ID = "742b4fc33ad8a8e9e57369f74b7544245622932fe16d99326f82a9163c1b801c"
CONTRASTS = ((0, "mutant_4"), (8, "mutant_0"), (8, "mutant_3"))


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _category(event: dict) -> str:
    if event["capture"] and event["check"]:
        return "capture_plus_check"
    if event["capture"]:
        return "capture_only"
    if event["check"]:
        return "check_only"
    return "zero"


def _find_saved_root(result: dict, opening_index: int) -> dict:
    stage = next((row for row in result["stages"] if row["sigma"] == .70 and row["position_limit"] == 12), None)
    if stage is None:
        raise AssertionError("F153 sigma-.70/12-root stage missing")
    matches = [row for row in stage["root_rows"]
               if row["position"].get("source") == "F151"
               and int(row["position"].get("seed", -1)) == F151_SEED
               and int(row["position"].get("opening_index", -1)) == opening_index]
    if len(matches) != 1:
        raise AssertionError(f"expected one F151 root at index {opening_index}, got {len(matches)}")
    return matches[0]


def _validate_root_metadata(row: dict, opening_index: int) -> None:
    position = row["position"]
    expected_id = ROOT_A_ID if opening_index == 0 else ROOT_B_ID
    expected_mutants = {0: {"mutant_4"}, 8: {"mutant_0", "mutant_3"}}[opening_index]
    if (position.get("source"), int(position.get("seed", -1)), int(position.get("opening_index", -1)),
        position.get("opening_id")) != ("F151", F151_SEED, opening_index, expected_id):
        raise AssertionError(f"F153 root metadata mismatch at F151 index {opening_index}")
    searches = {item["label"]: item for item in row["root_searches"]}
    if "Gen0" not in searches:
        raise AssertionError("F153 root lacks Gen0 record")
    recorded_divergences = {
        label for label, item in searches.items()
        if label.startswith("mutant_") and item.get("action_differs_from_gen0")
    }
    if recorded_divergences != expected_mutants:
        raise AssertionError(
            f"F153 divergent mutant set mismatch at index {opening_index}: {sorted(recorded_divergences)}"
        )
    if searches["Gen0"].get("action_differs_from_gen0"):
        raise AssertionError("F153 Gen0 row must be the reference action")


def _saved_searches(row: dict, mutant_label: str, expected_vector_sha: str) -> dict:
    searches = {item["label"]: item for item in row["root_searches"]}
    gen0_row, mutant_row = searches["Gen0"], searches[mutant_label]
    if gen0_row.get("vector_sha256") != row["root_searches"][0].get("vector_sha256"):
        raise AssertionError("unexpected Gen0 record order/vector identity")
    if mutant_row.get("vector_sha256") != expected_vector_sha:
        raise AssertionError(f"saved vector hash mismatch for {mutant_label}")
    gen0_search, mutant_search = gen0_row["search"], mutant_row["search"]
    for label, item in (("Gen0", gen0_search), (mutant_label, mutant_search)):
        action = item["best_action"]
        if action is None or item["best_action_key"] != f151._action_key(action):
            raise AssertionError(f"saved F153 action key mismatch for {label}")
    if not mutant_row.get("action_differs_from_gen0"):
        raise AssertionError(f"expected saved action divergence for {mutant_label}")
    return {"gen0": gen0_search, "mutant": mutant_search}


def _reconstruct_opening(openings: list, opening_id: str, expected_plies: int):
    matches = [opening for opening in openings if opening.final_position_key == opening_id]
    if len(matches) != 1:
        raise AssertionError(f"F151 opening identity not reconstructed uniquely: {opening_id}")
    opening = matches[0]
    if len(opening.actions) != expected_plies:
        raise AssertionError(f"F151 opening ply mismatch for {opening_id}")
    return opening


def _classify(contrasts: list[dict]) -> dict:
    event_divergent = [row for row in contrasts if row["comparison"]["event_tuple_same"] is False]
    point_gains = sum(row["comparison"]["point_delta"] > 0 for row in contrasts)
    point_ties = sum(row["comparison"]["point_delta"] == 0 for row in contrasts)
    point_losses = sum(row["comparison"]["point_delta"] < 0 for row in contrasts)
    transitions = Counter(
        f"{row['gen0_event']['category']} -> {row['mutant_event']['category']}"
        for row in event_divergent
    )
    classification = (
        "MATERIAL_DIVERGENCE_CHANGES_SCORE_EVENT" if event_divergent
        else "MATERIAL_DIVERGENCE_SCORE_EVENT_INVARIANT"
    )
    return {
        "classification": classification,
        "contrasts_examined": len(contrasts),
        "action_divergences_reproduced_from_f153": sum(row["comparison"]["action_divergence_reproduced"] for row in contrasts),
        "event_divergent_contrasts": len(event_divergent),
        "point_divergent_contrasts": sum(row["comparison"]["point_delta"] != 0 for row in contrasts),
        "mutant_point_gains": point_gains,
        "mutant_point_ties": point_ties,
        "mutant_point_losses": point_losses,
        "event_transition_counts": dict(sorted(transitions.items())),
        "fresh_searches_used": 0,
    }


def run(*, source_path: Path, output_path: Path) -> dict:
    current_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if current_sha != BASE_SHA:
        raise ValueError(f"unexpected work-order base SHA: {current_sha}")
    source_bytes = source_path.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest().upper()
    if source_sha != F153_RESULT_SHA256:
        raise ValueError(f"unexpected F153 source evidence SHA-256: {source_sha}")
    source = json.loads(source_bytes.decode("utf-8"))
    if source.get("schema") != "F153_SHOGI_MATERIAL_MUTATION_ROOT_SENSITIVITY_V1":
        raise ValueError("unexpected F153 evidence schema")
    if source.get("git_sha") != "91d333b76d512c3b203d860c1d5a8865397dc89b":
        raise ValueError("F153 evidence base SHA mismatch")
    if source.get("search") != {
        "max_nodes": 1000, "max_depth": 12, "qdepth": [4, 8],
        "tt_max_entries": 250000, "tuning": "SearchTuning()",
        "fresh_player_and_tt_per_search": True,
    }:
        raise ValueError("saved F153 search contract mismatch")

    compiled = race._compile()
    gen0 = tuple(gen0_vector(GEN0_SEED))
    mutants = f153.mutation_vectors_at_sigma(gen0, .70)
    if len(mutants) != 6:
        raise AssertionError("F153 sigma-.70 mutation set size mismatch")
    vector_by_label = {"Gen0": gen0, **{f"mutant_{i}": vector for i, vector in enumerate(mutants)}}
    vector_sha = {label: f153._sha(vector) for label, vector in vector_by_label.items()}
    f151_openings = race.opening_corpus(compiled, F151_SEED, 32)

    saved_rows = {index: _find_saved_root(source, index) for index in (0, 8)}
    for index, row in saved_rows.items():
        _validate_root_metadata(row, index)
    contrasts = []
    opportunity_by_root = {}
    for opening_index, mutant_label in CONTRASTS:
        row = saved_rows[opening_index]
        position = row["position"]
        recorded = _saved_searches(row, mutant_label, vector_sha[mutant_label])
        if row["root_searches"][0].get("vector_sha256") != vector_sha["Gen0"]:
            raise AssertionError("recorded Gen0 vector hash differs from the current F144 Gen0 vector")
        opening = _reconstruct_opening(f151_openings, position["opening_id"], int(position["actual_plies"]))
        session = GameSession(compiled)
        for action in opening.actions:
            session.submit(action)
        root_id = opening.final_position_key
        if root_id != position["opening_id"]:
            raise AssertionError("reconstructed F153 root identity mismatch")

        if opening_index not in opportunity_by_root:
            legal = session.legal_actions()
            event_by_key = {}
            counts = Counter()
            for action in legal:
                after = apply_action(session.state, action, compiled)
                event = race.score_event(session.state.position, action, after.position,
                                         session.state.position.side_to_move, compiled)
                action_dict = race.v2.action_to_dict(action)
                key = f151._action_key(action_dict)
                event_by_key[key] = {"capture": event["capture"], "check": event["check"],
                                     "points": event["points"], "category": _category(event)}
                counts[_category(event)] += 1
            opportunity_by_root[opening_index] = {
                "legal_action_count": len(legal),
                "legal_capture_only_action_count": counts["capture_only"],
                "legal_check_only_action_count": counts["check_only"],
                "legal_capture_plus_check_action_count": counts["capture_plus_check"],
                "legal_action_count_producing_any_score_race_point": sum(counts[c] for c in
                    ("capture_only", "check_only", "capture_plus_check")),
                "legal_event_map": event_by_key,
            }
        root_opportunity = opportunity_by_root[opening_index]
        gen0_key = recorded["gen0"]["best_action_key"]
        mutant_key = recorded["mutant"]["best_action_key"]
        legal_by_key = root_opportunity["legal_event_map"]
        gen0_event_data = legal_by_key.get(gen0_key)
        mutant_event_data = legal_by_key.get(mutant_key)
        if gen0_event_data is None or mutant_event_data is None:
            raise AssertionError(f"recorded selected action illegal at F153 root index {opening_index}")
        gen0_event = {"action": recorded["gen0"]["best_action"], "action_key": gen0_key, **gen0_event_data}
        mutant_event = {"action": recorded["mutant"]["best_action"], "action_key": mutant_key, **mutant_event_data}
        contrasts.append({
            "root": {
                "source": position["source"], "seed": position["seed"],
                "opening_index": position["opening_index"], "opening_id": root_id,
                "actual_plies": position["actual_plies"],
            },
            "mutant": mutant_label,
            "vectors": {
                "gen0_sha256": vector_sha["Gen0"],
                "mutant_sha256": vector_sha[mutant_label],
            },
            "recorded_f153_searches": {
                "gen0": {key: recorded["gen0"].get(key) for key in
                         ("best_action", "best_action_key", "score", "completed_depth", "nodes", "qnodes")},
                "mutant": {key: recorded["mutant"].get(key) for key in
                           ("best_action", "best_action_key", "score", "completed_depth", "nodes", "qnodes")},
                "termination_reason": "not recorded in the F153 artifact; no search was rerun",
            },
            "opportunity_counts": {key: value for key, value in root_opportunity.items() if key != "legal_event_map"},
            "gen0_event": gen0_event,
            "mutant_event": mutant_event,
            "comparison": {
                "action_divergence_reproduced": gen0_key != mutant_key,
                "event_tuple_same": (gen0_event["capture"], gen0_event["check"], gen0_event["points"])
                    == (mutant_event["capture"], mutant_event["check"], mutant_event["points"]),
                "point_delta": int(mutant_event["points"]) - int(gen0_event["points"]),
            },
        })
    if len(contrasts) != 3 or not all(row["comparison"]["action_divergence_reproduced"] for row in contrasts):
        raise AssertionError("the three required saved action divergences did not validate")
    summary = _classify(contrasts)
    result = {
        "schema": "F153_DIVERGENT_ROOT_SCORE_EVENT_PROBE_V1",
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "base_git_sha": BASE_SHA,
        "source_f153_result_sha256": source_sha,
        "source_f153_git_sha": source["git_sha"],
        "source_f153_classification": source.get("classification"),
        "searches_rerun": False,
        "new_opening_game_heavy": False,
        "primary_fitness_replaced": False,
        "unknown": "whether the three already-recorded F153 material-mutation move changes alter the current score-race event tuple",
        "contrasts": contrasts,
        **summary,
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite F153 event probe output: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_name(output_path.name + ".tmp")
    temp.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(source_path=args.source, output_path=args.output)
    print(json.dumps({"classification": result["classification"], "contrasts": result["contrasts_examined"],
                      "event_divergent": result["event_divergent_contrasts"],
                      "fresh_searches": result["fresh_searches_used"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
