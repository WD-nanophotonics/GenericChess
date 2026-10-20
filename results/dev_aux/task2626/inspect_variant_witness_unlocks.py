"""Check hand-R unlock availability at saved positive screen endpoints only."""
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

SCREEN = ROOT / "results/dev_aux/task2626/task2433-unvisited-variant-screen.json"
OUT = ROOT / "results/dev_aux/task2626/task2433-variant-unlock-endpoints.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> None:
    if OUT.exists():
        raise FileExistsError("witness endpoint inspection is write-once")
    screen_raw = SCREEN.read_bytes()
    screen = json.loads(screen_raw)
    rows = []
    for witness_row in screen["records"]:
        witness = witness_row["witness"]
        if witness is None:
            continue
        index = witness_row["index"]
        rule_raw = (ROOT / witness_row["rule_path"]).read_bytes()
        if sha(rule_raw) != witness_row["rule_sha256"]:
            raise ValueError(f"rule {index} changed after screen")
        compiled = compile_ruleset_for_execution(
            ruleset_from_dict(json.loads(rule_raw)))
        record = deserialize_game_record(json.dumps(witness["record"]))
        session = GameSession.replay(compiled, record)
        position = session.state.position
        owners = []
        for owner in (0, 1):
            board_r = sum(piece is not None and piece.owner == owner
                          and piece.current_type_id == "R"
                          for piece in position.board)
            hand_r = sum(count for type_id, count in position.hands[owner].counts
                         if type_id == "R")
            owners.append({"owner": owner, "board_current_R": board_r,
                           "hand_R": hand_r})
        unlocks = [action for action in session.legal_actions()
                   if getattr(action, "pattern_id", "").endswith(
                       "_hand_R_unlocks_rook_quiet")]
        rows.append({"index": index, "plies": witness["plies"],
                     "side_to_move": position.side_to_move,
                     "owners": owners,
                     "legal_hand_R_unlock_actions": [str(action)
                                                     for action in unlocks],
                     "full_record_sha256": sha(json.dumps(
                         witness["record"], sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode())})
    result = {
        "status": "SAVED_WITNESS_ENDPOINTS_REPLAYED",
        "screen_sha256": sha(screen_raw),
        "witness_count": len(rows),
        "records": rows,
        "search_expanded": False,
        "outcomes_read": False,
        "scope": "Endpoint coexistence and legal action availability for the four saved witnesses only; no frequency or reachability claim beyond them.",
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
