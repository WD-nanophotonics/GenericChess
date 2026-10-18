"""Do the promotion-leaf terms and the anchor penalty occur on stored game paths?

DEEPSEEK_AUX private probe, 2026-10-18, session
``6de032cc-45b4-4938-8700-2abdcae346aa``.  The published leaf-term audit
(``audit_leaf_terms.py``) established a *type* statement: the half-bonus
comparison cannot be true, the in-zone branch and the anchor penalty can.  It
said nothing about whether those terms occur on positions that were actually
played.  This script answers only that reachability question, from games that
are already stored: it replays the stored move lists and inspects the start
position and every position after each move.

No search, no new game, no fitness evaluation.  Endpoint pre-written in
``plan.json`` beside this file before the run.
"""

from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

import random  # noqa: E402

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.actions import BoardMove, DropMove  # noqa: E402
from generic_chess.core.attacks import anchor_square, pseudo_attacks  # noqa: E402
from generic_chess.core.coordinates import Square, index_to_square, square_to_index  # noqa: E402
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
    """Turn a stored ``repr(action)`` back into the action object."""
    expression = ast.parse(text, mode="eval")
    return eval(compile(expression, "<stored-move>", "eval"), {"__builtins__": {}}, _NAMESPACE)


def sample_start(compiled, seed: int):
    """Exactly the start-position walker of ``check_hand_term_match.py``."""
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


def term_scan(compiled, evaluator, state, counters: Counter) -> None:
    """Count promotion-leaf and anchor-term occurrences in one position."""
    position = state.position
    n = compiled.board_size
    for idx, piece in enumerate(position.board):
        if piece is None or piece.promoted:
            continue
        base = piece.base_type_id
        if base not in evaluator._profile.promotion_gain_by_type:
            continue
        gain = evaluator._profile.promotion_gain_by_type[base]
        if gain <= 0:
            continue
        zone = evaluator._zones.get((base, piece.owner))
        if zone is None:
            continue
        counters["promotable_observations"] += 1
        if idx in zone:
            counters["in_zone_live"] += 1
            continue
        forward = compiled.empty_forward_mobility[base][piece.owner][idx]
        if any(square_to_index(target, n) in zone for target in forward):
            counters["half_bonus_dead_branch_intent"] += 1
        else:
            counters["neither_branch"] += 1
    attacks = (pseudo_attacks(position, 0, compiled), pseudo_attacks(position, 1, compiled))
    if anchor_square(position, 0, compiled) in attacks[1]:
        counters["anchor_penalty_owner0"] += 1
    if anchor_square(position, 1, compiled) in attacks[0]:
        counters["anchor_penalty_owner1"] += 1


def main() -> int:
    seen: set[tuple] = set()
    counters: Counter = Counter()
    per_game: list[dict] = []
    problems: list[str] = []
    files_used: list[str] = []
    for name in FILES:
        payload = json.loads((GAMES_DIR / name).read_text(encoding="utf-8"))
        files_used.append(name)
        seed_range = payload["design"]["seeds"]
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
            start_state = sample_start(compiled, seed)
            if start_state is None:
                problems.append(f"no start position at seed {seed}")
                continue
            state = start_state
            local: Counter = Counter()
            position_count = 0
            term_scan(compiled, evaluator, state, local)
            position_count += 1
            replay_error = None
            for text in game["moves"]:
                action = parse_move(text)
                try:
                    state = apply_action(state, action, compiled)
                except Exception as error:  # noqa: BLE001 - recorded, not swallowed
                    replay_error = f"{type(error).__name__}: {error}"
                    break
                term_scan(compiled, evaluator, state, local)
                position_count += 1
            status = state.terminal_status
            replayed = {
                "status": status.status.value if status.is_terminal else "watchdog",
                "winner": status.winner if status.is_terminal else None,
                "plies": state.ply_count - start_state.ply_count,
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
            counters["positions_scanned"] += position_count
            per_game.append(
                dict(
                    seed=seed,
                    depth=depth,
                    game_index=game["game_index"],
                    outcome=game["outcome"],
                    positions=position_count,
                    in_zone_live=local["in_zone_live"],
                    half_bonus_dead_branch_intent=local["half_bonus_dead_branch_intent"],
                    anchor_penalty=local["anchor_penalty_owner0"] + local["anchor_penalty_owner1"],
                )
            )

    def games_with(field: str) -> int:
        return sum(1 for record in per_game if record[field] > 0)

    live = counters["in_zone_live"]
    dead = counters["half_bonus_dead_branch_intent"]
    if live and dead:
        decision = "leaf_terms_occur_on_stored_game_paths"
    else:
        decision = "leaf_terms_are_absent_on_stored_game_paths"
    summary = dict(
        decision=decision,
        files_used=files_used,
        games_scanned=counters["games_scanned"],
        games_deduplicated=counters["games_deduplicated"],
        games_failed_replay=counters["games_failed_replay"],
        positions_scanned=counters["positions_scanned"],
        promotable_observations=counters["promotable_observations"],
        in_zone_live=live,
        half_bonus_dead_branch_intent=dead,
        neither_branch=counters["neither_branch"],
        anchor_penalty_owner0=counters["anchor_penalty_owner0"],
        anchor_penalty_owner1=counters["anchor_penalty_owner1"],
        games_with_in_zone_live=games_with("in_zone_live"),
        games_with_dead_branch=games_with("half_bonus_dead_branch_intent"),
        games_with_anchor_penalty=games_with("anchor_penalty"),
        distinct_seeds=len({record["seed"] for record in per_game}),
        problems=problems,
    )
    payload = dict(
        role="DEEPSEEK_AUX",
        question=(
            "Do the promotion-leaf terms and the anchor-attack penalty occur on "
            "positions that were actually played in already-stored games?"
        ),
        design=dict(
            board_size=4,
            setup_preset="classic_like",
            replay_precondition="terminal status, winner and ply count must equal the stored values",
            deduplicate_by="(seed, depth, game_index, moves)",
            weights="EvaluationConfig defaults: promotion_potential_weight=3, anchor_escape_weight=5",
            no_new_search=True,
        ),
        summary=summary,
        per_game=per_game,
        nonclaims=[
            "utility/outcome/strength: a term occurring on a path does not imply it changed any chosen action or result",
            "the dead half-bonus branch is counted as intent only; as coded it contributes zero",
            "board 4 classic_like only; the published leaf audit measured boards 6 and 8",
            "not a sample of play: these are 2- and 3-ply games from one fixed start position per ruleset",
        ],
    )
    out = HERE / "results_stored_games_leaf_terms.json"
    out.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print("output_sha256", __import__("hashlib").sha256(out.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
