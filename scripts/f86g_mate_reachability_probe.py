"""F86G shallow mate-reachability and state-distribution probe."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from generic_chess.benchmark.policy_tape import PolicyTape
from generic_chess.core.actions import (
    action_is_board,
    action_to_dict,
    action_target_square,
)
from generic_chess.core.attacks import is_in_check
from generic_chess.core.coordinates import index_to_square, square_to_index
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Position
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession


SAMPLES = ("V4-3", "V5-3")
CELLS = ("ORTHO4_CURRENT", "FULL8_CURRENT")
MAX_PLY = 32
CHILD_PROBE_CAP = 4096
BFS_DEPTH_CAP = 8
BFS_EXPANSION_CAP = 8192
TOTAL_BFS_CAP = 32768


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _load_json(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _load_rulesets(root: Path) -> dict[tuple[str, str], object]:
    result: dict[tuple[str, str], object] = {}
    f86d = _load_json(root, "artifacts/f86d_mobility_ablation/counterfactual_rulesets.json")
    for row in f86d["rows"]:
        if row["sample_id"] in SAMPLES and row["profile"] == "A_FULL_ANCHOR":
            result[(row["sample_id"], "FULL8_CURRENT")] = ruleset_from_dict(row["ruleset"])
    f86e = _load_json(root, "artifacts/f86e_anchor_placement_ablation/counterfactual_rulesets.json")
    for row in f86e["rows"]:
        if row["sample_id"] in SAMPLES and row["cell"] == "ORTHO4_CURRENT":
            result[(row["sample_id"], "ORTHO4_CURRENT")] = ruleset_from_dict(row["ruleset"])
    return result


def _load_tapes(root: Path) -> dict[str, dict[str, PolicyTape]]:
    payload = _load_json(root, "artifacts/f86e_r1_common_policy_replay/policy_tapes.json")
    return {
        sample_id: {
            policy_id: PolicyTape(policy_id, value["seed"], tuple(value["uniforms"]))
            for policy_id, value in policies.items()
        }
        for sample_id, policies in payload["samples"].items()
    }


def _anchor_type_id(compiled) -> str:
    return next(piece_type.type_id for piece_type in compiled.piece_types if piece_type.is_anchor)


def _square_payload(square, n: int) -> list[int]:
    return [square.file, square.rank]


def _anchor_zone(position: Position, owner: int, compiled) -> set[int]:
    n = compiled.board_size
    anchor_type = _anchor_type_id(compiled)
    anchor_index = _anchor_index(position, owner, compiled)
    return {
        anchor_index,
        *(square_to_index(target, n) for target in compiled.empty_mobility[anchor_type][owner][anchor_index]),
    }


def _anchor_index(position: Position, owner: int, compiled) -> int:
    anchor_type = _anchor_type_id(compiled)
    return next(
        index for index, piece in enumerate(position.board)
        if piece is not None and piece.owner == owner and piece.current_type_id == anchor_type
    )


def _ordinary_attack_squares(position: Position, owner: int, compiled) -> set[int]:
    n = compiled.board_size
    attacks: set[int] = set()
    for index, piece in enumerate(position.board):
        if piece is None or piece.owner != owner:
            continue
        piece_type = compiled.types_by_id[piece.current_type_id]
        if piece_type.is_anchor:
            continue
        for atom_index, atom in enumerate(piece_type.movement_atoms):
            if isinstance(atom, LeapAtom):
                targets = compiled.leap_targets[piece.current_type_id][owner][index][atom_index]
                attacks.update(square_to_index(target, n) for target in targets)
            else:
                for target in compiled.ray_paths[piece.current_type_id][owner][index][atom_index]:
                    target_index = square_to_index(target, n)
                    attacks.add(target_index)
                    if position.board[target_index] is not None:
                        break
    return attacks


def _ordinary_counts(position: Position, compiled) -> dict[str, dict[str, int]]:
    counts = {"0": Counter(), "1": Counter()}
    for piece in position.board:
        if piece is None or compiled.types_by_id[piece.current_type_id].is_anchor:
            continue
        counts[str(piece.owner)][piece.current_type_id] += 1
    return {owner: dict(sorted(counter.items())) for owner, counter in counts.items()}


def _action_captured_piece(position: Position, action):
    if not action_is_board(action):
        return None
    n = position.board_size()
    target_index = action_target_square(action).rank * n + action_target_square(action).file
    return position.board[target_index]


def _action_sort_key(action) -> str:
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _canonical_actions(session: GameSession) -> tuple:
    return tuple(sorted(session.legal_actions(), key=_action_sort_key))


def _coverage_by_owner(position: Position, compiled) -> dict[str, dict[str, Any]]:
    n = compiled.board_size
    result: dict[str, dict[str, Any]] = {}
    for owner in (0, 1):
        anchor_index = _anchor_index(position, owner, compiled)
        zone = _anchor_zone(position, owner, compiled)
        attacks = _ordinary_attack_squares(position, 1 - owner, compiled)
        covered = sorted(zone & attacks)
        result[str(owner)] = {
            "anchor_zone_size": len(zone),
            "ordinary_attacked_squares": [
                _square_payload(index_to_square(index, n), n) for index in covered
            ],
            "coverage_fraction": len(covered) / len(zone) if zone else 0.0,
            "anchor_itself_ordinary_attacked": anchor_index in attacks,
        }
    return result


class ChildProbeBudget:
    def __init__(self, cap: int):
        self.cap = cap
        self.used = 0
        self.truncated = False

    def available(self) -> bool:
        if self.used >= self.cap:
            self.truncated = True
            return False
        self.used += 1
        return True


def _probe_state(
    session: GameSession,
    compiled,
    budget: ChildProbeBudget,
    capture_event: dict[str, Any] | None,
) -> dict[str, Any]:
    position = session.state.position
    side = position.side_to_move
    enemy = 1 - side
    n = compiled.board_size
    attacks = _ordinary_attack_squares(position, side, compiled)
    enemy_anchor_index = _anchor_index(position, enemy, compiled)
    enemy_zone = _anchor_zone(position, enemy, compiled)
    covered = sorted(enemy_zone & attacks)
    coverage = len(covered) / len(enemy_zone) if enemy_zone else 0.0
    coverage_by_owner = _coverage_by_owner(position, compiled)
    actions = list(_canonical_actions(session)) if session.result.status.value == "ongoing" else []
    checking_count: int | None = 0
    mate_one_count: int | None = 0
    state_probe_truncated = False
    if actions:
        for action in actions:
            if not budget.available():
                checking_count = None
                mate_one_count = None
                state_probe_truncated = True
                break
            child = GameSession.replay(compiled, session.to_record())
            child.submit(action)
            if is_in_check(child.state.position, child.state.position.side_to_move, compiled):
                checking_count += 1
            if child.result.status.value == "checkmate":
                mate_one_count += 1
    return {
        "ply": len(session.history),
        "side_to_move": side,
        "ordinary_pieces_remaining_by_owner": _ordinary_counts(position, compiled),
        "legal_action_count": len(actions),
        "side_to_move_currently_in_check": is_in_check(position, side, compiled),
        "legal_checking_move_count": checking_count,
        "legal_mate_in_one_move_count": mate_one_count,
        "enemy_anchor_zone_size": len(enemy_zone),
        "ordinary_only_attacked_squares_in_enemy_anchor_zone": [
            _square_payload(index_to_square(index, n), n) for index in covered
        ],
        "ordinary_only_anchor_zone_coverage_fraction": coverage,
        "enemy_anchor_itself_ordinary_attacked": enemy_anchor_index in attacks,
        "ordinary_anchor_zone_coverage_by_owner": coverage_by_owner,
        "capture_occurred_since_previous": capture_event is not None,
        "captured_owner": capture_event["captured_owner"] if capture_event else None,
        "captured_piece_type": capture_event["captured_piece_type"] if capture_event else None,
        "captured_owner_pre_capture_coverage": (
            capture_event["pre_capture_coverage"] if capture_event else None
        ),
        "captured_owner_post_capture_coverage": (
            coverage_by_owner[str(capture_event["captured_owner"])] ["coverage_fraction"]
            if capture_event else None
        ),
        "same_owner_capture_coverage_delta": (
            coverage_by_owner[str(capture_event["captured_owner"])] ["coverage_fraction"]
            - capture_event["pre_capture_coverage"]
            if capture_event else None
        ),
        "probe_truncated": state_probe_truncated,
    }


def _play_trajectory(compiled, tapes: dict[str, PolicyTape], seat_assignment: tuple[str, str], budget: ChildProbeBudget) -> dict[str, Any]:
    session = GameSession(compiled)
    consumed = {"A": 0, "B": 0}
    states: list[dict[str, Any]] = []
    capture_event: dict[str, Any] | None = None
    while True:
        state_probe = _probe_state(session, compiled, budget, capture_event)
        state_probe["state_index"] = len(states)
        states.append(state_probe)
        if session.result.status.value != "ongoing" or len(session.history) >= MAX_PLY:
            break
        actions = _canonical_actions(session)
        actor = session.state.position.side_to_move
        policy_id = seat_assignment[actor]
        move_index = consumed[policy_id]
        action = actions[tapes[policy_id].choose_index(move_index, len(actions))]
        consumed[policy_id] += 1
        captured = _action_captured_piece(session.state.position, action)
        if captured is None:
            capture_event = None
        else:
            pre_capture = state_probe["ordinary_anchor_zone_coverage_by_owner"][str(captured.owner)]
            capture_event = {
                "captured_owner": captured.owner,
                "captured_piece_type": captured.current_type_id,
                "pre_capture_coverage": pre_capture["coverage_fraction"],
            }
        session.submit(action)
    return {
        "seat_assignment": {"player0": seat_assignment[0], "player1": seat_assignment[1]},
        "plies": len(session.history),
        "terminal_status": session.result.status.value,
        "winner": session.result.winner,
        "policy_move_counts": consumed,
        "states": states,
    }


def _trajectory_summary(trajectories: list[dict[str, Any]], budget: ChildProbeBudget) -> dict[str, Any]:
    states = [state for trajectory in trajectories for state in trajectory["states"]]
    known = [state for state in states if state["legal_checking_move_count"] is not None]
    captures = [state for state in states if state["capture_occurred_since_previous"]]
    return {
        "trajectory_count": len(trajectories),
        "inspected_state_count": len(states),
        "states_with_current_check": sum(state["side_to_move_currently_in_check"] for state in states),
        "states_with_legal_checking_move": sum(state["legal_checking_move_count"] > 0 for state in known),
        "states_with_legal_mate_in_one": sum(state["legal_mate_in_one_move_count"] > 0 for state in known),
        "total_legal_checking_moves": sum(state["legal_checking_move_count"] for state in known),
        "total_legal_mate_in_one_moves": sum(state["legal_mate_in_one_move_count"] for state in known),
        "max_ordinary_anchor_zone_coverage": max(
            (state["ordinary_only_anchor_zone_coverage_fraction"] for state in states), default=0.0
        ),
        "enemy_anchor_attacked_state_count": sum(state["enemy_anchor_itself_ordinary_attacked"] for state in states),
        "capture_count": len(captures),
        "same_owner_capture_coverage_deltas": [
            state["same_owner_capture_coverage_delta"] for state in captures
        ],
        "probe_truncated": budget.truncated,
    }


class DedupSafetyError(RuntimeError):
    """The probe found history representatives that disagree under one key."""


def _assert_path_safe_dedup_preconditions(compiled) -> dict[str, Any]:
    checks = {
        "repetition_policy_is_draw": getattr(compiled, "repetition_policy", None) == "draw",
        "no_continuous_check_history_dependency": getattr(compiled, "repetition_policy", None) != "continuous_check_loss",
        "semantic_actions_empty": not getattr(compiled, "semantic_actions", ()),
        "automatic_adjudications_empty": not getattr(compiled, "automatic_adjudications", ()),
    }
    if not all(checks.values()):
        raise DedupSafetyError(f"path-safe dedup preconditions failed: {checks}")
    return checks


def _reachability_key(session: GameSession) -> tuple[Any, int, tuple[tuple[str, int], ...]]:
    state = session.state
    return (state.position, state.ply_count, state.repetition_counts)


def _representative_signature(session: GameSession) -> tuple[str, tuple[str, ...]]:
    return (
        session.result.status.value,
        tuple(_action_sort_key(action) for action in _canonical_actions(session)),
    )


def _assert_equivalent_representatives(left: GameSession, right: GameSession) -> None:
    left_signature = _representative_signature(left)
    right_signature = _representative_signature(right)
    if left_signature != right_signature:
        raise DedupSafetyError(
            "same reachability key has inconsistent terminal/legal-action signatures"
        )


def _cooperative_bfs_impl(
    compiled,
    *,
    dedup_enabled: bool,
    dedup_preconditions: dict[str, bool] | None,
    dedup_disabled_reason: str | None = None,
) -> dict[str, Any]:
    root = GameSession(compiled)
    frontier = [root]
    seen = {_reachability_key(root): root} if dedup_enabled else None
    depth = 0
    expansions = 0
    deepest_completed = -1
    first_check_depth: int | None = None
    first_mate_depth: int | None = None
    winner: int | None = None
    node_truncated = False
    generated_child_states = 0
    unique_enqueued_states = 0
    duplicate_pruned_states = 0
    current_level_states_already_expanded = 0
    unexpanded_current_frontier = 0
    generated_next_frontier = 0
    truncation_reason = None
    while frontier and depth <= BFS_DEPTH_CAP:
        next_frontier: list[GameSession] = []
        current_level_expanded = 0
        for index, session in enumerate(frontier):
            if expansions >= BFS_EXPANSION_CAP:
                node_truncated = True
                current_level_states_already_expanded = current_level_expanded
                unexpanded_current_frontier = len(frontier) - index
                generated_next_frontier = len(next_frontier)
                truncation_reason = "state_expansion_cap_with_unexpanded_current_frontier"
                break
            expansions += 1
            current_level_expanded += 1
            if is_in_check(session.state.position, session.state.position.side_to_move, compiled) and first_check_depth is None:
                first_check_depth = depth
            if session.result.status.value == "checkmate":
                first_mate_depth = depth
                winner = session.result.winner
                frontier = []
                next_frontier = []
                break
            if depth >= BFS_DEPTH_CAP:
                continue
            for action in _canonical_actions(session):
                child = GameSession.replay(compiled, session.to_record())
                child.submit(action)
                generated_child_states += 1
                key = _reachability_key(child)
                if seen is not None:
                    existing = seen.get(key)
                    if existing is not None:
                        _assert_equivalent_representatives(existing, child)
                        duplicate_pruned_states += 1
                        continue
                    seen[key] = child
                unique_enqueued_states += 1
                next_frontier.append(child)
        else:
            current_level_states_already_expanded = current_level_expanded
            deepest_completed = depth
            generated_next_frontier = len(next_frontier)
        if first_mate_depth is not None:
            break
        if node_truncated:
            break
        frontier = next_frontier
        depth += 1
    depth_cap_reached = first_mate_depth is None and deepest_completed >= BFS_DEPTH_CAP
    if depth_cap_reached and not node_truncated:
        truncation_reason = "depth_cap_reached_without_mate"
    if not node_truncated and not depth_cap_reached and first_mate_depth is None:
        truncation_reason = "frontier_exhausted_without_mate"
    return {
        "first_reachable_check_depth": first_check_depth,
        "first_reachable_checkmate_depth": first_mate_depth,
        "winner": winner,
        "state_expansions": expansions,
        "deepest_fully_completed_bfs_depth": deepest_completed,
        "frontier_size": unexpanded_current_frontier,
        "generated_child_states": generated_child_states,
        "unique_enqueued_states": unique_enqueued_states,
        "duplicate_pruned_states": duplicate_pruned_states,
        "current_level_states_already_expanded": current_level_states_already_expanded,
        "unexpanded_current_frontier": unexpanded_current_frontier,
        "generated_next_frontier": generated_next_frontier,
        "dedup_enabled": dedup_enabled,
        "dedup_preconditions": dedup_preconditions,
        "dedup_disabled_reason": dedup_disabled_reason,
        "exact_truncation_reason": truncation_reason,
        "node_truncated": node_truncated,
        "depth_cap_reached": depth_cap_reached,
        "truncation": node_truncated or depth_cap_reached,
    }


def _cooperative_bfs(compiled) -> dict[str, Any]:
    try:
        preconditions = _assert_path_safe_dedup_preconditions(compiled)
    except DedupSafetyError as exc:
        return _cooperative_bfs_impl(
            compiled,
            dedup_enabled=False,
            dedup_preconditions=None,
            dedup_disabled_reason=str(exc),
        )
    try:
        return _cooperative_bfs_impl(
            compiled,
            dedup_enabled=True,
            dedup_preconditions=preconditions,
        )
    except DedupSafetyError as exc:
        return _cooperative_bfs_impl(
            compiled,
            dedup_enabled=False,
            dedup_preconditions=preconditions,
            dedup_disabled_reason=str(exc),
        )


def _routing(trajectory_by_cell: dict[str, dict[str, Any]], bfs_by_cell: dict[str, dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    mates = [row["first_reachable_checkmate_depth"] for row in bfs_by_cell.values()]
    any_mate = any(depth is not None for depth in mates)
    any_node_truncated = any(row["node_truncated"] for row in bfs_by_cell.values())
    if any_node_truncated and not any_mate:
        labels.append("MATE_REACHABILITY_UNRESOLVED_DUE_TO_STATE_CAP")
    else:
        if any_mate and all(row["states_with_legal_mate_in_one"] == 0 for row in trajectory_by_cell.values()):
            labels.append("MATE_REACHABLE_BUT_BASELINE_STATE_DISTRIBUTION_MISSES_IT")
        if any(row["states_with_current_check"] > 0 for row in trajectory_by_cell.values()) and not any_mate:
            labels.append("CHECK_REACHABLE_MATE_PATH_UNRESOLVED")
        if not any_node_truncated and any_mate and len({depth is not None for depth in mates}) > 1:
            labels.append("ANCHOR_PROFILE_AFFECTS_SHALLOW_MATE_REACHABILITY")
        if not any_node_truncated and all(row["first_reachable_check_depth"] is not None for row in bfs_by_cell.values()) and not any_mate:
            labels.append("SHALLOW_MATE_REACHABILITY_LIMITED")
    return labels or ["MATE_REACHABILITY_NOT_RESOLVED_WITHIN_BOUND"]


def run(output_dir: Path, root: Path) -> dict[str, Any]:
    rulesets = _load_rulesets(root)
    tapes = _load_tapes(root)
    fingerprints: dict[str, dict[str, str]] = {}
    trajectories: list[dict[str, Any]] = []
    trajectory_by_cell: dict[str, dict[str, Any]] = {}
    total_budget = ChildProbeBudget(CHILD_PROBE_CAP)
    for sample_id in SAMPLES:
        for cell in CELLS:
            compiled = compile_ruleset(rulesets[(sample_id, cell)])
            fingerprints.setdefault(sample_id, {})[cell] = compiled.ruleset_fingerprint
            cell_trajectories = []
            for seat_assignment in (("A", "B"), ("B", "A")):
                trajectory = _play_trajectory(compiled, tapes[sample_id], seat_assignment, total_budget)
                trajectory["sample_id"] = sample_id
                trajectory["cell"] = cell
                cell_trajectories.append(trajectory)
                trajectories.append(trajectory)
            trajectory_by_cell[f"{sample_id}:{cell}"] = {
                **_trajectory_summary(cell_trajectories, total_budget),
                "sample_id": sample_id,
                "cell": cell,
            }

    bfs_results: dict[str, dict[str, Any]] = {}
    total_bfs_expansions = 0
    for sample_id in SAMPLES:
        for cell in CELLS:
            compiled = compile_ruleset(rulesets[(sample_id, cell)])
            result = _cooperative_bfs(compiled)
            result.update({"sample_id": sample_id, "cell": cell})
            bfs_results[f"{sample_id}:{cell}"] = result
            total_bfs_expansions += result["state_expansions"]
    if total_bfs_expansions > TOTAL_BFS_CAP:
        raise RuntimeError(f"BFS expansion cap exceeded: {total_bfs_expansions} > {TOTAL_BFS_CAP}")

    trajectory_payload = {
        "schema_version": 2,
        "sample_ids": list(SAMPLES),
        "cell_names": list(CELLS),
        "ruleset_fingerprints": fingerprints,
        "policy_tape_source": "artifacts/f86e_r1_common_policy_replay/policy_tapes.json",
        "policy_tape_algorithm": "python_random_mt19937_random_floor_index_v1",
        "policy_tape_seeds": {
            sample_id: {policy_id: tape.seed for policy_id, tape in policies.items()}
            for sample_id, policies in tapes.items()
        },
        "trajectory_count": len(trajectories),
        "trajectories": trajectories,
        "per_cell": trajectory_by_cell,
        "legal_child_probe_cap": CHILD_PROBE_CAP,
        "legal_child_probe_count": total_budget.used,
        "probe_truncated": total_budget.truncated,
        "real_new_random_seeds": 0,
        "teacher_learned_search_compute": 0,
        "default_generator_changed": False,
        "f85_actual_compute": 0,
    }
    cooperative_payload = {
        "schema_version": 2,
        "sample_ids": list(SAMPLES),
        "cell_names": list(CELLS),
        "ruleset_fingerprints": fingerprints,
        "depth_cap": BFS_DEPTH_CAP,
        "state_expansion_cap_per_cell": BFS_EXPANSION_CAP,
        "state_expansion_cap_total": TOTAL_BFS_CAP,
        "results": bfs_results,
        "path_safe_dedup": {
            "key_fields": ["position", "ply_count", "repetition_counts"],
            "scope": "this_probe_only",
            "preconditions": _assert_path_safe_dedup_preconditions(
                compile_ruleset(rulesets[(SAMPLES[0], CELLS[0])])
            ),
        },
        "total_state_expansions": total_bfs_expansions,
        "any_node_truncation": any(result["node_truncated"] for result in bfs_results.values()),
        "routing": _routing(trajectory_by_cell, bfs_results),
        "real_new_random_seeds": 0,
        "teacher_learned_search_compute": 0,
        "default_generator_changed": False,
        "f85_actual_compute": 0,
    }
    _write_json(output_dir / "trajectory_probe.json", trajectory_payload)
    _write_json(output_dir / "cooperative_reachability.json", cooperative_payload)
    return {"trajectory": trajectory_payload, "cooperative": cooperative_payload}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/f86g_mate_reachability"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.output_dir, args.root)
    print(json.dumps({
        "trajectory_count": result["trajectory"]["trajectory_count"],
        "inspected_state_count": sum(row["inspected_state_count"] for row in result["trajectory"]["per_cell"].values()),
        "legal_child_probe_count": result["trajectory"]["legal_child_probe_count"],
        "bfs_expansions": result["cooperative"]["total_state_expansions"],
        "routing": result["cooperative"]["routing"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
