"""Gate 2 R1: one frozen generated forced-win evaluator microbenchmark.

The harness replays the exact F86O policy tape to the exact F86Q root, then
uses only the production Python AlphaBetaPlayer with two evaluator profiles.
It does not modify production search, rules, evaluator, generator, or learner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import TerminalStatus
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from scripts import f86q_check_forcing_depth3_probe as f86q


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARM = "F"
SOURCE_SAMPLE = "V5-3"
SOURCE_FINGERPRINT = "29390db6050d1ba482a393f7466608a6f19d0df9e6d4f7c3bd3a556f2d194fff"
ROOT_DIGEST = "48cdc72b8ca6551f2a5cc0bd3b5c4aec6e05aa49a602c7436a22f49f59728114"
CERTIFIED_ACTION = {"from": [3, 4], "to": [2, 3]}
CERTIFIED_ACTION_DIGEST = "e99cf8e4ae8f10f5a4dfd5b0e02d42a5896eb067c83ff6c6ed30650c7055f273"


def _digest_action(action) -> str:
    payload = json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _source_entry(root: Path):
    manifest = f86q._f86o_manifest(root)
    entries = [
        entry for entry in manifest["rulesets"]
        if entry["arm"] == SOURCE_ARM and entry["sample_id"] == SOURCE_SAMPLE
    ]
    if len(entries) != 1:
        raise AssertionError("F86O source entry is not unique")
    entry = entries[0]
    compiled = compile_ruleset(ruleset_from_dict(entry["ruleset"]))
    if compiled.ruleset_fingerprint != SOURCE_FINGERPRINT:
        raise AssertionError("frozen ruleset fingerprint drift")
    return manifest, entry, compiled


def _replay_target_root(root: Path):
    manifest, entry, compiled = _source_entry(root)
    tapes = f86q._load_tapes(manifest)[SOURCE_SAMPLE]
    for seats in (("A", "B"), ("B", "A")):
        session = GameSession(compiled)
        consumed = {"A": 0, "B": 0}
        actions = []
        while session.result.status.value == "ongoing" and len(session.history) < f86q.MAX_PLY:
            digest = position_identity_key(session.state.position, compiled)
            if digest == ROOT_DIGEST:
                sequence_sha = hashlib.sha256(
                    json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                return compiled, session.state, session._search_witnesses, {
                    "arm": SOURCE_ARM,
                    "sample_id": SOURCE_SAMPLE,
                    "seat_assignment": {"player0": seats[0], "player1": seats[1]},
                    "root_position_digest": digest,
                    "root_actor": session.state.position.side_to_move,
                    "prefix_plies": len(actions),
                    "prefix_action_sequence_sha256": sequence_sha,
                }
            successors = f86q._canonical_successors(session.state, compiled)
            if not successors:
                break
            actor = session.state.position.side_to_move
            tape = tapes[seats[actor]]
            chosen, _child = successors[tape.choose_index(consumed[seats[actor]], len(successors))]
            actions.append({"actor": actor, "action": action_to_dict(chosen), "legal_action_count": len(successors)})
            consumed[seats[actor]] += 1
            session.submit(chosen)
    raise AssertionError("F86Q root digest was not reconstructed")


def _session_at(compiled, state, witnesses):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = witnesses
    return session


def _profiles(compiled):
    config = EvaluationConfig()
    rule_profile = build_ruleset_profile(compiled, config)
    ordinary = [
        value for type_id, value in rule_profile.board_value_by_type.items()
        if not compiled.types_by_id[type_id].is_anchor
    ]
    median = int(round(rule_profile.median_non_anchor_value))
    if rule_profile.board_value_by_type.get("P0") == rule_profile.board_value_by_type.get("P1"):
        raise RuntimeError("GATE2_R1_NO_VALUE_CONTRAST")
    flat_board = {
        type_id: (0 if compiled.types_by_id[type_id].is_anchor else median)
        for type_id in rule_profile.board_value_by_type
    }
    flat_hand_value = int(round(median * config.hand_weight))
    flat_hand = {
        type_id: (0 if compiled.types_by_id[type_id].is_anchor else flat_hand_value)
        for type_id in rule_profile.hand_value_by_base_type
    }
    flat_profile = replace(
        rule_profile,
        board_value_by_type=flat_board,
        hand_value_by_base_type=flat_hand,
        promotion_gain_by_type={type_id: 0 for type_id in rule_profile.promotion_gain_by_type},
    )
    return config, rule_profile, flat_profile, {
        "P0": rule_profile.board_value_by_type["P0"],
        "P1": rule_profile.board_value_by_type["P1"],
        "flat_ordinary": median,
        "flat_hand": flat_hand_value,
    }


def _decision(compiled, state, witnesses, config, profile):
    evaluator = Evaluator(compiled, profile, config)
    player = AlphaBetaPlayer(
        compiled,
        evaluation_config=config,
        evaluator_override=evaluator,
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
        use_native_semantic_legality=False,
    )
    decision = player.choose_action(
        _session_at(compiled, state, witnesses),
        SearchLimits(max_depth=2, quiescence_max_depth=0, quiescence_hard_max_depth=0),
    )
    return {
        "chosen_action": None if decision.action is None else action_to_dict(decision.action),
        "action_digest": None if decision.action is None else _digest_action(decision.action),
        "root_score": decision.score,
        "completed_depth": decision.completed_depth,
        "equals_certified_action": bool(
            decision.action is not None and _digest_action(decision.action) == CERTIFIED_ACTION_DIGEST
        ),
        "nodes": decision.nodes + decision.qnodes,
        "termination_reason": decision.termination_reason,
    }


def _conversion_trial(compiled, state, witnesses, config, rule_profile, flat_profile, rule_attacker: bool):
    current = state
    current_witnesses = witnesses
    actions = []
    for _ply in range(3):
        if current.terminal_status.status is not TerminalStatus.ONGOING:
            break
        owner0_turn = current.position.side_to_move == 0
        profile = rule_profile if owner0_turn == rule_attacker else flat_profile
        decision = _decision(compiled, current, current_witnesses, config, profile)
        if decision["chosen_action"] is None:
            break
        action = next(
            candidate for candidate in f86q._canonical_successors(current, compiled)
            if action_to_dict(candidate[0]) == decision["chosen_action"]
        )[0]
        actions.append(decision["chosen_action"])
        current = next(child for candidate, child in f86q._canonical_successors(current, compiled) if candidate == action)
        current_witnesses = current_witnesses + (current.position,)
        if current.terminal_status.status is TerminalStatus.CHECKMATE:
            break
    return {
        "rule_prior_controls_owner_0": rule_attacker,
        "plies": len(actions),
        "actions": actions,
        "terminal_status": current.terminal_status.status.value,
        "winner": current.terminal_status.winner,
        "conversion_success": current.terminal_status.status is TerminalStatus.CHECKMATE and current.terminal_status.winner == 0,
    }


def run_gate2(root: Path = ROOT):
    compiled, state, witnesses, replay = _replay_target_root(root)
    config, rule_profile, flat_profile, values = _profiles(compiled)
    rule_decision = _decision(compiled, state, witnesses, config, rule_profile)
    flat_decision = _decision(compiled, state, witnesses, config, flat_profile)
    decisions = {"rule_prior": rule_decision, "flat_control": flat_decision}
    trials = []
    certified = [item["equals_certified_action"] for item in decisions.values()]
    if rule_decision["equals_certified_action"] and not flat_decision["equals_certified_action"]:
        trials = [
            _conversion_trial(compiled, state, witnesses, config, rule_profile, flat_profile, True),
            _conversion_trial(compiled, state, witnesses, config, rule_profile, flat_profile, False),
        ]
        if trials[0]["conversion_success"] and not trials[1]["conversion_success"]:
            classification = "RULE_PRIOR_GENERATED_TACTICAL_STRENGTH_SIGNAL"
        elif trials[1]["conversion_success"] and not trials[0]["conversion_success"]:
            classification = "RULE_PRIOR_GENERATED_TACTICAL_COUNTEREXAMPLE"
        elif trials[0]["conversion_success"] and trials[1]["conversion_success"]:
            classification = "GATE2_R1_FORCED_WIN_TOO_EASY_TO_DISCRIMINATE"
        else:
            classification = "GATE2_R1_DEPTH2_FAILS_TO_CONVERT_CERTIFIED_WIN"
    elif rule_decision["equals_certified_action"] and flat_decision["equals_certified_action"]:
        classification = "GATE2_R1_BOTH_FIND_FORCED_WIN"
    elif rule_decision["chosen_action"] == flat_decision["chosen_action"]:
        classification = "GATE2_R1_SHARED_NONWINNING_POLICY"
    else:
        classification = "GATE2_R1_POLICY_DIVERGENCE_WITHOUT_WINNING_ROUTE"
    return {
        "status": "PASS",
        "classification": classification,
        "source_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "root_position_digest": position_identity_key(state.position, compiled),
        "certified_action": CERTIFIED_ACTION,
        "certified_action_digest": CERTIFIED_ACTION_DIGEST,
        "replay": replay,
        "rule_prior_values": values,
        "root_decisions": decisions,
        "conversion_trials": trials,
        "compute": {"root_searches": 2, "conversion_trials": len(trials), "max_conversion_plies": 6},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_gate2()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
