"""Successor contract for the ADR-018 Native semantic runtime publication."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generic_chess.native as native
from generic_chess.native import compiler as native_compiler
from generic_chess.rules.compiler import compile_semantic_ruleset

from phase19c1_native_semantic_fixtures import semantic_corpus
from rule_semantics_ir_fixtures import STRESS_GROUPS


def _module():
    assert native.native_available(), "native extension must be built"
    return native._module()


def test_c2_successor_version_and_semantic_capabilities_are_explicit():
    assert native.native_version() == "0.5.0"
    assert native_compiler.NATIVE_SCHEMA_VERSION == "native-0.5.0"
    caps = native.native_capabilities()
    assert caps["native_schema"] == "native-0.5.0"
    assert caps["semantic_position_state"] is True
    assert caps["semantic_s0_s4_executor"] is True
    assert caps["semantic_terminal"] is True
    assert caps["semantic_fixed_depth_search"] is True
    assert caps["semantic_material_evaluator"] is True
    assert caps["production_dynamic_evaluator"] is False
    assert caps["production_search_backend"] is False


def test_c2_public_entry_points_and_c1_surface_boundary():
    mod = _module()
    assert hasattr(mod, "semantic_terminal")
    assert hasattr(mod, "semantic_fixed_depth_search")
    for name in ("semantic_legal_actions", "semantic_make", "semantic_perft", "semantic_search"):
        assert not hasattr(mod, name), name


def test_c2_per_ruleset_gate_and_structural_fail_closed():
    for name, semantic in semantic_corpus():
        compiled = native_compiler.compile_native_semantic_rules(semantic)
        assert compiled.report.native_schema_version == "native-0.5.0", name
        assert compiled.report.native_executable is True, name
        assert compiled.native_executable is True, name

    semantic = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    payload, report = native_compiler.build_semantic_compile_payload(semantic)
    malformed = dict(payload)
    malformed.pop("patterns")
    assert native_compiler._native_payload_is_executable(malformed, report) is False
