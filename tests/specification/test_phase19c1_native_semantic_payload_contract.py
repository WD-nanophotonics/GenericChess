"""Frozen Phase 1.9C-1 static semantic payload contract evidence.

Successor runtime/version/capability expectations live in the ADR-018/C2
contract module.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generic_chess.native as native
from generic_chess.native import compiler as native_compiler
from generic_chess.rules.compiler import compile_semantic_ruleset

from phase19c1_native_semantic_fixtures import (
    SEMANTIC_ACTION_LAYOUT,
    expected_ids,
    geometry_overflow_semantic,
    semantic_corpus,
)
from rule_semantics_ir_fixtures import STRESS_GROUPS


def _module():
    assert native.native_available(), "native extension must be built"
    return native._module()


def _compile_api():
    assert hasattr(native_compiler, "NativeSemanticCompilationReport")
    assert hasattr(native_compiler, "NativeSemanticCompiledRules")
    assert hasattr(native_compiler, "build_semantic_compile_payload")
    assert hasattr(native_compiler, "compile_native_semantic_rules")
    return native_compiler.compile_native_semantic_rules


def test_c1_spec01_semantic_native_compile_api_exists():
    _compile_api()


def test_c1_spec02_static_payload_capabilities_are_additive():
    adr017 = (Path(__file__).resolve().parents[2] / "docs" / "architecture" / "ADR-017-native-semantic-payload-and-action-identity.md").read_text(encoding="utf-8")
    assert 'native_version()       == "0.4.0"' in adr017
    assert 'NATIVE_SCHEMA_VERSION  == "native-0.4.0"' in adr017
    caps = native.native_capabilities()
    assert caps["semantic_ir_v2_compile"] is True
    assert caps["semantic_payload_version"] == 3
    assert caps["semantic_exact_action_identity"] is True


def test_c1_spec03_c_extension_static_semantic_entry_points_exist():
    mod = _module()
    assert hasattr(mod, "compile_semantic_rules")
    assert hasattr(mod, "semantic_rules_info")
    assert hasattr(mod, "semantic_action_layout")
    assert not hasattr(mod, "semantic_legal_actions")
    assert not hasattr(mod, "semantic_perft")
    assert not hasattr(mod, "semantic_search")


def test_c1_spec04_all_frozen_semantic_corpus_compiles_to_separate_capsules():
    compile_semantic = _compile_api()
    for name, semantic in semantic_corpus():
        compiled = compile_semantic(semantic)
        assert compiled.capsule is not None, name
        assert compiled.fingerprint == semantic.ruleset_fingerprint, name
        assert compiled.report.ir_version == 2, name
        assert compiled.report.semantic_payload_version == 3, name


def test_c1_spec05_deterministic_reversible_numeric_id_maps():
    compile_semantic = _compile_api()
    for name, semantic in semantic_corpus():
        exp = expected_ids(semantic)
        a = compile_semantic(semantic)
        b = compile_semantic(semantic)
        assert tuple(a.type_ids) == exp["type_ids"], name
        assert tuple(a.pattern_ids) == exp["pattern_ids"], name
        assert tuple(a.geometry_ids) == exp["geometry_ids"], name
        assert tuple(a.zone_ids) == exp["zone_ids"], name
        assert tuple(a.type_ids) == tuple(b.type_ids), name
        assert tuple(a.pattern_ids) == tuple(b.pattern_ids), name
        assert tuple(a.geometry_ids) == tuple(b.geometry_ids), name


def test_c1_spec06_c_owned_payload_roundtrip_is_exact():
    _compile_api()
    mod = _module()
    for name, semantic in semantic_corpus():
        payload, _report = native_compiler.build_semantic_compile_payload(semantic)
        compiled = native_compiler.compile_native_semantic_rules(semantic)
        assert dict(mod.semantic_rules_info(compiled.capsule)) == payload, name


def test_c1_spec07_lowering_does_not_depend_on_legacy_compiled_handle():
    _compile_api()
    semantic = compile_semantic_ruleset(STRESS_GROUPS["en_passant"]())
    poisoned = replace(semantic, _legacy_compiled=object())
    payload_a, _ = native_compiler.build_semantic_compile_payload(semantic)
    payload_b, _ = native_compiler.build_semantic_compile_payload(poisoned)
    assert payload_a == payload_b
    a = native_compiler.compile_native_semantic_rules(semantic)
    b = native_compiler.compile_native_semantic_rules(poisoned)
    assert tuple(a.pattern_ids) == tuple(b.pattern_ids)
    assert tuple(a.geometry_ids) == tuple(b.geometry_ids)


def test_c1_spec08_semantic_action_layout_is_exact():
    layout = dict(_module().semantic_action_layout())
    for key, value in SEMANTIC_ACTION_LAYOUT.items():
        assert layout[key] == value, key
    high = (
        ((1 << layout["pattern_bits"]) - 1) << layout["pattern_shift"]
        | ((1 << layout["geometry_bits"]) - 1) << layout["geometry_shift"]
        | ((1 << layout["actor_current_bits"]) - 1)
        << layout["actor_current_shift"]
    )
    assert high == (((1 << 28) - 1) << 36)


def test_c1_spec09_native_geometry_capacity_fails_closed():
    _compile_api()
    with pytest.raises(
        native_compiler.NativeUnsupportedRuleError, match=r"(?i)geometr"
    ):
        native_compiler.build_semantic_compile_payload(
            geometry_overflow_semantic()
        )


def test_c1_spec12_legacy_native_surface_remains_present():
    # EXPECTED_GREEN before and after C-1.
    assert hasattr(native_compiler, "compile_native_rules")
    assert hasattr(native_compiler, "NativeCompiledRules")
    mod = _module()
    for name in (
        "compile_rules",
        "pack_position",
        "native_legal_actions",
        "native_perft",
        "native_make_checked",
        "native_fixed_depth_search",
    ):
        assert hasattr(mod, name), name
