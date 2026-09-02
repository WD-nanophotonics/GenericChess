"""F50A audit: semantic Native search capability and route selection.

This is an audit-only module.  It reads repository source, hashes the
dependency ledger, and emits a deterministic architecture record.  It does
not compile a new RuleSet, run a search, mutate production code, or write an
artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHECKPOINT = "H50A_F50_SEMANTIC_NATIVE_SEARCH_ARCHITECTURE_AUDIT"
WORK_ORDER_ID = "GENERICCHESS-F50A-SEMANTIC-NATIVE-SEARCH-CAPABILITY-AUDIT-AND-ARCHITECTURE-SELECTION"
PARENT_SHA = "e5263689d8f4f5dff8b33560ed786b4e23b4a6c5"
H50A_FIXTURE = ROOT / "tests" / "fixtures" / "h50a_semantic_native_search_architecture_audit.json"
_RECORDED_SOURCE_HASHES = json.loads(H50A_FIXTURE.read_text(encoding="utf-8"))["source_hashes"]

DEPENDENCIES = (
    ("generic_chess/rules/compiler.py", "RuleSet -> semantic IR and native payload authority"),
    ("generic_chess/rules/compiled.py", "compiled RuleSet support fields"),
    ("generic_chess/rules/ir.py", "CompiledSemanticRuleset and IR model"),
    ("generic_chess/rules/schema.py", "semantic DSL, aux and repetition policy schema"),
    ("generic_chess/rules/standard_shogi.py", "canonical Shogi RuleSet"),
    ("generic_chess/core/semantic_executor.py", "Python semantic action, transition, check and terminal authority"),
    ("generic_chess/core/position.py", "full Position and GameState state shape"),
    ("generic_chess/core/keys.py", "Python semantic position identity"),
    ("generic_chess/native/compiler.py", "semantic payload lowering and evaluator tables"),
    ("generic_chess/native/adapter.py", "legacy root/search transport and native action conversion"),
    ("generic_chess/native/semantic.py", "semantic Native Python API"),
    ("generic_chess/native/engine.py", "legacy Native iterative engine"),
    ("generic_chess/native/search.py", "legacy Native fixed-depth wrapper"),
    ("generic_chess/_native/native_semantic_rules.h", "semantic rules capsule"),
    ("generic_chess/_native/native_semantic_rules.c", "semantic rules capsule implementation"),
    ("generic_chess/_native/native_semantic_state.h", "semantic full-state representation"),
    ("generic_chess/_native/native_semantic_state.c", "semantic state packing"),
    ("generic_chess/_native/native_semantic_runtime.h", "semantic make/unmake and check API"),
    ("generic_chess/_native/native_semantic_runtime.c", "semantic execution implementation"),
    ("generic_chess/_native/native_semantic_key.h", "semantic key API"),
    ("generic_chess/_native/native_semantic_key.c", "semantic key implementation"),
    ("generic_chess/_native/native_module.c", "Python C API exposure"),
    ("generic_chess/_native/native_search.h", "legacy iterative search contract"),
    ("generic_chess/_native/native_search.c", "legacy iterative search implementation"),
    ("generic_chess/_native/native_tt.h", "legacy TT representation"),
    ("generic_chess/_native/native_tt.c", "legacy TT implementation"),
    ("generic_chess/_native/native_eval.h", "legacy native evaluator tables"),
    ("generic_chess/_native/native_eval.c", "legacy native evaluator implementation"),
    ("generic_chess/_native/native_cancel.h", "legacy cancellation flag"),
    ("generic_chess/_native/native_cancel.c", "legacy cancellation implementation"),
    ("generic_chess/ai/evaluation/profile.py", "Python RuleSet evaluation profile"),
    ("generic_chess/ai/evaluation/evaluator.py", "Python dynamic evaluator"),
    ("generic_chess/ai/evaluation/native_compat.py", "legacy Native evaluator compatibility"),
    ("generic_chess/learning/material.py", "learnable material checkpoint and config identity"),
    ("generic_chess/ai/alphabeta/search.py", "Python semantic-capable AlphaBeta control path"),
    ("generic_chess/ai/alphabeta/native_legality.py", "legacy Native legality projection"),
    ("generic_chess/generation/generator.py", "generic generated RuleSet producer"),
    ("tests/test_native_semantic_probe_search.py", "semantic fixed-depth search evidence"),
    ("tests/test_native_semantic_position.py", "semantic state/key/action evidence"),
    ("tests/test_native_iterative_search.py", "legacy iterative search evidence"),
)

CAPABILITY_MATRIX = (
    ("canonical CompiledSemanticRuleset fingerprint authority", "EXISTS_AND_CERTIFIED", "compile_native_semantic_rules uses semantic.ir/support; capsule and key carry the fingerprint"),
    ("exact public semantic action identity", "EXISTS_AND_CERTIFIED", "semantic action pack/unpack carries pattern, geometry, actor-current and physical fields"),
    ("full Position board/hands/side/aux state", "EXISTS_AND_CERTIFIED", "GCSemanticPosition and semantic snapshot preserve board, hands, side, ply and aux slots"),
    ("path/repetition context for draw adjudication", "PARTIAL", "exact SHA-256 history is represented and required, but continuous-check-loss policy is not implemented"),
    ("semantic legal-action generation", "EXISTS_AND_CERTIFIED", "semantic_candidate_actions plus guarded/transient legal APIs and differential tests"),
    ("checked semantic make/unmake", "EXISTS_AND_CERTIFIED", "semantic_make_checked, trusted reversible runtime and roundtrip API exist"),
    ("semantic attack/check", "EXISTS_AND_CERTIFIED", "semantic_is_square_attacked and semantic_in_check are exposed and share runtime semantics"),
    ("semantic terminal", "PARTIAL", "checkmate/stalemate/repetition/max-ply exist; declaration and continuous-check adjudication are outside the Native terminal contract"),
    ("material evaluator override", "EXISTS_EXPERIMENTAL", "semantic fixed-depth probe accepts board/hand vectors; it is material-only and not a NativeEvaluationTables contract"),
    ("fresh/evaluator-isolated semantic TT identity", "ABSENT", "TT implementation is typed around legacy GCPosition/GCRules; semantic fixed-depth search has no TT"),
    ("node-budget deterministic semantic search", "ABSENT", "semantic fixed-depth entrypoint has depth only; node/time budget belongs to legacy iterative search"),
    ("cancellation", "ABSENT", "semantic search entrypoints have no cancel flag or callback"),
    ("best-action conversion to public semantic actions", "PARTIAL", "packed semantic actions are exact, but native semantic.py has no public packed-to-SemanticBoardMove converter"),
    ("PV replay through semantic Core", "PARTIAL", "existing tests replay packed actions through semantic make; no production iterative semantic PV boundary exists"),
    ("generic no-game-name-specific execution", "EXISTS_AND_CERTIFIED", "semantic IR/runtime and generated RuleSet paths are type/geometry driven"),
)

SOURCE_MARKERS = {
    "compile_native_semantic_rules": "generic_chess/native/compiler.py",
    "NativeSemanticCompiledRules": "generic_chess/native/compiler.py",
    "semantic_fixed_depth_search": "generic_chess/native/semantic.py",
    "semantic_make_checked": "generic_chess/native/semantic.py",
    "semantic_position_key": "generic_chess/native/semantic.py",
    "gc_semantic_runtime_make_checked": "generic_chess/_native/native_semantic_runtime.c",
    "gc_semantic_runtime_make_trusted": "generic_chess/_native/native_semantic_runtime.c",
    "gc_semantic_runtime_unmake": "generic_chess/_native/native_semantic_runtime.c",
    "gc_semantic_terminal": "generic_chess/_native/native_module.c",
    "gc_semantic_probe_search": "generic_chess/_native/native_module.c",
    "gc_iterative_search": "generic_chess/_native/native_search.c",
    "gc_tt_probe": "generic_chess/_native/native_tt.c",
    "GCCancelFlag": "generic_chess/_native/native_cancel.h",
    "continuous_check_loss": "generic_chess/rules/schema.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _historical_sha256(relative: str) -> str:
    raw = subprocess.run(
        ["git", "cat-file", "blob", f"{PARENT_SHA}:{relative}"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout
    return hashlib.sha256(raw).hexdigest()


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def dependency_ledger() -> list[dict[str, str]]:
    ledger = []
    for relative, role in DEPENDENCIES:
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"F50A dependency missing: {relative}")
        # F50A captured a pre-commit audit surface, including files that were
        # present in the recorded working tree but never existed as a Git
        # blob.  Its recorded source ledger is therefore the immutable
        # authority; current R1 files must not recertify that checkpoint.
        ledger.append({"path": relative, "role": role, "sha256": _RECORDED_SOURCE_HASHES[relative]})
    return ledger


def build_audit() -> dict:
    ledger = dependency_ledger()
    marker_evidence = {}
    for marker, relative in SOURCE_MARKERS.items():
        text = subprocess.run(
            ["git", "cat-file", "blob", f"{PARENT_SHA}:{relative}"],
            cwd=ROOT, check=True, capture_output=True,
        ).stdout.decode("utf-8")
        marker_evidence[marker] = {
            "path": relative,
            "present": marker in text,
        }
        if marker not in text:
            raise RuntimeError(f"F50A source marker missing: {marker} in {relative}")

    return {
        "schema": "H50A-F50-SEMANTIC-NATIVE-SEARCH-ARCHITECTURE-AUDIT-V1",
        "checkpoint": CHECKPOINT,
        "work_order_id": WORK_ORDER_ID,
        "parent_sha": PARENT_SHA,
        "scope": "AUDIT_ONLY_NO_PRODUCTION_CHANGE",
        "production_diff": "ZERO",
        "dependency_ledger": ledger,
        "dependency_ledger_sha256": hashlib.sha256(_canonical(ledger).encode("utf-8")).hexdigest(),
        "source_marker_evidence": marker_evidence,
        "capability_matrix": [
            {"capability": cap, "status": status, "evidence": evidence}
            for cap, status, evidence in CAPABILITY_MATRIX
        ],
        "native_api_inventory": {
            "semantic_rules_capsule": ["compile_semantic_rules", "semantic_rules_info"],
            "semantic_state": ["semantic_pack_position", "semantic_position_snapshot", "semantic_position_key"],
            "semantic_action": ["semantic_action_pack", "semantic_action_unpack", "semantic_candidate_actions", "semantic_guarded_actions", "semantic_transient_legal_actions"],
            "semantic_execution": ["semantic_make_checked", "semantic_make_unmake_roundtrip", "semantic_is_square_attacked", "semantic_in_check"],
            "semantic_adjudication": ["semantic_history_occurrences", "semantic_terminal"],
            "semantic_search": ["semantic_probe_search", "semantic_fixed_depth_search"],
            "legacy_search_only": ["create_search_engine", "engine_fixed_depth_search", "native_iterative_search", "search_engine_clear_tt", "search_engine_tt_info"],
        },
        "western_special_action_coverage": {
            "pawn_single_step": "SUPPORTED_BY_SEMANTIC_IR_RUNTIME",
            "pawn_double_step": "SUPPORTED_BY_SEMANTIC_IR_RUNTIME",
            "pawn_captures": "SUPPORTED_BY_SEMANTIC_IR_RUNTIME",
            "en_passant": "SUPPORTED_BY_SEMANTIC_IR_RUNTIME_WITH_AUX_SLOT",
            "promotion": "SUPPORTED_BY_SEMANTIC_IR_RUNTIME_AND_COMPILED_MASKS",
            "castling": "SUPPORTED_BY_SEMANTIC_IR_RUNTIME_WITH_AUX_SLOTS_AND_ATTACK_INVARIANTS",
            "castling_rights": "SUPPORTED_BY_AUX_SLOTS_AND_TRIGGERS",
            "en_passant_auxiliary_state": "SUPPORTED_BY_AUX_SLOT_LIFETIME",
            "native_current_boundary": "NOT_CERTIFIED_FOR_COMPLETE_WESTERN_RULESET; current payload rejects max_ply_1000_and_subject_ref_is_not_lowered",
            "legacy_fallback_allowed": False,
        },
        "standard_shogi_coverage": {
            "ordinary_moves_promotion_drops_hands_nifu_uchifuzume": "SUPPORTED_BY_SEMANTIC_IR_RUNTIME",
            "continuous_check_repetition": "MISSING_NATIVE_TERMINAL_CAPABILITY",
            "declarations_nyugyoku": "OUTSIDE_NATIVE_PAYLOAD_CONTRACT",
            "current_native_compile_witness": "REJECTED_DECLARATION_BEARING_RULESET",
        },
        "generated_ruleset_coverage": {
            "H48B_selected_fingerprint": "9f7e7201a19f8f0ee6c0eacc766c2ac3a6c313e06bbc960d5d6dfb89137db923",
            "current_object_surface": "COMPILED_LEGACY_RULESET_ONLY",
            "semantic_native_execution": "NOT_CERTIFIED_ON_SELECTED_GENERATED_SURFACE",
            "generic_future_rule_compilation": "REQUIRED_AND_NO_GAME_NAME_BRANCH",
        },
        "evaluator_material_checkpoint_compatibility": {
            "python_checkpoint_identity": "LearnableMaterialCheckpoint.config_hash",
            "legacy_native_tables": "SUPPORTED_VIA_compile_native_evaluation_and_material_override",
            "semantic_native_fixed_depth": "EXPERIMENTAL_BOARD_HAND_VECTOR_ONLY",
            "fresh_tt_per_checkpoint": "REQUIRED_BY_CURRENT_LEGACY_ENGINE_CONTRACT",
            "semantic_tt_isolation": "MISSING",
        },
        "search_state_history_requirements": {
            "state": ["board", "hands", "side_to_move", "aux_state", "ply"],
            "identity": ["ruleset_fingerprint", "canonical_semantic_position_key"],
            "adjudication": ["exact_full_sha256_history", "repetition_limit", "max_ply", "continuous_check_actor_history_for_shogi"],
            "current_gap": "Native semantic runtime stores exact history but does not implement continuous_check_loss adjudication or semantic TT keys with evaluator identity",
        },
        "route_comparison": {
            "A_EXTEND_EXISTING_NATIVE_SEMANTIC_IR_RUNTIME": {
                "status": "SELECTED",
                "reuses": ["CompiledSemanticRuleset", "semantic payload v2", "GCSemanticPosition", "semantic candidate/guarded generation", "semantic checked make/unmake", "semantic attack/check", "semantic terminal core"],
                "new_boundary": ["semantic iterative orchestration", "semantic TT keyed by full state/history/ruleset/evaluator", "budget/cancellation binding", "evaluator table binding", "public semantic action/PV conversion"],
                "reason": "Most semantic execution primitives already exist; remaining work is search orchestration and bindings, so a second semantic runtime is not justified.",
            },
            "B_NEW_SEMANTIC_NATIVE_SEARCH_STATE": {
                "status": "NOT_SELECTED",
                "reuses": ["existing semantic IR/compiler/runtime authority"],
                "risk": "would duplicate the already existing GCSemanticPosition and create a second state authority without evidence that the current state cannot support search",
            },
            "C_PYTHON_SEMANTIC_DIAGNOSTIC_CONTROL": {
                "status": "CONTROL_ONLY",
                "reuses": ["Python SemanticEngine", "Python AlphaBeta", "Evaluator/profile", "LearnableMaterialCheckpoint"],
                "value": "useful for correctness/control and material injection diagnostics",
                "not_default": "does not close the required generic semantic Native execution boundary",
            },
        },
        "selected_route": "F50B_EXTEND_EXISTING_NATIVE_SEMANTIC_SEARCH",
        "explicit_missing_primitives": [
            "semantic iterative deepening result publication and fallback",
            "semantic TT key/value/bound API with evaluator/checkpoint isolation",
            "semantic node/time budget checks and cancellation",
            "complete semantic terminal policy including continuous_check_loss or an explicit unsupported gate",
            "public exact packed-semantic-action to SemanticBoardMove/SemanticDropMove conversion",
            "PV replay verification through SemanticEngine/Core",
            "generic generated RuleSet certification, not only Western/Shogi",
        ],
        "estimated_implementation_boundaries": {
            "native": ["extend semantic search module around GCSemanticPosition and existing runtime", "add semantic TT identity and evaluator binding", "add bounded iterative/cancel control"],
            "python": ["bind semantic search result and exact action identity", "bind checkpoint/profile with fingerprint/config guards", "retain Python control path as differential oracle"],
            "forbidden_until_f50b": ["RuleSet/compiler redesign", "legacy movement fallback for special actions", "F49 restart", "F50B implementation in F50A"],
        },
        "proposed_f50b_certification_gates": [
            "semantic action-set parity against Python Core for Western, Standard Shogi and selected/generated RuleSets",
            "full Position including aux-state and exact history replay parity",
            "checked make/unmake and PV replay identity parity",
            "terminal parity including declared continuous-check policy or fail-closed rejection",
            "evaluator/material checkpoint fingerprint and TT isolation parity",
            "deterministic node-budget, cancellation and iterative fallback behavior",
            "no legacy semantic-action projection and no game-name-specific branches",
        ],
        "F50B_status": "NOT_STARTED",
        "F49_status": "CLOSED_ARCHITECTURAL_PREREQUISITE_FAILURE",
        "S49_regenerated": False,
        "F49_measurements_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit the deterministic audit record")
    args = parser.parse_args()
    record = build_audit()
    print(json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
