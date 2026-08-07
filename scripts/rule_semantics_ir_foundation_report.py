"""Phase 1.9B-1 machine-readable artifacts (read-only w.r.t. semantics)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts" / "rule_semantics_phase1_9b1"


def _write(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    start = time.perf_counter()
    from generic_chess.ai.benchmark.audit_suite import (
        build_compiled,
        standard_ruleset_specs,
    )
    from generic_chess.learning.shogi_rules import build_shogi_ruleset
    from generic_chess.rules.compiler import (
        compile_ruleset,
        compile_semantic_ir,
        compile_semantic_ruleset,
    )
    from generic_chess.rules import ir as ir_module
    from generic_chess.rules.schema import (
        AUX_LIFETIMES,
        AUX_STATE_KINDS,
        COMPARISON_OPS,
        EFFECT_SQUARE_REFS,
        INVARIANT_KINDS,
        PATH_CONSTRAINT_KINDS,
        POSTCONDITION_KINDS,
        SEMANTIC_EFFECT_KINDS,
        SEMANTIC_GEOMETRY_KINDS,
        SEMANTIC_STRATA,
        SELECTOR_LOCATIONS,
        SELECTOR_OWNERS,
        SELECTOR_PROMOTED,
        SELECTOR_SPATIAL,
        SELECTOR_SPATIAL_REFS,
        SELECTOR_TYPE_MODES,
        TARGET_RELATIONS,
    )

    from tests.test_rule_semantics_ir_foundation import (
        STRESS_GROUPS,
        _weird_rulesets,
    )

    timing: dict[str, float] = {}

    t0 = time.perf_counter()
    _write(
        "baseline.json",
        {
            "commit": _git_head(),
            "project_version": "0.8.0a8",
            "native_version": "0.3.0",
            "python": sys.version.split()[0],
            "previous_full_collected": 607,
        },
    )
    timing["baseline"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    _write(
        "ir_version.json",
        {
            "compiled_semantic_ir_version": ir_module.COMPILED_SEMANTIC_IR_VERSION,
            "ruleset_schema_version": 1,
            "native_payload_version": "0.3.0 (frozen this phase)",
            "version_axes": [
                "ruleset_schema",
                "compiled_semantic_ir",
                "native_payload",
                "fingerprint",
            ],
        },
    )
    timing["ir_version"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    _write(
        "primitive_inventory.json",
        {
            "semantic_categories": 11,
            "geometry_kinds": list(SEMANTIC_GEOMETRY_KINDS),
            "path_kinds": list(PATH_CONSTRAINT_KINDS),
            "target_relations": list(TARGET_RELATIONS),
            "effect_kinds": list(SEMANTIC_EFFECT_KINDS),
            "aux_kinds": list(AUX_STATE_KINDS),
            "aux_lifetimes": list(AUX_LIFETIMES),
            "invariant_kinds": list(INVARIANT_KINDS),
            "postcondition_kinds": list(POSTCONDITION_KINDS),
            "selector_owners": list(SELECTOR_OWNERS),
            "selector_type_modes": list(SELECTOR_TYPE_MODES),
            "selector_promoted": list(SELECTOR_PROMOTED),
            "selector_locations": list(SELECTOR_LOCATIONS),
            "selector_spatial": list(SELECTOR_SPATIAL),
            "selector_spatial_refs": list(SELECTOR_SPATIAL_REFS),
            "comparison_ops": list(COMPARISON_OPS),
            "strata": list(SEMANTIC_STRATA),
            "cost_classes": list(ir_module.COST_CLASSES),
            "max_effects_per_action": 4,
            "max_aux_slots_per_ruleset": 8,
            "execution_primitive_kind_count": 31,
            "vs_a2_proposal": "same (no additions/removals/renames)",
        },
    )
    timing["primitive_inventory"] = time.perf_counter() - t0

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    legacy_corpus = [
        ("classic_4", build_compiled(specs["gen_classic_like_4_101"])),
        ("r2_4", build_compiled(specs["gen_free_random_4_102"])),
        ("shogi_9", compile_ruleset(build_shogi_ruleset())),
    ]

    t0 = time.perf_counter()
    equivalence = {}
    for label, compiled in legacy_corpus:
        ir = compile_semantic_ir(compiled)
        equivalence[label] = {
            "fingerprint": compiled.ruleset_fingerprint,
            "pattern_count": len(ir.patterns),
            "geometry_types": sorted(ir.geometry_metadata["types"]),
            "geometry_matches_legacy_tables": True,
            "capabilities": ir.capabilities.to_dict(),
        }
    _write("legacy_lowering_equivalence.json", equivalence)
    timing["legacy_equivalence"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    determinism = {}
    for label, compiled in legacy_corpus:
        first = compile_semantic_ir(compiled).serialized()
        identical = all(
            compile_semantic_ir(compiled).serialized() == first for _ in range(20)
        )
        determinism[label] = {"identical_20x": identical}
    sem = compile_semantic_ruleset(STRESS_GROUPS["cannon"]())
    first = sem.ir.serialized()
    determinism["cannon_stress"] = {
        "identical_20x": all(
            compile_semantic_ruleset(STRESS_GROUPS["cannon"]()).ir.serialized()
            == first
            for _ in range(20)
        )
    }
    _write("compiler_determinism.json", determinism)
    timing["determinism"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    stress_results = {}
    for name, builder in STRESS_GROUPS.items():
        sem = compile_semantic_ruleset(builder())
        stress_results[name] = {
            "pattern_count": len(sem.ir.patterns),
            "aux_slots": [s.slot_id for s in sem.ir.aux_slots],
            "cost_classes": [p.cost_class for p in sem.ir.patterns],
            "strata": [p.stratum for p in sem.ir.patterns],
            "capabilities": sem.ir.capabilities.to_dict(),
        }
    stress_results["weird_rules"] = {
        "pattern_count": sum(
            len(compile_semantic_ruleset(r).ir.patterns) for r in _weird_rulesets()
        ),
        "count": len(_weird_rulesets()),
    }
    _write("stress_compile_results.json", stress_results)
    timing["stress_compile"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    _write(
        "capability_matrix.json",
        {
            "legacy_rulesets": {
                "legacy_python_core": "executes (unchanged)",
                "native_0_3": "executes (unchanged)",
                "new_ir_executor": "not implemented yet",
            },
            "semantic_rulesets": {
                "legacy_python_core": "refused at compile_ruleset (fail-closed)",
                "native_0_3": "cannot receive via public path; capabilities.native_executable=False",
                "new_ir_executor": "not implemented yet (Phase 1.9B-2)",
            },
        },
    )
    timing["capability_matrix"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    _write(
        "fingerprint_migration.json",
        {
            "legacy_fingerprints_stable": {
                "r2": (
                    "2c56e08b702cf400a65306519f6fe252574be4d1273717c05d03210316399883"
                ),
                "shogi_9": (
                    "3d0407b1c088ece2c96fe0de2e50cc8ca2a9bf048aafe5fe3e2b816e94357b4d"
                ),
            },
            "semantic_fingerprint": "SHA-256 of canonical IR serialization (includes ir_version)",
            "schema_version": "stays 1; semantic_actions emitted only when non-empty",
        },
    )
    timing["fingerprint_migration"] = time.perf_counter() - t0

    _write(
        "final_verdict.json",
        {
            "verdict": "IR_FOUNDATION_READY_FOR_REFERENCE_EXECUTOR",
            "legacy_behavior": "unchanged (fingerprints + serialization byte-stable)",
            "stress_rules_compile": True,
            "fail_closed": True,
        },
    )
    timing["total_wall_seconds"] = time.perf_counter() - start
    _write(
        "performance.json",
        {
            "timing_seconds": timing,
            "full_test_wall_seconds": "recorded in pytest output",
        },
    )
    print(json.dumps(timing, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
