"""F158 bounded strength benchmark: rule-prior versus flat-value control."""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.benchmark.minimal_generator import MinimalGeneratedGame, generate_minimal_game
from generic_chess.core.identity import position_identity_key
from generic_chess.core.transition import initial_state
from generic_chess.session.result import SessionStatus
from generic_chess.session.session import GameSession


SEED_BY_RULESET = (15701, 15702)
BOARD_SIZE = 5
ORDINARY_COUNT = 4
CONFIG = EvaluationConfig()
MAX_DEPTH = 2


def _flat_profile(profile):
    values = {
        type_id: 0 if value == 0 else profile.median_non_anchor_value
        for type_id, value in profile.board_value_by_type.items()
    }
    hands = {
        type_id: int(round(value * CONFIG.hand_weight))
        for type_id, value in values.items()
    }
    return replace(
        profile,
        board_value_by_type=values,
        hand_value_by_base_type=hands,
        promotion_gain_by_type={type_id: 0 for type_id in values},
    )


def _player(compiled, profile):
    return AlphaBetaPlayer(
        compiled,
        evaluation_config=CONFIG,
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
        use_native_semantic_legality=False,
        evaluator_override=Evaluator(compiled, profile, CONFIG),
    )


def _opening(compiled, *, plies: int, seed: int):
    """Choose a deterministic evaluator-neutral opening from sorted actions."""
    rng = random.Random(seed)
    session = GameSession(compiled)
    opening = []
    for _ in range(plies):
        if session.result.status is not SessionStatus.ONGOING:
            return None
        actions = sorted(session.legal_actions(), key=str)
        if not actions:
            return None
        action = actions[rng.randrange(len(actions))]
        session.submit(action)
        opening.append(action)
    if session.result.status is not SessionStatus.ONGOING:
        return None
    return tuple(opening)


def _score_result(status: str, winner: int | None, rule_owner: int):
    if status == SessionStatus.CHECKMATE.value:
        return 1.0 if winner == rule_owner else 0.0
    if status in {
        SessionStatus.STALEMATE.value,
        SessionStatus.REPETITION.value,
        SessionStatus.MAX_PLY.value,
    }:
        return 0.5
    return None


def _play_game(game: MinimalGeneratedGame, rule_profile, flat_profile, *, rule_owner: int, opening, opening_id: str):
    session = GameSession(game.compiled)
    for action in opening:
        session.submit(action)
    players = {
        0: _player(game.compiled, rule_profile if rule_owner == 0 else flat_profile),
        1: _player(game.compiled, rule_profile if rule_owner == 1 else flat_profile),
    }
    search_limits = SearchLimits(
        max_depth=MAX_DEPTH,
        max_nodes=None,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
        deterministic=True,
    )
    failed = False
    while session.result.status is SessionStatus.ONGOING:
        side = session.state.position.side_to_move
        decision = players[side].choose_action(session, search_limits)
        if decision.action is None:
            failed = True
            break
        session.submit(decision.action)
    result = session.result
    status = "failed" if failed else result.status.value
    return {
        "ruleset_seed": game.seed,
        "opening_id": opening_id,
        "rule_prior_owner": rule_owner,
        "winner": None if failed else result.winner,
        "terminal_status": status,
        "plies": session.state.ply_count,
        "score": None if failed else _score_result(status, result.winner, rule_owner),
    }


def _pair(game, rule_profile, flat_profile, *, opening, opening_id):
    games = [
        _play_game(game, rule_profile, flat_profile, rule_owner=0, opening=opening, opening_id=opening_id),
        _play_game(game, rule_profile, flat_profile, rule_owner=1, opening=opening, opening_id=opening_id),
    ]
    scores = [row["score"] for row in games]
    pair_score = None if any(score is None for score in scores) else sum(scores) / len(scores)
    return {"opening_id": opening_id, "games": games, "pair_score": pair_score}


def run_benchmark():
    games = {}
    profiles = {}
    for seed in SEED_BY_RULESET:
        generated = generate_minimal_game(seed, board_size=BOARD_SIZE, ordinary_count=ORDINARY_COUNT)
        profile = build_ruleset_profile(generated.compiled, CONFIG)
        flat = _flat_profile(profile)
        initial = initial_state(generated.compiled)
        opening_id = f"initial:{position_identity_key(initial.position, generated.compiled)}"
        profiles[str(seed)] = {
            "ruleset_fingerprint": generated.ruleset_fingerprint,
            "rule_derived_values": dict(profile.board_value_by_type),
            "flat_control_values": dict(flat.board_value_by_type),
            "flat_median_non_anchor_value": profile.median_non_anchor_value,
        }
        games[str(seed)] = {
            "game": generated,
            "rule_profile": profile,
            "flat_profile": flat,
            "pairs": [_pair(generated, profile, flat, opening=(), opening_id=opening_id)],
        }

    initial_scores = {seed: games[seed]["pairs"][0]["pair_score"] for seed in games}
    if any(score is None or score < 0.5 for score in initial_scores.values()):
        classification = "RULE_PRIOR_FLAT_CONTROL_COUNTEREXAMPLE"
    else:
        neutral = [seed for seed, score in initial_scores.items() if score == 0.5]
        if neutral:
            for seed in neutral:
                generated = games[seed]["game"]
                opening_seed = 15800 + int(seed) - 15700
                opening = _opening(generated.compiled, plies=2, seed=opening_seed)
                if opening is None:
                    opening = ()
                    opening_id = "two_ply_opening_unavailable"
                else:
                    opening_id = f"two_ply:{position_identity_key(_opening_state(generated.compiled, opening).position, generated.compiled)}"
                games[seed]["pairs"].append(_pair(
                    games[seed]["game"], games[seed]["rule_profile"], games[seed]["flat_profile"],
                    opening=opening, opening_id=opening_id,
                ))
            final_scores = {
                seed: [pair["pair_score"] for pair in data["pairs"]]
                for seed, data in games.items()
            }
            if any(any(score is None or score < 0.5 for score in scores) for scores in final_scores.values()):
                classification = "RULE_PRIOR_FLAT_CONTROL_COUNTEREXAMPLE"
            elif all(any(score is not None and score > 0.5 for score in scores) for scores in final_scores.values()):
                classification = "RULE_PRIOR_BASELINE_STRENGTH_SIGNAL_PASS"
            elif any(any(score is not None and score > 0.5 for score in scores) for scores in final_scores.values()):
                classification = "RULE_PRIOR_BASELINE_STRENGTH_SIGNAL_PARTIAL"
            else:
                classification = "RULE_PRIOR_BASELINE_STRENGTH_SIGNAL_INCONCLUSIVE"
        else:
            classification = "RULE_PRIOR_BASELINE_STRENGTH_SIGNAL_PASS"

    output_games = {
        seed: {"pairs": data["pairs"]}
        for seed, data in games.items()
    }
    return {
        "classification": classification,
        "ruleset_seeds": list(SEED_BY_RULESET),
        "search": {"max_depth": MAX_DEPTH, "qsearch": "0/0", "max_nodes": None, "use_ordering": False, "use_tt": False},
        "profiles": profiles,
        "games": output_games,
        "game_count": sum(len(pair["games"]) for data in games.values() for pair in data["pairs"]),
        "pair_count": sum(len(data["pairs"]) for data in games.values()),
    }


def _opening_state(compiled, opening):
    session = GameSession(compiled)
    for action in opening:
        session.submit(action)
    return session.state


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    result = run_benchmark()
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    print(f"F158_CLASSIFICATION={result['classification']}")
    print(f"F158_GAMES={result['game_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
