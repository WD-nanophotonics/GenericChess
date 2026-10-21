"""Canonical identity bytes remain stable across encoder cost changes."""
import hashlib
import json
import random
import pytest

import generic_chess.native as native
from generic_chess import compile_ruleset_for_execution
from generic_chess.native.compiler import build_semantic_compile_payload
from generic_chess.rules.western_chess import build_western_chess_ruleset


@pytest.mark.parametrize("ids", [['ASCII', 'Q"quote', 'slash\\end', 'line\nbreak', '制御é', '😀'], ['\x08', '\x0c', '\r', '\t', '\x01', '\x1f'], ['α', '日本語', 'é', '𝄞', '𐀀', 'end\\"']])
def test_native_identity_matches_independent_json_for_public_type_ids(ids):
    if not native.native_available():
        pytest.skip("optional Native identity")
    module = native._module()
    payload, _ = build_semantic_compile_payload(
        compile_ruleset_for_execution(build_western_chess_ruleset()))
    capsule = module.compile_semantic_rules(dict(payload, type_ids=ids))
    rng = random.Random(2026101300)
    # These are valid typed representation fields, not claimed reachable games.
    for _ in range(8):
        board = []
        for square in range(64):
            tid = rng.randrange(6)
            board.append(None if rng.randrange(3) == 0 else
                         [tid, tid, rng.randrange(2), 1])
        side = rng.randrange(2)
        position = module.semantic_pack_position(capsule, dict(
            board=board, hands=[[rng.randrange(4) for _ in ids] for _ in range(2)],
            side=side, ply=0, aux=[]))
        snapshot = dict(module.semantic_position_snapshot(capsule, position))
        expected = dict(
            aux_state={f"{x[0]}:{x[1]}": x[2] for x in snapshot.get("aux_state", snapshot.get("aux", []))},
            board=[None if x is None else
                   [x[2], ids[x[0]], ids[x[1]], bool(x[3])]
                   for x in snapshot["board"]],
            hands=[[[[ids[t], n] for t, n in
                     sorted(enumerate(hand), key=lambda item: ids[item[0]]) if n]
                    for hand in snapshot["hands"]]],
            ruleset=payload["fingerprint"], side_to_move=side,
        )
        data = json.dumps(expected, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True).encode("utf-8")
        assert module.semantic_position_key(capsule, position) == hashlib.sha256(data).hexdigest()
