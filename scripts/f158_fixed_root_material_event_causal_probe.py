"""Fixed-root causal probe of F158 material values and score-event behavior."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.identity import position_identity_key
from generic_chess.core.transition import apply_action
from generic_chess.session.result import SessionStatus
from generic_chess.session.session import GameSession
from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts import f158_shogi_sigma070_single_pair_diagnostic as f158

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "9f01d71f2911cbb81d516f26f8ebb40fcfba6512"
TARGET_ROOTS = ((0, 1), (0, 2), (1, 1), (1, 2))
EXPECTED_IDENTITIES = {
    (0, 1): "5d4f445657c94a1d4a6ec5acc51ecdd0eaea001bdba8e7e81304d9277392dd6d",
    (0, 2): "16bc0ec20ceca03334b1b6f3d8816852b6d4732697b4dacef37d7b73ba7f0f7b",
    (1, 1): "5d4f445657c94a1d4a6ec5acc51ecdd0eaea001bdba8e7e81304d9277392dd6d",
    (1, 2): "16bc0ec20ceca03334b1b6f3d8816852b6d4732697b4dacef37d7b73ba7f0f7b",
}
CATEGORIES = ("capture_only", "check_only", "capture_plus_check", "zero")


def _category(event: dict) -> str:
    if event["capture"] and event["check"]:
        return "capture_plus_check"
    if event["capture"]:
        return "capture_only"
    if event["check"]:
        return "check_only"
    return "zero"


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _reconstruct_root(compiled, opening, game: dict, game_index: int, scored_ply: int):
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    for prior_ply, recorded in enumerate(game["actions"][:scored_ply - 1], 1):
        if session.result.status is not SessionStatus.ONGOING:
            raise AssertionError("saved trajectory terminated before target root")
        action = race.v2.action_from_dict(recorded["action"])
        if session.state.position.side_to_move != int(recorded["actor"]):
            raise AssertionError(f"recorded actor mismatch before game={game_index} ply={prior_ply}")
        if action not in session.legal_actions():
            raise AssertionError(f"saved prior action is illegal before game={game_index} ply={prior_ply}")
        before = session.state.position
        after = apply_action(session.state, action, compiled)
        event = race.score_event(before, action, after.position, int(recorded["actor"]), compiled)
        if event != {key: int(recorded[key]) for key in ("capture", "check", "points")}:
            raise AssertionError(f"saved prior event mismatch before game={game_index} ply={prior_ply}")
        session.submit(action)
    identity = str(position_identity_key(session.state.position, compiled))
    if identity != EXPECTED_IDENTITIES[(game_index, scored_ply)]:
        raise AssertionError(f"root identity mismatch for game={game_index} scored_ply={scored_ply}: {identity}")
    return session, identity


def _enumerate_root(compiled, session) -> tuple[list, dict, dict]:
    legal = session.legal_actions()
    candidate_by_key = {}
    counts = {category: 0 for category in CATEGORIES}
    for action in legal:
        after = apply_action(session.state, action, compiled)
        event = race.score_event(session.state.position, action, after.position,
                                 session.state.position.side_to_move, compiled)
        row = {
            "action": race.v2.action_to_dict(action),
            "category": _category(event),
            "capture": int(event["capture"]),
            "check": int(event["check"]),
            "points": int(event["points"]),
        }
        candidate_by_key[_canonical(row["action"])] = row
        counts[row["category"]] += 1
    return legal, candidate_by_key, {
        "legal_action_count": len(legal),
        "legal_capture_only_action_count": counts["capture_only"],
        "legal_check_only_action_count": counts["check_only"],
        "legal_capture_plus_check_action_count": counts["capture_plus_check"],
        "legal_action_count_producing_any_score_race_point": sum(counts[c] for c in CATEGORIES[:-1]),
    }


def _search(compiled, session, legal, candidates, values, ordering_values, label: str) -> dict:
    player = f158._player(compiled, tuple(values), dict(ordering_values))
    decision = player.choose_action(session, race._limits(f158.MAX_NODES_PER_MOVE))
    if decision.declaration is not None or decision.action is None:
        raise AssertionError(f"unexpected non-move result for {label}: {decision.termination_reason}")
    if decision.action not in legal:
        raise AssertionError(f"search selected illegal action for {label}")
    action = race.v2.action_to_dict(decision.action)
    event = candidates[_canonical(action)]
    return {
        "evaluator": label,
        "selected_action": action,
        "nodes": int(decision.nodes),
        "qnodes": int(decision.qnodes),
        "completed_depth": int(decision.completed_depth),
        "termination_reason": decision.termination_reason,
        "selected_action_capture": event["capture"],
        "selected_action_check": event["check"],
        "selected_action_score_race_points": event["points"],
        "selected_action_event_category": event["category"],
        "selected_action_belongs_to_each_event_category": {
            category: event["category"] == category for category in CATEGORIES
        },
    }


def _classify(roots: list[dict]) -> dict:
    action_divergent = event_divergent = point_divergent = gain = loss = move_only = 0
    for root in roots:
        gen0, mutant = root["decisions"]["gen0"], root["decisions"]["mutant0"]
        action_diff = gen0["selected_action"] != mutant["selected_action"]
        event0 = (gen0["selected_action_capture"], gen0["selected_action_check"],
                  gen0["selected_action_score_race_points"])
        event1 = (mutant["selected_action_capture"], mutant["selected_action_check"],
                  mutant["selected_action_score_race_points"])
        event_diff = event0 != event1
        action_divergent += int(action_diff)
        event_divergent += int(event_diff)
        point_divergent += int(event0[2] != event1[2])
        gain += int(event1[2] > event0[2])
        loss += int(event1[2] < event0[2])
        move_only += int(action_diff and not event_diff)
    if event_divergent:
        label = "MATERIAL_PERTURBATION_CHANGES_SCORE_EVENT_BEHAVIOR"
    elif action_divergent:
        label = "MATERIAL_PERTURBATION_CHANGES_MOVE_ONLY"
    else:
        label = "MATERIAL_PERTURBATION_NO_FIXED_ROOT_BEHAVIOR_CHANGE"
    return {
        "classification": label,
        "action_divergent_roots": action_divergent,
        "event_divergent_roots": event_divergent,
        "point_divergent_roots": point_divergent,
        "roots_where_mutant_gains_points": gain,
        "roots_where_mutant_loses_points": loss,
        "roots_with_different_action_but_identical_event": move_only,
    }


def run(*, source_path: Path, output_path: Path) -> dict:
    current_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if current_sha != BASE_SHA:
        raise ValueError(f"unexpected work-order base: {current_sha}")
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    if source.get("schema") != "F158_SHOGI_SIGMA070_SINGLE_PAIR_CAUSAL_DIAGNOSTIC_V1":
        raise ValueError("unexpected F158 source schema")
    if len(source.get("games", [])) != 2 or source.get("bounds", {}).get("games_started") != 2:
        raise ValueError("exactly two recorded F158 games are required")
    if source.get("opening", {}).get("seed") != f158.OPENING_SEED or source["opening"].get("count") != 1:
        raise ValueError("saved F158 opening contract mismatch")
    if source.get("mutant", {}).get("index") != 0 or source["mutant"].get("sigma") != .70:
        raise ValueError("saved F158 mutant is not sigma-.70 mutant_0")

    search = source["search"]
    expected_search = {"max_nodes_per_move": 1000, "max_depth": 12, "qdepth": [4, 8],
                       "tt_max_entries": 250000, "tuning": "SearchTuning()"}
    if any(search.get(key) != value for key, value in expected_search.items()):
        raise ValueError("saved F158 search configuration mismatch")
    compiled = race._compile()
    opening = race.opening_corpus(compiled, int(source["opening"]["seed"]), int(source["opening"]["count"]))[0]
    if opening.final_position_key != source["opening"]["opening_id"]:
        raise AssertionError("saved F158 opening identity mismatch")
    if len(opening.actions) != int(source["opening"]["actual_plies"]):
        raise AssertionError("saved F158 opening ply count mismatch")
    ordering_values = source["search"]["fixed_ordering_values"]
    if race._sha(ordering_values) != source["search"]["fixed_ordering_sha256"]:
        raise AssertionError("fixed ordering values hash mismatch")
    gen0, mutant = source["gen0"], source["mutant"]

    roots = []
    for game_index, scored_ply in TARGET_ROOTS:
        game = source["games"][game_index]
        session, identity = _reconstruct_root(compiled, opening, game, game_index, scored_ply)
        legal, candidates, opportunity_counts = _enumerate_root(compiled, session)
        decisions = {
            "gen0": _search(compiled, session, legal, candidates, gen0["values"], ordering_values, "F158 Gen0"),
            "mutant0": _search(compiled, session, legal, candidates, mutant["values"], ordering_values,
                               "F158 sigma-.70 mutant_0"),
        }
        gen0_event = (decisions["gen0"]["selected_action_capture"], decisions["gen0"]["selected_action_check"],
                      decisions["gen0"]["selected_action_score_race_points"])
        mutant_event = (decisions["mutant0"]["selected_action_capture"], decisions["mutant0"]["selected_action_check"],
                        decisions["mutant0"]["selected_action_score_race_points"])
        roots.append({
            "game_index": game_index,
            "scored_ply": scored_ply,
            "root_position_identity": identity,
            "recorded_trajectory_action": game["actions"][scored_ply - 1]["action"],
            "opportunity_counts": opportunity_counts,
            "decisions": decisions,
            "comparison": {
                "selected_action_same": decisions["gen0"]["selected_action"] == decisions["mutant0"]["selected_action"],
                "event_tuple_same": gen0_event == mutant_event,
                "gen0_event_tuple": list(gen0_event),
                "mutant0_event_tuple": list(mutant_event),
                "event_transition": None if gen0_event == mutant_event else {
                    "from": _category({"capture": gen0_event[0], "check": gen0_event[1]}),
                    "to": _category({"capture": mutant_event[0], "check": mutant_event[1]}),
                },
            },
        })
    if len(roots) != 4:
        raise AssertionError("fixed-root probe must contain exactly four roots")
    summary = _classify(roots)
    result = {
        "schema": "F158_FIXED_ROOT_MATERIAL_EVENT_CAUSAL_PROBE_V1",
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "base_git_sha": BASE_SHA,
        "source_result_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_run_id": source.get("run_id"),
        "opening_identity": opening.final_position_key,
        "search_configuration": expected_search,
        "fresh_player_and_tt_per_decision": True,
        "no_new_game_or_opening_or_heavy": True,
        "no_strength_or_promotion_claim": True,
        "unknown": "whether the existing material perturbation changes fixed-ABP selection on identical saved roots in a way that changes score-race events",
        "roots": roots,
        **summary,
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite fixed-root probe result: {output_path}")
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
    print(json.dumps({
        "classification": result["classification"],
        "roots": len(result["roots"]),
        "action_divergent_roots": result["action_divergent_roots"],
        "event_divergent_roots": result["event_divergent_roots"],
        "point_divergent_roots": result["point_divergent_roots"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
