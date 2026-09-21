"""F159 causal diagnostic: compare F158 root policies before more games."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus

from scripts.f158_rule_prior_vs_flat_control_microarena import (
    BOARD_SIZE,
    CONFIG,
    MAX_DEPTH,
    ORDINARY_COUNT,
    SEED_BY_RULESET,
    _flat_profile,
    _opening,
    _player,
)
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.benchmark.minimal_generator import generate_minimal_game
from generic_chess.core.movegen import legal_actions
from generic_chess.core.identity import position_identity_key


def _root(compiled, opening):
    session = GameSession(compiled)
    for action in opening:
        session.submit(action)
    return session


def _search(player, session):
    return player.choose_action(
        session,
        SearchLimits(
            max_depth=MAX_DEPTH,
            max_nodes=None,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
            deterministic=True,
        ),
    )


def run_probe():
    rows = []
    root_specs = (
        (15701, "initial", 0),
        (15701, "two_ply", 15801),
        (15702, "initial", 0),
        (15702, "two_ply", 15802),
    )
    for seed, opening_kind, opening_seed in root_specs:
        game = generate_minimal_game(seed, board_size=BOARD_SIZE, ordinary_count=ORDINARY_COUNT)
        profile = build_ruleset_profile(game.compiled, CONFIG)
        flat = _flat_profile(profile)
        opening = () if opening_kind == "initial" else _opening(game.compiled, plies=2, seed=opening_seed)
        if opening is None:
            return {
                "classification": "F159_F158_ROOT_REPRODUCTION_FAILURE",
                "rows": rows,
                "search_count": len(rows) * 2,
            }
        session = _root(game.compiled, opening)
        if session.result.status is not SessionStatus.ONGOING:
            return {
                "classification": "F159_F158_ROOT_REPRODUCTION_FAILURE",
                "rows": rows,
                "search_count": len(rows) * 2,
            }
        opening_id = f"{opening_kind}:{position_identity_key(session.state.position, game.compiled)}"
        rule_decision = _search(_player(game.compiled, profile), session)
        flat_decision = _search(_player(game.compiled, flat), session)
        rule_action = action_to_dict(rule_decision.action) if rule_decision.action else None
        flat_action = action_to_dict(flat_decision.action) if flat_decision.action else None
        row = {
            "seed": seed,
            "opening_id": opening_id,
            "opening_plies": len(opening),
            "legal_action_count": len(session.legal_actions()),
            "rule_prior": {
                "action": rule_action,
                "score": rule_decision.score,
                "completed_depth": rule_decision.completed_depth,
            },
            "flat_control": {
                "action": flat_action,
                "score": flat_decision.score,
                "completed_depth": flat_decision.completed_depth,
            },
            "actions_equal": rule_action == flat_action,
        }
        if not row["actions_equal"]:
            evaluator_rule = Evaluator(game.compiled, profile, CONFIG)
            evaluator_flat = Evaluator(game.compiled, flat, CONFIG)
            child_scores = {}
            for label, action in (("rule_prior_selected", rule_decision.action), ("flat_selected", flat_decision.action)):
                if action is None:
                    continue
                child = apply_action(session.state, action, game.compiled)
                child_scores[label] = {
                    "rule_prior": evaluator_rule.evaluate(child),
                    "flat_control": evaluator_flat.evaluate(child),
                }
            row["divergent_child_scores"] = child_scores
        rows.append(row)

    classification = (
        "F158_STRENGTH_SURFACE_HAS_NO_EARLY_POLICY_LEVERAGE"
        if all(row["actions_equal"] for row in rows)
        else "F158_POLICY_DIVERGENCE_EXISTS_BUT_STALEMATE_ERASES_OUTCOME_SIGNAL"
    )
    return {
        "classification": classification,
        "rulesets": list(SEED_BY_RULESET),
        "settings": {"depth": MAX_DEPTH, "qsearch": "0/0", "ordering": False, "tt": False, "disk_cache": False},
        "rows": rows,
        "search_count": len(rows) * 2,
        "game_count": 0,
        "heavy": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    result = run_probe()
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    print(f"F159_CLASSIFICATION={result['classification']}")
    print(f"F159_SEARCHES={result['search_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
