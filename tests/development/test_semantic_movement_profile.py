from dataclasses import replace
from types import SimpleNamespace

import pytest

from generic_chess.ai.evaluation.analyzer import movement_signature, profile_movement_atoms
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.unfamiliar_search import profile_input_scope


def test_semantic_shogi_profile_preserves_all_legacy_geometry():
    ruleset = build_standard_shogi_ruleset()
    compiled = compile_ruleset_for_execution(ruleset)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    for piece_type in ruleset.piece_types:
        if piece_type.is_anchor:
            continue
        projected = profile_movement_atoms(compiled, piece_type.type_id)
        assert movement_signature(projected) == movement_signature(piece_type.movement_atoms)
        assert profile.piece_profiles[piece_type.type_id].movement_signature == movement_signature(
            piece_type.movement_atoms
        )


def test_semantic_western_non_pawn_profiles_preserve_legacy_geometry():
    ruleset = build_western_chess_ruleset()
    compiled = compile_ruleset_for_execution(ruleset)
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    for piece_type in ruleset.piece_types:
        if piece_type.is_anchor or piece_type.type_id == "P":
            continue
        projected = profile_movement_atoms(compiled, piece_type.type_id)
        signature = movement_signature(piece_type.movement_atoms)
        assert movement_signature(projected) == signature
        assert profile.piece_profiles[piece_type.type_id].movement_signature == signature


def test_semantic_pawn_projection_is_union_of_unique_direct_geometries():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    atoms = profile_movement_atoms(compiled, "P")
    # One unguarded forward ray and two capture leaps. The guarded double step,
    # en-passant state and drop geometry are outside this static projection.
    assert len(atoms) == 3
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    assert profile.piece_profiles["P"].movement_signature == movement_signature(atoms)
    assert profile.board_value_by_type["P"] > 1


def test_guarded_xiangqi_semantic_moves_keep_existing_legacy_profile_geometry():
    ruleset = build_xiangqi_diagnostic_ruleset()
    compiled = compile_semantic_ruleset(ruleset)
    for type_id in ("E", "H"):
        legacy = next(t for t in ruleset.piece_types if t.type_id == type_id)
        projected = profile_movement_atoms(compiled, type_id)
        assert movement_signature(projected) == movement_signature(legacy.movement_atoms)



def test_semantic_only_guarded_movement_fails_visibly_without_legacy_fallback():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    patterns = []
    for pattern in compiled.ir.patterns:
        if "P" in pattern.type_ids and any(effect.kind == "move" for effect in pattern.effects):
            guarded = next(p for p in compiled.ir.patterns
                           if "P" in p.type_ids and p.guards)
            pattern = replace(pattern, guards=guarded.guards)
        patterns.append(pattern)
    fixture = SimpleNamespace(
        ir=SimpleNamespace(patterns=tuple(patterns), geometry=compiled.ir.geometry),
        _legacy_compiled=compiled._legacy_compiled,
        board_size=8,
    )
    with pytest.raises(ValueError, match="semantic-only movement P"):
        profile_movement_atoms(fixture, "P")
    scope = profile_input_scope(fixture)
    assert [row["type_id"] for row in scope["unsupported_semantic_profile_types"]] == ["P"]
