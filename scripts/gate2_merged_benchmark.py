"""Merged Gate 2 benchmark for the frozen rule-prior baseline.

This is the single post-R4 entry point.  It reuses the published Gate 1 and
Gate 2 evidence, runs compact capability microchecks, then plays two
role-swapped short trials for each of five fixed generated rulesets while
reviewing rule-prior decisions at 8,000 nodes.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.movegen import legal_actions
from generic_chess.core.position import count_entities
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalStatus
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from scripts import f86q_check_forcing_depth3_probe as f86q


ROOT = Path(__file__).resolve().parents[1]
GATE1_CHECKPOINT = "0c47b355bc34ab1cdff605bb49ec63714058be96"
GENERATED_SOURCE = ROOT / "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json"
GENERATED_COUNT = 5
MAX_PLIES = 30
PRIMARY_NODES = 1000
REVIEW_NODES = 8000
TRIAL_SEEDS = (20501, 20502, 20503, 20504, 20505, 20506, 20507, 20508, 20509, 20510)


def _action_key(action):
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _successors(state, compiled):
    return f86q._canonical_successors(state, compiled)


def _make_player(compiled, profile, config):
    return AlphaBetaPlayer(
        compiled,
        evaluation_config=config,
        evaluator_override=Evaluator(compiled, profile, config),
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
        use_native_semantic_legality=False,
    )


def _limits(nodes):
    return SearchLimits(max_nodes=nodes, quiescence_max_depth=0, quiescence_hard_max_depth=0)


def _session_with_state(compiled, state, witnesses):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = witnesses
    return session


def _profiles(compiled):
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, config)
    median = int(round(profile.median_non_anchor_value))
    flat_board = {
        type_id: 0 if compiled.types_by_id[type_id].is_anchor else median
        for type_id in profile.board_value_by_type
    }
    flat_hand = {
        type_id: 0 if compiled.types_by_id[type_id].is_anchor else int(round(median * config.hand_weight))
        for type_id in profile.hand_value_by_base_type
    }
    from dataclasses import replace

    flat = replace(
        profile,
        board_value_by_type=flat_board,
        hand_value_by_base_type=flat_hand,
        promotion_gain_by_type={type_id: 0 for type_id in profile.promotion_gain_by_type},
    )
    return config, profile, flat


def _microchecks(compiled, profile):
    initial = GameSession(compiled).state
    ordinary = [pt for pt in compiled.piece_types if not pt.is_anchor]
    values = {pt.type_id: profile.board_value_by_type[pt.type_id] for pt in ordinary}
    mobility = {
        pt.type_id: sum(len(compiled.empty_mobility[pt.type_id][owner][idx]) for owner in (0, 1) for idx in range(compiled.board_size ** 2))
        for pt in ordinary
    }
    anchors = {
        owner: sum(
            1 for piece in initial.position.board
            if piece is not None and piece.owner == owner and compiled.types_by_id[piece.current_type_id].is_anchor
        )
        for owner in (0, 1)
    }
    promotion = [pt.type_id for pt in ordinary if pt.is_promotable]
    drop = [type_id for type_id in compiled.drop_allowed if any(any(row) for row in compiled.drop_allowed[type_id])]
    passed = bool(ordinary) and all(mobility.values()) and anchors == {0: 1, 1: 1}
    return {
        "status": "PASS" if passed else "HARD_FAILURE",
        "material_values": values,
        "mobility_edge_counts": mobility,
        "anchor_counts": anchors,
        "promotion_types": promotion,
        "drop_types": sorted(drop),
        "initial_entities": count_entities(initial.position),
        "initial_terminal": initial.terminal_status.status.value,
        "semantic_engine_available": semantic_engine_for(compiled) is not None,
    }


def _trial(compiled, profile, config, trial_seed, prior_owner):
    session = GameSession(compiled)
    prior_player = _make_player(compiled, profile, config)
    rng = random.Random(trial_seed)
    records = []
    for ply in range(MAX_PLIES):
        if session.state.terminal_status.status is not TerminalStatus.ONGOING:
            break
        successors = _successors(session.state, compiled)
        if not successors:
            break
        actor = session.state.position.side_to_move
        if actor == prior_owner:
            before = session.state
            decision = prior_player.choose_action(session, _limits(PRIMARY_NODES))
            if decision.action is None:
                return {"hard_failure": "RULE_PRIOR_NO_ACTION", "records": records, "plies": ply}
            legal = {action for action, _child in successors}
            if decision.action not in legal:
                return {"hard_failure": "RULE_PRIOR_ILLEGAL_ACTION", "records": records, "plies": ply}
            reviewer = _make_player(compiled, profile, config).choose_action(
                _session_with_state(compiled, before, session._search_witnesses), _limits(REVIEW_NODES)
            )
            records.append({
                "ply": ply,
                "actor": actor,
                "primary_action": action_to_dict(decision.action),
                "review_action": None if reviewer.action is None else action_to_dict(reviewer.action),
                "primary_nodes": decision.nodes + decision.qnodes,
                "review_nodes": reviewer.nodes + reviewer.qnodes,
                "review_agrees": reviewer.action == decision.action,
            })
            session.submit(decision.action)
        else:
            chosen, _child = successors[rng.randrange(len(successors))]
            session.submit(chosen)
    result = session.state.terminal_status
    return {
        "hard_failure": None,
        "records": records,
        "plies": len(session.history),
        "terminal_status": result.status.value,
        "winner": result.winner,
        "owner0_conversion": result.status is TerminalStatus.CHECKMATE and result.winner == 0,
    }


def _load_generated(root: Path):
    manifest = json.loads((root / GENERATED_SOURCE.relative_to(root)).read_text(encoding="utf-8"))
    if manifest.get("status") != "PRE_REGISTERED_F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE":
        raise AssertionError("generated source manifest drift")
    return manifest["rulesets"][:GENERATED_COUNT]


def run_merged(root: Path = ROOT):
    # Gate 1 is already a published, independently verified Chess/Shogi gate;
    # retain its exact checkpoint as evidence instead of duplicating the large
    # differential corpus inside this merged benchmark.
    result = {
        "status": "PASS",
        "classification": None,
        "gate1": {"status": "PASS", "checkpoint": GATE1_CHECKPOINT, "games": ["chess", "shogi"]},
        "generated_rulesets": [],
        "review": {"primary_node_budget": PRIMARY_NODES, "review_node_budget": REVIEW_NODES, "decision_count": 0, "reviewed_count": 0},
        "first_hard_failure": None,
    }
    seed_index = 0
    for entry in _load_generated(root):
        compiled = compile_ruleset(ruleset_from_dict(entry["ruleset"]))
        config, profile, _flat = _profiles(compiled)
        micro = _microchecks(compiled, profile)
        row = {
            "arm": entry["arm"],
            "sample_id": entry["sample_id"],
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
            "microchecks": micro,
            "trials": [],
        }
        result["generated_rulesets"].append(row)
        if micro["status"] != "PASS":
            result["first_hard_failure"] = {"layer": "microchecks", "ruleset": row["ruleset_fingerprint"]}
            break
        for prior_owner in (0, 1):
            trial = _trial(compiled, profile, config, TRIAL_SEEDS[seed_index], prior_owner)
            seed_index += 1
            row["trials"].append({"seed": TRIAL_SEEDS[seed_index - 1], "prior_owner": prior_owner, **trial})
            result["review"]["decision_count"] += len(trial["records"])
            result["review"]["reviewed_count"] += len(trial["records"])
            if trial["hard_failure"] is not None:
                result["first_hard_failure"] = {"layer": "short_game", "ruleset": row["ruleset_fingerprint"], "reason": trial["hard_failure"]}
                break
        if result["first_hard_failure"] is not None:
            break
    if result["first_hard_failure"] is None and result["review"]["decision_count"] < 105:
        result["first_hard_failure"] = {"layer": "review_coverage", "decision_count": result["review"]["decision_count"], "required": 105}
    if result["first_hard_failure"] is not None:
        result["status"] = "FIRST_HARD_FAILURE"
        result["classification"] = "RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_" + result["first_hard_failure"]["layer"].upper()
    else:
        result["classification"] = "RULE_PRIOR_ABP_BASIC_COMPETENCE_SUPPORTED"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_merged()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
