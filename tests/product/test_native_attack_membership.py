"""Geometric rejection must preserve later matching targets and fallback."""
import copy
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.native import _module, native_available
from generic_chess.native.compiler import build_semantic_compile_payload

pytestmark = pytest.mark.skipif(not native_available(), reason="Native unavailable")

@pytest.mark.parametrize("owner", (0, 1))
def test_attack_can_use_later_duplicate_target_after_minimum_steps(owner):
    module = _module()
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    payload, _ = build_semantic_compile_payload(compiled)
    pattern = copy.deepcopy(next(p for p in payload["patterns"]
        if p["target"] == 1 and p["type_indices"] == [0]
        and not p["guards"] and not p["slot_guards"]))
    pattern["geometry_indices"] = [0]
    payload["patterns"] = [pattern]
    payload["geometries"][0]["paths"] = [
        [[27, [36, 36]]], [[27, [36, 36]]]]
    payload["geometries"][0]["min_steps"] = 2
    rules = module.compile_semantic_rules(payload)
    assert module.semantic_rules_info(rules) == payload
    board = [None] * 64
    board[27] = [0, 0, owner, 0]
    position = module.semantic_pack_position(rules,
        dict(board=board, hands=[[0]*6, [0]*6], side=owner, ply=0))
    before = module.semantic_position_snapshot(rules, position)
    # First target occurrence fails min_steps; the second is authoritative.
    assert module.semantic_is_square_attacked(rules, position, 36, owner)
    assert set(module.semantic_attacked_squares(rules, position, owner)) == {36}
    assert module.semantic_position_snapshot(rules, position) == before

def test_bounded_membership_construction_keeps_original_scanner():
    module = _module()
    compiled = compile_ruleset_for_execution(build_builtin_ruleset("western_chess"))
    payload, _ = build_semantic_compile_payload(compiled)
    pattern = copy.deepcopy(next(p for p in payload["patterns"]
        if p["target"] == 1 and p["type_indices"] == [0]
        and not p["guards"] and not p["slot_guards"]))
    pattern["geometry_indices"] = [0]
    base = copy.deepcopy(payload)
    base["patterns"] = [copy.deepcopy(pattern)]
    # Accepted repeated references exceed the derived-index work ceiling.
    pattern["geometry_indices"] = [0] * 255
    payload["patterns"] = [copy.deepcopy(pattern) for _ in range(256)]
    board = [None] * 64
    board[27] = [0, 0, 0, 0]
    state = dict(board=board, hands=[[0]*6, [0]*6], side=0, ply=0)
    actual_rules = module.compile_semantic_rules(payload)
    reference_rules = module.compile_semantic_rules(base)
    assert module.semantic_rules_info(actual_rules) == payload
    actual = module.semantic_pack_position(actual_rules, state)
    reference = module.semantic_pack_position(reference_rules, state)
    assert module.semantic_attacked_squares(actual_rules, actual, 0) == (
        module.semantic_attacked_squares(reference_rules, reference, 0))
