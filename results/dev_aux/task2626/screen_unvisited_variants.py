"""Bounded outcome-blind mechanism screen for task2433 rules 2..15."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import serialize_game_record
from generic_chess.session.session import GameSession
from tools.local_agent.environment import require_identity

OUT = ROOT / "results/dev_aux/task2626/task2433-unvisited-variant-screen.json"
INPUTS = ROOT / "results/dev_aux/task2433/inputs.json"
INDICES = tuple(range(2, 16))
NODE_CAP_PER_RULE = 20_000
DEPTH_CAP = 24
TIME_CAP_PER_RULE = 30.0


def clone(session: GameSession) -> GameSession:
    other = object.__new__(GameSession)
    for name in type(session).__slots__:
        setattr(other, name, getattr(session, name))
    return other


def p_to_r(session: GameSession) -> bool:
    return any(piece is not None and piece.base_type_id == "P"
               and piece.current_type_id == "R"
               for piece in session.state.position.board)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def screen_rule(index: int, input_by_index: dict[int, dict]) -> dict:
    relative = f"results/dev_aux/task2433/rules-{index}.json"
    raw = (ROOT / relative).read_bytes()
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
    start = GameSession(compiled)
    queue = deque([(start, [])])
    seen = {start.state.position}
    expanded = generated = p_moves = p_captures = 0
    max_depth = 0
    witness = None
    began = time.perf_counter()

    while (queue and expanded < NODE_CAP_PER_RULE
           and time.perf_counter() - began < TIME_CAP_PER_RULE):
        state, action_path = queue.popleft()
        depth = len(action_path)
        max_depth = max(max_depth, depth)
        if depth >= DEPTH_CAP:
            continue
        legal = state.legal_actions()
        expanded += 1
        position = state.state.position
        for action in legal:
            is_pawn_action = getattr(action, "actor_type_id", None) == "P"
            if is_pawn_action:
                p_moves += 1
                target = action.to_square
                captured = position.board[target.rank * 4 + target.file]
                if captured is not None and captured.owner != position.side_to_move:
                    p_captures += 1
            child = clone(state)
            child.submit(action)
            generated += 1
            path = action_path + [action_to_dict(action)]
            if p_to_r(child):
                witness = {
                    "plies": len(path),
                    "actions": path,
                    "record": json.loads(serialize_game_record(child.to_record())),
                }
                break
            if not any(piece is not None and piece.owner == 0
                       and piece.base_type_id == "P" and piece.current_type_id == "P"
                       for piece in child.state.position.board):
                continue
            key = child.state.position
            if key not in seen:
                seen.add(key)
                queue.append((child, path))
        if witness is not None:
            break

    status = ("WITNESS_FOUND" if witness is not None else
              "EXHAUSTED_POSITION_GRAPH" if not queue else "CAP_REACHED")
    input_record = input_by_index[index]["record"]
    return {
        "index": index,
        "rule_path": relative,
        "rule_sha256": sha(raw),
        "prefit_full_record_sha256": sha(json.dumps(
            input_record, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode()),
        "status": status,
        "expanded_positions": expanded,
        "unique_positions": len(seen),
        "generated_transitions": generated,
        "legal_P_moves": p_moves,
        "legal_P_capture_actions": p_captures,
        "max_expanded_depth": max_depth,
        "frontier_remaining": len(queue),
        "seconds": time.perf_counter() - began,
        "witness": witness,
    }


def main() -> None:
    require_identity()
    if OUT.exists():
        raise FileExistsError("unvisited-variant screen is write-once")
    inputs_raw = INPUTS.read_bytes()
    inputs = json.loads(inputs_raw)
    input_by_index = {row["index"]: row for row in inputs}
    rows = []
    began = time.perf_counter()
    for index in INDICES:
        row = screen_rule(index, input_by_index)
        rows.append(row)
        print(json.dumps({k: v for k, v in row.items() if k != "witness"},
                         sort_keys=True), flush=True)
    result = {
        "status": "UNVISITED_FIXED_ORDER_MECHANISM_SCREEN_COMPLETE",
        "selection_rule": "For each fixed variant index2..15, search legal GameSession histories for P-base/R-current transition only; no W/L, search targets, fitness or model values.",
        "screened_rule_indices": list(INDICES),
        "candidate_rule_sha256": {str(row["index"]): row["rule_sha256"] for row in rows},
        "task2433_inputs_sha256": sha(inputs_raw),
        "screen_script_sha256": sha(Path(__file__).read_bytes()),
        "records": rows,
        "limits": {"per_rule_node_cap": NODE_CAP_PER_RULE,
                   "depth_cap": DEPTH_CAP,
                   "per_rule_time_cap_seconds": TIME_CAP_PER_RULE,
                   "aggregate_time_cap_seconds": len(INDICES) * TIME_CAP_PER_RULE},
        "seconds": time.perf_counter() - began,
        "scope": "Mechanism reachability only. Positive witnesses are complete histories for their rule; negative CAP_REACHED results do not prove absence. No roots, training, outcomes or strength claims.",
    }
    with OUT.open("xb") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True,
                                ensure_ascii=False, allow_nan=False).encode() + b"\n")
    print(json.dumps({"status": result["status"],
                      "witnesses": sum(row["status"] == "WITNESS_FOUND" for row in rows),
                      "capped": sum(row["status"] == "CAP_REACHED" for row in rows),
                      "seconds": result["seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
