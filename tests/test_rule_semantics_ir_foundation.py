"""Phase 1.9B-1 foundation tests, updated for IR v2 (1.9B-1.5).

The B-1 stress fixtures exercised placeholder semantics and were replaced by
the stronger static-closure tests in ``test_rule_semantics_ir_hardening.py``;
the legacy-preservation, determinism, fail-closed and payload tests below
remain and now run against the v2 IR.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from generic_chess.rules.compiler import (
    compile_ruleset,
    compile_semantic_ir,
    compile_semantic_ruleset,
)
from generic_chess.rules.ir import COMPILED_SEMANTIC_IR_VERSION
from generic_chess.rules.schema import RuleSet, ruleset_from_dict, ruleset_to_dict

from rule_semantics_ir_fixtures import STRESS_GROUPS, weird_rulesets


ROOT = Path(__file__).resolve().parent.parent


def _legacy_corpus():
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.learning.shogi_rules import build_shogi_ruleset
    from native_test_helpers import generated_compiled

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    return [
        build_compiled(specs["gen_classic_like_4_101"]),
        build_compiled(specs["gen_free_random_4_102"]),  # R2
        compile_ruleset(build_shogi_ruleset()),
        generated_compiled(size=6, seed=11),
    ]


def compiled_rule_to_ruleset(compiled):
    n = compiled.board_size
    board = compiled.initial_position.board
    rows = tuple(tuple(board[r * n : (r + 1) * n]) for r in range(n))
    return RuleSet(
        board_size=n,
        piece_types=compiled.piece_types,
        initial_position=rows,
        drop_allowed=compiled.drop_allowed,
        promotion_allowed=compiled.promotion_allowed,
        promotion_forced=compiled.promotion_forced,
        repetition_limit=compiled.repetition_limit,
        max_ply=compiled.max_ply,
        stalemate_result=compiled.stalemate_result,
    )


def test_legacy_fingerprints_stable():
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.learning.shogi_rules import build_shogi_ruleset

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    r2 = build_compiled(specs["gen_free_random_4_102"])
    assert r2.ruleset_fingerprint == (
        "2c56e08b702cf400a65306519f6fe252574be4d1273717c05d03210316399883"
    )
    shogi = compile_ruleset(build_shogi_ruleset())
    assert shogi.ruleset_fingerprint == (
        "3d0407b1c088ece2c96fe0de2e50cc8ca2a9bf048aafe5fe3e2b816e94357b4d"
    )


def test_legacy_serialization_has_no_new_keys():
    compiled = _legacy_corpus()[0]
    ruleset = compiled_rule_to_ruleset(compiled)
    data = ruleset_to_dict(ruleset)
    assert "semantic_actions" not in data
    assert "semantic_dsl_version" not in data
    assert set(data) == {
        "schema_version",
        "board_size",
        "piece_types",
        "initial_position",
        "drop_allowed",
        "promotion_allowed",
        "promotion_forced",
        "repetition_limit",
        "max_ply",
        "stalemate_result",
        "metadata",
    }


def test_semantic_actions_serialization_roundtrip():
    ruleset = STRESS_GROUPS["cannon"]()
    data = ruleset_to_dict(ruleset)
    assert data["semantic_dsl_version"] == 2
    restored = ruleset_from_dict(data)
    assert ruleset_to_dict(restored) == data


def test_legacy_lowering_ir_v2_geometry_equivalence():
    from generic_chess.core.movement import RayAtom
    from generic_chess.rules.ir import geometry_candidates

    for compiled in _legacy_corpus():
        ir = compile_semantic_ir(compiled)
        assert ir.ir_version == COMPILED_SEMANTIC_IR_VERSION
        assert ir.capabilities.legacy_core_executable is True
        assert ir.capabilities.native_executable is True
        n = compiled.board_size
        for tid, pt in compiled.types_by_id.items():
            if pt.is_anchor:
                continue
            for atom_index, atom in enumerate(pt.movement_atoms):
                gid = next(
                    g.geometry_id
                    for g in ir.geometry.values()
                    if g.atom_source == (tid, atom_index)
                )
                geo = ir.geometry[gid]
                assert geo.kind == ("ray" if isinstance(atom, RayAtom) else "leap")
                for owner in ("0", "1"):
                    for idx in range(n * n):
                        candidates = geometry_candidates(geo, owner, idx)
                        legacy_leaps = compiled.leap_targets[tid][int(owner)][idx][atom_index]
                        legacy_rays = compiled.ray_paths[tid][int(owner)][idx][atom_index]
                        expected = [
                            (sq.rank * n + sq.file, ())
                            for sq in legacy_leaps
                        ] + [
                            (
                                sq.rank * n + sq.file,
                                tuple(s.rank * n + s.file for s in legacy_rays[:step]),
                            )
                            for step, sq in enumerate(legacy_rays)
                        ]
                        assert candidates == tuple(expected)


def test_compiler_determinism():
    for compiled in _legacy_corpus():
        first = compile_semantic_ir(compiled)
        for _ in range(10):
            again = compile_semantic_ir(compiled)
            assert again.serialized() == first.serialized()
            assert again.fingerprint() == first.fingerprint()
    sem = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    first = sem.ir.serialized()
    for _ in range(10):
        assert compile_semantic_ruleset(STRESS_GROUPS["cannon"]()).ir.serialized() == first


def test_stress_rules_compile_and_fail_closed():
    for name, builder in STRESS_GROUPS.items():
        sem = compile_semantic_ruleset(builder())
        assert sem.ir.patterns, name
        assert sem.ir.capabilities.legacy_core_executable is False
        assert sem.ir.capabilities.native_executable is False
        assert sem.ir.capabilities.new_ir_core_executable is (name != "uchifuzume")
        with pytest.raises(Exception) as exc:
            compile_ruleset(builder())
        assert "SEMANTIC_ACTIONS_NOT_LEGACY_EXECUTABLE" in str(exc.value)


def test_weird_rules_compile():
    for ruleset in weird_rulesets():
        sem = compile_semantic_ruleset(ruleset)
        assert sem.ir.patterns
        assert sem.ir.capabilities.legacy_core_executable is False


def test_no_game_specific_production_semantics():
    forbidden = (
        "cannon",
        "castle",
        "castl",
        "en_passant",
        "nifu",
        "uchifuzume",
        "pawn",
        "rook",
        "bishop",
        "shogi",
        "chess",
        "xiangqi",
    )
    from generic_chess.rules import ir as ir_module
    from generic_chess.rules import schema as schema_module

    for module in (ir_module, schema_module):
        for attr in dir(module):
            if not attr.isupper():
                continue
            value = getattr(module, attr)
            if isinstance(value, (tuple, list)):
                for item in value:
                    if isinstance(item, str) and any(t in item.lower() for t in forbidden):
                        raise AssertionError(
                            f"{module.__name__}.{attr} contains forbidden token {item}"
                        )


def test_production_does_not_import_experiments():
    for path in (ROOT / "generic_chess").rglob("*.py"):
        source = path.read_text(encoding="utf-8", errors="ignore")
        assert "rule_ir_design_prototype" not in source


def test_ir_types_frozen_and_deterministic():
    import dataclasses

    from generic_chess.rules.ir import CompiledMovePattern

    assert CompiledMovePattern.__dataclass_params__.frozen is True
    compiled = compile_semantic_ir(_legacy_corpus()[0])
    assert compiled.serialized() == compiled.serialized()
    assert compiled.fingerprint() == compiled.fingerprint()


def test_geometry_payload_size_bounded():
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.learning.shogi_rules import build_shogi_ruleset
    from generic_chess.rules.serialization import serialize_ruleset
    from native_test_helpers import generated_compiled

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    corpus = [
        ("8x8_classic", build_compiled(specs["gen_classic_like_8_301"])),
        ("9x9_shogi", compile_ruleset(build_shogi_ruleset())),
        ("16x16_gen", generated_compiled(size=16, seed=5)),
    ]
    for label, compiled in corpus:
        legacy_serialized = len(serialize_ruleset(compiled_rule_to_ruleset(compiled)))
        ir_serialized = len(compile_semantic_ir(compiled).serialized())
        ratio = ir_serialized / legacy_serialized
        # Bound re-audited in Phase 1.9B-2: anchor movement is a frozen
        # specification requirement; 16x16 measures 12.04x.
        assert ratio < 13.0, (label, ratio)
