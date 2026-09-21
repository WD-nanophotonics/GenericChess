"""Gate 2 R3: test the R2 counterexample at the solving horizon."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from scripts import f86q_check_forcing_depth3_probe as f86q
from scripts.gate2_r1_rule_prior_forced_win_microbench import (
    CERTIFIED_ACTION_DIGEST,
    ROOT,
    ROOT_DIGEST,
    SOURCE_FINGERPRINT,
    _digest_action,
    _profiles,
    _replay_target_root,
    _session_at,
)
from scripts.gate2_r2_selected_action_forced_win_check import _exact_forced_win


def _decision_depth3(compiled, state, witnesses, config, profile):
    player = AlphaBetaPlayer(
        compiled,
        evaluation_config=config,
        evaluator_override=Evaluator(compiled, profile, config),
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
        use_native_semantic_legality=False,
    )
    decision = player.choose_action(
        _session_at(compiled, state, witnesses),
        SearchLimits(max_depth=3, quiescence_max_depth=0, quiescence_hard_max_depth=0),
    )
    return {
        "chosen_action": None if decision.action is None else action_to_dict(decision.action),
        "action_digest": None if decision.action is None else _digest_action(decision.action),
        "root_score": decision.score,
        "completed_depth": decision.completed_depth,
        "nodes": decision.nodes + decision.qnodes,
        "termination_reason": decision.termination_reason,
    }


def run_gate2_r3(root: Path = ROOT):
    compiled, state, witnesses, replay = _replay_target_root(root)
    if compiled.ruleset_fingerprint != SOURCE_FINGERPRINT:
        raise AssertionError("ruleset fingerprint drift")
    if position_identity_key(state.position, compiled) != ROOT_DIGEST:
        raise AssertionError("root digest drift")
    config, rule_profile, flat_profile, values = _profiles(compiled)

    # This is the only search work in R3: exactly two fresh depth-3 searches.
    rule_decision = _decision_depth3(compiled, state, witnesses, config, rule_profile)
    flat_decision = _decision_depth3(compiled, state, witnesses, config, flat_profile)
    decisions = {"rule_prior": rule_decision, "flat_control": flat_decision}

    legal_by_digest = {
        _digest_action(action): action
        for action, _child in f86q._canonical_successors(state, compiled)
    }
    digests_to_check = [
        digest for digest in dict.fromkeys(
            [rule_decision["action_digest"], flat_decision["action_digest"], CERTIFIED_ACTION_DIGEST]
        ) if digest is not None
    ]
    exact_rows = [
        _exact_forced_win(state, compiled, legal_by_digest[digest])
        for digest in digests_to_check
    ]
    exact_by_digest = {row["action_digest"]: row for row in exact_rows}
    certified_pass = exact_by_digest[CERTIFIED_ACTION_DIGEST]["forced_mate_within_3_plies"]
    rule_pass = exact_by_digest[rule_decision["action_digest"]]["forced_mate_within_3_plies"]
    flat_pass = exact_by_digest[flat_decision["action_digest"]]["forced_mate_within_3_plies"]

    if not certified_pass:
        classification = "GATE2_R3_CERTIFIED_FORCED_WIN_REPRODUCTION_FAILURE"
    elif rule_pass and flat_pass:
        classification = "GATE2_DEPTH2_COUNTEREXAMPLE_IS_HORIZON_LOCAL"
    elif rule_pass and not flat_pass:
        classification = "RULE_PRIOR_RECOVERS_FORCED_WIN_AT_SOLVING_DEPTH"
    elif not rule_pass and flat_pass:
        classification = "RULE_PRIOR_COUNTEREXAMPLE_PERSISTS_AT_SOLVING_DEPTH"
    else:
        classification = "DEPTH3_SEARCH_FAILS_VISIBLE_FORCED_WIN"
    return {
        "status": "PASS",
        "classification": classification,
        "source_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "root_position_digest": ROOT_DIGEST,
        "replay": replay,
        "rule_prior_values": values,
        "depth_3_decisions": decisions,
        "exact_forced_win_checks": exact_rows,
        "compute": {"depth_3_root_searches": 2, "exact_actions_checked": len(exact_rows), "max_plies": 3},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_gate2_r3()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
