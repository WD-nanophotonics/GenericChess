from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import (
    BoardMove, DropMove, PassAction, SemanticBoardMove, SemanticDropMove,
)
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.transition import apply_action
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.session.session import GameSession
from audit import (
    board_hand_turn_mirror_matches, mirrored_initial_state, mirror_action,
    mirror_position,
)

HERE = Path(__file__).resolve().parent
BASELINE = json.loads((HERE / "result.json").read_text(encoding="utf-8"))
PLAN = HERE / "exposure-plan.json"
OUTPUT = HERE / "exposure.json"
SEEDS = tuple(row["seed"] for row in BASELINE["rule_seeds"])
COUNTERS = (
    "board_moves", "drops", "semantic_board_moves", "semantic_drops", "passes",
    "captures", "promotions", "states_with_promoted_piece",
    "states_with_occupied_hand", "states_with_nonempty_aux",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    totals = {key: 0 for key in COUNTERS}
    per_rule = []
    failures = []
    sampled_states = 0

    for seed in SEEDS:
        game = generate_game(GeneratorConfig(
            seed=seed, board_size=6, setup_preset="classic_like",
            movement_symmetry="bilateral", allow_hybrid=True,
        ))
        compiled = game.compiled_ruleset
        n = compiled.board_size
        frozen = next(row for row in BASELINE["rule_seeds"] if row["seed"] == seed)
        if compiled.ruleset_fingerprint != frozen["ruleset_fingerprint"]:
            failures.append({"seed": seed, "kind": "ruleset_fingerprint_mismatch"})
            continue

        left = GameSession(compiled)
        right_state = mirrored_initial_state(
            compiled, mirror_position(left.state.position, n)
        )
        rng = random.Random(seed ^ 0x5A17)
        counts = {key: 0 for key in COUNTERS}
        for ply in range(21):
            actions_left = tuple(left.legal_actions())
            actions_right = tuple(legal_actions_from_position(
                right_state.position, compiled
            ))
            if set(mirror_action(action, n) for action in actions_left) != set(actions_right):
                failures.append({"seed": seed, "ply": ply, "kind": "legal_action_set_mismatch"})
                break
            if not board_hand_turn_mirror_matches(
                left.state.position, right_state.position, n
            ):
                failures.append({"seed": seed, "ply": ply, "kind": "position_mirror_mismatch"})
                break

            position = left.state.position
            if any(piece is not None and piece.promoted for piece in position.board):
                counts["states_with_promoted_piece"] += 1
            if any(hand.total() for hand in position.hands):
                counts["states_with_occupied_hand"] += 1
            if position.aux_state:
                counts["states_with_nonempty_aux"] += 1
            sampled_states += 1
            if not actions_left:
                break

            ordered = sorted(actions_left, key=str)
            action = ordered[rng.randrange(len(ordered))]
            mirrored = mirror_action(action, n)
            if isinstance(action, BoardMove):
                counts["board_moves"] += 1
                target_index = action.to_square.rank * n + action.to_square.file
                if position.board[target_index] is not None:
                    counts["captures"] += 1
                if action.promotion_target_id is not None:
                    counts["promotions"] += 1
            elif isinstance(action, SemanticBoardMove):
                counts["semantic_board_moves"] += 1
                target_index = action.to_square.rank * n + action.to_square.file
                if position.board[target_index] is not None:
                    counts["captures"] += 1
                if action.promotion_target_id is not None:
                    counts["promotions"] += 1
            elif isinstance(action, (DropMove, SemanticDropMove)):
                key = "drops" if isinstance(action, DropMove) else "semantic_drops"
                counts[key] += 1
            elif isinstance(action, PassAction):
                counts["passes"] += 1
            left.submit(action)
            right_state = apply_action(right_state, mirrored, compiled)

        per_rule.append({"seed": seed, **counts})
        for key in COUNTERS:
            totals[key] += counts[key]

    result = {
        "status": "PASS_REPLAY_EXPOSURE" if not failures else "REPLAY_MISMATCH",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_plan_sha256": BASELINE["plan_sha256"],
        "baseline_result_sha256": sha256(HERE / "result.json"),
        "exposure_plan_sha256": sha256(PLAN),
        "source_head": BASELINE["source_head"],
        "rules_replayed": len(per_rule),
        "sampled_mirrored_state_pairs": sampled_states,
        "totals": totals,
        "per_rule": per_rule,
        "failures": failures,
        "scope_limit": "Replay-only feature-coverage audit of the registered histories; no new searches, games, outcomes or training.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"per_rule", "failures"}}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
