"""Frozen helpers for Phase 1.9C-1 specification tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import CompiledGeometry

from rule_semantics_ir_fixtures import STRESS_GROUPS, weird_rulesets


SEMANTIC_ACTION_LAYOUT = {
    "legacy_board_kind": 0,
    "legacy_drop_kind": 1,
    "semantic_board_kind": 2,
    "semantic_drop_kind": 3,
    "to_shift": 0,
    "from_shift": 8,
    "promo_shift": 16,
    "base_shift": 24,
    "kind_shift": 32,
    "pattern_shift": 36,
    "geometry_shift": 44,
    "actor_current_shift": 56,
    "pattern_bits": 8,
    "geometry_bits": 12,
    "actor_current_bits": 8,
    "max_patterns": 256,
    "max_geometries": 4096,
}


def semantic_corpus():
    corpus = [
        (name, compile_semantic_ruleset(builder()))
        for name, builder in STRESS_GROUPS.items()
    ]
    corpus.extend(
        (f"weird_{i}", compile_semantic_ruleset(ruleset))
        for i, ruleset in enumerate(weird_rulesets())
    )
    return tuple(corpus)


def expected_ids(semantic):
    return {
        "type_ids": tuple(sorted(semantic.support.type_metadata)),
        "pattern_ids": tuple(p.pattern_id for p in semantic.ir.patterns),
        "geometry_ids": tuple(sorted(semantic.ir.geometry)),
        "zone_ids": tuple(sorted(semantic.ir.zones)),
    }


def geometry_overflow_semantic():
    semantic = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    geometry = dict(semantic.ir.geometry)
    i = 0
    while len(geometry) <= SEMANTIC_ACTION_LAYOUT["max_geometries"]:
        gid = f"overflow_g_{i:04d}"
        if gid not in geometry:
            geometry[gid] = CompiledGeometry(geometry_id=gid, kind="drop")
        i += 1
    return replace(semantic, ir=replace(semantic.ir, geometry=geometry))
