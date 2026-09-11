"""F86Q bounded forcing probe over the frozen F86O trajectory states."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from generic_chess.benchmark.policy_tape import PolicyTape
from generic_chess.core.actions import action_to_dict
from generic_chess.core.attacks import is_in_check
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import initial_state, legal_successors
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ("V4-3", "V5-3")
ARMS = ("L", "F", "N")
MAX_PLY = 32
PROBE_CAP = 8192
F86P_BASELINE = "e0aa2d7c606b395402ec252c5688a51c8eac2c2a"
F86O_MANIFEST_BLOB = "1d16cf69a7ce5f7347352162dcbd351485ee8c5af"
F86O_RESULT_BLOB = "fccfffdb5ec8c3e72eeb78f4bb73c8244ca2e322"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _action_key(action) -> str:
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _action_digest(action) -> str:
    return hashlib.sha256(_canonical_json(action_to_dict(action))).hexdigest()


def _canonical_successors(state, compiled):
    return sorted(list(legal_successors(state, compiled)), key=lambda pair: _action_key(pair[0]))


def _gives_check(child, compiled) -> bool:
    return is_in_check(child.position, child.position.side_to_move, compiled)


def _is_mate(child, actor: int) -> bool:
    return child.terminal_status.status is TerminalStatus.CHECKMATE and child.terminal_status.winner == actor


def _f86o_manifest(root: Path) -> dict[str, Any]:
    manifest = _load_json(root, "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json")
    if manifest["status"] != "PRE_REGISTERED_F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE":
        raise RuntimeError("F86Q requires the frozen F86O PREP manifest")
    return manifest


def _f86o_result(root: Path) -> dict[str, Any]:
    result = _load_json(root, "artifacts/f86o_common_tape_triarm_dynamic_smoke/summary.json")
    if result["status"] != "F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE_COMPLETE":
        raise RuntimeError("F86Q requires the frozen F86O RESULT")
    return result


def build_prep(root: Path, output: Path) -> dict[str, Any]:
    source_manifest = _f86o_manifest(root)
    source_result = _f86o_result(root)
    expected_games = []
    for game in source_result["games"]:
        expected_games.append({
            "arm": game["arm"],
            "sample_id": game["sample_id"],
            "seat_assignment": game["seat_assignment"],
            "action_sequence_sha256": game["action_sequence_sha256"],
            "final_position_digest": game["final_position_digest"],
        })
    expected_games.sort(key=lambda row: (
        row["arm"], row["sample_id"], row["seat_assignment"]["player0"], row["seat_assignment"]["player1"],
    ))
    manifest = {
        "schema_version": 1,
        "status": "PRE_REGISTERED_F86Q_CHECK_FORCING_DEPTH3_PROBE",
        "baseline_commit": F86P_BASELINE,
        "source_f86o_manifest": "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json",
        "source_f86o_manifest_blob": F86O_MANIFEST_BLOB,
        "source_f86o_result": "artifacts/f86o_common_tape_triarm_dynamic_smoke/summary.json",
        "source_f86o_result_blob": F86O_RESULT_BLOB,
        "arms": list(ARMS),
        "sample_ids": list(SAMPLES),
        "rulesets": [
            {"arm": row["arm"], "sample_id": row["sample_id"], "ruleset_fingerprint": row["ruleset_fingerprint"]}
            for row in source_manifest["rulesets"]
        ],
        "policy_tape_algorithm": source_manifest["policy_tape_algorithm"],
        "policy_tape_length": source_manifest["policy_tape_length"],
        "policy_tapes": source_manifest["policy_tapes"],
        "frozen_replay_evidence": expected_games,
        "state_selection": {
            "replay": "deterministically replay all 12 F86O games with unchanged rulesets, tapes, ordering, and max ply",
            "selected_occurrence": "a pre-move state with at least one corrected legal checking action",
            "deduplication": ["ruleset_fingerprint", "position_identity_key"],
            "occurrence_accounting": "retain trajectory occurrence multiplicity after deduplication",
            "check_predicate": "is_in_check(child.position, child.position.side_to_move, compiled)",
        },
        "forcing_classifications": {
            "MATE_IN_ONE": "checking child is CHECKMATE with winner equal to the root actor",
            "FORCED_MATE_IN_TWO": "every legal opponent reply has at least one attacker CHECKMATE action",
            "FORCED_CHECK_CONTINUATION": "not forced mate in two, and every legal opponent reply has at least one attacker checking action",
            "ESCAPABLE_CHECK": "at least one legal opponent reply has neither attacker mate-in-one nor attacker checking continuation",
        },
        "probe_accounting": {
            "new_successors": "count every enumerated opponent-reply and attacker-continuation successor; root replay successors are not double-counted",
            "maximum_specialized_depth_plies": 3,
            "hard_cap": PROBE_CAP,
            "fail_closed_route": "CHECK_FORCING_VALUE_UNRESOLVED_DUE_TO_PROBE_CAP",
        },
        "prohibited_compute": {
            "new_real_games": 0,
            "generic_search_depth": 0,
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
    manifest = _load_json(root, "artifacts/f86q_check_forcing_depth3_probe/manifest.json")
    if manifest["status"] != "PRE_REGISTERED_F86Q_CHECK_FORCING_DEPTH3_PROBE":
        raise RuntimeError("F86Q PREP manifest status drift")
    if manifest["baseline_commit"] != F86P_BASELINE:
        raise RuntimeError("F86Q baseline drift")
    if manifest["source_f86o_manifest_blob"] != F86O_MANIFEST_BLOB:
        raise RuntimeError("F86O manifest authority drift")
    if len(manifest["rulesets"]) != 6 or len(manifest["frozen_replay_evidence"]) != 12:
        raise RuntimeError("F86Q frozen replay cohort is incomplete")
    if manifest["probe_accounting"]["hard_cap"] != PROBE_CAP:
        raise RuntimeError("F86Q probe cap drift")
    return manifest


def _load_tapes(manifest: dict[str, Any]) -> dict[str, dict[str, PolicyTape]]:
    result = {}
    for sample_id in SAMPLES:
        result[sample_id] = {}
        for policy_id in ("A", "B"):
            data = manifest["policy_tapes"][sample_id][policy_id]
            result[sample_id][policy_id] = PolicyTape(policy_id, data["seed"], tuple(data["uniforms"]))
    return result


def _expected_by_key(manifest: dict[str, Any]) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    return {
        (row["arm"], row["sample_id"], row["seat_assignment"]["player0"], row["seat_assignment"]["player1"]): row
        for row in manifest["frozen_replay_evidence"]
    }


def _classify_checking_action(check_child, actor: int, compiled, probe: dict[str, Any]) -> dict[str, Any]:
    if _is_mate(check_child, actor):
        return {
            "opponent_legal_reply_count": 0,
            "minimum_attacker_continuation_count": 0,
            "maximum_attacker_continuation_count": 0,
            "replies_with_mate_continuation": 0,
            "replies_with_check_continuation": 0,
            "classification": "MATE_IN_ONE",
        }
    replies = _canonical_successors(check_child, compiled)
    probe["successors"] = _consume_probe(probe, len(replies))
    continuation_counts = []
    replies_with_mate = 0
    replies_with_check = 0
    for _reply_action, reply_child in replies:
        attacker = reply_child.position.side_to_move
        continuations = _canonical_successors(reply_child, compiled)
        probe["successors"] = _consume_probe(probe, len(continuations))
        mate_count = sum(_is_mate(child, attacker) for _action, child in continuations)
        check_count = sum(_gives_check(child, compiled) for _action, child in continuations)
        continuation_counts.append(len(continuations))
        replies_with_mate += mate_count > 0
        replies_with_check += check_count > 0
    forced_mate = bool(replies) and replies_with_mate == len(replies)
    forced_check = bool(replies) and replies_with_check == len(replies)
    if forced_mate:
        classification = "FORCED_MATE_IN_TWO"
    elif forced_check:
        classification = "FORCED_CHECK_CONTINUATION"
    else:
        classification = "ESCAPABLE_CHECK"
    return {
        "opponent_legal_reply_count": len(replies),
        "minimum_attacker_continuation_count": min(continuation_counts, default=0),
        "maximum_attacker_continuation_count": max(continuation_counts, default=0),
        "replies_with_mate_continuation": replies_with_mate,
        "replies_with_check_continuation": replies_with_check,
        "classification": classification,
    }


def _consume_probe(probe: dict[str, Any], count: int) -> int:
    if probe["successors"] + count > PROBE_CAP:
        probe["truncated"] = True
        raise _ProbeCapReached
    return probe["successors"] + count


class _ProbeCapReached(RuntimeError):
    pass


def _replay_and_probe(root: Path, prep: dict[str, Any]) -> dict[str, Any]:
    source_manifest = _f86o_manifest(root)
    expected = _expected_by_key(prep)
    tapes = _load_tapes(prep)
    roots: dict[tuple[str, str], dict[str, Any]] = {}
    replay_rows = []
    probe = {"successors": 0, "truncated": False}
    try:
        for entry in source_manifest["rulesets"]:
            compiled = compile_ruleset(ruleset_from_dict(entry["ruleset"]))
            if compiled.ruleset_fingerprint != next(row["ruleset_fingerprint"] for row in prep["rulesets"] if row["arm"] == entry["arm"] and row["sample_id"] == entry["sample_id"]):
                raise RuntimeError("F86Q ruleset fingerprint drift")
            for seats in (("A", "B"), ("B", "A")):
                key = (entry["arm"], entry["sample_id"], seats[0], seats[1])
                session = GameSession(compiled)
                consumed = {"A": 0, "B": 0}
                actions = []
                while session.result.status.value == "ongoing" and len(session.history) < MAX_PLY:
                    successors = _canonical_successors(session.state, compiled)
                    if not successors:
                        break
                    actor = session.state.position.side_to_move
                    check_pairs = [(action, child) for action, child in successors if _gives_check(child, compiled)]
                    tape_index = consumed[seats[actor]]
                    chosen_index = tapes[entry["sample_id"]][seats[actor]].choose_index(tape_index, len(successors))
                    chosen_action, _chosen_child = successors[chosen_index]
                    actions.append({"actor": actor, "action": action_to_dict(chosen_action), "legal_action_count": len(successors)})
                    if check_pairs:
                        root_key = (compiled.ruleset_fingerprint, position_identity_key(session.state.position, compiled))
                        root_row = roots.setdefault(root_key, {
                            "arm": entry["arm"],
                            "sample_id": entry["sample_id"],
                            "ruleset_fingerprint": compiled.ruleset_fingerprint,
                            "root_position_digest": root_key[1],
                            "root_actor": actor,
                            "trajectory_occurrence_count": 0,
                            "tape_chosen_check_occurrence_count": 0,
                            "actions": {},
                        })
                        root_row["trajectory_occurrence_count"] += 1
                        chosen_digest = _action_digest(chosen_action)
                        if any(_action_digest(action) == chosen_digest for action, _child in check_pairs):
                            root_row["tape_chosen_check_occurrence_count"] += 1
                        for check_action, check_child in check_pairs:
                            digest = _action_digest(check_action)
                            action_row = root_row["actions"].setdefault(digest, {
                                "checking_action_canonical_digest": digest,
                                "tape_chosen_occurrence_count": 0,
                                "action": action_to_dict(check_action),
                            })
                            action_row["trajectory_occurrence_count"] = action_row.get("trajectory_occurrence_count", 0) + 1
                            if digest == chosen_digest:
                                action_row["tape_chosen_occurrence_count"] += 1
                            if "classification" not in action_row:
                                action_row.update(_classify_checking_action(check_child, actor, compiled, probe))
                    consumed[seats[actor]] += 1
                    session.submit(chosen_action)
                sequence_sha = hashlib.sha256(_canonical_json(actions)).hexdigest()
                final_digest = position_identity_key(session.state.position, compiled)
                expected_row = expected[key]
                if sequence_sha != expected_row["action_sequence_sha256"] or final_digest != expected_row["final_position_digest"]:
                    raise RuntimeError(f"F86O replay mismatch for {key}")
                replay_rows.append({
                    "arm": entry["arm"],
                    "sample_id": entry["sample_id"],
                    "seat_assignment": expected_row["seat_assignment"],
                    "action_sequence_sha256": sequence_sha,
                    "final_position_digest": final_digest,
                    "plies": len(session.history),
                })
    except _ProbeCapReached:
        pass
    if not probe["truncated"] and len(replay_rows) != 12:
        raise RuntimeError("F86Q did not replay all 12 frozen trajectories")
    root_rows = []
    for row in sorted(roots.values(), key=lambda item: (item["arm"], item["sample_id"], item["root_position_digest"])):
        row = dict(row)
        row["actions"] = [row["actions"][key] for key in sorted(row["actions"])]
        root_rows.append(row)
    return {"replay_rows": replay_rows, "roots": root_rows, "probe": probe}


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actions = [action for row in rows for action in row["actions"]]
    unique_counts = Counter(action["classification"] for action in actions)
    occurrence_counts = Counter()
    chosen_counts = Counter()
    reply_distribution = Counter()
    for action in actions:
        occurrence_counts[action["classification"]] += action["trajectory_occurrence_count"]
        reply_distribution[str(action["opponent_legal_reply_count"])] += 1
        if action["tape_chosen_occurrence_count"]:
            chosen_counts[action["classification"]] += action["tape_chosen_occurrence_count"]
    return {
        "selected_root_state_occurrences": sum(row["trajectory_occurrence_count"] for row in rows),
        "unique_selected_states": len(rows),
        "total_legal_checking_actions": len(actions),
        "total_checking_action_occurrences": sum(action["trajectory_occurrence_count"] for action in actions),
        "classification_counts_unique": dict(sorted(unique_counts.items())),
        "classification_counts_by_occurrence": dict(sorted(occurrence_counts.items())),
        "opponent_reply_count_distribution": dict(sorted(reply_distribution.items(), key=lambda item: int(item[0]))),
        "actual_tape_chosen_check_classifications": dict(sorted(chosen_counts.items())),
    }


def _route(sample: dict[str, Any]) -> str:
    unique = sample["classification_counts_unique"]
    if unique.get("MATE_IN_ONE", 0) or unique.get("FORCED_MATE_IN_TWO", 0):
        return "SHALLOW_FORCED_MATE_EXISTS_RANDOM_POLICY_FAILED_TO_CONVERT"
    if unique.get("FORCED_CHECK_CONTINUATION", 0):
        return "FORCING_CHECK_CHAIN_EXISTS_WITHOUT_MATE_IN_TWO"
    if sample["total_legal_checking_actions"] and unique.get("ESCAPABLE_CHECK", 0) == sample["total_legal_checking_actions"]:
        return "CHECK_PRESSURE_IS_NONFORCING"
    return "NO_CHECK_PRESSURE_IN_FROZEN_TRAJECTORIES"


def run(root: Path, output: Path) -> dict[str, Any]:
    prep = _load_prep(root)
    evidence = _replay_and_probe(root, prep)
    by_arm_sample = {}
    for arm in ARMS:
        by_arm_sample[arm] = {}
        for sample_id in SAMPLES:
            rows = [row for row in evidence["roots"] if row["arm"] == arm and row["sample_id"] == sample_id]
            summary = _aggregate(rows)
            summary["route"] = _route(summary) if not evidence["probe"]["truncated"] else "CHECK_FORCING_VALUE_UNRESOLVED_DUE_TO_PROBE_CAP"
            by_arm_sample[arm][sample_id] = summary
    n_routes = [by_arm_sample["N"][sample]["route"] for sample in SAMPLES]
    overall = "CHECK_FORCING_VALUE_UNRESOLVED_DUE_TO_PROBE_CAP" if evidence["probe"]["truncated"] else (
        "CHECK_FORCING_STRUCTURE_IS_SAMPLE_DEPENDENT" if len(set(n_routes)) > 1 else n_routes[0]
    )
    result = {
        "schema_version": 1,
        "status": "F86Q_CHECK_FORCING_DEPTH3_PROBE_COMPLETE" if not evidence["probe"]["truncated"] else "F86Q_CHECK_FORCING_DEPTH3_PROBE_TRUNCATED",
        "prep_manifest": "artifacts/f86q_check_forcing_depth3_probe/manifest.json",
        "baseline_commit": F86P_BASELINE,
        "replayed_trajectories": len(evidence["replay_rows"]),
        "new_real_games": 0,
        "specialized_forcing_depth_plies": 3,
        "probe_successor_count": evidence["probe"]["successors"],
        "probe_cap": PROBE_CAP,
        "truncation": evidence["probe"]["truncated"],
        "generic_search_depth": 0,
        "alphabeta_nodes": 0,
        "bfs_expansions": 0,
        "training_compute": 0,
        "teacher_compute": 0,
        "f85_actual_compute": 0,
        "default_generator_changed": False,
        "replay_equality": {
            "action_sequence_matches": sum(row["action_sequence_sha256"] == next(item["action_sequence_sha256"] for item in prep["frozen_replay_evidence"] if item["arm"] == row["arm"] and item["sample_id"] == row["sample_id"] and item["seat_assignment"] == row["seat_assignment"]) for row in evidence["replay_rows"]),
            "final_position_digest_matches": sum(row["final_position_digest"] == next(item["final_position_digest"] for item in prep["frozen_replay_evidence"] if item["arm"] == row["arm"] and item["sample_id"] == row["sample_id"] and item["seat_assignment"] == row["seat_assignment"]) for row in evidence["replay_rows"]),
        },
        "replayed_games": evidence["replay_rows"],
        "selected_roots": evidence["roots"],
        "by_arm_sample": by_arm_sample,
        "routing": {
            "arm_n_by_sample": {sample: by_arm_sample["N"][sample]["route"] for sample in SAMPLES},
            "overall": [overall],
        },
    }
    _write_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--prep", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/f86q_check_forcing_depth3_probe/summary.json")
    parser.add_argument("--manifest-output", type=Path, default=ROOT / "artifacts/f86q_check_forcing_depth3_probe/manifest.json")
    args = parser.parse_args()
    result = build_prep(args.root, args.manifest_output) if args.prep else run(args.root, args.output)
    print(json.dumps({key: result[key] for key in ("status", "replayed_trajectories", "new_real_games", "probe_successor_count", "truncation")} if not args.prep else {"status": result["status"], "frozen_games": len(result["frozen_replay_evidence"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
