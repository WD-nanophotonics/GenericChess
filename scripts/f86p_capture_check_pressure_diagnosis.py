"""F86P deterministic interaction-pressure diagnosis for the frozen F86O games."""

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
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.core.terminal import TerminalStatus


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ("V4-3", "V5-3")
ARMS = ("L", "F", "N")
MAX_PLY = 32
PROBE_CAP = 4096


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _action_key(action) -> str:
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _canonical_successors(state, compiled):
    pairs = list(legal_successors(state, compiled))
    return sorted(pairs, key=lambda pair: _action_key(pair[0]))


def _ordinary_counts(position, compiled) -> dict[str, int]:
    counts = {"player0": 0, "player1": 0}
    for piece in position.board:
        if piece is not None and not compiled.types_by_id[piece.current_type_id].is_anchor:
            counts[f"player{piece.owner}"] += 1
    return counts


def _is_capture(action, position, actor, compiled) -> bool:
    if not action_is_board(action):
        return False
    target = position.board[square_to_index(action.to_square, compiled.board_size)]
    return target is not None and target.owner != actor and not compiled.types_by_id[target.current_type_id].is_anchor


def _anchor_pressure(position, actor, compiled) -> int:
    opponent = 1 - actor
    target = anchor_square(position, opponent, compiled)
    if target is None:
        return 0
    attacked = pseudo_attacks(position, actor, compiled)
    n = compiled.board_size
    return sum(
        1
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
        and 0 <= target.file + df < n
        and 0 <= target.rank + dr < n
        and index_to_square((target.rank + dr) * n + target.file + df, n) in attacked
    )


def _square_pair(value: Any) -> tuple[int, int]:
    if isinstance(value, str):
        parts = value.replace(",", " ").split()
        return int(parts[0]), int(parts[1])
    return int(value[0]), int(value[1])


def _shortest_empty_distance(compiled, type_id: str, owner: int, source: int, target: int) -> int | None:
    if source == target:
        return 0
    n = compiled.board_size
    frontier = [source]
    distances = {source: 0}
    while frontier:
        current = frontier.pop(0)
        for square in compiled.empty_mobility[type_id][owner][current]:
            nxt = square.rank * n + square.file
            if nxt in distances:
                continue
            distances[nxt] = distances[current] + 1
            if nxt == target:
                return distances[nxt]
            frontier.append(nxt)
    return None


def _minimum_assignment_distances(actual: list[int], targets: list[int], compiled, type_id: str, owner: int) -> int:
    if not actual and not targets:
        return 0
    penalty = compiled.board_size * compiled.board_size + 1
    if len(actual) != len(targets):
        penalty *= abs(len(actual) - len(targets))
    if not actual or not targets:
        return penalty
    best = None
    import itertools
    for permutation in itertools.permutations(targets, min(len(actual), len(targets))):
        distance = 0
        reachable = True
        for source, target in zip(actual, permutation):
            step = _shortest_empty_distance(compiled, type_id, owner, source, target)
            if step is None:
                reachable = False
                break
            distance += step
        if reachable:
            best = distance if best is None else min(best, distance)
    return penalty + (penalty if best is None else best)


def _frozen_target_templates(root: Path, sample_id: str) -> list[dict[str, Any]]:
    """Load persisted target geometry without running a census.

    F86N-R1 retained compact witness counts and the backbone witness, but not
    target-square rows. The closest persisted, frozen geometry catalog is the
    F86H ORTHO4_CURRENT witness set, reused only as an occupancy/check-agnostic
    target-distance surrogate. It is never revalidated or called a legal mate.
    """
    payload = _load_json(root, "artifacts/f86h_kinematic_mate_reachability/templates.json")
    cells = [row for row in payload["cells"] if row["sample_id"] == sample_id and row["cell"] == "ORTHO4_CURRENT"]
    return cells[0]["templates"] if cells else []


def _template_distance(position, compiled, templates: list[dict[str, Any]]) -> int:
    n = compiled.board_size
    anchors = {
        owner: next((index for index, piece in enumerate(position.board) if piece is not None and piece.owner == owner and compiled.types_by_id[piece.current_type_id].is_anchor), None)
        for owner in (0, 1)
    }
    actual_by_type = {}
    for index, piece in enumerate(position.board):
        if piece is not None and piece.owner == 0 and not compiled.types_by_id[piece.current_type_id].is_anchor:
            actual_by_type.setdefault(piece.current_type_id, []).append(index)
    best = None
    penalty = n * n + 1
    for template in templates:
        ordinary_targets = {}
        for item in template["ordinary"]:
            x, y = _square_pair(item["square"])
            ordinary_targets.setdefault(item["type_id"], []).append(y * n + x)
        distance = 0
        for type_id in sorted(set(actual_by_type) | set(ordinary_targets)):
            distance += _minimum_assignment_distances(
                actual_by_type.get(type_id, []), ordinary_targets.get(type_id, []), compiled, type_id, 0
            )
        defender_x, defender_y = _square_pair(template["defender_anchor"])
        defender_target = defender_y * n + defender_x
        if anchors[1] is None:
            distance += penalty
        else:
            distance += _shortest_empty_distance(compiled, "K", 1, anchors[1], defender_target) or penalty
        attacker_targets = [y * n + x for x, y in map(_square_pair, template.get("allowed_attacker_anchor_squares", []))]
        if anchors[0] is None or not attacker_targets:
            distance += penalty
        else:
            distances = [_shortest_empty_distance(compiled, "K", 0, anchors[0], target) for target in attacker_targets]
            finite = [value for value in distances if value is not None]
            distance += min(finite) if finite else penalty
        best = distance if best is None else min(best, distance)
    return best if best is not None else penalty * 4


def _instrument_game(entry: dict[str, Any], compiled, tape_payload: dict[str, Any], expected: dict[str, Any], templates: list[dict[str, Any]], probe_state: dict[str, Any]) -> dict[str, Any]:
    session = GameSession(compiled)
    tapes = {
        policy_id: PolicyTape(policy_id, data["seed"], tuple(data["uniforms"]))
        for policy_id, data in tape_payload.items()
    }
    seats = (expected["seat_assignment"]["player0"], expected["seat_assignment"]["player1"])
    consumed = {"A": 0, "B": 0}
    actions = []
    per_ply = []
    cumulative_captures = 0
    first_capture_ply = None
    first_check_ply = None
    minimum_opponent_material = {"player0": None, "player1": None}
    template_trace = []
    while session.result.status.value == "ongoing" and len(session.history) < MAX_PLY:
        state = session.state
        actor = state.position.side_to_move
        if probe_state["one_ply_child_probes"] >= PROBE_CAP:
            probe_state["truncated"] = True
            break
        successors = _canonical_successors(state, compiled)
        if probe_state["one_ply_child_probes"] + len(successors) > PROBE_CAP:
            probe_state["truncated"] = True
            break
        probe_state["one_ply_child_probes"] += len(successors)
        legal_count = len(successors)
        if not successors:
            break
        current_material = _ordinary_counts(state.position, compiled)
        current_key = position_identity_key(state.position, compiled)
        pressure = _anchor_pressure(state.position, actor, compiled)
        capture_flags = [_is_capture(action, state.position, actor, compiled) for action, _child in successors]
        check_flags = [is_in_check(child.position, actor, compiled) for _action, child in successors]
        mate_flags = [child.terminal_status.status is TerminalStatus.CHECKMATE and child.terminal_status.winner == actor for _action, child in successors]
        capture_available = sum(capture_flags)
        check_available = sum(check_flags)
        mate_available = sum(mate_flags)
        policy_id = seats[actor]
        tape_index = consumed[policy_id]
        chosen_index = tapes[policy_id].choose_index(tape_index, legal_count)
        chosen_action, chosen_child = successors[chosen_index]
        chosen_capture = capture_flags[chosen_index]
        chosen_check = check_flags[chosen_index]
        if chosen_capture:
            cumulative_captures += 1
            first_capture_ply = first_capture_ply or len(session.history) + 1
        if chosen_check:
            first_check_ply = first_check_ply or len(session.history) + 1
        for owner in (0, 1):
            opponent = current_material[f"player{1 - owner}"]
            prior = minimum_opponent_material[f"player{owner}"]
            minimum_opponent_material[f"player{owner}"] = opponent if prior is None else min(prior, opponent)
        if entry["arm"] == "N":
            template_trace.append(_template_distance(state.position, compiled, templates))
        actions.append({"actor": actor, "action": action_to_dict(chosen_action), "legal_action_count": legal_count})
        per_ply.append({
            "ply": len(session.history) + 1,
            "actor": actor,
            "position_digest": current_key,
            "ordinary_material_counts": current_material,
            "chosen_capture": chosen_capture,
            "chosen_check": chosen_check,
            "side_to_move_in_check": is_in_check(state.position, actor, compiled),
            "legal_action_count": legal_count,
            "legal_capture_action_count": capture_available,
            "legal_check_giving_action_count": check_available,
            "legal_mate_in_one_action_count": mate_available,
            "opponent_anchor_pressure_count": pressure,
            "cumulative_captures": cumulative_captures,
        })
        consumed[policy_id] += 1
        session.submit(chosen_action)
    terminal_status = session.result.status.value
    outcome_label = f"ongoing@{MAX_PLY}" if terminal_status == "ongoing" else terminal_status
    sequence = json.dumps(actions, sort_keys=True, separators=(",", ":")).encode("utf-8")
    action_sha = hashlib.sha256(sequence).hexdigest()
    if action_sha != expected["action_sequence_sha256"]:
        raise RuntimeError(f"F86O action replay mismatch for {entry['arm']}/{entry['sample_id']}/{seats}")
    final_digest = position_identity_key(session.state.position, compiled)
    if final_digest != expected["final_position_digest"]:
        raise RuntimeError(f"F86O final position mismatch for {entry['arm']}/{entry['sample_id']}/{seats}")
    start_material = _ordinary_counts(GameSession(compiled).state.position, compiled)
    final_material = _ordinary_counts(session.state.position, compiled)
    record = {
        "arm": entry["arm"],
        "sample_id": entry["sample_id"],
        "seat_assignment": expected["seat_assignment"],
        "terminal_label": outcome_label,
        "plies": len(session.history),
        "action_sequence_sha256": action_sha,
        "final_position_digest": final_digest,
        "one_ply_child_probes": sum(row["legal_action_count"] for row in per_ply),
        "per_ply": per_ply,
        "policy_tape_consumed_count": consumed,
        "chosen_capture_count": sum(row["chosen_capture"] for row in per_ply),
        "chosen_check_count": sum(row["chosen_check"] for row in per_ply),
        "capture_available_ply_count": sum(row["legal_capture_action_count"] > 0 for row in per_ply),
        "check_available_ply_count": sum(row["legal_check_giving_action_count"] > 0 for row in per_ply),
        "mate_in_one_opportunity_count": sum(row["legal_mate_in_one_action_count"] for row in per_ply),
        "first_capture_ply": first_capture_ply,
        "first_check_ply": first_check_ply,
        "cumulative_captures": cumulative_captures,
        "start_ordinary_material": start_material,
        "final_ordinary_material": final_material,
        "material_reduction": sum(start_material.values()) - sum(final_material.values()),
        "minimum_opponent_ordinary_material_remaining": minimum_opponent_material,
        "opponent_anchor_pressure_trajectory": [row["opponent_anchor_pressure_count"] for row in per_ply],
    }
    if entry["arm"] == "N":
        record["template_distance_surrogate"] = {
            "definition": "occupancy/check/capture-ignorant empty-board minimum assignment plus two Anchor distances",
            "template_source": "artifacts/f86h_kinematic_mate_reachability/templates.json:ORTHO4_CURRENT frozen target geometry; F86N-R1 compact result retained counts, not target rows",
            "start_value": template_trace[0] if template_trace else None,
            "minimum_value": min(template_trace) if template_trace else None,
            "final_value": template_trace[-1] if template_trace else None,
            "ply_of_minimum": (template_trace.index(min(template_trace)) + 1) if template_trace else None,
        }
    return record


def _aggregate(games: list[dict[str, Any]]) -> dict[str, Any]:
    total_plies = sum(len(game["per_ply"]) for game in games)
    return {
        "trajectory_count": len(games),
        "plies": total_plies,
        "plies_with_capture_available_fraction": sum(game["capture_available_ply_count"] for game in games) / total_plies if total_plies else 0.0,
        "chosen_capture_count": sum(game["chosen_capture_count"] for game in games),
        "captures_per_game": [game["chosen_capture_count"] for game in games],
        "plies_with_check_available_fraction": sum(game["check_available_ply_count"] for game in games) / total_plies if total_plies else 0.0,
        "chosen_check_count": sum(game["chosen_check_count"] for game in games),
        "mate_in_one_opportunity_count": sum(game["mate_in_one_opportunity_count"] for game in games),
        "material_reduction": [game["material_reduction"] for game in games],
        "first_capture_ply": [game["first_capture_ply"] for game in games],
        "first_check_ply": [game["first_check_ply"] for game in games],
        "terminal_distribution": dict(sorted(Counter(game["terminal_label"] for game in games).items())),
        "opponent_anchor_pressure_trajectories": [game["opponent_anchor_pressure_trajectory"] for game in games],
    }


def _route(by_arm: dict[str, dict[str, Any]]) -> str:
    n = by_arm["N"]
    low_pressure = n["plies_with_capture_available_fraction"] <= 0.10 and n["plies_with_check_available_fraction"] <= 0.10
    no_material = sum(n["material_reduction"]) == 0
    no_mate_one = n["mate_in_one_opportunity_count"] == 0
    if low_pressure and no_material and no_mate_one:
        return "DYNAMIC_INTERACTION_PRESSURE_INSUFFICIENT"
    if (
        n["mate_in_one_opportunity_count"] > 0
        and n["plies_with_check_available_fraction"] > 0.10
        and n["chosen_check_count"] < n["plies"] * 0.10
    ):
        return "RANDOM_POLICY_MISSES_EXISTING_TERMINATION_OPPORTUNITIES"
    if sum(n["material_reduction"]) > 0 and no_mate_one:
        return "LEGAL_PATH_OR_MATE_BASIN_OBSTRUCTION_REMAINS"
    return "DYNAMIC_TERMINATION_FAILURE_IS_MULTI_MECHANISM"


def run(root: Path, output: Path) -> dict[str, Any]:
    manifest = _load_json(root, "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json")
    f86o = _load_json(root, "artifacts/f86o_common_tape_triarm_dynamic_smoke/summary.json")
    expected = {(game["arm"], game["sample_id"], game["seat_assignment"]["player0"], game["seat_assignment"]["player1"]): game for game in f86o["games"]}
    tapes = {
        sample_id: {
            policy_id: data
            for policy_id, data in policies.items()
        }
        for sample_id, policies in manifest["policy_tapes"].items()
    }
    probe_state = {"one_ply_child_probes": 0, "truncated": False}
    games = []
    for entry in manifest["rulesets"]:
        compiled = compile_ruleset(ruleset_from_dict(entry["ruleset"]))
        for seats in (("A", "B"), ("B", "A")):
            key = (entry["arm"], entry["sample_id"], seats[0], seats[1])
            templates = _frozen_target_templates(root, entry["sample_id"]) if entry["arm"] == "N" else []
            games.append(_instrument_game(entry, compiled, tapes[entry["sample_id"]], expected[key], templates, probe_state))
            if probe_state["truncated"]:
                break
        if probe_state["truncated"]:
            break
    if len(games) != 12 and not probe_state["truncated"]:
        raise RuntimeError("F86P did not replay all 12 frozen trajectories")
    by_arm = {arm: _aggregate([game for game in games if game["arm"] == arm]) for arm in ARMS}
    result = {
        "schema_version": 1,
        "status": "F86P_FROZEN_TRAJECTORY_INTERACTION_DIAGNOSIS_COMPLETE",
        "source_f86o_manifest": "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json",
        "source_f86o_result": "artifacts/f86o_common_tape_triarm_dynamic_smoke/summary.json",
        "replayed_trajectories": len(games),
        "new_real_games": 0,
        "one_ply_child_probes": probe_state["one_ply_child_probes"],
        "one_ply_child_probe_cap": PROBE_CAP,
        "truncation": probe_state["truncated"],
        "deeper_search_nodes": 0,
        "bfs_expansions": 0,
        "alphabeta_nodes": 0,
        "training_compute": 0,
        "teacher_compute": 0,
        "f85_actual_compute": 0,
        "by_arm": by_arm,
        "games": games,
        "routing": [_route(by_arm)] if len(games) == 12 else ["F86P_ONE_PLY_PROBE_CAP_TRUNCATED"],
        "default_generator_changed": False,
    }
    _write_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/f86p_capture_check_pressure_diagnosis/summary.json")
    args = parser.parse_args()
    result = run(args.root, args.output)
    print(json.dumps({key: result[key] for key in ("status", "replayed_trajectories", "new_real_games", "one_ply_child_probes", "truncation", "routing")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
