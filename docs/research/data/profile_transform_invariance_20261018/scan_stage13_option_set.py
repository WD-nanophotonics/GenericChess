"""Was the played contact promotion the only legal action, or did the position offer alternatives?

Replay only: the six stored Stage-8 game files are walked with the unchanged
generator and engine.  Nothing is generated, nothing is searched and the
evaluator is not edited.  At every Stage-8/Stage-12 contact the option set of the
reconstructed position is recorded, so the endpoint can say whether the 17
played promotions were forced or chosen over a sibling move.

Endpoint, decision rule, cost and non-goals were written before the run in
plan_stage13_option_set.json.  No in-zone-versus-outside rate is computed.  A
played move is not a counterfactual and a forced move carries no preference
information at all.
"""

from __future__ import annotations

import ast
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _worktree_root(start: Path) -> Path:
    """Find the checkout root by marker so the script runs from either copy."""
    for candidate in (start, *start.parents):
        if (candidate / "generic_chess").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise SystemExit(f"cannot locate the worktree root above {start}")


ROOT = _worktree_root(HERE)
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

SESSION = "3d8dc073-5fcc-456e-933c-a7b6646296e5"
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

PLAYED_IS_PROMOTION = "played_move_is_the_promotion_from_the_paid_square"
PLAYED_OTHER_FROM_SQUARE = "played_move_is_another_move_from_the_paid_square"
PLAYED_ELSEWHERE = "played_move_is_from_a_different_square"
NO_PLAYED_MOVE = "no_played_move_after_this_position"


def parse_move(text: str):
    expression = ast.parse(text, mode="eval")
    return eval(compile(expression, "<stored-move>", "eval"), {"__builtins__": {}}, _NAMESPACE)


def sample_start(compiled, seed: int):
    """The start-position walker of the stored-game generator path, unchanged."""
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


def zone_squares(evaluator, piece):
    """The evaluator's paid zone for this piece, or None when no zone applies."""
    base = piece.base_type_id
    if piece.promoted or base not in evaluator._profile.promotion_gain_by_type:
        return None
    if evaluator._profile.promotion_gain_by_type[base] <= 0:
        return None
    return evaluator._zones.get((base, piece.owner))


def classify_played(played, idx: int, board_size: int) -> str:
    if played is None:
        return NO_PLAYED_MOVE
    if not isinstance(played, BoardMove):
        return PLAYED_ELSEWHERE
    if square_to_index(played.from_square, board_size) != idx:
        return PLAYED_ELSEWHERE
    if played.promotion_target_id is not None:
        return PLAYED_IS_PROMOTION
    return PLAYED_OTHER_FROM_SQUARE


def option_set(legal, idx: int, board_size: int) -> dict:
    """Count what the position offered from the paid square."""
    total = 0
    from_square = 0
    promotions = 0
    for action in legal:
        total += 1
        if not isinstance(action, BoardMove):
            continue
        if square_to_index(action.from_square, board_size) != idx:
            continue
        from_square += 1
        if action.promotion_target_id is not None:
            promotions += 1
    return dict(
        legal_actions_total=total,
        actions_from_paid_square=from_square,
        promotions_from_paid_square=promotions,
        promotion_is_only_legal_action=total == 1 and promotions == 1,
        promotion_is_only_action_from_square=from_square == promotions and promotions >= 1,
        has_unpromoted_sibling=from_square - promotions >= 1,
    )


def main() -> int:
    started = time.time()
    seen: set[tuple] = set()
    totals: Counter = Counter()
    per_seed: dict[int, Counter] = {}
    per_game: list[dict] = []
    events: list[dict] = []
    problems: list[str] = []
    replay_mismatches = 0

    for name in FILES:
        payload = json.loads((GAMES_DIR / name).read_text(encoding="utf-8"))
        depth = payload["design"]["search"]["max_depth"]
        for game in payload["games"]:
            key = (game["seed"], depth, game["game_index"], tuple(game["moves"]))
            if key in seen:
                totals["games_deduplicated"] += 1
                continue
            seen.add(key)
            seed = game["seed"]
            compiled = generate_game(
                GeneratorConfig(seed=seed, board_size=4, setup_preset="classic_like")
            ).compiled_ruleset
            board_size = compiled.board_size
            config = EvaluationConfig()
            evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
            state = sample_start(compiled, seed)
            if state is None:
                problems.append(f"no start position at seed {seed}")
                continue
            start_ply = state.ply_count
            actions_played = [parse_move(text) for text in game["moves"]]
            counts: Counter = Counter()
            ply = 0

            def scan(state, played, ply: int) -> None:
                legal = legal_actions(state, compiled)
                legal_set = set(legal)
                if played is not None and played not in legal_set:
                    problems.append(
                        f"seed {seed} depth {depth} game {game['game_index']} ply {ply}: "
                        f"played action is not legal in the reconstructed position"
                    )
                promo_squares = {
                    square_to_index(action.from_square, board_size)
                    for action in legal
                    if isinstance(action, BoardMove) and action.promotion_target_id is not None
                }
                side_to_move = state.position.side_to_move
                for idx, piece in enumerate(state.position.board):
                    if piece is None or piece.owner != side_to_move or idx not in promo_squares:
                        continue
                    zone = zone_squares(evaluator, piece)
                    if zone is None or idx not in zone:
                        continue
                    klass = classify_played(played, idx, board_size)
                    options = option_set(legal, idx, board_size)
                    counts["in_zone_contact"] += 1
                    counts[klass] += 1
                    if klass == PLAYED_IS_PROMOTION and options["promotion_is_only_legal_action"]:
                        counts["played_promotion_was_forced"] += 1
                    if klass == PLAYED_IS_PROMOTION and options["has_unpromoted_sibling"]:
                        counts["played_promotion_had_an_unpromoted_sibling"] += 1
                    per_seed.setdefault(seed, Counter())[klass] += 1
                    events.append(
                        dict(
                            seed=seed,
                            depth=depth,
                            game_index=game["game_index"],
                            ply=ply,
                            square=idx,
                            played_class=klass,
                            **options,
                        )
                    )

            scan(state, actions_played[0] if actions_played else None, ply)
            replay_error = None
            for action in actions_played:
                try:
                    state = apply_action(state, action, compiled)
                except Exception as error:  # noqa: BLE001 - recorded, not swallowed
                    replay_error = f"{type(error).__name__}: {error}"
                    break
                ply += 1
                scan(state, actions_played[ply] if ply < len(actions_played) else None, ply)

            status = state.terminal_status
            replayed = {
                "status": status.status.value if status.is_terminal else "watchdog",
                "winner": status.winner if status.is_terminal else None,
                "plies": state.ply_count - start_ply,
            }
            stored = {"status": game["status"], "winner": game["winner"], "plies": game["plies"]}
            if replay_error is not None or replayed != stored:
                replay_mismatches += 1
                problems.append(
                    f"seed {seed} depth {depth} game {game['game_index']}: "
                    f"replay {replayed} != stored {stored} ({replay_error})"
                )
                continue

            totals.update(counts)
            totals["games_scanned"] += 1
            per_game.append(
                dict(
                    seed=seed,
                    depth=depth,
                    game_index=game["game_index"],
                    in_zone_contact=counts["in_zone_contact"],
                    played_promotion=counts[PLAYED_IS_PROMOTION],
                    forced_promotion=counts["played_promotion_was_forced"],
                )
            )

    contacts = totals["in_zone_contact"]
    promotion_played = totals[PLAYED_IS_PROMOTION]
    forced = totals["played_promotion_was_forced"]
    if promotion_played == 0:
        decision = "no_played_promotions_to_classify"
    elif forced == promotion_played:
        decision = "every_played_contact_promotion_was_forced"
    elif forced == 0:
        decision = "no_played_contact_promotion_was_forced"
    else:
        decision = "played_contact_promotions_are_a_mixture_of_forced_and_optional"

    payload = dict(
        role="DEEPSEEK_AUX",
        session=SESSION,
        question=(
            "At the 17 in-zone contacts where the promotion from the paid square was played, "
            "was it the only legal action, or did the position offer alternatives?"
        ),
        plan="plan_stage13_option_set.json",
        design=dict(
            board_size=4,
            setup_preset="classic_like",
            no_new_search=True,
            no_new_games=True,
            replay_precondition="terminal status, winner and ply count must equal the stored values",
            deduplicate_by="(seed, depth, game_index, moves)",
            contact_definition="unchanged: in-zone paid square that is the from_square of a legal BoardMove with promotion_target_id not None",
            option_set_source="legal_actions of the position rebuilt from the stored move list",
        ),
        summary=dict(
            decision=decision,
            in_zone_contact=contacts,
            played_move_is_the_promotion_from_the_paid_square=promotion_played,
            played_move_is_another_move_from_the_paid_square=totals[PLAYED_OTHER_FROM_SQUARE],
            played_move_is_from_a_different_square=totals[PLAYED_ELSEWHERE],
            no_played_move_after_this_position=totals[NO_PLAYED_MOVE],
            played_promotion_was_forced=forced,
            played_promotion_had_an_unpromoted_sibling=totals[
                "played_promotion_had_an_unpromoted_sibling"
            ],
            contacts_with_a_single_legal_action=sum(
                1 for event in events if event["legal_actions_total"] == 1
            ),
            games_scanned=totals["games_scanned"],
            games_deduplicated=totals["games_deduplicated"],
            replay_mismatches=replay_mismatches,
            wall_seconds=round(time.time() - started, 2),
        ),
        per_seed=[
            dict(seed=seed, **{key: counts[key] for key in sorted(counts)})
            for seed, counts in sorted(per_seed.items())
        ],
        per_game=per_game,
        events=events,
        problems=problems,
        nonclaims=[
            "a forced move carries no preference information; only the optional promotions say anything about search",
            "an optional promotion is a depth-2/3 search outcome under one evaluator, not a value or strength judgement",
            "the played move is not a counterfactual",
            "no in-zone-versus-outside rate; the withdrawn 0-vs-53 contrast is not reproduced",
            "no strength, playing-quality or utility claim",
        ],
    )
    out = HERE / "results_stage13_option_set.json"
    out.write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], indent=1))
    if problems:
        print("PROBLEMS:")
        for problem in problems[:10]:
            print(" -", problem)
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
