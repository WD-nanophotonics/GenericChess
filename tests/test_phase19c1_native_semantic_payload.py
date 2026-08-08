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
    # Valid payload still round-trips exactly.
    compiled = native_compiler.compile_native_semantic_rules(semantic)
    observed = dict(module.semantic_rules_info(compiled.capsule))
    assert observed == payload
    # cannon types have zero promotion targets: any set bit is outside the
    # semantic mask domain.  The value 1<<40 must first be parsed through the
    # strict uint64 reader and then rejected by the domain check; a 32-bit
    # signed-long parse would instead raise OverflowError here.
    mutated = copy.deepcopy(payload)
    mutated["alive_promo"][0][0][0] = 1 << 40
    with pytest.raises(ValueError, match="promotion-target domain"):
        module.compile_semantic_rules(mutated)


def test_c1_bool_aux_initial_must_not_be_none(module):
    semantic = compile_semantic_ruleset(STRESS_GROUPS["castling"]())
    payload, _ = native_compiler.build_semantic_compile_payload(semantic)
    bool_idx = next(
        i for i, s in enumerate(payload["aux_slots"]) if s["value_kind"] == 0
    )
    # Valid bool initial 1 compiles and round-trips exactly.
    compiled = native_compiler.compile_native_semantic_rules(semantic)
    assert dict(module.semantic_rules_info(compiled.capsule)) == payload
    # Valid bool initial 0 compiles and round-trips exactly.
    zero = copy.deepcopy(payload)
    zero["aux_slots"][bool_idx]["initial"] = 0
    compiled_zero = module.compile_semantic_rules(zero)
    assert dict(module.semantic_rules_info(compiled_zero)) == zero
    # bool + None must fail closed before becoming a trusted rules object.
    mutated = copy.deepcopy(payload)
    mutated["aux_slots"][bool_idx]["initial"] = None
    with pytest.raises(ValueError, match="None initial"):
        module.compile_semantic_rules(mutated)


def _find_effect(payload, kind):
    for pat in payload["patterns"]:
        for eff in pat["effects"]:
            if eff["kind"] == kind:
                return pat, eff
    raise AssertionError(f"no effect kind {kind} in payload")


def _find_ref(payload, kind):
    for pat in payload["patterns"]:
        for eff in pat["effects"]:
            for key in ("from_ref", "to_ref", "square_ref"):
                r = eff.get(key)
                if isinstance(r, dict) and r["kind"] == kind:
                    return eff, r
        for g in pat["guards"]:
            for r in g["spatial"]["refs"]:
                if r["kind"] == kind:
                    return g, r
        for sg in pat["slot_guards"]:
            r = sg.get("square_ref")
            if isinstance(r, dict) and r["kind"] == kind:
                return sg, r
        for inv in pat["invariants"]:
            for r in inv["square_refs"]:
                if r["kind"] == kind:
                    return inv, r
    for t in payload["triggers"]:
        if t["square_ref"]["kind"] == kind:
            return t, t["square_ref"]
    raise AssertionError(f"no square_ref kind {kind} in payload")


def test_c1_square_ref_structural_shapes(module):
    from rule_semantics_ir_fixtures import castling_ruleset, en_passant_ruleset

    castling = compile_semantic_ruleset(castling_ruleset())
    en_passant = compile_semantic_ruleset(en_passant_ruleset())
    p_castling, _ = native_compiler.build_semantic_compile_payload(castling)
    p_ep, _ = native_compiler.build_semantic_compile_payload(en_passant)

    # fixed + square=None
    _mutate_rejected(module, p_castling,
                     lambda p: _find_ref(p, 2)[1].__setitem__("square", None),
                     "fixed square None")
    # source + unrelated square
    _mutate_rejected(module, p_castling,
                     lambda p: _find_ref(p, 0)[1].__setitem__("square", 4),
                     "source with square")
    # offset_from_source + offset=None
    _mutate_rejected(module, p_castling,
                     lambda p: _find_ref(p, 3)[1].__setitem__("offset", None),
                     "offset ref None")
    # path_step + step=None
    _mutate_rejected(module, p_castling,
                     lambda p: _find_ref(p, 5)[1].__setitem__("step", None),
                     "path_step None")
    # aux_slot_square + slot_id=None
    def _aux_slot_none(q):
        _owner, ref = _find_ref(q, 1)
        ref["kind"] = 6
        ref["slot_id"] = None
    _mutate_rejected(module, p_ep, _aux_slot_none, "aux_slot_square None")


def test_c1_spatial_cardinality(module):
    from rule_semantics_ir_fixtures import nifu_ruleset
    from rule_semantics_ir_fixtures import weird_rulesets

    nifu = compile_semantic_ruleset(nifu_ruleset())
    zone = compile_semantic_ruleset(weird_rulesets()[1])
    p_nifu, _ = native_compiler.build_semantic_compile_payload(nifu)
    p_zone, _ = native_compiler.build_semantic_compile_payload(zone)

    def _find_spatial(payload, kind):
        return next(
            g["spatial"]
            for pat in payload["patterns"]
            for g in pat["guards"]
            if g["spatial"]["kind"] == kind
        )

    def _same_file_0_refs(q):
        _find_spatial(q, 0)["refs"] = []
    _mutate_rejected(module, p_nifu, _same_file_0_refs, "same_file 0 refs")

    def _same_file_2_refs(q):
        ref = dict(_find_spatial(q, 0)["refs"][0])
        _find_spatial(q, 0)["refs"] = [ref, dict(ref)]
    _mutate_rejected(module, p_nifu, _same_file_2_refs, "same_file 2 refs")

    def _path_between_1_ref(q):
        _find_spatial(q, 0)["kind"] = 4
    _mutate_rejected(module, p_nifu, _path_between_1_ref, "path_between 1 ref")

    def _non_zone_with_zone(q):
        _find_spatial(q, 0)["zone_index"] = 0
    _mutate_rejected(module, p_nifu, _non_zone_with_zone, "non-zone with zone_index")

    def _zone_without_zone(q):
        _find_spatial(q, 5)["zone_index"] = None
    _mutate_rejected(module, p_zone, _zone_without_zone, "zone without zone_index")


def test_c1_promotion_mode_shape(module):
    from rule_semantics_ir_fixtures import cannon_ruleset

    cannon = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    p, _ = native_compiler.build_semantic_compile_payload(cannon)
    pat = p["patterns"][0]
    _mutate_rejected(module, p,
                     lambda q: q["patterns"][0].__setitem__("promotion_mode", 2),
                     "explicit mode without type")
    _mutate_rejected(module, p,
                     lambda q: q["patterns"][0].__setitem__(
                         "explicit_promotion_type", 0),
                     "non-explicit with type")


def test_c1_aux_duplicate_slot_id(module):
    from rule_semantics_ir_fixtures import castling_ruleset

    castling = compile_semantic_ruleset(castling_ruleset())
    p, _ = native_compiler.build_semantic_compile_payload(castling)
    _mutate_rejected(
        module, p,
        lambda q: q["aux_slots"].append(dict(q["aux_slots"][0])),
        "duplicate aux slot_id",
    )


def test_c1_slot_guard_kind_consistency(module):
    from rule_semantics_ir_fixtures import castling_ruleset, en_passant_ruleset

    castling = compile_semantic_ruleset(castling_ruleset())
    en_passant = compile_semantic_ruleset(en_passant_ruleset())
    p_castling, _ = native_compiler.build_semantic_compile_payload(castling)
    p_ep, _ = native_compiler.build_semantic_compile_payload(en_passant)

    def _first_slot_guard(payload):
        return next(
            sg
            for pat in payload["patterns"]
            for sg in pat["slot_guards"]
        )

    def _bool_value_2(q):
        _first_slot_guard(q)["value"] = 2
    _mutate_rejected(module, p_castling, _bool_value_2, "bool slot guard value 2")

    def _bool_with_square(q):
        _first_slot_guard(q)["square_ref"] = {
            "kind": 1, "square": None, "offset": None,
            "owner_relative": 1, "step": None, "slot_id": None,
        }
    _mutate_rejected(module, p_castling, _bool_with_square,
                     "bool slot guard with square_ref")

    def _square_none_lt(q):
        guard = _first_slot_guard(q)
        guard["square_ref"] = None
        guard["comparison"] = 2
    _mutate_rejected(module, p_ep, _square_none_lt, "square slot None + lt")


def test_c1_effect_structural_requirements(module):
    from rule_semantics_ir_fixtures import (
        castling_ruleset,
        en_passant_ruleset,
        nifu_ruleset,
        weird_rulesets,
    )

    castling = compile_semantic_ruleset(castling_ruleset())
    en_passant = compile_semantic_ruleset(en_passant_ruleset())
    nifu = compile_semantic_ruleset(nifu_ruleset())
    weird2 = compile_semantic_ruleset(weird_rulesets()[2])
    weird3 = compile_semantic_ruleset(weird_rulesets()[3])
    p_castling, _ = native_compiler.build_semantic_compile_payload(castling)
    p_ep, _ = native_compiler.build_semantic_compile_payload(en_passant)
    p_nifu, _ = native_compiler.build_semantic_compile_payload(nifu)
    p_w2, _ = native_compiler.build_semantic_compile_payload(weird2)
    p_w3, _ = native_compiler.build_semantic_compile_payload(weird3)

    cases = [
        (p_w3, 9, lambda e: e.__setitem__("to_ref", None)),        # shift
        (p_nifu, 2, lambda e: e.__setitem__("piece_type_ref", None)),  # remove_from_hand
        (p_nifu, 3, lambda e: e.__setitem__("to_ref", None)),      # place
        (p_w2, 4, lambda e: e.__setitem__("type_ref", None)),      # set_current_type
        (p_w2, 5, lambda e: e.__setitem__("value", None)),         # set_bool
        (p_castling, 6, lambda e: e.__setitem__("slot_id", None)),  # clear_right
        (p_ep, 7, lambda e: e.__setitem__("square_ref", None)),    # set_token
        (p_ep, 8, lambda e: e.__setitem__("slot_id", None)),       # clear_token
        (p_castling, 0, lambda e: e.__setitem__("from_ref", None)),  # move
        (p_castling, 0, lambda e: e.__setitem__("disposition", 0)),  # move + forbidden
    ]
    for payload, kind, mutator in cases:
        _mutate_rejected(module, payload,
                         lambda q, k=kind, m=mutator: m(_find_effect(q, k)[1]),
                         f"effect kind {kind}")


def test_c1_invariant_and_postcondition_cardinality(module):
    from rule_semantics_ir_fixtures import castling_ruleset, uchifuzume_ruleset

    castling = compile_semantic_ruleset(castling_ruleset())
    uchifuzume = compile_semantic_ruleset(uchifuzume_ruleset())
    p_castling, _ = native_compiler.build_semantic_compile_payload(castling)
    p_uchi, _ = native_compiler.build_semantic_compile_payload(uchifuzume)

    def _empty_invariant(q):
        next(
            inv
            for pat in q["patterns"]
            for inv in pat["invariants"]
            if inv["kind"] == 1
        )["square_refs"] = []
    _mutate_rejected(module, p_castling, _empty_invariant,
                     "squares_not_attacked empty")

    def _three_postconditions(q):
        pc_pat = next(pat for pat in q["patterns"] if pat["postconditions"])
        pc_pat["postconditions"].append(dict(pc_pat["postconditions"][0]))
    _mutate_rejected(module, p_uchi, _three_postconditions,
                     "three postconditions")


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
