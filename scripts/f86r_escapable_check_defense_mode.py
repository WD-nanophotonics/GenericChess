"""F86R exact defensive-mechanism diagnosis for the frozen F86Q checks."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from generic_chess.benchmark.policy_tape import PolicyTape
from generic_chess.core.actions import action_is_board, action_to_dict
from generic_chess.core.attacks import anchor_square, is_in_check, pseudo_attacks
from generic_chess.core.coordinates import index_to_square, square_to_index
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movement import LeapAtom
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ("V4-3", "V5-3")
ARMS = ("L", "F", "N")
MAX_PLY = 32
PROBE_CAP = 2048
BASELINE = "35d9dfcbf76a5e51dc72f49722389e8dc1b60076"
F86Q_PREP_BLOB = "76e15ba9320ab490d5d6321852eb5b683b6002fb"
F86Q_RESULT_BLOB = "84fba9e85b918895f451ce478fdabe77d8fb00c4"
F86O_MANIFEST_BLOB = "1d16cf69a7ce5f7347352162dcbd351485ee8c5af"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _action_key(action) -> str:
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _action_digest(action) -> str:
    return hashlib.sha256(_canon(action_to_dict(action))).hexdigest()


def _successors(state, compiled):
    return sorted(list(legal_successors(state, compiled)), key=lambda pair: _action_key(pair[0]))


def _gives_check(child, compiled) -> bool:
    return is_in_check(child.position, child.position.side_to_move, compiled)


def _mate(child, actor: int) -> bool:
    return child.terminal_status.status is TerminalStatus.CHECKMATE and child.terminal_status.winner == actor


def _manifest(root: Path) -> dict[str, Any]:
    value = _load(root, "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json")
    if value["status"] != "PRE_REGISTERED_F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE":
        raise RuntimeError("F86R requires the frozen F86O manifest")
    return value


def _f86q(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    prep = _load(root, "artifacts/f86q_check_forcing_depth3_probe/manifest.json")
    result = _load(root, "artifacts/f86q_check_forcing_depth3_probe/summary.json")
    if prep["status"] != "PRE_REGISTERED_F86Q_CHECK_FORCING_DEPTH3_PROBE":
        raise RuntimeError("F86Q PREP status drift")
    if result["status"] != "F86Q_CHECK_FORCING_DEPTH3_PROBE_COMPLETE":
        raise RuntimeError("F86Q RESULT status drift")
    return prep, result


def build_prep(root: Path, output: Path) -> dict[str, Any]:
    f86o = _manifest(root)
    f86q_prep, f86q_result = _f86q(root)
    selected = []
    for root_row in f86q_result["selected_roots"]:
        for action in root_row["actions"]:
            selected.append({
                "arm": root_row["arm"],
                "sample_id": root_row["sample_id"],
                "ruleset_fingerprint": root_row["ruleset_fingerprint"],
                "root_position_digest": root_row["root_position_digest"],
                "root_actor": root_row["root_actor"],
                "trajectory_occurrence_count": root_row["trajectory_occurrence_count"],
                "checking_action_canonical_digest": action["checking_action_canonical_digest"],
                "action": action["action"],
                "f86q_classification": action["classification"],
                "f86q_opponent_legal_reply_count": action["opponent_legal_reply_count"],
                "f86q_tape_chosen_occurrence_count": action["tape_chosen_occurrence_count"],
            })
    selected.sort(key=lambda row: (row["arm"], row["sample_id"], row["root_position_digest"], row["checking_action_canonical_digest"]))
    manifest = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_F86R_ESCAPABLE_CHECK_DEFENSE_MODE",
        "baseline_commit": BASELINE,
        "f86q_prep_manifest_blob": F86Q_PREP_BLOB,
        "f86q_result_blob": F86Q_RESULT_BLOB,
        "f86o_manifest_blob": F86O_MANIFEST_BLOB,
        "arms": list(ARMS),
        "sample_ids": list(SAMPLES),
        "rulesets": [
            {"arm": row["arm"], "sample_id": row["sample_id"], "ruleset_fingerprint": row["ruleset_fingerprint"]}
            for row in f86o["rulesets"]
        ],
        "policy_tape_algorithm": f86q_prep["policy_tape_algorithm"],
        "policy_tape_length": f86q_prep["policy_tape_length"],
        "policy_tapes": f86q_prep["policy_tapes"],
        "frozen_f86o_replay_evidence": f86q_prep["frozen_replay_evidence"],
        "selected_f86q_checking_actions": selected,
        "f86q_classifications": f86q_prep["forcing_classifications"],
        "breaking_reply": {
            "definition": "a legal defender reply after which the attacker has neither mate-in-one nor any checking continuation",
            "primary_mechanism_precedence": ["ANCHOR_FLIGHT", "CHECKER_CAPTURE", "INTERPOSITION_OR_SCREEN", "OTHER_CHECK_ESCAPE"],
        },
        "checker_geometry": {
            "definition": "each attacking piece whose own compiled Leap/Ray geometry reaches the defender Anchor square under child occupancy and ray blocking",
            "required_contracts": [
                "identified checker set is nonempty",
                "every selected F86Q checking child has at least one exact checker",
                "every breaking reply leaves defender not in check",
                "CHECKER_CAPTURE removes at least one pre-reply checker",
            ],
        },
        "probe_accounting": {
            "replay": "replay frozen F86O trajectories and analyze only frozen F86Q selected root/checking-action pairs",
            "specialized_depth_plies": 3,
            "new_successors": "count opponent replies and attacker continuations, as in F86Q",
            "hard_cap": PROBE_CAP,
            "fail_closed_route": "CHECK_ESCAPE_MECHANISM_UNRESOLVED_DUE_TO_PROBE_CAP",
        },
        "prohibited_compute": {
            "new_real_games": 0,
            "generic_search": 0,
            "alphabeta": 0,
            "bfs": 0,
            "training": 0,
            "teacher": 0,
            "f85": 0,
            "heavy": 0,
        },
        "default_generator_changed": False,
        "result_driven_replacement_forbidden": True,
    }
    _write_json(output, manifest)
    return manifest


def _load_prep(root: Path) -> dict[str, Any]:
    prep = _load(root, "artifacts/f86r_escapable_check_defense_mode/manifest.json")
    if prep["status"] != "PRE_REGISTERED_F86R_ESCAPABLE_CHECK_DEFENSE_MODE":
        raise RuntimeError("F86R PREP status drift")
    if prep["baseline_commit"] != BASELINE or prep["f86q_prep_manifest_blob"] != F86Q_PREP_BLOB or prep["f86q_result_blob"] != F86Q_RESULT_BLOB:
        raise RuntimeError("F86R authority drift")
    if len(prep["selected_f86q_checking_actions"]) == 0:
        raise RuntimeError("F86R selected action cohort is empty")
    if prep["probe_accounting"]["hard_cap"] != PROBE_CAP:
        raise RuntimeError("F86R probe cap drift")
    return prep


def _anchor_neighbors(anchor, n: int):
    if anchor is None:
        return set()
    return {
        index_to_square((anchor.rank + dr) * n + anchor.file + df, n)
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
        and 0 <= anchor.file + df < n
        and 0 <= anchor.rank + dr < n
    }


def _exact_checkers(position, attacker: int, defender: int, compiled) -> list[dict[str, Any]]:
    target = anchor_square(position, defender, compiled)
    if target is None:
        return []
    n = compiled.board_size
    target_idx = square_to_index(target, n)
    checkers = []
    for idx, piece in enumerate(position.board):
        if piece is None or piece.owner != attacker:
            continue
        tid = piece.current_type_id
        atoms = compiled.types_by_id[tid].movement_atoms
        matched_atoms = []
        for atom_index, atom in enumerate(atoms):
            if isinstance(atom, LeapAtom):
                if target in compiled.leap_targets[tid][attacker][idx][atom_index]:
                    matched_atoms.append({"movement_kind": "leap", "atom_index": atom_index})
            else:
                for square in compiled.ray_paths[tid][attacker][idx][atom_index]:
                    if square == target:
                        matched_atoms.append({"movement_kind": "ray", "atom_index": atom_index})
                        break
                    if position.board[square_to_index(square, n)] is not None:
                        break
        if matched_atoms:
            square = index_to_square(idx, n)
            checkers.append({
                "square": [square.file, square.rank],
                "type_id": tid,
                "matched_atoms": matched_atoms,
            })
    if not checkers:
        raise RuntimeError("F86R exact checker geometry found no checker for a checking child")
    return checkers


def _reply_is_capture(action, position, defender: int, compiled) -> bool:
    if not action_is_board(action):
        return False
    target = position.board[square_to_index(action.to_square, compiled.board_size)]
    return target is not None and target.owner != defender


def _source_piece_type(action, position, compiled) -> str | None:
    if not action_is_board(action):
        return None
    piece = position.board[square_to_index(action.from_square, compiled.board_size)]
    return piece.current_type_id if piece is not None else None


def _mechanism(primary_features: dict[str, bool]) -> str:
    if primary_features["anchor_moved"]:
        return "ANCHOR_FLIGHT"
    if primary_features["captured_checking_piece"]:
        return "CHECKER_CAPTURE"
    if primary_features["interposition_candidate"]:
        return "INTERPOSITION_OR_SCREEN"
    return "OTHER_CHECK_ESCAPE"


def _probe_action(action_row: dict[str, Any], root_state, checking_child, actor: int, compiled, probe: dict[str, Any]) -> dict[str, Any]:
    defender = 1 - actor
    n = compiled.board_size
    checkers = _exact_checkers(checking_child.position, actor, defender, compiled)
    checker_squares = {tuple(item["square"]) for item in checkers}
    anchor_before = anchor_square(checking_child.position, defender, compiled)
    neighbors = _anchor_neighbors(anchor_before, n)
    attacked = pseudo_attacks(checking_child.position, actor, compiled)
    neighborhood_attacked_count = len(neighbors & attacked)
    replies = _successors(checking_child, compiled)
    probe["successors"] = _consume(probe, len(replies))
    anchor_flight_count = sum(
        action_is_board(action)
        and action.from_square == anchor_before
        and action.to_square in neighbors
        for action, _child in replies
    )
    breaking = []
    checker_types = sorted({item["type_id"] for item in checkers})
    for reply_action, reply_child in replies:
        attacker_next = reply_child.position.side_to_move
        continuations = _successors(reply_child, compiled)
        probe["successors"] = _consume(probe, len(continuations))
        has_mate = any(_mate(child, attacker_next) for _action, child in continuations)
        has_check = any(_gives_check(child, compiled) for _action, child in continuations)
        if has_mate or has_check:
            continue
        if is_in_check(reply_child.position, defender, compiled):
            raise RuntimeError("F86R breaking reply still leaves defender in check")
        anchor_after = anchor_square(reply_child.position, defender, compiled)
        anchor_moved = anchor_before != anchor_after
        reply_capture = _reply_is_capture(reply_action, checking_child.position, defender, compiled)
        captured = action_is_board(reply_action) and tuple((reply_action.to_square.file, reply_action.to_square.rank)) in checker_squares
        if captured and not reply_capture:
            raise RuntimeError("F86R checker capture flag disagrees with capture geometry")
        features = {
            "anchor_moved": anchor_moved,
            "reply_is_capture": reply_capture,
            "captured_checking_piece": captured,
            "interposition_candidate": not anchor_moved and not captured,
        }
        mechanism = _mechanism(features)
        if mechanism == "CHECKER_CAPTURE" and not captured:
            raise RuntimeError("F86R CHECKER_CAPTURE lacks a removed checker")
        breaking.append({
            "anchor_moved": anchor_moved,
            "reply_is_capture": reply_capture,
            "captured_checking_piece": captured,
            "checker_count_before_reply": len(checkers),
            "checker_types_before_reply": checker_types,
            "checker_squares_before_reply": [item["square"] for item in checkers],
            "anchor_neighbor_attacked_count_before_reply": neighborhood_attacked_count,
            "anchor_neighbor_legal_flight_count": anchor_flight_count,
            "reply_destination": [reply_action.to_square.file, reply_action.to_square.rank],
            "defender_piece_type": _source_piece_type(reply_action, checking_child.position, compiled),
            "primary_mechanism": mechanism,
        })
    mechanism_counts = Counter(item["primary_mechanism"] for item in breaking)
    return {
        "checking_action_canonical_digest": action_row["checking_action_canonical_digest"],
        "f86q_classification": action_row["f86q_classification"],
        "trajectory_occurrence_count": action_row["trajectory_occurrence_count"],
        "tape_chosen_occurrence_count": action_row["f86q_tape_chosen_occurrence_count"],
        "checker_multiplicity": len(checkers),
        "checker_types": checker_types,
        "checker_squares": [item["square"] for item in checkers],
        "anchor_neighbor_attacked_count_before_reply": neighborhood_attacked_count,
        "anchor_neighbor_legal_flight_count": anchor_flight_count,
        "opponent_legal_reply_count": len(replies),
        "breaking_reply_count": len(breaking),
        "breaking_reply_mechanism_counts": dict(sorted(mechanism_counts.items())),
        "breaking_replies": breaking,
    }


def _consume(probe: dict[str, Any], count: int) -> int:
    if probe["successors"] + count > PROBE_CAP:
        probe["truncated"] = True
        raise _ProbeCapReached
    return probe["successors"] + count


class _ProbeCapReached(RuntimeError):
    pass


def _route(summary: dict[str, Any]) -> str:
    counts = summary["breaking_reply_mechanism_counts"]
    if not counts:
        return "NO_BREAKING_REPLY_OBSERVED"
    maximum = max(counts.values())
    winners = [mechanism for mechanism, count in counts.items() if count == maximum]
    if len(winners) != 1:
        return "CHECK_ESCAPE_MECHANISM_IS_MIXED"
    return {
        "ANCHOR_FLIGHT": "ANCHOR_FLIGHT_IS_PRIMARY_BREAKING_REPLY_MODE",
        "CHECKER_CAPTURE": "CHECKER_CAPTURE_IS_PRIMARY_BREAKING_REPLY_MODE",
        "INTERPOSITION_OR_SCREEN": "INTERPOSITION_IS_PRIMARY_BREAKING_REPLY_MODE",
        "OTHER_CHECK_ESCAPE": "OTHER_ESCAPE_IS_PRIMARY_BREAKING_REPLY_MODE",
    }[winners[0]]


def _aggregate(actions: list[dict[str, Any]]) -> dict[str, Any]:
    mechanisms = Counter()
    checker_dist = Counter()
    neighborhood_dist = Counter()
    reply_counts = [row["opponent_legal_reply_count"] for row in actions]
    breaking_counts = [row["breaking_reply_count"] for row in actions]
    for action in actions:
        checker_dist[str(action["checker_multiplicity"])] += 1
        neighborhood_dist[str(action["anchor_neighbor_attacked_count_before_reply"])] += 1
        mechanisms.update(action["breaking_reply_mechanism_counts"])
    return {
        "checking_actions": len(actions),
        "breaking_replies": sum(breaking_counts),
        "breaking_reply_mechanism_counts": dict(sorted(mechanisms.items())),
        "mean_min_max_legal_replies": [sum(reply_counts) / len(reply_counts), min(reply_counts, default=0), max(reply_counts, default=0)],
        "mean_min_max_breaking_replies": [sum(breaking_counts) / len(breaking_counts), min(breaking_counts, default=0), max(breaking_counts, default=0)],
        "checker_multiplicity_distribution": dict(sorted(checker_dist.items(), key=lambda item: int(item[0]))),
        "anchor_neighborhood_coverage_distribution": dict(sorted(neighborhood_dist.items(), key=lambda item: int(item[0]))),
        "route": _route({"breaking_reply_mechanism_counts": dict(mechanisms)}),
    }


def run(root: Path, output: Path) -> dict[str, Any]:
    prep = _load_prep(root)
    f86o = _manifest(root)
    target_map = {
        (row["ruleset_fingerprint"], row["root_position_digest"], row["checking_action_canonical_digest"]): row
        for row in prep["selected_f86q_checking_actions"]
    }
    actions_by_key = {}
    probe = {"successors": 0, "truncated": False}
    replay_rows = []
    try:
        for entry in f86o["rulesets"]:
            compiled = compile_ruleset(ruleset_from_dict(entry["ruleset"]))
            for seats in (("A", "B"), ("B", "A")):
                key = (entry["arm"], entry["sample_id"], seats[0], seats[1])
                session = GameSession(compiled)
                tapes = {policy: PolicyTape(policy, f86o["policy_tapes"][entry["sample_id"]][policy]["seed"], tuple(f86o["policy_tapes"][entry["sample_id"]][policy]["uniforms"])) for policy in ("A", "B")}
                consumed = {"A": 0, "B": 0}
                actions = []
                while session.result.status.value == "ongoing" and len(session.history) < MAX_PLY:
                    successors = _successors(session.state, compiled)
                    if not successors:
                        break
                    actor = session.state.position.side_to_move
                    tape = tapes[seats[actor]]
                    chosen_index = tape.choose_index(consumed[seats[actor]], len(successors))
                    chosen_action, _chosen_child = successors[chosen_index]
                    actions.append({"actor": actor, "action": action_to_dict(chosen_action), "legal_action_count": len(successors)})
                    root_digest = position_identity_key(session.state.position, compiled)
                    root_key = (compiled.ruleset_fingerprint, root_digest)
                    candidates = [item for item in prep["selected_f86q_checking_actions"] if (item["ruleset_fingerprint"], item["root_position_digest"]) == root_key]
                    if candidates and root_key not in {key[:2] for key in actions_by_key}:
                        for candidate in candidates:
                            pair = next((pair for pair in successors if _action_digest(pair[0]) == candidate["checking_action_canonical_digest"]), None)
                            if pair is None or not _gives_check(pair[1], compiled):
                                raise RuntimeError("F86R selected F86Q checking action reproduction failed")
                            action_key = (candidate["ruleset_fingerprint"], candidate["root_position_digest"], candidate["checking_action_canonical_digest"])
                            actions_by_key[action_key] = _probe_action(candidate, session.state, pair[1], actor, compiled, probe)
                    consumed[seats[actor]] += 1
                    session.submit(chosen_action)
                sequence_sha = hashlib.sha256(_canon(actions)).hexdigest()
                final_digest = position_identity_key(session.state.position, compiled)
                frozen = next(row for row in prep["frozen_f86o_replay_evidence"] if (row["arm"], row["sample_id"], row["seat_assignment"]["player0"], row["seat_assignment"]["player1"]) == key)
                if sequence_sha != frozen["action_sequence_sha256"] or final_digest != frozen["final_position_digest"]:
                    raise RuntimeError(f"F86R F86O replay mismatch for {key}")
                replay_rows.append({"arm": key[0], "sample_id": key[1], "seat_assignment": frozen["seat_assignment"], "action_sequence_sha256": sequence_sha, "final_position_digest": final_digest})
    except _ProbeCapReached:
        pass
    if not probe["truncated"] and len(replay_rows) != 12:
        raise RuntimeError("F86R did not replay all 12 frozen trajectories")
    if not probe["truncated"] and set(actions_by_key) != set(target_map):
        raise RuntimeError("F86R did not reproduce the complete F86Q selected action cohort")
    all_actions = list(actions_by_key.values())
    by_arm_sample = {}
    for arm in ARMS:
        by_arm_sample[arm] = {}
        for sample in SAMPLES:
            rows = [row for key, row in actions_by_key.items() if key[0] == next(item["ruleset_fingerprint"] for item in prep["selected_f86q_checking_actions"] if item["arm"] == arm and item["sample_id"] == sample) and next(item["sample_id"] for item in prep["selected_f86q_checking_actions"] if item["arm"] == arm and item["sample_id"] == sample) == sample]
            by_arm_sample[arm][sample] = _aggregate(rows)
    n_routes = [by_arm_sample["N"][sample]["route"] for sample in SAMPLES]
    overall = "CHECK_ESCAPE_MECHANISM_UNRESOLVED_DUE_TO_PROBE_CAP" if probe["truncated"] else ("CHECK_ESCAPE_STRUCTURE_IS_SAMPLE_DEPENDENT" if len(set(n_routes)) > 1 else n_routes[0])
    result = {
        "schema_version": 1,
        "status": "F86R_ESCAPABLE_CHECK_DEFENSE_MODE_COMPLETE" if not probe["truncated"] else "F86R_ESCAPABLE_CHECK_DEFENSE_MODE_TRUNCATED",
        "prep_manifest": "artifacts/f86r_escapable_check_defense_mode/manifest.json",
        "baseline_commit": BASELINE,
        "f86q_prep_manifest_blob": F86Q_PREP_BLOB,
        "f86q_result_blob": F86Q_RESULT_BLOB,
        "replayed_trajectories": len(replay_rows),
        "new_real_games": 0,
        "specialized_depth_plies": 3,
        "probe_successor_count": probe["successors"],
        "probe_cap": PROBE_CAP,
        "truncation": probe["truncated"],
        "generic_search": 0,
        "alphabeta_nodes": 0,
        "bfs_expansions": 0,
        "training_compute": 0,
        "teacher_compute": 0,
        "f85_actual_compute": 0,
        "default_generator_changed": False,
        "replay_equality": {"action_sequence_matches": len(replay_rows), "final_position_digest_matches": len(replay_rows)},
        "replayed_games": replay_rows,
        "checking_actions": all_actions,
        "by_arm_sample": by_arm_sample,
        "routing": {"arm_n_by_sample": {sample: by_arm_sample["N"][sample]["route"] for sample in SAMPLES}, "overall": [overall]},
    }
    _write_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--prep", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/f86r_escapable_check_defense_mode/summary.json")
    parser.add_argument("--manifest-output", type=Path, default=ROOT / "artifacts/f86r_escapable_check_defense_mode/manifest.json")
    args = parser.parse_args()
    result = build_prep(args.root, args.manifest_output) if args.prep else run(args.root, args.output)
    print(json.dumps({"status": result["status"], "selected": len(result.get("selected_f86q_checking_actions", [])), "probe_successor_count": result.get("probe_successor_count", 0)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
