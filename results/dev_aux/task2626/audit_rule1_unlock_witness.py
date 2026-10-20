"""Verify the saved rule1 hand-R unlock mechanics witness without outcome labels."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

WITNESS = ROOT / "results/dev_aux/task2626/rule1-unlock-legal-action-witness.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    data = json.loads(WITNESS.read_text(encoding="utf-8"))
    for relative, expected in data["source_sha256"].items():
        if sha((ROOT / relative).read_bytes()) != expected:
            raise ValueError(f"pinned source changed: {relative}")
    rule_path = ROOT / "results/dev_aux/task2433/rules-1.json"
    rule_raw = rule_path.read_bytes()
    if sha(rule_raw) != data["rule_sha256"]:
        raise ValueError("candidate rule hash mismatch")
    compiled = compile_ruleset_for_execution(ruleset_from_dict(json.loads(rule_raw)))

    before_record = data["before_record"]
    after_record = data["after_record"]
    before_typed = deserialize_game_record(json.dumps(before_record))
    after_typed = deserialize_game_record(json.dumps(after_record))
    before_session = GameSession.replay(compiled, before_typed)
    after_session = GameSession.replay(compiled, after_typed)
    if len(before_record["actions"]) != 8 or len(after_record["actions"]) != 9:
        raise ValueError("full-history lengths differ from the frozen witness")
    legal = [action for action in before_session.legal_actions()
             if str(action) == data["chosen_unlock_action"]]
    if len(legal) != 1 or not getattr(legal[0], "pattern_id", "").endswith(
            "_hand_R_unlocks_rook_quiet"):
        raise ValueError("saved hand-R unlock action is not uniquely legal")
    before_session.submit(legal[0])
    if before_session.to_record() != after_session.to_record():
        raise ValueError("chosen action does not reproduce the saved after-history")

    before_env = FixedScaleSessionEnv(GameSession.replay(compiled, before_typed))
    after_env = FixedScaleSessionEnv(after_session)
    features_before = list(before_env.features())
    features_after = list(after_env.features())
    delta = [right - left for left, right in zip(features_before, features_after)]
    if (features_before != data["features_before"]
            or features_after != data["features_after"]
            or delta != data["feature_delta"]
            or delta != [0, 0, 0, 0, 0, -1]):
        raise ValueError("fixed-scale feature transition mismatch")
    owner0_hand_r = sum(count for type_id, count in after_session.state.position.hands[0].counts
                        if type_id == "R")
    if owner0_hand_r != data["owner0_hand_R_after"] or owner0_hand_r != 0:
        raise ValueError("hand-R consumption does not match the saved receipt")
    if data.get("terminal_outcome_read") is not False:
        raise ValueError("witness must not use a terminal outcome")

    print(json.dumps({
        "status": "PASS_LEGAL_RULE1_HAND_R_UNLOCK_FEATURE_TRANSITION",
        "witness_sha256": sha(WITNESS.read_bytes()),
        "start_plies": data["starting_plies"],
        "reply": data["reply_action"],
        "unlock_action": data["chosen_unlock_action"],
        "feature_delta": delta,
        "terminal_outcome_read": False,
        "scope": data["scope"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
