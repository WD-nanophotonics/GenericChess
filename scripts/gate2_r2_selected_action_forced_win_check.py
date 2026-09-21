"""Gate 2 R2: exact three-ply forced-win check for the two R1 actions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import TerminalStatus
from scripts.gate2_r1_rule_prior_forced_win_microbench import (
    CERTIFIED_ACTION_DIGEST,
    ROOT,
    ROOT_DIGEST,
    SOURCE_FINGERPRINT,
    _digest_action,
    _replay_target_root,
    run_gate2,
)
from scripts import f86q_check_forcing_depth3_probe as f86q


def _is_owner0_mate(state) -> bool:
    return (
        state.terminal_status.status is TerminalStatus.CHECKMATE
        and state.terminal_status.winner == 0
    )


def _exact_forced_win(root_state, compiled, root_action):
    root_successors = {
        _digest_action(action): child
        for action, child in f86q._canonical_successors(root_state, compiled)
    }
    child = root_successors[_digest_action(root_action)]
    immediate_mate = _is_owner0_mate(child)
    replies = []
    if not immediate_mate:
        for reply_action, reply_child in f86q._canonical_successors(child, compiled):
            mating_continuations = sum(
                _is_owner0_mate(continuation)
                for _continuation_action, continuation in f86q._canonical_successors(reply_child, compiled)
            )
            replies.append({
                "reply_action": action_to_dict(reply_action),
                "mating_continuation_count": mating_continuations,
            })
    forced = immediate_mate or bool(replies) and all(
        row["mating_continuation_count"] > 0 for row in replies
    )
    return {
        "action": action_to_dict(root_action),
        "action_digest": _digest_action(root_action),
        "immediate_mate": immediate_mate,
        "opponent_reply_count": len(replies),
        "opponent_replies": replies,
        "forced_mate_within_3_plies": forced,
    }


def run_gate2_r2(root: Path = ROOT):
    compiled, state, _witnesses, _replay = _replay_target_root(root)
    if compiled.ruleset_fingerprint != SOURCE_FINGERPRINT:
        raise AssertionError("ruleset fingerprint drift")
    if position_identity_key(state.position, compiled) != ROOT_DIGEST:
        raise AssertionError("root digest drift")

    r1 = run_gate2(root)
    rule_decision = r1["root_decisions"]["rule_prior"]
    flat_decision = r1["root_decisions"]["flat_control"]
    reproduces = (
        flat_decision["equals_certified_action"]
        and not rule_decision["equals_certified_action"]
        and flat_decision["action_digest"] == CERTIFIED_ACTION_DIGEST
    )
    if not reproduces:
        return {
            "status": "FIRST_HARD_FORK",
            "classification": "GATE2_R2_R1_DECISION_REPRODUCTION_FAILURE",
            "root_position_digest": ROOT_DIGEST,
            "r1_reproduction": r1["root_decisions"],
            "actions": [],
        }

    legal_by_digest = {
        _digest_action(action): action
        for action, _child in f86q._canonical_successors(state, compiled)
    }
    certified_action = legal_by_digest[CERTIFIED_ACTION_DIGEST]
    rule_action = legal_by_digest[rule_decision["action_digest"]]
    rows = [
        _exact_forced_win(state, compiled, certified_action),
        _exact_forced_win(state, compiled, rule_action),
    ]
    if not rows[0]["forced_mate_within_3_plies"]:
        classification = "GATE2_R2_F86Q_FORCED_WIN_REPRODUCTION_FAILURE"
    elif rows[1]["forced_mate_within_3_plies"]:
        classification = "GATE2_R1_DIVERGENCE_BOTH_FORCED_WINS"
    else:
        classification = "RULE_PRIOR_TACTICAL_COUNTEREXAMPLE_CONFIRMED"
    return {
        "status": "PASS",
        "classification": classification,
        "source_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "root_position_digest": ROOT_DIGEST,
        "r1_reproduction": r1["root_decisions"],
        "actions": rows,
        "compute": {"depth_2_root_searches": 2, "root_actions_checked": 2, "max_plies": 3},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_gate2_r2()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
