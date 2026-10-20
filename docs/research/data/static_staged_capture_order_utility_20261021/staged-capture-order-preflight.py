from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from generic_chess.ai.alphabeta.ordering import MoveOrderer, StagedMovePicker
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict, action_promotion_target_id
from generic_chess.core.coordinates import square_to_index
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

OUT = ROOT / "docs/research/data/static_staged_capture_order_utility_20261021"
SEEDS = tuple(range(622091, 622099))
PLIES = (3, 4)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(record_value(value)).encode()).hexdigest()


class ProbeEvaluator:
    """Same Unit leaf/type values; candidate may change only capture ordering."""

    def __init__(self, compiled, profile, kind):
        self.compiled = compiled
        self.delegate = Evaluator(compiled, profile, EvaluationConfig())
        self.kind = kind
        self.capture_calls = []
        self.type_calls = []

    def evaluate(self, state):
        score = 0
        for piece in state.position.board:
            if piece is not None and not self.compiled.types_by_id[piece.current_type_id].is_anchor:
                score += 100 if piece.owner == 0 else -100
        for owner, hand in enumerate(state.position.hands):
            sign = 100 if owner == 0 else -100
            for tid, count in hand.counts:
                if not self.compiled.types_by_id[tid].is_anchor:
                    score += sign * count
        return score if state.position.side_to_move == 0 else -score

    def capture_order_value(self, moving, captured):
        if self.kind == "static":
            value = self.delegate.capture_order_value(moving, captured)
        else:
            moving_value = 0 if self.compiled.types_by_id[moving.current_type_id].is_anchor else 100
            captured_value = 0 if self.compiled.types_by_id[captured.current_type_id].is_anchor else 100
            value = captured_value * 10 - moving_value // 10
        self.capture_calls.append((moving.current_type_id, captured.current_type_id, value))
        return value

    def type_value(self, type_id):
        self.type_calls.append(type_id)
        return 0 if self.compiled.types_by_id[type_id].is_anchor else 100


def make_root(compiled, seed, family, plies):
    game = GameSession(compiled)
    rng = random.Random(seed * 1_000_000 + family)
    actions = []
    for _ in range(plies):
        if game.result.status.value != "ongoing":
            break
        legal = sorted(game.legal_actions(), key=lambda a: canonical(action_to_dict(a)))
        if not legal:
            break
        action = legal[rng.randrange(len(legal))]
        actions.append(action)
        game.submit(action)
    return game, actions


def main():
    source_head = "e009c4a531aebd21bf8d07cb2115b43786cc3d94"
    rules, roots, exposures = [], [], []
    for index, seed in enumerate(SEEDS):
        setup = ("classic_like", "bilateral_random", "free_random")[index % 3]
        symmetry = ("bilateral", "none")[index % 2]
        generated = generate_game(GeneratorConfig(
            seed=seed, board_size=5, setup_preset=setup,
            movement_symmetry=symmetry, allow_hybrid=True,
            require_promotable_type=True, require_nonpromotable_type=True,
            max_generation_attempts=16, require_no_opening_win_in_one=False,
        ))
        compiled = compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        rules.append({"seed": seed, "setup": setup, "symmetry": symmetry,
                      "fingerprint": compiled.ruleset_fingerprint,
                      "ruleset": ruleset_to_dict(generated.ruleset),
                      "profile_board": dict(profile.board_value_by_type)})
        for family, plies in enumerate(PLIES):
            game, opening = make_root(compiled, seed, family, plies)
            root = {"seed": seed, "family": family, "plies": plies,
                    "opening": [action_to_dict(a) for a in opening],
                    "state_digest": digest(game.state),
                    "legal_actions": len(game.legal_actions()),
                    "side_to_move": game.state.position.side_to_move}
            roots.append(root)
            if game.result.status.value != "ongoing":
                exposures.append({"root": root, "status": game.result.status.value,
                                  "terminal_before_search": True})
                continue
            actions = game.legal_actions()
            unit = ProbeEvaluator(compiled, profile, "unit")
            static = ProbeEvaluator(compiled, profile, "static")
            tuning = SearchTuning(use_staged_move_picker=True)
            orderer = MoveOrderer()
            unit_stats = SearchStatistics()
            unit_order = list(StagedMovePicker(game.state, list(actions), unit, 3, None, None, orderer, tuning, unit_stats))
            static_stats = SearchStatistics()
            static_order = list(StagedMovePicker(game.state, list(actions), static, 3, None, None, orderer, tuning, static_stats))
            unit_ids = [canonical(action_to_dict(a)) for a in unit_order]
            static_ids = [canonical(action_to_dict(a)) for a in static_order]
            cap_count = len(unit.capture_calls)
            search_call_counts = {}
            for kind in ("unit", "static"):
                probe = ProbeEvaluator(compiled, profile, kind)
                player = AlphaBetaPlayer(compiled, evaluator_override=probe,
                                         use_tt=False, use_ordering=True,
                                         tuning=tuning)
                decision = player.choose_action(game, SearchLimits(
                    max_depth=3, max_nodes=8192, max_time_seconds=None,
                    quiescence_max_depth=0, quiescence_hard_max_depth=8))
                search_call_counts[kind] = {
                    "calls": len(probe.capture_calls),
                    "trace": probe.capture_calls,
                    "type_calls": len(probe.type_calls),
                    "nodes": decision.nodes,
                    "qnodes": decision.qnodes,
                    "choice": None if decision.action is None else action_to_dict(decision.action),
                    "depth": decision.completed_depth,
                }
            exposures.append({
                "root": root, "terminal_before_search": False,
                "root_order_capture_calls": cap_count,
                "root_order_changed": unit_ids != static_ids,
                "root_order_unit": unit_ids,
                "root_order_static": static_ids,
                "unit_capture_trace": unit.capture_calls,
                "static_capture_trace": static.capture_calls,
                "search": search_call_counts,
            })
    output = {
        "schema": "primary-static-staged-capture-order-preflight-v1",
        "session_id": "d427542d-8462-4080-ab3d-28923b2f3472",
        "source_head": source_head,
        "seed_range": list(SEEDS), "rules": rules, "roots": roots,
        "exposures": exposures, "outcomes_collected": 0,
    }
    path = OUT / "staged-capture-order-preflight.json"
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "rules": len(rules), "roots": len(roots),
        "nonterminal": sum(not e.get("terminal_before_search") for e in exposures),
        "root_capture_calls": sum(e.get("root_order_capture_calls", 0) for e in exposures),
        "root_orders_changed": sum(bool(e.get("root_order_changed")) for e in exposures),
        "search_calls": {k: sum(e.get("search", {}).get(k, {}).get("calls", 0) for e in exposures)
                         for k in ("unit", "static")},
        "choice_differences": sum(
            e.get("search", {}).get("unit", {}).get("choice")
            != e.get("search", {}).get("static", {}).get("choice")
            for e in exposures),
        "outcomes_collected": 0,
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
