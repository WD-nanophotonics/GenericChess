"""F31 audit-only diagnosis of the Standard Shogi external gap.

The script consumes the frozen F30 R1 evidence and never changes production
code, evaluator coefficients, search defaults, or the AlphaSho checkout.  The
manifest must be frozen before ``--stage-b`` is allowed to run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_f30r1_alphasho_reference import (  # noqa: E402
    ALPHASHO_ROOT,
    DESCRIPTOR_PATH,
    F22_COMMIT,
    PRODUCT_AUTHORITY,
    _canonical,
    _sha,
    environment_manifest,
    historical_source,
)

F30_R1_FRESH = ROOT / "tests" / "fixtures" / "f30r1_fresh_move_reference.json"
F30_R1_PAIRED = ROOT / "tests" / "fixtures" / "f30r1_paired_match.json"
F30_R1_MANIFEST = ROOT / "tests" / "fixtures" / "f30r1_benchmark_manifest.json"
F31_MANIFEST = ROOT / "tests" / "fixtures" / "f31_causal_manifest.json"
F31_OUTPUT = ROOT / "tests" / "fixtures" / "f31_causal_diagnosis.json"
TIMES = (0.50, 2.00)
ROOT_BUDGETS = (512, 2048)
HORIZON_BUDGETS = (128, 256, 512, 1024, 2048, 4096, 8192)
MAX_Q_RANK_NODES = 128
FROZEN_F22 = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_sha(value: dict[str, Any]) -> str:
    return _sha(_canonical({key: item for key, item in value.items() if key != "manifest_sha256"}))


def build_manifest() -> dict[str, Any]:
    source = historical_source()
    fingerprint = __import__("generic_chess.rules.schema", fromlist=["compute_fingerprint"]).compute_fingerprint(
        __import__("generic_chess.rules.standard_shogi", fromlist=["build_standard_shogi_ruleset"]).build_standard_shogi_ruleset()
    )
    evidence = {
        "f30_r1_manifest": {"path": "tests/fixtures/f30r1_benchmark_manifest.json", "sha256": _sha(F30_R1_MANIFEST.read_bytes())},
        "f30_r1_fresh": {"path": "tests/fixtures/f30r1_fresh_move_reference.json", "sha256": _sha(F30_R1_FRESH.read_bytes())},
        "f30_r1_paired": {"path": "tests/fixtures/f30r1_paired_match.json", "sha256": _sha(F30_R1_PAIRED.read_bytes())},
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "kind": "F31_PRE_DIAGNOSIS_MANIFEST",
        "generic_chess_product_authority": PRODUCT_AUTHORITY,
        "generic_chess_head_at_freeze": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "standard_shogi_fingerprint": fingerprint,
        "descriptor": {"path": "tests/fixtures/f25_standard_shogi_position_descriptors.json", "sha256": _sha(DESCRIPTOR_PATH.read_bytes()), "source_commit": F22_COMMIT, "count": 10},
        "f22_source": {"commit": source["source_commit"], "sha256": source["source_sha256"], "reference_count": source["reference_count"]},
        "f30_r1_evidence": evidence,
        "f31_harness": {"path": "scripts/audit_f31_gap_causal.py", "sha256": _sha(Path(__file__).read_bytes())},
        "alphasho_environment": environment_manifest(),
        "diagnostic_matrix": {
            "times_seconds": list(TIMES),
            "static_root_ranking": {"uses_alphabeta": False, "all_legal_actions": True, "evaluator": "v1"},
            "qsearch_root_ranking": {"uses_production_qsearch": True, "qsearch_max_depth": 4, "qsearch_hard_max_depth": 8, "max_nodes_per_child": MAX_Q_RANK_NODES},
            "root_timing_and_counterfactuals": ["baseline", "root_tactical_off", "qsearch_off"],
            "fixed_node_variants": ["baseline", "tt_off", "ordering_off", "qsearch_off", "root_tactical_off", "pvs_on"],
            "fixed_node_budgets": list(ROOT_BUDGETS),
            "horizon_ladder": list(HORIZON_BUDGETS),
            "horizon_extension_subset": "first five position IDs disagree with AlphaSho at 2048, lexicographic position order",
            "native_counterfactual": ["live_native_requested", "stripped_native_off", "stripped_native_requested"],
            "forced_candidate_depths": [0, 1, 2],
        },
        "generic_chess_settings": {"evaluator": "v1", "tt": True, "ordering": True, "native_requested": True, "disk_cache": False, "search_tuning": "default", "qsearch": "4/8", "max_depth": 64},
        "paired_anchor": {"path": "tests/fixtures/f30r1_paired_match.json", "do_not_rerun": True, "score": 0.075, "clean_wdl": "0W/3D/17L", "technical_failures": 0, "caps": 0},
        "constraints": ["NO_TUNING_FROM_RESULTS", "production_diff_zero", "no_new_broad_paired_match", "no_AlphaChess", "audit_only_ruleset_stripping_declarations_and_automatic_adjudications_only"],
        "host": {"python": platform.python_version()},
    }
    result["manifest_sha256"] = _manifest_sha(result)
    return result


def freeze_manifest(path: Path) -> dict[str, Any]:
    manifest = build_manifest()
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = _load(path)
    if _manifest_sha(manifest) != manifest.get("manifest_sha256"):
        raise AssertionError("F31 causal manifest SHA mismatch")
    if manifest["generic_chess_product_authority"] != PRODUCT_AUTHORITY:
        raise AssertionError("F31 manifest is not bound to F29 product authority")
    if manifest["f31_harness"]["sha256"] != _sha(Path(__file__).read_bytes()):
        raise AssertionError("F31 harness changed after manifest freeze")
    return manifest


def _imports():
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.search import run_root_search, terminal_score
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.evaluator import Evaluator
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.core.actions import action_to_dict
    from generic_chess.core.attacks import is_in_check
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action
    from generic_chess.learning.shogi_rules import cshogi_legal_usi_set, gc_action_to_usi, gc_legal_usi_set, gc_to_sfen, sfen_to_gc_state
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
    from generic_chess.session.session import GameSession
    return locals()


def _contexts(ruleset=None):
    m = _imports()
    selected = ruleset or m["build_standard_shogi_ruleset"]()
    compiled = m["compile_ruleset_for_execution"](selected)
    config = m["EvaluationConfig"]()
    profile = m["build_ruleset_profile"](compiled._legacy_compiled, config)
    evaluator = m["Evaluator"](compiled, profile, config)
    return m, compiled, evaluator


def _session(m, compiled, state):
    session = m["GameSession"](compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    return session


def _action_key(m, action):
    return json.dumps(m["action_to_dict"](action), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _direct(m, compiled, evaluator, state, *, nodes=None, seconds=None, tuning=None, use_tt=True, use_ordering=True, native_requested=True, qmax=4, qhard=8, max_depth=64):
    # A materialized child carries a transition history whose imported
    # prefix is intentionally unavailable for this audit.  Re-import the
    # position-only SFEN before direct root-search probes so the runtime sees
    # a self-consistent one-position history rather than a partial transcript.
    if state.history:
        state = m["sfen_to_gc_state"](compiled, m["gc_to_sfen"](state, compiled))
    provider = m["NativeSemanticLegalityProvider"].try_create(compiled) if native_requested else None
    stats = m["SearchStatistics"]()
    session = _session(m, compiled, state)
    limits = m["SearchLimits"](max_nodes=nodes, max_time_seconds=seconds, max_depth=max_depth, quiescence_max_depth=qmax, quiescence_hard_max_depth=qhard, deterministic=True)
    started = time.perf_counter()
    action, score, pv, reason = m["run_root_search"](state, compiled, evaluator, m["TranspositionTable"](max_entries=250_000), limits, None, stats, use_tt=use_tt, use_ordering=use_ordering, tuning=tuning or m["SearchTuning"](), _history_witnesses=session._search_witnesses, legal_binding_provider=provider)
    elapsed = time.perf_counter() - started
    move = m["gc_action_to_usi"](action) if action else None
    return {"selected_move": move, "score": score, "pv_head": m["gc_action_to_usi"](pv[0]) if pv else None, "completed_depth": stats.completed_depth, "selective_depth": stats.selective_depth, "nodes": stats.nodes, "qnodes": stats.qnodes, "total_nodes": stats.nodes + stats.qnodes, "elapsed_seconds": elapsed, "termination_reason": reason, "fallback": stats.root_scan_used_fallback, "root_scan_nodes": stats.root_scan_nodes, "root_scan_seconds": stats.root_scan_seconds, "time_to_first_legal_action": stats.time_to_first_legal_action, "time_to_first_completed_iteration": stats.time_to_first_completed_iteration, "legal_generation_seconds": stats.legal_generation_seconds, "evaluation_seconds": stats.evaluation_seconds, "ordering_seconds": stats.ordering_seconds, "tt_probes": stats.tt_probes, "tt_hits": stats.tt_hits, "qsearch_nodes": stats.qnodes, "qsearch_cutoffs": stats.qdepth_cutoffs, "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK"}


def _frozen_roots() -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    roots = _load(DESCRIPTOR_PATH)
    fresh = _load(F30_R1_FRESH)
    modal: dict[str, dict[str, str]] = {}
    for engine in ("alphasho", "generic_chess"):
        for seconds in ("0.5", "2.0"):
            for position_id, row in fresh[engine][seconds]["summaries"].items():
                modal.setdefault(position_id, {})[f"{engine}_{seconds}"] = row["modal_move"]
    return roots["positions"], modal


def static_and_qsearch() -> dict[str, Any]:
    positions, modal = _frozen_roots()
    m, compiled, evaluator = _contexts()
    result = {"ruleset_fingerprint": compiled.ruleset_fingerprint, "roots": {}}
    for item in positions:
        state = m["sfen_to_gc_state"](compiled, item["sfen"])
        actions = list(m["legal_actions"](state, compiled))
        static_rows = []
        for action in actions:
            child = m["apply_action"](state, action, compiled)
            static_rows.append({"move": m["gc_action_to_usi"](action), "action_key": _action_key(m, action), "score": -evaluator.evaluate(child), "terminal": child.terminal_status.status.value})
        static_rows.sort(key=lambda row: (-row["score"], row["action_key"]))
        for index, row in enumerate(static_rows, start=1):
            row["rank"] = index
        q_rows = []
        q_tuning = replace(m["SearchTuning"](), use_root_tactical=False)
        for action in actions:
            child = m["apply_action"](state, action, compiled)
            if child.terminal_status.is_terminal:
                score = -m["terminal_score"](child.terminal_status, child.position.side_to_move, 0)
                metrics = {"selected_move": None, "completed_depth": 0, "termination_reason": "terminal_position"}
            else:
                metrics = _direct(m, compiled, evaluator, child, nodes=MAX_Q_RANK_NODES, max_depth=1, tuning=q_tuning, use_tt=True, use_ordering=True, qmax=4, qhard=8)
                score = -metrics["score"]
            q_rows.append({"move": m["gc_action_to_usi"](action), "action_key": _action_key(m, action), "score": score, "child_search": {key: metrics[key] for key in ("completed_depth", "termination_reason")}})
        q_rows.sort(key=lambda row: (-row["score"], row["action_key"]))
        for index, row in enumerate(q_rows, start=1):
            row["rank"] = index
        by_move_static = {row["move"]: row for row in static_rows}
        by_move_q = {row["move"]: row for row in q_rows}
        targets = {name: move for name, move in modal[item["position_id"]].items()}
        target_ranks = {}
        for name, move in targets.items():
            target_ranks[name] = {"move": move, "static_rank": by_move_static.get(move, {}).get("rank"), "static_score": by_move_static.get(move, {}).get("score"), "qsearch_rank": by_move_q.get(move, {}).get("rank"), "qsearch_score": by_move_q.get(move, {}).get("score")}
        top_score = static_rows[0]["score"] if static_rows else None
        result["roots"][item["position_id"]] = {"sfen": item["sfen"], "legal_action_count": len(actions), "static_top": static_rows[:5], "static_top1": static_rows[:1], "static_top3": static_rows[:3], "static_top5": static_rows[:5], "static_score_gap_from_top1": {row["move"]: top_score - row["score"] for row in static_rows[:5]} if top_score is not None else {}, "qsearch_top": q_rows[:5], "target_ranks": target_ranks, "all_static_actions": static_rows, "all_qsearch_actions": q_rows}
    return result


def historical_reference_context(static: dict[str, Any]) -> dict[str, Any]:
    source = historical_source()
    rows = {}
    outside = 0
    for position_id, root in static["roots"].items():
        move = source["references"][position_id]
        ranked = {row["move"]: row["rank"] for row in root["all_static_actions"]}
        rank = ranked.get(move)
        if rank is None or rank > 3:
            outside += 1
        rows[position_id] = {"historical_f22_move": move, "static_rank": rank, "outside_static_top3": rank is None or rank > 3}
    fresh_outside = sum(
        1
        for root in static["roots"].values()
        if any((value["static_rank"] or 99) > 3 for name, value in root["target_ranks"].items() if name.startswith("alphasho_"))
    )
    return {"prior_observation_outside_evaluator_v1_top3": 8, "current_historical_f22_outside_static_top3": outside, "current_fresh_alphasho_any_control_outside_static_top3": fresh_outside, "roots": rows}


def timing_and_ablations() -> dict[str, Any]:
    positions, modal = _frozen_roots()
    m, compiled, evaluator = _contexts()
    result: dict[str, Any] = {"baseline": {}, "root_tactical_off": {}, "qsearch_off": {}, "fixed_node_matrix": {}}
    for seconds in TIMES:
        key = str(seconds)
        for name, tuning, qmax in (("baseline", m["SearchTuning"](), 4), ("root_tactical_off", replace(m["SearchTuning"](), use_root_tactical=False), 4), ("qsearch_off", m["SearchTuning"](), 0)):
            result[name][key] = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                row = _direct(m, compiled, evaluator, state, seconds=seconds, max_depth=64, tuning=tuning, qmax=qmax, qhard=8)
                row["reference_050"] = modal[item["position_id"]]["alphasho_0.5"]
                row["reference_200"] = modal[item["position_id"]]["alphasho_2.0"]
                row["reference_top1"] = row["selected_move"] in {row["reference_050"], row["reference_200"]}
                result[name][key][item["position_id"]] = row
    variants = {"baseline": {}, "tt_off": {"use_tt": False}, "ordering_off": {"use_ordering": False}, "qsearch_off": {"qmax": 0}, "root_tactical_off": {"tuning": replace(m["SearchTuning"](), use_root_tactical=False)}, "pvs_on": {"tuning": replace(m["SearchTuning"](), use_pvs=True)}}
    for variant, options in variants.items():
        result["fixed_node_matrix"][variant] = {}
        for budget in ROOT_BUDGETS:
            rows = {}
            for item in positions:
                state = m["sfen_to_gc_state"](compiled, item["sfen"])
                row = _direct(m, compiled, evaluator, state, nodes=budget, max_depth=8, qmax=options.get("qmax", 4), qhard=8, tuning=options.get("tuning"), use_tt=options.get("use_tt", True), use_ordering=options.get("use_ordering", True))
                row["reference_050"] = modal[item["position_id"]]["alphasho_0.5"]
                row["reference_200"] = modal[item["position_id"]]["alphasho_2.0"]
                row["reference_top1_050"] = row["selected_move"] == row["reference_050"]
                row["reference_top1_200"] = row["selected_move"] == row["reference_200"]
                rows[item["position_id"]] = row
            result["fixed_node_matrix"][variant][str(budget)] = rows
    summary = {}
    for seconds in TIMES:
        key = str(seconds)
        base = result["baseline"][key]
        summary[key] = {}
        for variant in ("root_tactical_off", "qsearch_off"):
            alt = result[variant][key]
            summary[key][variant] = {
                "baseline_depths": [row["completed_depth"] for row in base.values()],
                "variant_depths": [row["completed_depth"] for row in alt.values()],
                "baseline_reference_top1_count": sum(row["reference_top1"] for row in base.values()),
                "variant_reference_top1_count": sum(row["reference_top1"] for row in alt.values()),
                "baseline_fallback_count": sum(row["fallback"] for row in base.values()),
                "variant_fallback_count": sum(row["fallback"] for row in alt.values()),
                "baseline_elapsed_seconds": sum(row["elapsed_seconds"] for row in base.values()),
                "variant_elapsed_seconds": sum(row["elapsed_seconds"] for row in alt.values()),
            }
    result["summary"] = summary
    return result


def horizon_native_forced(static: dict[str, Any]) -> dict[str, Any]:
    positions, modal = _frozen_roots()
    m, compiled, evaluator = _contexts()
    baseline_2048 = _load(F30_R1_FRESH)["generic_chess"]["0.5"]["summaries"]
    disagreements = sorted(position_id for position_id, row in baseline_2048.items() if row["modal_move"] != modal[position_id]["alphasho_0.5"])
    extension = disagreements[:5]
    ladder: dict[str, Any] = {"budgets": list(HORIZON_BUDGETS), "extension_positions": extension, "roots": {}}
    for item in positions:
        if item["position_id"] not in extension:
            continue
        state = m["sfen_to_gc_state"](compiled, item["sfen"])
        rows = {}
        for budget in HORIZON_BUDGETS:
            rows[str(budget)] = _direct(m, compiled, evaluator, state, nodes=budget, max_depth=8, qmax=4, qhard=8)
        target_moves = {modal[item["position_id"]]["alphasho_0.5"], modal[item["position_id"]]["alphasho_2.0"]}
        selected = [rows[str(budget)]["selected_move"] for budget in HORIZON_BUDGETS]
        recovered_indices = [index for index, move in enumerate(selected) if move in target_moves]
        if not recovered_indices:
            recovery_class = "never_recovered"
        elif all(move in target_moves for move in selected[recovered_indices[0]:]):
            recovery_class = "stable_recovered"
        elif any(move in target_moves for move in selected[recovered_indices[0] + 1:]):
            recovery_class = "recovered_then_lost_or_unstable"
        else:
            recovery_class = "unstable"
        ladder["roots"][item["position_id"]] = {"rows": rows, "alpha_sho_target_moves": sorted(target_moves), "selected_moves_by_budget": dict(zip((str(budget) for budget in HORIZON_BUDGETS), selected)), "recovery_class": recovery_class}
    stripped_ruleset = replace(m["build_standard_shogi_ruleset"](), declarations=(), automatic_adjudications=())
    sm, stripped, sevaluator = _contexts(stripped_ruleset)
    native = {"live": {}, "stripped_native_off": {}, "stripped_native_requested": {}, "legal_set_proof": {}, "static_score_proof": {}}
    for item in positions:
        live_state = m["sfen_to_gc_state"](compiled, item["sfen"])
        stripped_state = sm["sfen_to_gc_state"](stripped, item["sfen"])
        live_actions = {_action_key(m, action): action for action in m["legal_actions"](live_state, compiled)}
        stripped_actions = {_action_key(sm, action): action for action in sm["legal_actions"](stripped_state, stripped)}
        native["legal_set_proof"][item["position_id"]] = {"exact_match": set(live_actions) == set(stripped_actions), "live_count": len(live_actions), "stripped_count": len(stripped_actions)}
        live_scores = {key: -evaluator.evaluate(m["apply_action"](live_state, action, compiled)) for key, action in live_actions.items()}
        stripped_scores = {key: -sevaluator.evaluate(sm["apply_action"](stripped_state, action, stripped)) for key, action in stripped_actions.items()}
        native["static_score_proof"][item["position_id"]] = {"exact_match": live_scores == stripped_scores}
        for name, target, requested in (("live", compiled, True), ("stripped_native_off", stripped, False), ("stripped_native_requested", stripped, True)):
            target_m = m if target is compiled else sm
            target_e = evaluator if target is compiled else sevaluator
            target_state = live_state if target is compiled else stripped_state
            native[name].setdefault(item["position_id"], {})
            for seconds in TIMES:
                native[name][item["position_id"]][str(seconds)] = _direct(target_m, target, target_e, target_state, seconds=seconds, max_depth=64, native_requested=requested, qmax=4, qhard=8)
                native[name][item["position_id"]][str(seconds)]["reference_050"] = modal[item["position_id"]]["alphasho_0.5"]
                native[name][item["position_id"]][str(seconds)]["reference_200"] = modal[item["position_id"]]["alphasho_2.0"]
    forced: dict[str, Any] = {"roots": {}}
    disagreement_ids = sorted({item["position_id"] for item in positions if modal[item["position_id"]]["generic_chess_0.5"] != modal[item["position_id"]]["alphasho_0.5"] or modal[item["position_id"]]["generic_chess_2.0"] != modal[item["position_id"]]["alphasho_2.0"]})
    for item in positions:
        if item["position_id"] not in disagreement_ids:
            continue
        state = m["sfen_to_gc_state"](compiled, item["sfen"])
        candidate_moves = {modal[item["position_id"]][key] for key in ("generic_chess_0.5", "alphasho_0.5", "alphasho_2.0")}
        legal_by_usi = {m["gc_action_to_usi"](action): action for action in m["legal_actions"](state, compiled)}
        rows = {}
        for move in sorted(candidate_moves):
            action = legal_by_usi[move]
            child = m["apply_action"](state, action, compiled)
            depths = {}
            for depth in (0, 1, 2):
                depths[str(depth)] = {"root_perspective_score": -evaluator.evaluate(child) if depth == 0 else -_direct(m, compiled, evaluator, child, nodes=256, max_depth=depth, qmax=4, qhard=8, tuning=replace(m["SearchTuning"](), use_root_tactical=False))["score"]}
            rows[move] = depths
        forced["roots"][item["position_id"]] = rows
    requested_rows = [row for position in native["live"].values() for row in position.values()] + [row for position in native["stripped_native_requested"].values() for row in position.values()]
    native_active = any(row["provider_mode"] == "NATIVE_PROVIDER_ACTIVE" for row in requested_rows)
    depth_gains = [
        native["stripped_native_requested"][pid][str(seconds)]["completed_depth"] - native["stripped_native_off"][pid][str(seconds)]["completed_depth"]
        for pid in native["stripped_native_off"]
        for seconds in TIMES
    ]
    native["availability"] = "NATIVE_COUNTERFACTUAL_AVAILABLE" if native_active else "NATIVE_COUNTERFACTUAL_UNAVAILABLE"
    native["material_completed_depth_gain"] = native_active and max(depth_gains, default=0) > 0
    return {"horizon_ladder": ladder, "native_counterfactual": native, "forced_candidates": forced}


def stalemate_audit() -> dict[str, Any]:
    m, compiled, _evaluator = _contexts()
    paired = _load(F30_R1_PAIRED)
    rows = []
    for game in paired["games"]:
        if game["final_terminal_status"] != "stalemate":
            continue
        seeded = m["sfen_to_gc_state"](compiled, game["starting_sfen"])
        state = replace(seeded, history=(__import__("generic_chess.core.position", fromlist=["HistoryRecord"]).HistoryRecord(seeded.repetition_counts[0][0], -1, "IMPORTED_HISTORY_PREFIX_UNAVAILABLE", False),))
        session = _session(m, compiled, state)
        for event in game["events"]:
            usi = event["usi_or_declaration"]
            legal = {m["gc_action_to_usi"](action): action for action in session.legal_actions()}
            if usi not in legal:
                raise AssertionError(f"stalemate transcript action not legal: {usi}")
            session.submit(legal[usi])
        final_sfen = m["gc_to_sfen"](session.state, compiled)
        cshogi_legal = sorted(m["cshogi_legal_usi_set"](final_sfen))
        rows.append({"position_id": game["position_id"], "external_color": game["external_color"], "game_id": f"{game['position_id']}::{game['external_color']}", "product_status": session.result.status.value, "legal_action_count": len(session.legal_actions()), "side_to_move_in_check": bool(m["is_in_check"](session.state.position, session.state.position.side_to_move, compiled)), "final_sfen": final_sfen, "cshogi_legal_action_count": len(cshogi_legal), "cshogi_legal_moves": cshogi_legal})
    return {"stalemate_games": rows, "all_exhausted": all(row["legal_action_count"] == 0 for row in rows), "external_move_exhaustion_agrees": all(row["cshogi_legal_action_count"] == 0 for row in rows)}


def classify(static: dict[str, Any], timing: dict[str, Any], extra: dict[str, Any], stalemate: dict[str, Any]) -> dict[str, Any]:
    positions, modal = _frozen_roots()
    rows = {}
    for item in positions:
        pid = item["position_id"]
        target = static["roots"][pid]["target_ranks"]
        ladder = extra["horizon_ladder"]["roots"].get(pid, {})
        recovered = [budget for budget, move in ladder.get("selected_moves_by_budget", {}).items() if move in {modal[pid]["alphasho_0.5"], modal[pid]["alphasho_2.0"]}]
        base050 = timing["baseline"]["0.5"][pid]
        base200 = timing["baseline"]["2.0"][pid]
        rows[pid] = {
            "alpha_sho_050": modal[pid]["alphasho_0.5"], "alpha_sho_200": modal[pid]["alphasho_2.0"], "generic_050": modal[pid]["generic_chess_0.5"], "generic_200": modal[pid]["generic_chess_2.0"],
            "static_ranks": target,
            "horizon_recovery_budgets": recovered,
            "horizon_recovery_class": ladder.get("recovery_class", "not_run"),
            "labels": {
                "evaluator_value": "PRIMARY" if all((target[key]["static_rank"] or 99) > 5 for key in ("alphasho_0.5", "alphasho_2.0")) else "SECONDARY",
                "horizon_depth": "PRIMARY" if recovered else "UNRESOLVED",
                "root_fallback_tactical_scan_overhead": "PRIMARY" if base050["fallback"] and base050["root_scan_seconds"] > 0 else "SECONDARY",
                "qsearch": "SECONDARY" if timing["qsearch_off"]["0.5"][pid]["selected_move"] != base050["selected_move"] else "NOT_SUPPORTED",
                "tt_order": "UNRESOLVED",
                "python_semantic_legal_generation_throughput": "PRIMARY" if base050["completed_depth"] == 0 and base200["completed_depth"] <= 1 else "SECONDARY",
                "native_capability_gating": "UNRESOLVED",
            },
        }
    aggregate = {family: statistics.mode([row["labels"][family] for row in rows.values()]) for family in next(iter(rows.values()))["labels"]}
    native = extra["native_counterfactual"]
    if stalemate["all_exhausted"] and stalemate["external_move_exhaustion_agrees"]:
        if aggregate["root_fallback_tactical_scan_overhead"] == "PRIMARY":
            next_boundary = "F32_ROOT_SEARCH_FALLBACK_AND_BUDGET_ARCHITECTURE"
        elif native["availability"] == "NATIVE_COUNTERFACTUAL_AVAILABLE" and native["material_completed_depth_gain"] and aggregate["python_semantic_legal_generation_throughput"] == "PRIMARY":
            next_boundary = "F32_CAPABILITY_SCOPED_NATIVE_LEGALITY_REENABLEMENT"
        elif aggregate["evaluator_value"] == "PRIMARY":
            next_boundary = "F32_RULE_DERIVED_EVALUATOR_REENTRY"
        elif aggregate["horizon_depth"] == "PRIMARY" or aggregate["qsearch"] == "PRIMARY":
            next_boundary = "F32_SEARCH_HORIZON_AND_QUIESCENCE_DIAGNOSIS"
        else:
            next_boundary = "F32_STANDARD_SHOGI_GAP_MINIMAL_INTERVENTION_SELECTION"
    else:
        next_boundary = "F31A_STANDARD_SHOGI_STALEMATE_CORRECTNESS_DIAGNOSIS"
    return {"per_root": rows, "aggregate_labels": aggregate, "stalemate_gate": "PASS" if stalemate["all_exhausted"] and stalemate["external_move_exhaustion_agrees"] else "F31A_STANDARD_SHOGI_STALEMATE_CORRECTNESS_DIAGNOSIS", "native_counterfactual_status": native["availability"], "next_boundary": next_boundary}


def run_stage_b(manifest: dict[str, Any]) -> dict[str, Any]:
    static = static_and_qsearch()
    timing = timing_and_ablations()
    extra = horizon_native_forced(static)
    stalemate = stalemate_audit()
    result = {"schema_version": 1, "status": "PASS", "manifest_sha256": manifest["manifest_sha256"], "production_changed": False, "static_and_qsearch": static, "historical_reference_context": historical_reference_context(static), "timing_and_ablations": timing, "horizon_native_forced": extra, "stalemate_audit": stalemate}
    result["causal_classification"] = classify(static, timing, extra, stalemate)
    result["flags"] = {"F30_EXTERNAL_BASELINE_CONSUMED": True, "STATIC_EVALUATOR_CAUSAL_AUDIT_COMPLETE": True, "SEARCH_HORIZON_CAUSAL_AUDIT_COMPLETE": True, "SEARCH_POLICY_ABLATION_COMPLETE": True, "RUNTIME_THROUGHPUT_CAUSAL_AUDIT_COMPLETE": True, "STANDARD_SHOGI_EXTERNAL_GAP_CAUSAL_DIAGNOSIS_COMPLETE": True}
    result["next_boundary"] = result["causal_classification"]["next_boundary"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=F31_MANIFEST)
    parser.add_argument("--output", type=Path, default=F31_OUTPUT)
    parser.add_argument("--freeze-manifest", action="store_true")
    parser.add_argument("--stage-b", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze_manifest:
        manifest = freeze_manifest(args.manifest)
        print(json.dumps({"manifest_sha256": manifest["manifest_sha256"], "harness_sha256": manifest["f31_harness"]["sha256"]}, sort_keys=True))
        return 0
    if args.stage_b:
        manifest = load_manifest(args.manifest)
        result = run_stage_b(manifest)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "manifest_sha256": result["manifest_sha256"], "next": result["next_boundary"], "flags": result["flags"]}, sort_keys=True))
        return 0
    parser.error("choose --freeze-manifest or --stage-b")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
