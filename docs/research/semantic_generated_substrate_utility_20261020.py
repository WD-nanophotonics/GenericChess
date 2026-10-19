"""Paired profile-only utility diagnostic for the pinned seed-21 substrate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

from rule_semantics_ir_fixtures import _own_anchor, _ref  # noqa: E402
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer  # noqa: E402
from generic_chess.ai.alphabeta.tuning import SearchTuning  # noqa: E402
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.semantic_executor import semantic_engine_for  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.execution import ExecutableSemanticRuleset  # noqa: E402
from generic_chess.rules.schema import (  # noqa: E402
    RuleActionEffect,
    RuleGeometrySpec,
    RuleSemanticAction,
)
from generic_chess.session.session import GameSession  # noqa: E402
from generic_chess.session.result import SessionStatus  # noqa: E402


BASE_FINGERPRINT = "a3807253490f8161c6a18418795a2e887a8edd0aadd5b1da827d88a42f15adc1"
PREFIX_SEED_RANGE = tuple(range(202610201, 202610233))
ROOT_COUNT = 8
GAME_LIMIT = 128
NODE_CAP = 4096


def build_case():
    from dataclasses import replace

    base = generate_game(GeneratorConfig(
        seed=21, board_size=4, setup_preset="bilateral_random", allow_hybrid=True
    ))
    if base.compiled_ruleset.ruleset_fingerprint != BASE_FINGERPRINT:
        raise RuntimeError("pinned generated substrate fingerprint changed")
    compound = RuleSemanticAction(
        name="move_and_shift_adjacent_friendly",
        type_ids=("P",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 1)),
        target_relation="empty",
        composition="augment",
        effects=(
            RuleActionEffect("move", from_ref=_ref("source"), to_ref=_ref("target")),
            RuleActionEffect(
                "shift",
                from_ref=_ref("offset_from_source", offset=(0, 1)),
                to_ref=_ref("offset_from_source", offset=(0, 2)),
                piece_owner="self",
            ),
        ),
        invariants=_own_anchor(),
    )
    augmented = replace(base.ruleset, semantic_actions=(compound,))
    compiled = ExecutableSemanticRuleset.from_compiled(
        compile_semantic_ruleset(augmented)
    )
    return base, augmented, compiled


def make_roots(compiled):
    roots = []
    attempted = []
    for seed in PREFIX_SEED_RANGE:
        rng = random.Random(seed)
        session = GameSession(compiled)
        path = []
        for _ in range(12):
            if session.result.status is not SessionStatus.ONGOING:
                break
            actions = sorted(session.legal_actions(), key=str)
            if not actions:
                break
            action = rng.choice(actions)
            path.append(action)
            session.submit(action)
        engine = semantic_engine_for(compiled)
        legal = session.legal_actions()
        semantic_available = sum(
            1 for action in legal
            if getattr(action, "pattern_id", "").startswith("sem_")
        )
        root = {
            "seed": seed,
            "prefix": [str(action) for action in path],
            "prefix_plies": len(path),
            "root_status": session.result.status.value,
            "root_side_to_move": session.state.position.side_to_move,
            "semantic_action_count": semantic_available,
            "root_legal_count": len(legal),
            "state": session.state,
            "engine": engine,
        }
        attempted.append({k: v for k, v in root.items() if k not in ("state", "engine")})
        if (session.result.status is SessionStatus.ONGOING
                and len(path) == 12 and session.state.position.side_to_move == 0):
            roots.append(root)
            if len(roots) == ROOT_COUNT:
                break
    return roots, attempted


def public_preflight():
    base, augmented, compiled = build_case()
    config = EvaluationConfig()
    candidate = build_ruleset_profile(compiled, config)
    # Same augmented rules and action space; only the static profile is rebuilt
    # from the preserved legacy atom view for the control.
    control = build_ruleset_profile(compiled._legacy_compiled, config)
    roots, attempted = make_roots(compiled)
    return {
        "base_fingerprint": base.compiled_ruleset.ruleset_fingerprint,
        "augmented_fingerprint": compiled.ruleset_fingerprint,
        "candidate_profile": {
            "board": dict(candidate.board_value_by_type),
            "hand": dict(candidate.hand_value_by_base_type),
            "promotion": dict(candidate.promotion_gain_by_type),
        },
        "legacy_profile_control": {
            "board": dict(control.board_value_by_type),
            "hand": dict(control.hand_value_by_base_type),
            "promotion": dict(control.promotion_gain_by_type),
        },
        "prefix_roots": [{k: v for k, v in root.items() if k not in ("state", "engine")}
                         for root in roots],
        "root_seed_range": [PREFIX_SEED_RANGE[0], PREFIX_SEED_RANGE[-1]],
        "target_root_count": ROOT_COUNT,
        "eligible_seed_attempts": attempted,
        "root_selection_rule": "first8nonterminal12-ply roots in ascending fixed seed range; terminal prefix seeds retained as preflight exclusions",
        "same_augmented_ruleset_for_both_arms": True,
    }, compiled, candidate, control, roots


def play_game(compiled, candidate_profile, control_profile, root_path, candidate_color):
    config = EvaluationConfig()
    evaluators = {
        "candidate": Evaluator(compiled, candidate_profile, config),
        "control": Evaluator(compiled, control_profile, config),
    }
    players = {}
    for color, label in ((candidate_color, "candidate"), (1 - candidate_color, "control")):
        players[color] = AlphaBetaPlayer(
            compiled,
            evaluator_override=evaluators[label],
            use_tt=False,
            use_ordering=False,
            use_native_semantic_legality=False,
            tuning=SearchTuning(use_root_tactical=False),
        )
    session = GameSession(compiled)
    for action in root_path:
        session.submit(action)
    events = []
    for _ in range(GAME_LIMIT):
        if session.result.status is not SessionStatus.ONGOING:
            break
        side = session.state.position.side_to_move
        decision = players[side].choose_action(
            session,
            SearchLimits(max_depth=3, max_nodes=NODE_CAP, quiescence_max_depth=0),
        )
        if decision.action is None:
            raise RuntimeError("ongoing public caller returned no action")
        events.append({
            "side": side,
            "policy": "candidate" if side == candidate_color else "control",
            "action": str(decision.action),
            "score": decision.score,
            "depth": decision.completed_depth,
            "nodes": decision.nodes + decision.qnodes,
            "stop": decision.termination_reason,
        })
        session.submit(decision.action)
    result = session.result
    if result.status is SessionStatus.ONGOING:
        reward = None
    elif result.winner is None:
        reward = 0
    else:
        reward = 1 if result.winner == candidate_color else -1
    return {
        "candidate_color": candidate_color,
        "status": result.status.value,
        "winner": result.winner,
        "candidate_reward": reward,
        "additional_plies": len(events),
        "total_nodes": sum(event["nodes"] for event in events),
        "semantic_actions_played": sum(
            "move_and_shift_adjacent_friendly" in event["action"] for event in events
        ),
        "events": events,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="execute the frozen 16-game panel")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    preflight, compiled, candidate, control, roots = public_preflight()
    if not args.run:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return
    if args.out is None:
        parser.error("--run requires --out")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frozen_path = args.out.with_name("preflight.json")
    if not frozen_path.exists():
        raise RuntimeError("frozen preflight.json must exist before the run")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if frozen != preflight:
        raise RuntimeError("preflight differs from the frozen plan; refuse execution")
    with args.out.open("w", encoding="utf-8") as output:
        for root_index, root in enumerate(roots):
            for candidate_color in (0, 1):
                game = play_game(
                    compiled, candidate, control, root["prefix"], candidate_color
                )
                row = {
                    "slot": len(roots[:root_index]) * 2 + candidate_color + 1,
                    "root_seed": root["seed"],
                    **game,
                }
                output.write(json.dumps(row, sort_keys=True) + "\n")
                output.flush()


if __name__ == "__main__":
    main()
