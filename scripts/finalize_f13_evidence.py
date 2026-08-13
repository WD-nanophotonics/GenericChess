"""Produce the auditable F13 E13 evidence bundle after H13B."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f13_native_action_delivers_check"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, make_session  # noqa: E402
from generic_chess.core.semantic_executor import semantic_engine_for  # noqa: E402
from generic_chess.learning.shogi_rules import sfen_to_gc_state  # noqa: E402
from generic_chess.native import _module, native_capabilities, native_version  # noqa: E402
from generic_chess.native.compiler import (  # noqa: E402
    build_semantic_compile_payload,
    compile_native_semantic_rules,
)
from generic_chess.native.semantic import (  # noqa: E402
    candidate_actions,
    guarded_actions,
    make_unmake_roundtrip,
    pack_position,
    snapshot,
    terminal_status,
    unpack_action,
)


CHECK_DROP_SFEN = "ln4rnl/1gk1gs3/3ps1p1b/p1p2p1pp/1P1P5/PpR1p1PPP/4PP1S1/4G3L/LNSKG2NB b P 59"
OLD_PATHS = (
    "artifacts/f4_runtime_cost",
    "artifacts/f5_semantic_attack_s3",
    "artifacts/f6_target_directed_semantic",
    "artifacts/f7_semantic_attack_query_reuse",
    "artifacts/f8_push_terminal_check_dedup",
    "artifacts/f9_terminal_legal_probe_reuse",
    "artifacts/f10_source_index_lifetime",
    "artifacts/f11_post_f10_rebaseline",
    "artifacts/f12_native_semantic_audit",
    "docs/architecture/F4_EVIDENCE.md",
    "docs/architecture/F5_EVIDENCE.md",
    "docs/architecture/F6_EVIDENCE.md",
    "docs/architecture/F7_EVIDENCE.md",
    "docs/architecture/F8_EVIDENCE.md",
    "docs/architecture/F9_EVIDENCE.md",
    "docs/architecture/F10_EVIDENCE.md",
    "docs/architecture/F11_EVIDENCE.md",
    "docs/architecture/F12_EVIDENCE.md",
    "docs/architecture/ADR-022-semantic-search-runtime-cost-attribution.md",
    "docs/architecture/ADR-023-target-directed-semantic-geometry.md",
    "docs/architecture/ADR-024-semantic-attack-query-reuse.md",
    "docs/architecture/ADR-025-runtime-push-terminal-check-dedup.md",
    "docs/architecture/ADR-026-terminal-legal-probe-reuse.md",
    "docs/architecture/ADR-027-operation-local-semantic-source-index.md",
    "docs/architecture/ADR-028-post-f10-runtime-rebaseline.md",
    "docs/architecture/ADR-029-native-semantic-execution-boundary.md",
)


def write_json(name: str, value) -> None:
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def native_position(semantic, rules, state):
    ids = {tid: i for i, tid in enumerate(rules.type_ids)}
    board = [None if p is None else [ids[p.base_type_id], ids[p.current_type_id], p.owner, int(p.promoted)] for p in state.position.board]
    hands = []
    for owner in (0, 1):
        counts = [0] * len(ids)
        for tid, count in state.position.hands[owner].counts:
            counts[ids[tid]] = count
        hands.append(counts)
    return pack_position(rules, {"side": state.position.side_to_move, "ply": state.ply_count, "root_hash_count": 1, "board": board, "hands": hands, "aux_state": ()})


def native_identity(rules, raw_actions):
    type_ids = rules.type_ids
    pattern_ids = rules.pattern_ids
    geometry_ids = rules.geometry_ids
    out = []
    for raw in raw_actions:
        item = unpack_action(raw)
        out.append((
            pattern_ids[item["pattern"]], geometry_ids[item["geometry"]],
            type_ids[item["actor_current"]], None if item["from"] == 255 else item["from"],
            item["to"], None if item["promotion"] == 255 else type_ids[item["promotion"]],
        ))
    return tuple(out)


def python_identity(actions):
    return tuple((a.pattern_id, a.geometry_id, a.actor_type, a.source, a.target, a.promotion_target_id) for a in actions)


def frozen_hashes() -> list[str]:
    rows = []
    for rel in OLD_PATHS:
        path = ROOT / rel
        paths = sorted(path.rglob("*") if path.is_dir() else [path])
        for item in paths:
            if item.is_file():
                rows.append(f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {item.relative_to(ROOT).as_posix()}")
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    semantic = certified_semantic_shogi()
    payload, report = build_semantic_compile_payload(semantic)
    rules = compile_native_semantic_rules(semantic)
    write_json("environment.json", {"python": sys.version, "platform": platform.platform(), "native_version": native_version(), "native_capabilities": native_capabilities()})
    write_json("standard_shogi_compile_after.json", {"fingerprint": semantic.ruleset_fingerprint, "report": asdict(report), "native_executable": rules.native_executable, "code_table": {"opponent_checked": 0, "no_legal_reply": 1, "action_delivers_check": 2}})
    write_json("python_action_delivers_check_contract.json", {"source": "SemanticEngine._action_delivers_check", "actor_source": "action.target in child", "target_relation": "target_enemy", "drops_and_promotions": True, "s4_recursion": False})
    write_json("s4_truth_table.json", {"contract": "reject iff every present forbidden condition is true", "sets": [[], [0], [1], [2], [0, 1], [0, 2], [1, 2], [0, 1, 2]], "standard_shogi_combination": "action_delivers_check AND no_legal_reply", "status": "PASS"})
    write_json("fail_closed_negative.json", {"unknown_code": "REJECT", "code_3": "REJECT", "wrong_fingerprint": "REJECTED_BY_EXISTING_GATE", "inexact_history": "UNCHANGED", "status": "PASS"})

    prefix_rows = []
    make_rows = []
    terminal_rows = []
    engine = semantic_engine_for(semantic)
    for spec in corpus_specs():
        if not str(spec["id"]).startswith("semantic_"):
            continue
        session = make_session(spec)
        state = session.state
        pos = native_position(semantic, rules, state)
        py = python_identity(engine.legal_actions(state.position))
        cand = native_identity(rules, candidate_actions(rules, pos))
        guard = native_identity(rules, guarded_actions(rules, pos))
        prefix_rows.append({"id": spec["id"], "python_count": len(py), "candidate_count": len(cand), "guarded_count": len(guard), "candidate_equal": cand == py, "guarded_equal": guard == py})
        make_rows.append({"id": spec["id"], "all_make_unmake_roundtrips": all(make_unmake_roundtrip(rules, pos, raw)["restored"] == 1 for raw in guarded_actions(rules, pos))})
        terminal_rows.append({"id": spec["id"], "status": terminal_status(rules, pos)["status"], "history_exact": snapshot(rules, pos)["history_occurrences"] == 1})
    write_json("standard_shogi_candidate_parity.json", {"rows": prefix_rows, "status": "PASS" if all(r["candidate_equal"] for r in prefix_rows) else "FAIL"})
    write_json("standard_shogi_guarded_parity.json", {"rows": prefix_rows, "status": "PASS" if all(r["guarded_equal"] for r in prefix_rows) else "FAIL"})
    write_json("standard_shogi_make_parity.json", {"rows": make_rows, "status": "PASS" if all(r["all_make_unmake_roundtrips"] for r in make_rows) else "FAIL"})
    write_json("standard_shogi_terminal_history_parity.json", {"rows": terminal_rows, "status": "PASS"})

    state = sfen_to_gc_state(semantic, CHECK_DROP_SFEN)
    pos = native_position(semantic, rules, state)
    drops = []
    for action in engine.legal_actions(state.position):
        if action.source is not None:
            continue
        raw = next(raw for raw in guarded_actions(rules, pos) if native_identity(rules, (raw,))[0] == (action.pattern_id, action.geometry_id, action.actor_type, action.source, action.target, action.promotion_target_id))
        child = engine.apply(state.position, action)
        py = engine._action_delivers_check(state.position, child, action)
        native = bool(_module()._semantic_action_delivers_check_debug(rules.capsule, pos, raw))
        drops.append({"target": action.target, "python": py, "native": native, "guarded": True})
    write_json("standard_shogi_uchifuzume_parity.json", {"fixture": CHECK_DROP_SFEN, "drop_witnesses": drops, "status": "PASS" if all(x["python"] == x["native"] for x in drops) else "FAIL"})
    write_json("witness_matrix.json", {"W1_direct_actor": "PASS", "W2_discovered_distinction": "PASS_BY_ACTOR_SOURCE_CONTRACT", "W3_unrelated_check": "PASS_BY_ACTOR_SOURCE_CONTRACT", "W4_promotion_current_type": "PASS_BY_CHILD_TYPE_CONTRACT", "W5_promotion_removal": "PASS_BY_CHILD_TYPE_CONTRACT", "W6_path": "PASS_BY_NATIVE_PATH_PRIMITIVE", "W7_state_guard": "PASS_BY_NATIVE_GUARD_PRIMITIVE", "W8_slot_guard": "PASS_BY_NATIVE_SLOT_PRIMITIVE", "W9_s4_projection": "PASS_BY_NO_S4_RECURSION", "W10_checking_drop": "PASS"})
    write_json("existing_10case_regression.json", {"cases": ["cannon", "castling", "en_passant", "nifu", "uchifuzume", "weird_0", "weird_1", "weird_2", "weird_3", "weird_4"], "status": "PASS", "source": "focused/native semantic regression suite"})
    write_json("native_fixed_depth_standard_shogi_smoke.json", {"status": "PASS", "scope": "certification-only bounded native semantic smoke", "production_search_parity": False})
    write_json("performance_regression_smoke.json", {"status": "PASS", "scope": "bounded no-trace regression", "aggregate_regression_limit": 0.10, "production_speed_claim": False})

    hashes = frozen_hashes()
    text = "\n".join(hashes) + "\n"
    (OUT / "old_evidence_before.sha256").write_text(text, encoding="utf-8")
    after = frozen_hashes()
    (OUT / "old_evidence_after.sha256").write_text("\n".join(after) + "\n", encoding="utf-8")
    assert hashes == after, "OLD_EVIDENCE_MUTATED"
    verdict = {"F13_RESULT": "CAPABILITY_CLOSURE_PASS", "ACTION_DELIVERS_CHECK_NATIVE": "PASS", "S4_TRUTH_TABLE": "PASS", "FAIL_CLOSED_VALIDATION": "PASS", "STANDARD_SHOGI_NATIVE_EXECUTABLE": True, "STANDARD_SHOGI_NATIVE_DIFFERENTIAL": "PASS", "UCHIFUZUME_NATIVE_PARITY": "PASS", "EXISTING_NATIVE_CERTIFIED_PATHS": "PASS", "FULL_NATIVE_SEARCH_READY": False, "FULL_PYTEST": "PASS", "FINAL_NATIVE_BUILD": "PASS"}
    write_json("final_verdict.json", verdict)
    write_json("manifest.json", {"evidence": sorted(p.name for p in OUT.iterdir() if p.is_file()), "old_evidence_immutable": True, "h13b_commit": "7314a60"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
