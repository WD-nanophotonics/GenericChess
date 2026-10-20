from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from dataclasses import replace

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import (
    BoardMove, DropMove, PassAction, SemanticBoardMove, SemanticDropMove,
)
from generic_chess.core.coordinates import rotate_square
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState, HistoryRecord
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.terminal import _terminal_from_parts
from generic_chess.core.transition import apply_action
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.session.session import GameSession

HERE = Path(__file__).resolve().parent
PLAN = HERE / "plan.json"
OUTPUT = HERE / "result.json"
SEEDS = (863201, 863202, 863203, 863204, 863205, 863206, 863207, 863208)
MAX_SECONDS = 1200
MAX_PLIES = 20


def mirror_action(action, n):
    if isinstance(action, BoardMove):
        return BoardMove(
            rotate_square(action.from_square, n),
            rotate_square(action.to_square, n),
            action.promotion_target_id,
        )
    if isinstance(action, DropMove):
        return DropMove(action.base_type_id, rotate_square(action.to_square, n))
    if isinstance(action, SemanticBoardMove):
        return SemanticBoardMove(
            action.pattern_id, action.geometry_id, action.actor_type_id,
            rotate_square(action.from_square, n),
            rotate_square(action.to_square, n), action.promotion_target_id,
        )
    if isinstance(action, SemanticDropMove):
        return SemanticDropMove(
            action.pattern_id, action.geometry_id, action.base_type_id,
            rotate_square(action.to_square, n),
        )
    if isinstance(action, PassAction):
        return action
    raise TypeError(f"unhandled action type: {type(action).__name__}")


def board_hand_turn_mirror_matches(a, b, n):
    mirrored = [None] * (n * n)
    for index, piece in enumerate(a.board):
        if piece is None:
            continue
        rank, file = divmod(index, n)
        target = (n - 1 - rank) * n + (n - 1 - file)
        mirrored[target] = Piece(
            1 - piece.owner, piece.base_type_id, piece.current_type_id,
            piece.promoted,
        )
    return (
        tuple(mirrored) == b.board
        and (a.hands[1], a.hands[0]) == b.hands
        and 1 - a.side_to_move == b.side_to_move
    )


def mirror_position(position, n):
    mirrored = [None] * (n * n)
    for index, piece in enumerate(position.board):
        if piece is None:
            continue
        rank, file = divmod(index, n)
        target = (n - 1 - rank) * n + (n - 1 - file)
        mirrored[target] = Piece(
            1 - piece.owner, piece.base_type_id, piece.current_type_id,
            piece.promoted,
        )
    return replace(
        position,
        board=tuple(mirrored),
        hands=(position.hands[1], position.hands[0]),
        side_to_move=1 - position.side_to_move,
    )


def mirrored_initial_state(compiled, position):
    key = repetition_identity_key(position, compiled)
    counts = ((key, 1),)
    terminal = _terminal_from_parts(position, 0, counts, compiled)
    return GameState(
        position=position,
        ply_count=0,
        repetition_counts=counts,
        terminal_status=terminal,
        history=(HistoryRecord(key, -1, "", False),),
    )


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main():
    start = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    plan_hash = sha256(PLAN)
    rules = []
    samples = []
    structural_failures = []
    score_mismatches = []
    timed_out = False
    config = EvaluationConfig()

    for seed in SEEDS:
        if time.perf_counter() - start >= MAX_SECONDS:
            timed_out = True
            break
        game = generate_game(GeneratorConfig(
            seed=seed,
            board_size=6,
            setup_preset="classic_like",
            movement_symmetry="bilateral",
            allow_hybrid=True,
        ))
        compiled = game.compiled_ruleset
        n = compiled.board_size
        left = GameSession(compiled)
        right_state = mirrored_initial_state(
            compiled, mirror_position(left.state.position, n)
        )
        evaluator = Evaluator(
            compiled, build_ruleset_profile(compiled, config), config
        )
        rule_row = {
            "seed": seed,
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
            "profile_type_count": len(compiled.types_by_id),
            "board_size": n,
        }
        rules.append(rule_row)

        if not board_hand_turn_mirror_matches(
            left.state.position, right_state.position, n
        ):
            structural_failures.append({
                "seed": seed,
                "at_ply": 0,
                "kind": "opening_position_not_mirrored",
            })
            continue

        rng = random.Random(seed ^ 0x5A17)
        for ply in range(MAX_PLIES + 1):
            if time.perf_counter() - start >= MAX_SECONDS:
                timed_out = True
                break
            actions_left = tuple(left.legal_actions())
            actions_right = tuple(
                legal_actions_from_position(right_state.position, compiled)
            )
            mirrored = tuple(mirror_action(a, n) for a in actions_left)
            if set(mirrored) != set(actions_right):
                structural_failures.append({
                    "seed": seed,
                    "at_ply": ply,
                    "kind": "legal_action_sets_not_mirrored",
                    "left_count": len(actions_left),
                    "right_count": len(actions_right),
                })
                break
            if not board_hand_turn_mirror_matches(
                left.state.position, right_state.position, n
            ):
                structural_failures.append({
                    "seed": seed,
                    "at_ply": ply,
                    "kind": "board_hand_turn_not_mirrored",
                })
                break

            score_left = evaluator.evaluate(left.state)
            score_right = evaluator.evaluate(right_state)
            row = {
                "seed": seed,
                "ply": ply,
                "left_side_to_move": left.state.position.side_to_move,
                "score_left": score_left,
                "score_mirrored": score_right,
                "equal": score_left == score_right,
                "left_aux": left.state.position.aux_state,
                "mirrored_aux": right_state.position.aux_state,
                "legal_action_count": len(actions_left),
            }
            samples.append(row)
            if score_left != score_right:
                score_mismatches.append(row)

            if not actions_left:
                break
            ordered = sorted(actions_left, key=str)
            action = ordered[rng.randrange(len(ordered))]
            right_action = mirror_action(action, n)
            if right_action not in actions_right:
                structural_failures.append({
                    "seed": seed,
                    "at_ply": ply,
                    "kind": "selected_mirror_not_legal",
                    "action": str(action),
                    "mirrored_action": str(right_action),
                })
                break
            left.submit(action)
            right_state = apply_action(right_state, right_action, compiled)
        if timed_out:
            break

    result = {
        "status": (
            "HARD_CAP_PARTIAL" if timed_out else
            "STRUCTURAL_MISMATCH" if structural_failures else
            "EVALUATOR_SYMMETRY_MISMATCH" if score_mismatches else
            "PASS_FINITE_SCREEN"
        ),
        "started_at_utc": started_at,
        "elapsed_seconds": time.perf_counter() - start,
        "source_head": "e009c4a531aebd21bf8d07cb2115b43786cc3d94",
        "plan_sha256": plan_hash,
        "rules_attempted": len(rules),
        "rule_seeds": rules,
        "sampled_state_pairs": len(samples),
        "unique_rules_with_samples": len({row["seed"] for row in samples}),
        "nonempty_aux_state_pairs": sum(
            bool(row["left_aux"] or row["mirrored_aux"]) for row in samples
        ),
        "structural_failure_count": len(structural_failures),
        "score_mismatch_count": len(score_mismatches),
        "structural_failures": structural_failures,
        "score_mismatches": score_mismatches,
        "sample_head": samples[:8],
        "sample_tail": samples[-8:],
        "scope_limit": (
            "Finite 6x6 generated profiles and at most 20 plies per legal path; "
            "no search symmetry, utility, strength or population claim."
        ),
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {
        "rule_seeds", "structural_failures", "score_mismatches",
        "sample_head", "sample_tail",
    }}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
