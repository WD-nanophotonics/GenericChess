"""Independently verify source pins and replay positive task2433 witnesses."""
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
INPUTS = ROOT / "results/dev_aux/task2433/inputs.json"
OUT = ROOT / "results/dev_aux/task2626/task2433-unvisited-variant-audit.json"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def p_to_r(session: GameSession) -> bool:
    return any(piece is not None and piece.base_type_id == "P"
               and piece.current_type_id == "R"
               for piece in session.state.position.board)


def main() -> None:
    if OUT.exists():
        raise FileExistsError("independent screen audit is write-once")
    screen_raw = SCREEN.read_bytes()
    screen = json.loads(screen_raw)
    inputs_raw = INPUTS.read_bytes()
    inputs = {row["index"]: row for row in json.loads(inputs_raw)}
    if screen["screened_rule_indices"] != list(range(2, 16)):
        raise ValueError("screen index set differs from the fixed plan")
    if screen["task2433_inputs_sha256"] != sha(inputs_raw):
        raise ValueError("input manifest changed")
    if len(screen["records"]) != 14:
        raise ValueError("screen record count mismatch")

    verified = []
    for row in screen["records"]:
        index = row["index"]
        rule_raw = (ROOT / row["rule_path"]).read_bytes()
        if sha(rule_raw) != row["rule_sha256"]:
            raise ValueError(f"rule {index} hash mismatch")
        if screen["candidate_rule_sha256"].get(str(index)) != row["rule_sha256"]:
            raise ValueError(f"rule {index} aggregate hash mismatch")
        input_digest = sha(json.dumps(
            inputs[index]["record"], sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode())
        if input_digest != row["prefit_full_record_sha256"]:
            raise ValueError(f"rule {index} prefit input hash mismatch")

        witness = row["witness"]
        if row["status"] == "WITNESS_FOUND":
            if not witness or witness["plies"] != len(witness["actions"]):
                raise ValueError(f"rule {index} witness path length mismatch")
            typed = deserialize_game_record(json.dumps(witness["record"]))
            compiled = compile_ruleset_for_execution(
                ruleset_from_dict(json.loads(rule_raw)))
            replayed = GameSession.replay(compiled, typed)
            if not p_to_r(replayed):
                raise ValueError(f"rule {index} witness does not end with P->R")
            saved_actions = witness["record"].get("actions", [])
            if len(saved_actions) != witness["plies"]:
                raise ValueError(f"rule {index} full record length mismatch")
            verified.append({"index": index, "plies": witness["plies"],
                             "record_sha256": sha(json.dumps(
                                 witness["record"], sort_keys=True,
                                 separators=(",", ":"), ensure_ascii=False).encode())})
        elif witness is not None:
            raise ValueError(f"rule {index} unexpected witness")

    result = {
        "status": "PASS_SOURCE_PINS_AND_POSITIVE_WITNESS_REPLAY",
        "screen_sha256": sha(screen_raw),
        "input_sha256": sha(inputs_raw),
        "record_count": len(screen["records"]),
        "status_counts": {status: sum(row["status"] == status
                                       for row in screen["records"])
                          for status in sorted({row["status"]
                                                for row in screen["records"]})},
        "verified_witnesses": verified,
        "negative_limit": "CAP_REACHED is unresolved; only reported exhausted finite graphs are exhausted within depth24.",
        "outcomes_read": False,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
