"""Numeric source paths retain first-match semantics, including accepted disorder."""
import copy
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.native import _module, native_available
from generic_chess.native.compiler import build_semantic_compile_payload

pytestmark = pytest.mark.skipif(not native_available(), reason="native unavailable")

@pytest.mark.parametrize("owner", [0, 1])
@pytest.mark.parametrize("case", ["sorted", "sorted_duplicate", "unsorted_duplicate", "missing", "empty", "max65535"])
def test_path_source_lookup_retains_first_duplicate_and_missing_sources(owner, case):
    module = _module()
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    payload, _ = build_semantic_compile_payload(compiled)
    pattern = copy.deepcopy(next(p for p in payload["patterns"]
        if p["target"] == 1 and p["type_indices"] == [0]
        and not p["guards"] and not p["slot_guards"]))
    pattern["geometry_indices"] = [0]
    payload["patterns"] = [pattern]
    entries = {
        "sorted": [[0, [9]], [27, [36]], [50, [59]]],
        "sorted_duplicate": [[0, [9]], [27, [36]], [27, [45]], [50, [59]]],
        "unsorted_duplicate": [[50, [59]], [27, [36]], [0, [9]], [27, [45]]],
        "missing": [[50, [59]], [0, [9]]],
        "empty": [],
    }.get(case)
    if case == "max65535":
        entries = [[27, [36]]] + [[27, [45]]] * 65534
    payload["geometries"][0]["paths"] = [entries, entries]
    rules = module.compile_semantic_rules(payload)
    assert module.semantic_rules_info(rules) == payload
    board = [None] * 64
    board[27] = [0, 0, owner, 0]
    position = module.semantic_pack_position(rules,
        dict(board=board, hands=[[0]*6, [0]*6], side=owner, ply=0))
    before = module.semantic_position_snapshot(rules, position)
    # The first source-27 entry reaches 36; the later duplicate reaching 45
    # must never replace it. This is a numeric capsule contract, not a game.
    expected = {36} if case not in ("missing", "empty") else set()
    assert set(module.semantic_attacked_squares(rules, position, owner)) == expected
    for target in range(64):
        assert module.semantic_is_square_attacked(rules, position, target, owner) == (target in expected)
    assert module.semantic_position_snapshot(rules, position) == before
