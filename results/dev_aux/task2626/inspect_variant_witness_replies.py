"""Test one legal opponent reply from each saved witness for unlock availability."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession

SCREEN = ROOT / "results/dev_aux/task2626/task2433-unvisited-variant-screen.json"
OUT = ROOT / "results/dev_aux/task2626/task2433-variant-unlock-one-reply.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def clone(session: GameSession) -> GameSession:
    other = object.__new__(GameSession)
    for name in type(session).__slots__:
        setattr(other, name, getattr(session, name))
    return other


def is_unlock(action: object) -> bool:
    return getattr(action, "pattern_id", "").endswith(
        "_hand_R_unlocks_rook_quiet")


def main() -> None:
    if OUT.exists():
        raise FileExistsError("one-reply witness audit is write-once")
    screen_raw = SCREEN.read_bytes()
    screen = json.loads(screen_raw)
    rows = []
    for row in screen["records"]:
        witness = row["witness"]
        if witness is None:
            continue
        index = row["index"]
        rule_raw = (ROOT / row["rule_path"]).read_bytes()
        if sha(rule_raw) != row["rule_sha256"]:
            raise ValueError(f"rule {index} changed")
        compiled = compile_ruleset_for_execution(
            ruleset_from_dict(json.loads(rule_raw)))
        record = deserialize_game_record(json.dumps(witness["record"]))
        session = GameSession.replay(compiled, record)
        replies = []
        for reply in session.legal_actions():
            after_reply = clone(session)
            after_reply.submit(reply)
            if after_reply.state.position.side_to_move != 0:
                raise ValueError("expected candidate owner0 to move after one reply")
            unlocks = [action for action in after_reply.legal_actions()
                       if is_unlock(action)]
            if unlocks:
                replies.append({
                    "opponent_reply": action_to_dict(reply),
                    "unlock_actions": [action_to_dict(action) for action in unlocks],
                })
        rows.append({"index": index, "plies_before_reply": witness["plies"],
                     "opponent_legal_replies": len(session.legal_actions()),
                     "replies_with_legal_unlock": replies})
    result = {
        "status": "ONE_REPLY_WITNESS_CHECK_COMPLETE",
        "screen_sha256": sha(screen_raw),
        "witness_count": len(rows),
        "records": rows,
        "max_extension_plies": 1,
        "search_expanded": False,
        "outcomes_read": False,
        "scope": "Only one legal opponent reply from each existing witness endpoint; availability after a reply is existential and is not an opponent-policy or frequency claim.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
