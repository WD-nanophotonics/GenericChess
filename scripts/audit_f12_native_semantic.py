"""F12 audit-only evidence generator.

This script measures and records the existing native semantic surface.  It
does not change production modules, select a migration, or enable a native
search backend.
"""

from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f12_native_semantic_audit"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from phase19c1_native_semantic_fixtures import semantic_corpus  # noqa: E402

import generic_chess.native as native  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402
from generic_chess.learning.round5_corrective_r1 import SearchSemanticCompiled  # noqa: E402
from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset  # noqa: E402
from generic_chess.native.compiler import (  # noqa: E402
    NativeUnsupportedRuleError,
    compile_native_rules,
    compile_native_semantic_rules,
)
from generic_chess.native.semantic import (  # noqa: E402
    candidate_actions,
    fixed_depth_search,
    guarded_actions,
    pack_action,
    pack_position,
    position_key,
    snapshot,
    terminal_status,
)
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402
from generic_chess.core.transition import initial_state  # noqa: E402


FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
REPORTS = {}


def _json(name: str, value) -> None:
    # The desktop workspace policy requires file edits to go through
    # apply_patch.  Keep the generator side-effect-free and emit a selected
    # report for archival by the audit workflow.
    REPORTS[name] = value


def _error(exc: BaseException) -> dict:
    return {"type": type(exc).__name__, "message": str(exc)}


def _semantic_position(semantic):
    rules = compile_native_semantic_rules(semantic)
    python_pos = SemanticEngine(semantic)._initial_position()
    ids = {type_id: i for i, type_id in enumerate(rules.type_ids)}
    board = [
        None
        if piece is None
        else [ids[piece.base_type_id], ids[piece.current_type_id], piece.owner, int(piece.promoted)]
        for piece in python_pos.board
    ]
    base = pack_position(
        rules,
        {
            "side": python_pos.side_to_move,
            "ply": 0,
            "board": board,
            "hands": [[0] * len(ids), [0] * len(ids)],
            "aux_state": python_pos.aux_state,
        },
    )
    digest = position_key(rules, base)
    words = tuple(int(digest[i : i + 16], 16) for i in range(0, 64, 16))
    packed = pack_position(
        rules,
        {
            "side": python_pos.side_to_move,
            "ply": 0,
            "board": board,
            "hands": [[0] * len(ids), [0] * len(ids)],
            "aux_state": python_pos.aux_state,
            "history": (words,),
        },
    )
    return rules, python_pos, packed


def _surface() -> None:
    module = native._module()
    names = (
        "semantic_pack_position", "semantic_position_snapshot", "semantic_position_key",
        "semantic_action_pack", "semantic_action_unpack", "semantic_candidate_actions",
        "semantic_guarded_actions", "semantic_make_checked", "semantic_terminal",
        "semantic_probe_search", "semantic_fixed_depth_search", "semantic_legal_actions",
        "semantic_make", "semantic_perft", "semantic_search", "native_attack_map",
        "native_legal_actions", "native_make_checked", "native_fixed_depth_search",
    )
    _json(
        "native_surface_inventory.json",
        {
            "python_module": "generic_chess.native.semantic",
            "python_entry_points": [
                "pack_position", "snapshot", "position_key", "pack_action", "unpack_action",
                "candidate_actions", "guarded_actions", "history_occurrences", "make_checked",
                "make_unmake_roundtrip", "candidate_perft", "terminal_status", "probe_search",
                "fixed_depth_search",
            ],
            "extension_entry_points": {name: hasattr(module, name) for name in names},
            "internal_runtime_symbols": {
                "gc_semantic_runtime_make_checked": "generic_chess/_native/native_semantic_runtime.c:323",
                "gc_semantic_runtime_in_check": "generic_chess/_native/native_semantic_runtime.c:327",
                "semantic_attacked_by": "generic_chess/_native/native_semantic_runtime.c:179",
                "gc_semantic_terminal_status": "generic_chess/_native/native_module.c:2756",
                "gc_semantic_probe_search": "generic_chess/_native/native_module.c:2931",
            },
            "native_capabilities": native.native_capabilities(),
        },
    )


def _standard_shogi() -> None:
    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    result = {
        "ruleset_fingerprint": semantic.ruleset_fingerprint,
        "fingerprint_matches_certified": semantic.ruleset_fingerprint == FINGERPRINT,
        "ir_capabilities": asdict(semantic.ir.capabilities),
        "counts": {
            "types": len(semantic.support.type_metadata),
            "patterns": len(semantic.ir.patterns),
            "geometries": len(semantic.ir.geometry),
            "aux_slots": len(semantic.ir.aux_slots),
            "max_ply": semantic.support.max_ply,
            "repetition_limit": semantic.support.repetition_limit,
        },
        "postconditions": [
            {
                "pattern_id": pattern.pattern_id,
                "items": [asdict(post) for post in pattern.postconditions],
            }
            for pattern in semantic.ir.patterns
            if pattern.postconditions
        ],
    }
    try:
        compiled = SearchSemanticCompiled(
            ir=semantic.ir,
            _legacy_compiled=semantic._legacy_compiled,
            support=semantic.support,
        )
        native_rules = compile_native_semantic_rules(compiled)
        result["native_executable"] = native_rules.native_executable
        result["native_report"] = asdict(native_rules.report)
    except NativeUnsupportedRuleError as exc:
        result["native_executable"] = False
        result["compile_error"] = _error(exc)
        result["blocking_boundary"] = "action_delivers_check postcondition is not in native schema native-0.5.0"
    _json("standard_shogi_compile.json", result)


def _corpus_runtime() -> None:
    rows = []
    for name, semantic in semantic_corpus():
        row = {
            "name": name,
            "fingerprint": semantic.ruleset_fingerprint,
            "ir_capabilities": asdict(semantic.ir.capabilities),
        }
        try:
            rules, python_pos, position = _semantic_position(semantic)
            candidates = candidate_actions(rules, position)
            guarded = guarded_actions(rules, position)
            row.update(
                {
                    "native_executable": rules.native_executable,
                    "report": asdict(rules.report),
                    "candidate_count": len(candidates),
                    "guarded_count": len(guarded),
                    "terminal": terminal_status(rules, position),
                    "fixed_depth_1": fixed_depth_search(rules, position, 1),
                    "snapshot_roundtrip": snapshot(rules, position)["side"] == python_pos.side_to_move,
                    "runtime_status": "PASS",
                }
            )
        except Exception as exc:
            row["runtime_status"] = "FAIL"
            row["error"] = _error(exc)
        rows.append(row)
    _json("existing_native_differential.json", {
        "corpus": rows,
        "test_sources": [
            "tests/test_native_semantic_position.py",
            "tests/test_native_semantic_stress_differential.py",
            "tests/test_native_semantic_randomized_closure.py",
            "tests/test_native_semantic_probe_search.py",
        ],
    })


def _legacy_attack_comparison() -> None:
    rows = []
    module = native._module()
    for name, semantic in semantic_corpus():
        row = {"name": name, "status": "NOT_RUN_UNSUPPORTED"}
        try:
            legacy = semantic._legacy_compiled
            native_rules = compile_native_rules(legacy)
            state = initial_state(legacy)
            from generic_chess.native.adapter import pack_native_position

            packed = pack_native_position(legacy, native_rules, state)
            engine = SemanticEngine(semantic)
            diffs = []
            for owner in (0, 1):
                native_map = set(module.native_attack_map(native_rules.capsule, packed, owner))
                semantic_map = {
                    square
                    for square in range(semantic.support.board_size ** 2)
                    if engine.is_square_attacked(state.position, square, owner)
                }
                if native_map != semantic_map:
                    diffs.append({
                        "owner": owner,
                        "native_only": sorted(native_map - semantic_map),
                        "semantic_only": sorted(semantic_map - native_map),
                    })
            row.update({"status": "MATCH" if not diffs else "DIFFER", "diffs": diffs})
        except Exception as exc:
            row["error"] = _error(exc)
        rows.append(row)
    shogi = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    shogi_legacy_error = None
    try:
        compile_native_rules(shogi._legacy_compiled)
    except Exception as exc:
        shogi_legacy_error = _error(exc)
    _json("legacy_vs_semantic_attack.json", {
        "comparison": rows,
        "standard_shogi": {
            "status": "NOT_RUN_UNSUPPORTED",
            "reason": "Standard Shogi legacy native compilation is rejected before a common native attack map exists.",
            "error": shogi_legacy_error,
        },
        "interpretation": "native_attack_map is a legacy movement-atom surface; no public semantic attack/check map exists.",
    })


def _bench(fn, *, warmup=30, loops=200) -> dict:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(7):
        start = time.perf_counter_ns()
        for _ in range(loops):
            fn()
        samples.append((time.perf_counter_ns() - start) / loops / 1000.0)
    return {
        "median_us": statistics.median(samples),
        "min_us": min(samples),
        "samples_us": samples,
        "loops_per_sample": loops,
    }


def _microbench() -> None:
    from generic_chess.core.semantic_executor import SemanticEngine

    semantic = compile_semantic_ruleset(__import__("rule_semantics_ir_fixtures").castling_ruleset())
    rules, python_pos, position = _semantic_position(semantic)
    engine = SemanticEngine(semantic)
    action = min(guarded_actions(rules, position))
    fields = {"to": 7, "from": 2, "promotion": 255, "base": 0, "kind": 2, "pattern": 0, "geometry": 0, "actor_current": 0}
    rows = {
        "python_semantic_attack_query": _bench(lambda: engine.is_square_attacked(python_pos, 0, 1), loops=300),
        "native_pack_position": _bench(lambda: _semantic_position(semantic), loops=50),
        "native_snapshot": _bench(lambda: snapshot(rules, position), loops=300),
        "native_position_key": _bench(lambda: position_key(rules, position), loops=300),
        "native_action_pack": _bench(lambda: pack_action(fields), loops=1000),
        "native_candidate_actions": _bench(lambda: candidate_actions(rules, position), loops=100),
        "native_guarded_actions": _bench(lambda: guarded_actions(rules, position), loops=100),
        "native_terminal": _bench(lambda: terminal_status(rules, position), loops=50),
        "native_fixed_depth_1": _bench(lambda: fixed_depth_search(rules, position, 1), loops=20),
        "native_make_checked": _bench(lambda: native._module().semantic_make_checked(rules.capsule, position, action), loops=100),
    }
    _json("boundary_microbench.json", {
        "ruleset": "castling semantic fixture",
        "fingerprint": semantic.ruleset_fingerprint,
        "position": {"board_squares": len(python_pos.board), "candidate_count": len(candidate_actions(rules, position)), "guarded_count": len(guarded_actions(rules, position))},
        "measurements": rows,
        "method": "process-local perf_counter_ns; warmup 30; seven samples; median reported; audit-only",
    })


def _matrices() -> None:
    _json("native_capability_matrix.json", {
        "classifications": [
            "SUPPORTED_AND_DIFFERENTIAL_TESTED", "IMPLEMENTED_BUT_NOT_CERTIFIED",
            "LOWERED_BUT_NOT_EXECUTED", "FAIL_CLOSED_UNSUPPORTED", "NOT_APPLICABLE",
        ],
        "rows": [
            {"surface": "semantic payload / C-owned rules capsule", "classification": "SUPPORTED_AND_DIFFERENTIAL_TESTED", "evidence": ["tests/specification/test_phase19c1_native_semantic_payload_contract.py", "tests/specification/test_phase19c2_native_semantic_runtime_contract.py"]},
            {"surface": "semantic position identity, history and exact action packing", "classification": "SUPPORTED_AND_DIFFERENTIAL_TESTED", "evidence": ["tests/test_native_semantic_position.py"]},
            {"surface": "semantic candidate / guarded action runtime", "classification": "SUPPORTED_AND_DIFFERENTIAL_TESTED", "evidence": ["tests/test_native_semantic_stress_differential.py", "tests/test_native_semantic_randomized_closure.py"]},
            {"surface": "semantic make_checked / terminal / probe and fixed-depth search", "classification": "SUPPORTED_AND_DIFFERENTIAL_TESTED", "evidence": ["tests/test_native_semantic_probe_search.py", "tests/test_native_semantic_position.py"]},
            {"surface": "internal semantic attacked_by / in_check", "classification": "IMPLEMENTED_BUT_NOT_CERTIFIED", "evidence": ["generic_chess/_native/native_semantic_runtime.c:179", "generic_chess/_native/native_semantic_runtime.c:327"]},
            {"surface": "public semantic attack/check entry point", "classification": "NOT_APPLICABLE", "evidence": ["generic_chess/_native/native_module.c:3151-3168"]},
            {"surface": "Standard Shogi semantic executable payload", "classification": "FAIL_CLOSED_UNSUPPORTED", "evidence": ["artifacts/f12_native_semantic_audit/standard_shogi_compile.json"]},
            {"surface": "production semantic native search backend", "classification": "NOT_APPLICABLE", "evidence": ["native_capabilities.production_search_backend=false", "native_capabilities.semantic_fixed_depth_search=true"]},
        ],
    })
    _json("semantic_gap_matrix.json", {
        "ruleset_fingerprint": FINGERPRINT,
        "rows": [
            {"gap": "action_delivers_check postcondition lowering", "status": "FAIL_CLOSED_UNSUPPORTED", "impact": "blocks Standard Shogi native executable capsule", "evidence": "standard_shogi_compile.json"},
            {"gap": "public semantic is_square_attacked / in_check API", "status": "IMPLEMENTED_BUT_NOT_CERTIFIED", "impact": "internal check logic is reachable only through terminal/make paths", "evidence": "native_surface_inventory.json"},
            {"gap": "dynamic Standard Shogi evaluator and production search integration", "status": "NOT_APPLICABLE", "impact": "fixed-depth semantic probe cannot be promoted to production", "evidence": "native_capabilities.production_dynamic_evaluator=false"},
            {"gap": "legacy native attack equivalence for Standard Shogi", "status": "FAIL_CLOSED_UNSUPPORTED", "impact": "legacy compiler rejects the Standard Shogi history policy before comparison", "evidence": "legacy_vs_semantic_attack.json"},
        ],
    })
    _json("python_attack_contract.json", {
        "authority": "SemanticEngine.is_square_attacked / in_check",
        "requirements": [
            "owner/current-type source index _sources_by_owner_type",
            "target_enemy only",
            "type and geometry compatibility, including atom_source",
            "owner-relative geometry",
            "path predicates",
            "state guards and slot guards",
            "S4-bearing patterns project only S0/S1 capture eligibility; no S3/S4 recursion",
            "in_check finds the side's anchor and asks the opponent attack query",
        ],
        "evidence": [
            "generic_chess/core/semantic_executor.py:96",
            "generic_chess/core/semantic_executor.py:580-637",
            "generic_chess/core/semantic_executor.py:801-836",
            "tests/specification/test_phase19b2_review_r2.py:406-552",
            "tests/test_phase19b3_s4_executor.py:96-145",
        ],
    })
    _json("attack_slice_requirements.json", {
        "required_before_native_attack_check_slice": [
            "direct public native semantic attack/check call with target/owner contract",
            "Standard Shogi lowering including action_delivers_check or an explicit semantics-preserving boundary split",
            "differential corpus over rays, screens, type/geometry binding, guards, slots and S4 projection",
            "root position ownership and cancellation/checkpoint behavior",
            "failure-closed fallback to Python SemanticEngine",
        ],
        "current_decision": "not ready; capability gap closure precedes attack/check migration",
    })
    _json("position_ownership_matrix.json", {
        "rows": [
            {"option": "A", "owner": "Python Position", "crossing": "pack/copy on every native operation", "rollback": "Python authoritative", "history": "Python unless full exact history copied", "risk": "low correctness / low speedup"},
            {"option": "B", "owner": "Python root + mirrored Native frame", "crossing": "one root pack; native child frames", "rollback": "native child lifecycle plus Python root", "history": "native only after exact replay", "risk": "medium"},
            {"option": "C", "owner": "Native search path; Python shadow", "crossing": "one root pack + sampled/checkpoint shadow", "rollback": "native trusted make/unmake", "history": "native exact history required", "risk": "high"},
            {"option": "D", "owner": "Native semantic backend", "crossing": "production backend boundary", "rollback": "native", "history": "native complete semantic authority", "risk": "very high; not currently executable for Standard Shogi"},
        ],
        "current_authority": "Python semantic Position and SemanticEngine remain authoritative",
    })
    _json("search_readiness_matrix.json", {
        "semantic_runtime": {
            "candidate_generation": True,
            "guarded_make": True,
            "terminal_and_repetition": True,
            "fixed_depth_probe": True,
            "native_tt": False,
            "native_qsearch": False,
            "dynamic_evaluator": False,
            "node_or_time_budget": False,
            "native_cancellation": False,
            "production_backend": False,
        },
        "decision": "not production-search-ready",
        "evidence": ["generic_chess/_native/native_module.c:2931-3050", "native_capabilities.json equivalent in native_surface_inventory.json"],
    })
    _json("speedup_ceiling.json", {
        "model": [
            {"boundary": "A", "native_fraction_of_hot_path": "pack/key only", "ceiling": "low; crossing overhead dominates"},
            {"boundary": "B", "native_fraction_of_hot_path": "position/make/terminal", "ceiling": "medium; attack/check and semantic gaps remain"},
            {"boundary": "C", "native_fraction_of_hot_path": "search subtree", "ceiling": "high in principle", "constraint": "requires complete Standard Shogi semantic execution and interruptibility"},
            {"boundary": "D", "native_fraction_of_hot_path": "full production search", "ceiling": "highest in principle", "constraint": "not available under current capability matrix"},
        ],
        "F11_context": {"python_local_runtime_headroom": "LIMITED", "hotspot": "semantic attack/check and downstream legal/terminal paths"},
    })
    _json("future_boundary_candidates.json", {
        "candidates": [
            {"name": "NATIVE_ATTACK_CHECK_SLICE", "status": "deferred", "reason": "requires public API, Standard Shogi lowering and differential certification"},
            {"name": "NATIVE_SEMANTIC_POSITION_FRAME", "status": "deferred", "reason": "ownership/history boundary is not yet safe for Standard Shogi"},
            {"name": "NATIVE_SEMANTIC_SEARCH_PATH", "status": "deferred", "reason": "fixed-depth probe lacks production budgets, TT/qsearch/evaluator and Standard Shogi executable payload"},
            {"name": "NATIVE_CAPABILITY_GAP_CLOSURE", "status": "selected", "reason": "action_delivers_check blocks the certified target before any migration boundary is safe"},
        ],
    })
    _json("selected_future_boundary.json", {
        "selected": "NATIVE_CAPABILITY_GAP_CLOSURE",
        "scope": "H12A audit outcome only; no production migration in F12",
        "next_required_work": [
            "design semantics-preserving lowering for action_delivers_check",
            "re-run Standard Shogi native compile and full differential corpus",
            "only then re-evaluate attack/check slice boundary",
        ],
    })
    _json("interruptibility_analysis.json", {
        "current_python_contract": "SemanticEngine accepts Checkpoint and checks it through attack, guards, candidate and reply-probe loops",
        "current_semantic_native_contract": "no Checkpoint, cancellation token, node budget or monotonic deadline in semantic probe entry point",
        "consequence": "native semantic search cannot replace the interruptible Python production search path",
        "evidence": ["generic_chess/core/semantic_executor.py:580-637", "generic_chess/_native/native_module.c:2931-3050"],
    })
    _json("failure_model.json", {
        "fail_closed_cases": [
            "native extension unavailable",
            "ruleset fingerprint mismatch",
            "unsupported semantic enum/postcondition",
            "inexact or truncated history for terminal/search",
            "malformed packed action or position",
        ],
        "fallback_authority": "Python semantic executor",
        "production_migration": "not performed",
    })


def main() -> int:
    _surface()
    _standard_shogi()
    _corpus_runtime()
    _legacy_attack_comparison()
    _microbench()
    _matrices()
    _json("environment.json", {
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "native_available": native.native_available(),
        "native_version": native.native_version(),
    })
    emit = next((arg for arg in sys.argv[1:] if arg.startswith("--emit=")), None)
    if emit is not None:
        name = emit.split("=", 1)[1]
        if not name.endswith(".json"):
            name += ".json"
        print(json.dumps(REPORTS[name], ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps({"reports": sorted(REPORTS), "standard_shogi": REPORTS["standard_shogi_compile.json"], "native": native.native_capabilities()}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
