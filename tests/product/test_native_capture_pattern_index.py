"""Derived capture selectors must retain their final pattern and Boolean membership."""
import copy
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.native import _module, native_available
from generic_chess.native.compiler import build_semantic_compile_payload

pytestmark = pytest.mark.skipif(not native_available(), reason="native unavailable")

@pytest.mark.parametrize("owner", [0, 1])
@pytest.mark.parametrize("last_witness", [False, True])
def test_capture_subsequence_retains_256th_pattern_and_deduplicates_types(owner, last_witness):
    module = _module()
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    payload, _ = build_semantic_compile_payload(compiled)
    pattern = copy.deepcopy(next(p for p in payload["patterns"]
        if p["target"] == 1 and p["type_indices"] == [0]
        and not p["guards"] and not p["slot_guards"]))
    drop_gid = next(i for i, g in enumerate(payload["geometries"]) if g["kind"] == 2)
    base = copy.deepcopy(payload)
    base["patterns"] = [copy.deepcopy(pattern)]
    reference_rules = module.compile_semantic_rules(base)
    board = [None] * 64
    board[27] = [0, 0, owner, 0]
    state = dict(board=board, hands=[[0]*6, [0]*6], side=owner, ply=0)
    reference = module.semantic_pack_position(reference_rules, state)
    expected = tuple(module.semantic_attacked_squares(reference_rules, reference, owner))
    assert expected
    # Valid numeric capsule boundary: 255 duplicate selector entries represent
    # Boolean membership, not 255 index appends. Only the final pattern can
    # witness; earlier capture-eligible patterns have drop geometry.
    payload["patterns"] = []
    for index in range(256):
        entry = copy.deepcopy(pattern)
        entry["type_indices"] = [0] * 255
        if index != 255 or not last_witness:
            entry["geometry_indices"] = [drop_gid]
        payload["patterns"].append(entry)
    rules = module.compile_semantic_rules(payload)
    assert module.semantic_rules_info(rules) == payload
    position = module.semantic_pack_position(rules, state)
    before = module.semantic_position_snapshot(rules, position)
    actual = tuple(module.semantic_attacked_squares(rules, position, owner))
    assert actual == (expected if last_witness else ())
    for target in range(64):
        assert module.semantic_is_square_attacked(rules, position, target, owner) == (target in actual)
    assert module.semantic_position_snapshot(rules, position) == before
