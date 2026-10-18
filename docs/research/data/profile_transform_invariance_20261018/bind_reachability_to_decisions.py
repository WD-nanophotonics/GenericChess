"""Does the in-zone promotion bonus pay pieces that can actually promote?

DEEPSEEK_AUX private probe, 2026-10-18, session
``6de032cc-45b4-4938-8700-2abdcae346aa``.  Stage 7
(``scan_stored_games_leaf_terms.py``) counted how often the evaluator's
in-zone branch fires on positions that were really played.  A count of fires
is not a statement about promotion: the zone is defined as "no empty forward
step from this square", so a piece standing in it may be unable to advance at
all.  This script asks the narrower and decision-changing question, using the
same stored games: when the full bonus is paid, does that piece have a legal
promotion in that same position, and do the games ever choose a promotion
from an in-zone or half-bonus-intent square?

Replay only.  No search, no new games, no fitness evaluation, no evaluator
edit.  Endpoint pre-written in ``plan_bind_reachability_to_decisions.json``
before this run.
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.actions import BoardMove, DropMove  # noqa: E402
from generic_chess.core.coordinates import Square, square_to_index  # noqa: E402
from generic_chess.core.movegen import legal_actions  # noqa: E402
from generic_chess.core.transition import apply_action, initial_state, legal_successors  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

GAMES_DIR = ROOT / ".local_agent" / "hand-utility-games-20261018"
FILES = [
    "results_hand_term_match_served-blind_d2_n20000_s59-70.json",
    "results_hand_term_match_served-blind_d2_n20000_s71-94.json",
    "results_hand_term_match_served-blind_d3_n20000_s59-70.json",
    "results_hand_term_match_served-blind_d3_n20000_s71-94.json",
    "results_hand_term_match_served-served_d2_n20000_s59-70.json",
    "results_hand_term_match_served-served_d2_n20000_s71-94.json",
]

START_PLY = 8
MIN_START_ACTIONS = 6
_NAMESPACE = {"Square": Square, "BoardMove": BoardMove, "DropMove": DropMove}


def parse_move(text: str):
    expression = ast.parse(text, mode="eval")
    return eval(compile(expression, "<stored-move>", "eval"), {"__builtins__": {}}, _NAMESPACE)


def sample_start(compiled, seed: int):
    """Exactly the start-position walker of the stored-game generator path."""
    for offset in range(4):
        rng = random.Random(seed * 1009 + offset)
        state = initial_state(compiled)
        while state.ply_count < 60:
            if state.terminal_status.is_terminal:
                break
            if state.ply_count >= START_PLY:
                children = legal_successors(state, compiled)
                if len(legal_actions(state, compiled)) >= MIN_START_ACTIONS:
                    if not any(child.terminal_status.is_terminal for _, child in children):
                        return state
            children = legal_successors(state, compiled)
            if not children:
                break
            _, state = rng.choice(children)
    return None


def zone_squares(evaluator, piece) -> frozenset[int] | None:
    base = piece.base_type_id
    if piece.promoted or base not in evaluator._profile.promotion_gain_by_type:
        return None
    if evaluator._profile.promotion_gain_by_type[base] <= 0:
        return None
    return evaluator._zones.get((base, piece.owner))


def position_probe(compiled, evaluator, state, counters: Counter) -> set[int]:
    """Count in-zone/dead/neither payments and return in-zone paid squares."""
    position = state.position
    n = compiled.board_size
    paid: set[int] = set()
    classed: list[tuple[int, str]] = []
    for idx, piece in enumerate(position.board):
        if piece is None:
            continue
        zone = zone_squares(evaluator, piece)
        if zone is None:
            continue
        counters["promotable_observations"] += 1
        if idx in zone:
            counters["in_zone_live"] += 1
            paid.add(idx)
            classed.append((idx, "in_zone"))
            continue
        forward = compiled.empty_forward_mobility[piece.base_type_id][piece.owner][idx]
        if any(square_to_index(target, n) in zone for target in forward):
            counters["half_bonus_dead_branch_intent"] += 1
            classed.append((idx, "dead_intent"))
        else:
            counters["neither_branch"] += 1
            classed.append((idx, "neither"))
    counters["_classed"] = classed  # consumed by the caller, never serialised
    return paid


def main() -> int:
    started = time.time()
    seen: set[tuple] = set()
    counters: Counter = Counter()
    per_game: list[dict] = []
    problems: list[str] = []
    paid_with_promotion_examples: list[dict] = []
    start_paid_by_seed: Counter = Counter()
    play_paid_by_seed: Counter = Counter()

    for name in FILES:
        payload = json.loads((GAMES_DIR / name).read_text(encoding="utf-8"))
        depth = payload["design"]["search"]["max_depth"]
        for game in payload["games"]:
            key = (game["seed"], depth, game["game_index"], tuple(game["moves"]))
            if key in seen:
                counters["games_deduplicated"] += 1
                continue
            seen.add(key)
            seed = game["seed"]
            compiled = generate_game(
                GeneratorConfig(seed=seed, board_size=4, setup_preset="classic_like")
            ).compiled_ruleset
            config = EvaluationConfig()
            evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
            state = sample_start(compiled, seed)
            if state is None:
                problems.append(f"no start position at seed {seed}")
                continue
            start_ply = state.ply_count

            local: Counter = Counter()
            positions = 0

            def scan(state, index: int) -> None:
                nonlocal positions
                actions = legal_actions(state, compiled)
                promotion_from: set[int] = set()
                for action in actions:
                    if isinstance(action, BoardMove) and action.promotion_target_id is not None:
                        promotion_from.add(square_to_index(action.from_square, compiled.board_size))
                paid = position_probe(compiled, evaluator, state, local)
                for idx, klass in local["_classed"]:
                    local[f"promotable_{klass}"] += 1
                    if idx in promotion_from:
                        local[f"promotable_{klass}_with_promotion"] += 1
                del local["_classed"]
                positions += 1
                local["positions"] += 1
                local["legal_actions"] += len(actions)
                local["legal_promotion_actions"] += sum(
                    1
                    for action in actions
                    if isinstance(action, BoardMove) and action.promotion_target_id is not None
                )
                if index == 0:
                    local["in_zone_at_start"] += len(paid)
                    if paid:
                        local["start_positions_with_in_zone"] += 1
                        start_paid_by_seed[seed] += len(paid)
                else:
                    local["in_zone_during_play"] += len(paid)
                    play_paid_by_seed[seed] += len(paid)
                contact = paid & promotion_from
                local["in_zone_with_legal_promotion"] += len(contact)
                if contact and len(paid_with_promotion_examples) < 8:
                    for idx in sorted(contact):
                        piece = state.position.board[idx]
                        paid_with_promotion_examples.append(
                            dict(
                                seed=seed,
                                depth=depth,
                                game_index=game["game_index"],
                                position_index=index,
                                square_index=idx,
                                base_type=piece.base_type_id,
                                owner=piece.owner,
                            )
                        )

            scan(state, 0)
            replay_error = None
            move_index = 0
            for text in game["moves"]:
                action = parse_move(text)
                before_board = state.position.board
                try:
                    state = apply_action(state, action, compiled)
                except Exception as error:  # noqa: BLE001 - recorded, not swallowed
                    replay_error = f"{type(error).__name__}: {error}"
                    break
                move_index += 1
                if isinstance(action, BoardMove):
                    idx = square_to_index(action.from_square, compiled.board_size)
                    piece = before_board[idx]
                    zone = zone_squares(evaluator, piece) if piece is not None else None
                    class_square = "neither"
                    if zone is not None:
                        if idx in zone:
                            class_square = "in_zone"
                        else:
                            forward = compiled.empty_forward_mobility[
                                piece.base_type_id
                            ][piece.owner][idx]
                            if any(
                                square_to_index(target, compiled.board_size) in zone
                                for target in forward
                            ):
                                class_square = "dead_intent"
                    local[f"moves_from_{class_square}"] += 1
                    if action.promotion_target_id is not None:
                        local["promotions_chosen"] += 1
                        local[f"promotions_from_{class_square}"] += 1
                else:
                    local["drops_chosen"] += 1
                scan(state, move_index)

            status = state.terminal_status
            replayed = {
                "status": status.status.value if status.is_terminal else "watchdog",
                "winner": status.winner if status.is_terminal else None,
                "plies": state.ply_count - start_ply,
            }
            stored = {
                "status": game["status"],
                "winner": game["winner"],
                "plies": game["plies"],
            }
            if replay_error is not None or replayed != stored:
                problems.append(
                    f"seed {seed} depth {depth} game {game['game_index']}: "
                    f"replay {replayed} != stored {stored} ({replay_error})"
                )
                counters["games_failed_replay"] += 1
                continue

            counters.update(local)
            counters["games_scanned"] += 1
            per_game.append(
                dict(
                    seed=seed,
                    depth=depth,
                    game_index=game["game_index"],
                    outcome=game["outcome"],
                    positions=local["positions"],
                    in_zone_at_start=local["in_zone_at_start"],
                    in_zone_during_play=local["in_zone_during_play"],
                    in_zone_with_legal_promotion=local["in_zone_with_legal_promotion"],
                    promotions_chosen=local["promotions_chosen"],
                    promotions_from_in_zone=local["promotions_from_in_zone"],
                    promotions_from_dead_intent=local["promotions_from_dead_intent"],
                    # Per-arm denominators per game, added after the first run.
                    # The summary above is unchanged by these fields; they let a
                    # reader decompose both arms by seed instead of trusting the
                    # pooled 2.13% against 13.98% contrast.
                    promotable_in_zone=local["promotable_in_zone"],
                    promotable_in_zone_with_promotion=local[
                        "promotable_in_zone_with_promotion"
                    ],
                    promotable_dead_intent=local["promotable_dead_intent"],
                    promotable_dead_intent_with_promotion=local[
                        "promotable_dead_intent_with_promotion"
                    ],
                    promotable_neither=local["promotable_neither"],
                    promotable_neither_with_promotion=local[
                        "promotable_neither_with_promotion"
                    ],
                )
            )

    elapsed = time.time() - started
    live = counters["in_zone_live"]
    contact = counters["in_zone_with_legal_promotion"]
    if live and contact == 0:
        primary = "in_zone_full_bonus_has_no_immediate_promotion_contact"
    else:
        primary = "in_zone_full_bonus_has_immediate_promotion_contact"
    promotions = counters["promotions_chosen"]
    in_zone_obs = counters["promotable_in_zone"]
    other_obs = counters["promotable_dead_intent"] + counters["promotable_neither"]
    in_zone_hit = counters["promotable_in_zone_with_promotion"]
    other_hit = (
        counters["promotable_dead_intent_with_promotion"]
        + counters["promotable_neither_with_promotion"]
    )
    in_zone_rate = in_zone_hit / in_zone_obs if in_zone_obs else 0.0
    other_rate = other_hit / other_obs if other_obs else 0.0
    if in_zone_obs and other_obs and other_rate and in_zone_rate * 2 <= other_rate:
        contrast = "in_zone_promotability_is_depressed_relative_to_other_promotable_pieces"
    else:
        contrast = "in_zone_promotability_matches_other_promotable_pieces"
    summary = dict(
        primary_decision=primary,
        secondary_decision=f"promotions_chosen_from_in_zone={counters['promotions_from_in_zone']} of {promotions}",
        promotability_contrast=contrast,
        promotable_in_zone_observations=in_zone_obs,
        promotable_in_zone_with_legal_promotion=in_zone_hit,
        in_zone_legal_promotion_rate=round(in_zone_rate, 5),
        promotable_not_in_zone_observations=other_obs,
        promotable_not_in_zone_with_legal_promotion=other_hit,
        not_in_zone_legal_promotion_rate=round(other_rate, 5),
        rate_ratio_not_in_zone_over_in_zone=(
            round(other_rate / in_zone_rate, 2) if in_zone_rate else None
        ),
        promotable_dead_intent_with_legal_promotion=counters["promotable_dead_intent_with_promotion"],
        promotable_neither_with_legal_promotion=counters["promotable_neither_with_promotion"],
        games_scanned=counters["games_scanned"],
        games_deduplicated=counters["games_deduplicated"],
        games_failed_replay=counters["games_failed_replay"],
        positions_scanned=counters["positions"],
        legal_actions_enumerated=counters["legal_actions"],
        legal_promotion_actions=counters["legal_promotion_actions"],
        promotable_observations=counters["promotable_observations"],
        in_zone_live=live,
        in_zone_at_start=counters["in_zone_at_start"],
        in_zone_during_play=counters["in_zone_during_play"],
        half_bonus_dead_branch_intent=counters["half_bonus_dead_branch_intent"],
        neither_branch=counters["neither_branch"],
        in_zone_with_legal_promotion=contact,
        in_zone_without_legal_promotion=live - contact,
        start_positions_with_in_zone=counters["start_positions_with_in_zone"],
        distinct_seeds_with_start_in_zone=len(start_paid_by_seed),
        distinct_seeds_with_play_in_zone=len(play_paid_by_seed),
        moves_classified=(
            counters["moves_from_in_zone"]
            + counters["moves_from_dead_intent"]
            + counters["moves_from_neither"]
        ),
        moves_from_in_zone=counters["moves_from_in_zone"],
        moves_from_dead_intent=counters["moves_from_dead_intent"],
        moves_from_neither=counters["moves_from_neither"],
        drops_chosen=counters["drops_chosen"],
        promotions_chosen=promotions,
        promotions_from_in_zone=counters["promotions_from_in_zone"],
        promotions_from_dead_intent=counters["promotions_from_dead_intent"],
        promotions_from_neither=counters["promotions_from_neither"],
        wall_seconds=round(elapsed, 2),
        problems=problems,
    )
    payload = dict(
        role="DEEPSEEK_AUX",
        session="6de032cc-45b4-4938-8700-2abdcae346aa",
        question=(
            "Does the live in-zone promotion bonus ever pay a piece that can promote in that "
            "position, and do stored games choose promotions from in-zone squares?"
        ),
        plan="plan_bind_reachability_to_decisions.json",
        design=dict(
            board_size=4,
            setup_preset="classic_like",
            no_new_search=True,
            replay_precondition="terminal status, winner and ply count must equal the stored values",
            deduplicate_by="(seed, depth, game_index, moves)",
            zone_definition="squares where compiled.empty_forward_mobility leaves no empty forward destination",
            promotion_identification="legal BoardMove with promotion_target_id not None",
        ),
        summary=summary,
        in_zone_promotion_contact_examples=paid_with_promotion_examples,
        per_game=per_game,
        nonclaims=[
            "utility/outcome/strength: no claim that any term changed a chosen action or a result",
            "board 4 classic_like, 2-3 ply stored games: zero contact here does not bound deeper play or boards 6 and 8",
            "a legal promotion being available does not mean search would choose it",
            "the zone is 'no empty forward step', not a promotion rank; this script does not redefine it",
        ],
    )
    out = HERE / "results_bind_reachability_to_decisions.json"
    out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print("output_sha256", hashlib.sha256(out.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
