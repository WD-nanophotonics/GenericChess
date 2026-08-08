"""Focused implementation hardening for Phase 1.9C-1 (not specification).

Covers architecture hazards not directly observable through the frozen C-1
spec tests: capsule ownership independence, deterministic ID maps, exact
geometry-path authority, malformed payload fail-closed behavior, and the
legacy checked-make semantic-kind rejection boundary.
"""

from __future__ import annotations

import copy
import gc
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import generic_chess.native as native
from generic_chess.native import compiler as native_compiler
from generic_chess.rules.compiler import compile_semantic_ruleset

from phase19c1_native_semantic_fixtures import semantic_corpus
from rule_semantics_ir_fixtures import STRESS_GROUPS


@pytest.fixture(scope="module")
def module():
    assert native.native_available(), "native extension must be built"
    return native._module()


def _compile_group(name):
    semantic = compile_semantic_ruleset(STRESS_GROUPS[name]())
    return semantic, native_compiler.compile_native_semantic_rules(semantic)


def test_c1_capsule_survives_python_payload_deletion(module):
    semantic, compiled = _compile_group("cannon")
    payload, report = native_compiler.build_semantic_compile_payload(semantic)
    del semantic, payload, report
    gc.collect()
    observed = dict(module.semantic_rules_info(compiled.capsule))
    assert observed["fingerprint"] == compiled.fingerprint
    assert observed["semantic_payload_version"] == 1
    assert observed["board_size"] >= 4


def test_c1_repeated_compile_does_not_alias_c_state(module):
    semantic = compile_semantic_ruleset(STRESS_GROUPS["castling"]())
    payload, _ = native_compiler.build_semantic_compile_payload(semantic)
    a = native_compiler.compile_native_semantic_rules(semantic)
    b = native_compiler.compile_native_semantic_rules(semantic)
    assert dict(module.semantic_rules_info(a.capsule)) == payload
    assert dict(module.semantic_rules_info(b.capsule)) == payload
    del a
    gc.collect()
    assert dict(module.semantic_rules_info(b.capsule)) == payload


def test_c1_malformed_payload_fails_closed(module):
    semantic = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    payload, _ = native_compiler.build_semantic_compile_payload(semantic)
    bad_types = copy.deepcopy(payload)
    bad_types["types"] = [{"is_anchor": 0}]
    with pytest.raises(Exception):
        module.compile_semantic_rules(bad_types)
    bad_pattern = copy.deepcopy(payload)
    bad_pattern["patterns"] = [{}]
    with pytest.raises(Exception):
        module.compile_semantic_rules(bad_pattern)
    bad_count = copy.deepcopy(payload)
    bad_count["patterns"] = bad_count["patterns"] * 300  # exceeds 256
    with pytest.raises(Exception):
        module.compile_semantic_rules(bad_count)


def _mutate_rejected(module, payload, mutator, note):
    mutated = copy.deepcopy(payload)
    mutator(mutated)
    with pytest.raises(Exception):
        module.compile_semantic_rules(mutated)


def test_c1_single_field_mutations_fail_closed(module):
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from rule_semantics_ir_fixtures import (
        castling_ruleset,
        en_passant_ruleset,
        uchifuzume_ruleset,
    )

    cannon = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    castling = compile_semantic_ruleset(castling_ruleset())
    en_passant = compile_semantic_ruleset(en_passant_ruleset())
    uchifuzume = compile_semantic_ruleset(uchifuzume_ruleset())
    p_cannon, _ = native_compiler.build_semantic_compile_payload(cannon)
    p_castling, _ = native_compiler.build_semantic_compile_payload(castling)
    p_ep, _ = native_compiler.build_semantic_compile_payload(en_passant)
    p_uchi, _ = native_compiler.build_semantic_compile_payload(uchifuzume)

    n = p_cannon["board_size"]
    n2 = n * n

    # top-level version / scalars
    _mutate_rejected(module, p_cannon, lambda p: p.__setitem__("semantic_payload_version", 2), "version 2")
    _mutate_rejected(module, p_cannon, lambda p: p.__setitem__("board_size", 257), "board_size 257")
    _mutate_rejected(module, p_cannon, lambda p: p.__setitem__("board_size", -1), "board_size -1")
    _mutate_rejected(module, p_cannon, lambda p: p.__setitem__("repetition_limit", 65537), "repetition_limit 65537")

    # enum domains
    _mutate_rejected(module, p_cannon, lambda p: p["geometries"][0].__setitem__("kind", 99), "geometry kind 99")
    _mutate_rejected(module, p_cannon, lambda p: p["geometries"][0].__setitem__("kind", 257), "geometry kind 257")
    _mutate_rejected(module, p_cannon, lambda p: p["patterns"][0].__setitem__("target", 99), "target 99")
    _mutate_rejected(module, p_cannon, lambda p: p["patterns"][0].__setitem__("target", 259), "target 259")
    _mutate_rejected(module, p_cannon, lambda p: p["patterns"][0].__setitem__("promotion_mode", 99), "promotion_mode 99")
    _mutate_rejected(module, p_cannon, lambda p: p["patterns"][0].__setitem__("cost", 99), "cost 99")
    _mutate_rejected(module, p_cannon, lambda p: p["patterns"][0].__setitem__("stratum", 99), "stratum 99")

    # postconditions
    pc_idx = next(
        i
        for i, pat in enumerate(p_uchi["patterns"])
        if pat["postconditions"]
    )
    _mutate_rejected(
        module, p_uchi,
        lambda p: p["patterns"][pc_idx]["postconditions"][0].__setitem__("kind", 99),
        "postcondition kind 99",
    )
    _mutate_rejected(
        module, p_uchi,
        lambda p: p["patterns"][pc_idx]["postconditions"][0].__setitem__("max_stratum", 4),
        "postcondition max_stratum S4",
    )

    # aux slots
    _mutate_rejected(module, p_castling, lambda p: p["aux_slots"][0].__setitem__("value_kind", 99), "aux value_kind 99")
    _mutate_rejected(module, p_castling, lambda p: p["aux_slots"][0].__setitem__("scope", 99), "aux scope 99")
    _mutate_rejected(module, p_castling, lambda p: p["aux_slots"][0].__setitem__("lifetime", 99), "aux lifetime 99")

    # triggers
    _mutate_rejected(module, p_castling, lambda p: p["triggers"][0].__setitem__("event", 99), "trigger event 99")
    # fixed square in castling trigger -> out of board range
    _mutate_rejected(
        module, p_castling,
        lambda p: p["triggers"][0]["square_ref"].__setitem__("square", n2),
        "trigger fixed square out of board",
    )

    # cross-reference indices
    _mutate_rejected(
        module, p_cannon,
        lambda p: p["patterns"][0]["type_indices"].__setitem__(0, len(p["types"])),
        "pattern type index == type_count",
    )
    _mutate_rejected(
        module, p_cannon,
        lambda p: p["patterns"][0]["geometry_indices"].__setitem__(0, len(p["geometries"])),
        "pattern geometry index == geometry_count",
    )
    # invalid slot_id in a pattern slot guard (castling king_right)
    sg_idx = next(
        i
        for i, pat in enumerate(p_castling["patterns"])
        if pat["slot_guards"]
    )
    _mutate_rejected(
        module, p_castling,
        lambda p: p["patterns"][sg_idx]["slot_guards"][0].__setitem__("slot_id", 999),
        "slot guard slot_id unknown",
    )


def test_c1_alive_promo_parsed_as_u64(module):
    semantic = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    payload, _ = native_compiler.build_semantic_compile_payload(semantic)
    # cannon has no promotion targets; a high-bit mask (> INT32_MAX) must be
    # preserved exactly through the u64 path, not rejected by a 32-bit long.
    high = 1 << 40
    mutated = copy.deepcopy(payload)
    mutated["alive_promo"][0][0][0] = high
    compiled = native_compiler.compile_native_semantic_rules(semantic)
    observed = dict(module.semantic_rules_info(compiled.capsule))
    assert observed == payload  # valid payload unaffected
    # direct C compile of the mutated payload round-trips the high mask
    from generic_chess.native import _module as _raw_module

    capsule = _raw_module().compile_semantic_rules(mutated)
    assert dict(_raw_module().semantic_rules_info(capsule)) == mutated


def test_c1_legacy_checked_make_rejects_semantic_kinds(module):
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.core.transition import initial_state
    from generic_chess.native.adapter import (
        native_make_checked,
        pack_native_position,
    )
    from generic_chess.native.compiler import (
        NativeActionError,
        compile_native_rules,
    )

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    compiled = build_compiled(specs["gen_classic_like_4_101"])
    rules = compile_native_rules(compiled)
    pos = pack_native_position(compiled, rules, initial_state(compiled))
    for kind in (2, 3):
        packed = kind << 32
        with pytest.raises(NativeActionError) as exc:
            native_make_checked(rules, pos, packed)
        assert exc.value.status == 10  # GC_STATUS_ACTION_INVALID_KIND


def test_c1_no_semantic_execution_entry_points(module):
    for name in (
        "semantic_legal_actions",
        "semantic_make",
        "semantic_child_snapshot",
        "semantic_terminal",
        "semantic_perft",
        "semantic_fixed_depth_search",
        "semantic_search",
    ):
        assert not hasattr(module, name), name


def test_c1_id_maps_deterministic_over_repeated_compile():
    for name, semantic in list(semantic_corpus())[:4]:
        a = native_compiler.compile_native_semantic_rules(semantic)
        b = native_compiler.compile_native_semantic_rules(semantic)
        assert tuple(a.type_ids) == tuple(b.type_ids) == tuple(
            sorted(semantic.support.type_metadata)
        ), name
        assert tuple(a.pattern_ids) == tuple(b.pattern_ids) == tuple(
            p.pattern_id for p in semantic.ir.patterns
        ), name
        assert tuple(a.geometry_ids) == tuple(b.geometry_ids) == tuple(
            sorted(semantic.ir.geometry)
        ), name
        assert tuple(a.zone_ids) == tuple(b.zone_ids) == tuple(
            sorted(semantic.ir.zones)
        ), name


def test_c1_geometry_paths_match_compiled_authority(module):
    semantic = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    compiled = native_compiler.compile_native_semantic_rules(semantic)
    info = dict(module.semantic_rules_info(compiled.capsule))
    for gi, gid in enumerate(compiled.geometry_ids):
        geo = semantic.ir.geometry[gid]
        for owner_idx, owner in enumerate(("0", "1")):
            per_source = geo.paths.get(owner, {})
            expected = [
                [source, list(per_source[source])]
                for source in sorted(per_source)
                if per_source[source]
            ]
            assert info["geometries"][gi]["paths"][owner_idx] == expected, gid
        assert info["geometries"][gi]["kind"] == (
            0 if geo.kind == "leap" else 1 if geo.kind == "ray" else 2
        ), gid
