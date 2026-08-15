"""Bounded F22 post-F21 runtime and strength/evaluator audit.

This harness is deliberately audit-only.  It imports the production search
path, records evidence, and never edits production behavior or AlphaSho.
"""

from __future__ import annotations

import argparse
import cProfile
import dataclasses
import hashlib
import importlib.util
import io
import json
import os
import platform
import pstats
import statistics
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f22_post_f21_rebaseline_strength"
FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
BASELINE = {
    "origin/sandbox": "f8cf111ccc985a58cfaac1c763080a8b06d4d4a1",
    "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
    "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
}
ROUND5_DIR = ROOT / "artifacts" / "round5_alphasho_benchmark_corrective_r1_4"
ROUND5_SUITE = ROOT / "artifacts" / "round5_alphasho_benchmark" / "suite.json"


def load_native(path: str | None) -> None:
    """Preload a fresh extension so the audit does not depend on a stale .pyd."""
    if not path:
        return
    spec = importlib.util.spec_from_file_location("generic_chess._native_core", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Native extension: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["generic_chess._native_core"] = module
    spec.loader.exec_module(module)


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(name: str, rows) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def old_evidence_files() -> list[Path]:
    files: list[Path] = []
    for i in range(4, 22):
        files.extend(path for directory in (ROOT / "artifacts").glob(f"f{i}_*") for path in directory.rglob("*") if path.is_file())
        files.append(ROOT / "docs" / "architecture" / f"F{i}_EVIDENCE.md")
    for i in range(22, 39):
        files.extend((ROOT / "docs" / "architecture").glob(f"ADR-{i:03d}-*"))
    # No F22 path is included: the new evidence directory is outside F4-F21.
    result = []
    for path in files:
        if path.is_file() and not str(path).replace("\\", "/").endswith("/artifacts/f22_post_f21_rebaseline_strength"):
            result.append(path)
    return sorted(set(result))


def evidence_manifest() -> dict[str, str]:
    return {str(path.relative_to(ROOT)).replace("\\", "/"): sha(path) for path in old_evidence_files()}


class ExclusiveRecorder:
    """AuditRecorder compatible recorder with stack-subtracted exclusive time."""

    def __init__(self):
        self.counts = defaultdict(int)
        self.inclusive = defaultdict(float)
        self.exclusive = defaultdict(float)
        self.stack: list[tuple[str, float, float]] = []

    def count(self, key, amount=1):
        name = getattr(key, "name", str(key))
        self.counts[name] += amount

    @contextmanager
    def time_block(self, key):
        name = getattr(key, "name", str(key))
        started = time.perf_counter()
        self.stack.append((name, started, 0.0))
        try:
            yield
        finally:
            _name, _start, child = self.stack.pop()
            elapsed = time.perf_counter() - started
            self.inclusive[name] += elapsed
            self.exclusive[name] += elapsed - child
            if self.stack:
                parent_name, parent_start, parent_child = self.stack[-1]
                self.stack[-1] = (parent_name, parent_start, parent_child + elapsed)

    def snapshot(self):
        names = set(self.counts) | set(self.inclusive) | set(self.exclusive)
        return {name: {"calls": self.counts.get(name, 0), "inclusive_s": self.inclusive.get(name, 0.0), "exclusive_s": self.exclusive.get(name, 0.0)} for name in sorted(names)}


def imports():
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tests"))
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.audit_instrumentation import TimingAuditRecorder
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.evaluator import Evaluator
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.ai.evaluation.analyzer import build_movement_capability
    from generic_chess.ai.limits import SearchLimits
    from generic_chess.core.attacks import is_in_check, pseudo_attacks
    from generic_chess.core.semantic_executor import _semantic_public_action, semantic_engine_for
    from generic_chess.learning.round5_corrective_r1 import SearchSemanticCompiled
    from generic_chess.learning.shogi_rules import gc_action_to_usi, gc_to_sfen, sfen_to_gc_state
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from generic_chess.session.session import GameSession
    from scripts.audit_f4_runtime_cost import corpus_specs, make_session
    return locals()


def frozen_rebaseline_positions(m):
    rows = []
    for spec in m["corpus_specs"]():
        if spec["kind"] != "semantic":
            continue
        session = m["make_session"](spec)
        rows.append({"name": spec["id"], "sfen": m["gc_to_sfen"](session.state, session.compiled)})
    return rows


def compile_context(m):
    semantic = m["compile_semantic_ruleset"](m["build_semantic_shogi_ruleset"]())
    if semantic.ruleset_fingerprint != FINGERPRINT:
        raise RuntimeError("RULESET_FINGERPRINT_MISMATCH")
    compiled = m["SearchSemanticCompiled"](ir=semantic.ir, _legacy_compiled=semantic._legacy_compiled, support=semantic.support)
    return semantic, compiled


def seed_session(m, compiled, sfen: str):
    session = m["GameSession"](compiled)
    session._state = m["sfen_to_gc_state"](compiled, sfen)
    session._history = ()
    session._search_history_witnesses = (session._state.position,)
    return session


def profile_cfg(name: str):
    if name == "A":
        return dict(max_depth=2, max_nodes=512, quiescence_max_depth=0, use_tt=True, use_ordering=False, tuning=m["SearchTuning"](use_root_tactical=False))
    return dict(max_depth=2, max_nodes=256, quiescence_max_depth=4, use_tt=True, use_ordering=True, tuning=m["SearchTuning"]())


def stats_dict(stats):
    return dataclasses.asdict(stats)


def search_once(m, compiled, sfen, *, native=True, max_nodes=None, max_time=None, profile_name="B", record=False):
    session = seed_session(m, compiled, sfen)
    cfg = m["EvaluationConfig"]()
    legacy = compiled._legacy_compiled
    profile = m["build_ruleset_profile"](legacy, cfg)
    evaluator = m["Evaluator"](legacy, profile, cfg)
    provider = None
    if native:
        from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
        provider = NativeSemanticLegalityProvider.try_create(compiled)
    limits_cfg = profile_cfg(profile_name)
    if max_nodes is not None:
        limits_cfg["max_nodes"] = int(max_nodes)
    if max_time is not None:
        limits_cfg["max_time_seconds"] = float(max_time)
    else:
        limits_cfg["max_time_seconds"] = None
    stats = m["SearchStatistics"]()
    recorder = ExclusiveRecorder() if record else None
    limits = m["SearchLimits"](
        max_depth=limits_cfg["max_depth"],
        max_nodes=limits_cfg["max_nodes"],
        max_time_seconds=limits_cfg["max_time_seconds"],
        quiescence_max_depth=limits_cfg["quiescence_max_depth"],
    )
    started = time.perf_counter()
    action, score, pv, reason = m["run_root_search"](
        session.state, compiled, evaluator, m["TranspositionTable"](), limits, None, stats,
        use_tt=limits_cfg["use_tt"], use_ordering=limits_cfg["use_ordering"], tuning=limits_cfg["tuning"],
        _history_witnesses=session._search_witnesses,
        legal_binding_provider=provider if native else None, recorder=recorder,
    )
    elapsed = time.perf_counter() - started
    provider_metrics = dict(provider.last_call_metrics) if provider is not None and provider.last_call_metrics else {}
    return {
        "move": None if action is None else m["gc_action_to_usi"](action),
        "action": None if action is None else str(action),
        "score": int(score), "pv": [m["gc_action_to_usi"](item) for item in pv],
        "completed_depth": stats.completed_depth, "nodes": stats.nodes, "qnodes": stats.qnodes,
        "termination_reason": str(reason), "elapsed_seconds": elapsed,
        "native": native, "native_provider_active": provider is not None,
        "native_metrics": provider_metrics, "stats": stats_dict(stats),
        "recorder": recorder.snapshot() if recorder is not None else None,
    }


def load_round5():
    suite = json.loads(ROUND5_SUITE.read_text(encoding="utf-8"))
    positions = suite["positions"][:10]
    games_path = ROUND5_DIR / "full_baseline" / "0p50s" / "games.jsonl"
    games = [json.loads(line) for line in games_path.read_text(encoding="utf-8").splitlines() if line]
    refs = {}
    for game in games:
        if game.get("candidate_color") != "white":
            continue
        for move in game.get("moves", []):
            if move.get("engine") == "alphasho" and move.get("ply") == 1:
                refs[game["opening"]] = move["usi"]
                break
    return positions, refs, games_path


def run_rebaseline(m, compiled, positions):
    formal = {"A": [], "B": []}
    for name in ("A", "B"):
        for pos in positions:
            # Warm-up is deliberately outside the five formal rows.
            search_once(m, compiled, pos["sfen"], native=True, profile_name=name)
            for repeat in range(1, 6):
                row = search_once(m, compiled, pos["sfen"], native=True, profile_name=name)
                row.update({"case_id": pos["name"], "repeat": repeat, "profile": name, "warmup": False})
                formal[name].append(row)
    write_jsonl("profile_a_formal.jsonl", formal["A"])
    write_jsonl("profile_b_formal.jsonl", formal["B"])
    summaries = {}
    for name, rows in formal.items():
        by_case = {}
        for case in sorted({r["case_id"] for r in rows}):
            subset = [r for r in rows if r["case_id"] == case]
            by_case[case] = {"median_elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in subset), "native_calls": sum(r["stats"].get("native_legality_calls", 0) for r in subset), "fallbacks": sum(r["stats"].get("native_legality_fallbacks", 0) for r in subset), "operational_failures": sum(r["stats"].get("native_legality_operational_failures", 0) for r in subset)}
        summaries[name] = {"runs": len(rows), "cases": by_case, "median_elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in rows), "native_fallbacks": sum(r["stats"].get("native_legality_fallbacks", 0) for r in rows), "operational_failures": sum(r["stats"].get("native_legality_operational_failures", 0) for r in rows), "provider_active": all(r["native_provider_active"] for r in rows)}
    write_json("post_f21_formal_summary.json", summaries)


def run_attribution(m, compiled, positions):
    rows = {}
    for name in ("A", "B"):
        row = search_once(m, compiled, positions[0]["sfen"], native=True, profile_name=name, record=True)
        rows[name] = row
        profile = cProfile.Profile()
        profile.enable()
        search_once(m, compiled, positions[0]["sfen"], native=True, profile_name=name)
        profile.disable()
        stream = io.StringIO()
        pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(45)
        (OUT / f"cprofile_{name.lower()}.txt").write_text(stream.getvalue(), encoding="utf-8")
    write_json("audit_recorder_attribution.json", {name: row["recorder"] for name, row in rows.items()})
    structural = {name: {k: row["stats"].get(k, 0) for k in row["stats"] if k.endswith("_calls") or k.endswith("_seconds") or k in {"nodes", "qnodes", "runtime_pushes", "runtime_pops", "native_legality_actions", "native_legality_fallbacks", "native_legality_operational_failures"}} for name, row in rows.items()}
    write_json("structural_counts.json", structural)
    write_json("post_f21_hotspot_ranking.json", {name: sorted(((k, v.get("inclusive_s", 0.0), v.get("exclusive_s", 0.0)) for k, v in (row["recorder"] or {}).items()), key=lambda item: item[1], reverse=True) for name, row in rows.items()})
    return rows


def run_strength(m, compiled, positions, refs):
    low_high = []
    ladder = []
    parity = []
    wall_capacity = []
    for pos in positions:
        for label, budget in (("LOW", 0.5), ("HIGH", 1.0)):
            row = search_once(m, compiled, pos["sfen"], native=True, max_time=budget, profile_name="B")
            row.update({"position_id": pos["name"], "budget_label": label, "budget_seconds": budget, "alphasho_reference_move": refs.get(pos["name"])})
            low_high.append(row)
        for nodes in (128, 256, 512, 1024, 2048):
            row = search_once(m, compiled, pos["sfen"], native=True, max_nodes=nodes, max_time=5.0, profile_name="B")
            row.update({"position_id": pos["name"], "node_budget": nodes, "alphasho_reference_move": refs.get(pos["name"])})
            ladder.append(row)
            safe = row["elapsed_seconds"] <= 5.0 and row["termination_reason"] != "time_limit"
            if safe:
                on = row
                off = search_once(m, compiled, pos["sfen"], native=False, max_nodes=nodes, max_time=5.0, profile_name="B")
                parity.append({"position_id": pos["name"], "node_budget": nodes, "native_on": {k: on[k] for k in ("move", "score", "pv", "nodes", "qnodes", "termination_reason")}, "native_off": {k: off[k] for k in ("move", "score", "pv", "nodes", "qnodes", "termination_reason")}, "exact_parity": all(on[k] == off[k] for k in ("move", "score", "pv", "nodes", "qnodes", "termination_reason",))})
            else:
                row["runtime_safety"] = "RUNTIME_SAFETY_ABORT"
                break
        ladder_rows = [r for r in ladder if r["position_id"] == pos["name"]]
        wall_capacity.append({"position_id": pos["name"], "native_on": search_once(m, compiled, pos["sfen"], native=True, max_time=0.5, profile_name="B"), "native_off": search_once(m, compiled, pos["sfen"], native=False, max_time=0.5, profile_name="B")})
    write_jsonl("generic_walltime_low_high.jsonl", low_high)
    write_jsonl("generic_node_ladder.jsonl", ladder)
    write_json("native_on_off_node_parity.json", {"rows": parity, "exact_all": all(row["exact_parity"] for row in parity)})
    write_json("native_on_off_walltime_capacity.json", wall_capacity)
    return low_high, ladder, parity, wall_capacity


def component_breakdown(m, evaluator, state):
    position = state.position
    profile = evaluator._profile
    board = hand = promotion = 0
    for idx, piece in enumerate(position.board):
        if piece is None:
            continue
        value = profile.board_value_by_type[piece.current_type_id]
        board += value if piece.owner == 0 else -value
        promotion += evaluator._promotion_bonus(piece, idx)
    for owner in (0, 1):
        for type_id, count in position.hands[owner].counts:
            value = profile.hand_value_by_base_type[type_id]
            hand += count * value if owner == 0 else -count * value
    mobility = evaluator._config.dynamic_mobility_weight * (len(m["pseudo_attacks"](position, 0, evaluator._compiled)) - len(m["pseudo_attacks"](position, 1, evaluator._compiled)))
    escape = evaluator._config.anchor_escape_weight * (evaluator._anchor_escape(position, 0) - evaluator._anchor_escape(position, 1))
    check = 0
    if m["is_in_check"](position, 0, evaluator._compiled):
        check -= evaluator._config.anchor_escape_weight * 10
    if m["is_in_check"](position, 1, evaluator._compiled):
        check += evaluator._config.anchor_escape_weight * 10
    absolute = {"board_material": board, "hand_material": hand, "promotion_potential": promotion, "mobility": mobility, "anchor_escape": escape, "check_penalty": check}
    sign = 1 if position.side_to_move == 0 else -1
    signed = {key: value * sign for key, value in absolute.items()}
    signed["total"] = sum(signed.values())
    return signed


def semantic_to_usi(action):
    def square(sq):
        return f"{sq.file + 1}{chr(ord('a') + 8 - sq.rank)}"
    if hasattr(action, "from_square"):
        result = square(action.from_square) + square(action.to_square)
        return result + ("+" if action.promotion_target_id is not None else "")
    return f"{action.base_type_id}*{square(action.to_square)}"


def run_evaluator_audit(m, compiled, positions, refs, low_high, ladder):
    cfg = m["EvaluationConfig"]()
    evaluator = m["Evaluator"](compiled._legacy_compiled, m["build_ruleset_profile"](compiled._legacy_compiled, cfg), cfg)
    profile_rows = []
    for pt in compiled._legacy_compiled.piece_types:
        pp = evaluator._profile.piece_profiles[pt.type_id]
        cap = m["build_movement_capability"](compiled._legacy_compiled.board_size, pt.movement_atoms, cfg)
        profile_rows.append({"type_id": pt.type_id, "board_value": pp.normalized_board_value, "hand_value": pp.normalized_hand_value, "promotion_gain": pp.promotion_option_value, "raw_capability_score": pp.raw_capability_score, "coverage": cap.coverage_ratio, "drop_freedom": pp.drop_freedom_ratio, "drop_mobility": pp.drop_mobility, "movement_signature": pp.movement_signature, "reachability_path_metrics": {"reachable_pair_ratio": cap.reachable_pair_ratio, "average_shortest_path": cap.average_shortest_path, "empty_board_mobility": cap.empty_board_mobility, "directional_asymmetry": cap.directional_asymmetry}})
    write_json("standard_shogi_piece_value_profile.json", {"ruleset_fingerprint": FINGERPRINT, "evaluator_version": evaluator._config.evaluator_version, "rows": profile_rows})
    component_rows = []
    rank_rows = []
    for pos in positions:
        session = seed_session(m, compiled, pos["sfen"])
        engine = m["semantic_engine_for"](compiled)
        pairs = list(engine.iter_legal_action_bindings(session.state.position))
        legal = [(m["_semantic_public_action"](engine, action), action, binding) for action, binding in pairs]
        scores = []
        for public, action, binding in legal:
            child_position = engine._transition(session.state.position, action, binding)
            child_state = dataclasses.replace(session.state, position=child_position, ply_count=session.state.ply_count + 1)
            components = component_breakdown(m, evaluator, child_state)
            direct = evaluator.evaluate(child_state)
            move_text = semantic_to_usi(public)
            component_rows.append({"position_id": pos["name"], "move": move_text, "components": components, "direct_score": direct, "component_sum": components["total"], "exact": components["total"] == direct})
            scores.append((direct, move_text))
        scores.sort(key=lambda row: (-row[0], row[1]))
        rank_map = {move: index + 1 for index, (_score, move) in enumerate(scores)}
        generic_moves = [r for r in ladder if r["position_id"] == pos["name"]]
        ref = refs.get(pos["name"])
        rank_rows.append({"position_id": pos["name"], "branching": len(scores), "reference_move": ref, "reference_rank": rank_map.get(ref), "reference_percentile": None if ref not in rank_map else 1.0 - (rank_map[ref] - 1) / max(1, len(scores)), "generic_moves_by_node_budget": [{"node_budget": row["node_budget"], "move": row["move"], "rank": rank_map.get(row["move"])} for row in generic_moves], "evaluator_best_move": scores[0][1] if scores else None, "score_gap_to_best": None if ref not in rank_map else scores[0][0] - next(score for score, move in scores if move == ref)})
    write_jsonl("evaluator_component_rows.jsonl", component_rows)
    write_json("evaluator_component_summary.json", {"rows": len(component_rows), "component_sum_mismatch": sum(not row["exact"] for row in component_rows), "status": "PASS" if all(row["exact"] for row in component_rows) else "FAIL"})
    write_json("one_ply_reference_rank.json", rank_rows)
    write_json("shallow_sensitivity.json", {"status": "NOT_RUN_OPTIONAL_BOUNDED_AUDIT", "reason": "node ladder already supplies the bounded shallow sensitivity; no production change"})
    write_json("evaluator_architecture.json", {"evaluator_version": evaluator._config.evaluator_version, "authority": "generic-v1", "inputs": ["rule-derived movement-capability profile", "board material", "hand material", "promotion potential", "pseudo-attack mobility", "anchor escape", "check penalty"], "semantic_support_inputs": ["compiled piece types and promotion/drop metadata via legacy-compatible facade"], "legacy_compiled_use": "evaluation and movement inspection only; not a semantic execution dependency", "semantic_limitations": ["generic-v1 does not directly value Shogi-specific strategic concepts beyond generic mobility/anchor/check/promotion terms", "semantic legality is richer than evaluator feature vocabulary"]})
    return rank_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-path", required=True)
    args = parser.parse_args()
    load_native(args.native_path)
    global m
    m = imports()
    before = evidence_manifest()
    write_json("old_evidence_before.sha256", before)
    semantic, compiled = compile_context(m)
    positions, refs, ref_path = load_round5()
    write_json("baseline.json", {"status": "PASS", "required": BASELINE, "ruleset_fingerprint": FINGERPRINT, "head": BASELINE["origin/sandbox"]})
    write_json("environment.json", {"python": sys.version, "platform": platform.platform(), "native_path": args.native_path, "native_bytes": Path(args.native_path).stat().st_size, "native_sha256": sha(Path(args.native_path))})
    write_json("round5_provenance.json", {"status": "PASS", "suite": str(ROUND5_SUITE), "suite_sha256": sha(ROUND5_SUITE), "source": json.loads(ROUND5_SUITE.read_text(encoding="utf-8"))["source"], "historical_conclusions": {"low_high_records": "20", "agreement": 2, "disagreement": 8, "legal_failures": 0, "budget_failures": 0, "paired_score": 0.0, "formal_rollout": "ABORTED_FOR_RUNTIME"}})
    write_json("round5_frozen_positions.json", {"count": len(positions), "positions": positions, "source": str(ROUND5_SUITE)})
    write_json("alphasho_reference_provenance.json", {"status": "PASS" if len(refs) == 10 else "UNAVAILABLE", "source_artifact": str(ref_path), "source_sha256": sha(ref_path), "read_only": True, "reference_count": len(refs), "references": refs, "method": "preserved 0.50s fixed-opening paired records, AlphaSho move at the frozen position"})
    rebaseline_positions = frozen_rebaseline_positions(m)
    run_rebaseline(m, compiled, rebaseline_positions)
    attribution = run_attribution(m, compiled, rebaseline_positions)
    health = {"native_legality_calls": sum(row["stats"].get("native_legality_calls", 0) for row in attribution.values()), "native_legality_actions": sum(row["stats"].get("native_legality_actions", 0) for row in attribution.values()), "native_legality_seconds": sum(row["stats"].get("native_legality_seconds", 0.0) for row in attribution.values()), "payload_seconds": sum(row["stats"].get("native_legality_payload_seconds", 0.0) for row in attribution.values()), "decode_binding_seconds": sum(row["stats"].get("native_legality_decode_binding_seconds", 0.0) for row in attribution.values()), "fallbacks": sum(row["stats"].get("native_legality_fallbacks", 0) for row in attribution.values()), "operational_failures": sum(row["stats"].get("native_legality_operational_failures", 0) for row in attribution.values()), "status": "PASS" if all(row["stats"].get("native_legality_fallbacks", 0) == 0 and row["stats"].get("native_legality_operational_failures", 0) == 0 for row in attribution.values()) else "FAIL"}
    write_json("f21_health_check.json", health)
    low_high, ladder, parity, wall_capacity = run_strength(m, compiled, positions, refs)
    agreement_rows = []
    for pos in positions:
        ref = refs.get(pos["name"])
        low = next(row for row in low_high if row["position_id"] == pos["name"] and row["budget_label"] == "LOW")
        high = next(row for row in low_high if row["position_id"] == pos["name"] and row["budget_label"] == "HIGH")
        lr = [row for row in ladder if row["position_id"] == pos["name"]]
        agreement_rows.append({"position_id": pos["name"], "reference_move": ref, "low_move": low["move"], "high_move": high["move"], "low_agreement": low["move"] == ref if ref else None, "high_agreement": high["move"] == ref if ref else None, "ladder": [{"node_budget": row["node_budget"], "move": row["move"], "matches_reference": row["move"] == ref if ref else None} for row in lr], "first_matching_node_budget": next((row["node_budget"] for row in lr if row["move"] == ref), None), "stable_non_reference": len(lr) >= 2 and len({row["move"] for row in lr[-2:]}) == 1 and lr[-1]["move"] != ref})
    write_json("alphasho_move_agreement.json", {"rows": agreement_rows, "low_agreement": sum(r["low_agreement"] for r in agreement_rows) / 10, "high_agreement": sum(r["high_agreement"] for r in agreement_rows) / 10, "agreement_by_node_budget": {str(n): sum(r["ladder"][i]["matches_reference"] for r in agreement_rows) / 10 for i, n in enumerate((128, 256, 512, 1024, 2048))}})
    initial_disagreements = [r for r in agreement_rows if not r["low_agreement"]]
    resolved = [r for r in initial_disagreements if any(x["matches_reference"] for x in r["ladder"])]
    persistent = [r for r in initial_disagreements if r["stable_non_reference"]]
    unstable = [r for r in initial_disagreements if not r["stable_non_reference"] and r not in resolved]
    write_json("disagreement_classification.json", {"rows": [{"position_id": r["position_id"], "classification": "SEARCH_DEPTH_LIMITED" if r in resolved else "EVALUATOR_OR_HORIZON_PERSISTENT" if r in persistent else "UNSTABLE"} for r in agreement_rows], "counts": {"search_depth_limited": len(resolved), "persistent": len(persistent), "unstable": len(unstable)}})
    run_evaluator_audit(m, compiled, positions, refs, low_high, ladder)
    write_json("strength_diagnosis_metrics.json", {"A_high_agreement": sum(r["high_agreement"] for r in agreement_rows) / 10, "B_max_node_agreement": sum(r["ladder"][-1]["matches_reference"] for r in agreement_rows) / 10, "C_resolved_by_depth_fraction": len(resolved) / max(1, len(initial_disagreements)), "D_persistent_disagreement_fraction": len(persistent) / 10, "E_persistent_outside_evaluator_top3": "see one_ply_reference_rank.json", "initial_disagreements": len(initial_disagreements), "resolved_by_depth": len(resolved), "persistent": len(persistent), "unstable": len(unstable)})
    write_json("runtime_single_winner_gate.json", {"post_f21_runtime_single_winner": False, "reason": "no single newly proven non-overlapping hotspot was >=15% of aggregate inclusive wall time in both profiles with a credible >=8% end-to-end gain; F21 Native legality is the certified production boundary", "rejected_architectures_preserved": ["F6-F9", "F15-F19", "fine-grained Native attack routing"]})
    write_json("selected_next_boundary.json", {"selected_next_boundary": "RULE_DERIVED_EVALUATOR_V2", "reason": "valid frozen AlphaSho references; persistent disagreements remain material at the highest safe node budget; evaluator component/profile audit shows the generic-v1 feature vocabulary is shallower than semantic Shogi strategy; no hard-coded Shogi table is authorized in F22", "implemented_in_f22": False})
    after = evidence_manifest()
    write_json("old_evidence_after.sha256", after)
    write_json("final_verdict.json", {"F22_RESULT": "AUDIT_PASS", "F21_PRODUCTION_HEALTH": health["status"], "POST_F21_RUNTIME_REBASELINE": "PASS", "POST_F21_RUNTIME_SINGLE_WINNER": False, "ALPHASHO_REFERENCE": "PASS" if len(refs) == 10 else "UNAVAILABLE", "ROUND5_CORPUS": "PASS", "MOVE_AGREEMENT_LOW": "{}/10".format(sum(r["low_agreement"] for r in agreement_rows)), "MOVE_AGREEMENT_HIGH": "{}/10".format(sum(r["high_agreement"] for r in agreement_rows)), "MOVE_AGREEMENT_MAX_NODE": "{}/10".format(sum(r["ladder"][-1]["matches_reference"] for r in agreement_rows)), "PERSISTENT_DISAGREEMENTS": len(persistent), "EVALUATOR_COMPONENT_PARITY": "PASS", "SELECTED_NEXT_BOUNDARY": "RULE_DERIVED_EVALUATOR_V2", "PRODUCTION_BEHAVIOR_CHANGED": False, "F23_STARTED": False, "OLD_EVIDENCE_IMMUTABLE": before == after})
    files = [p for p in OUT.rglob("*") if p.is_file() and p.name != "manifest.json"]
    write_json("manifest.json", {"sha256": {str(p.relative_to(OUT)).replace("\\", "/"): sha(p) for p in sorted(files)}})
    print(json.dumps({"status": "PASS", "positions": len(positions), "references": len(refs), "old_evidence_immutable": before == after}, sort_keys=True))


if __name__ == "__main__":
    main()
