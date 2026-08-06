"""Native-readiness audit orchestrator (node budgets, instrumentation,
Core microbenchmarks, cache timing, profiler subset).

Normal benchmark runs never enable instrumentation; instrumented audits
inject a :class:`TimingAuditRecorder` and report its overhead separately.
"""

from __future__ import annotations

import cProfile
import io
import json
import os
import pstats
import shutil
import subprocess
import sys
import time
import tracemalloc
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...core.actions import Action
from ...core.movegen import legal_actions
from ...rules.compiled import CompiledRuleSet
from ...session.session import GameSession
from ..alphabeta.player import AlphaBetaPlayer
from ..alphabeta.tuning import SearchTuning
from ..audit_instrumentation import AuditMetric, TimingAuditRecorder
from ..evaluation.cache import EvaluationProfileCache, _profile_to_dict
from ..evaluation.config import EvaluationConfig
from ..limits import SearchLimits
from . import core_profiling
from .audit_schema import (
    PositionFixtureSpec,
    RuleSetFixtureSpec,
    medians_min_max,
    write_json,
)
from .audit_suite import (
    FULL_MANIFEST_PATH,
    REPRESENTATIVE_FIXTURE_IDS,
    build_compiled,
    build_manifest,
    build_session,
    classify_ruleset,
    smoke_ruleset_specs,
    standard_ruleset_specs,
)
from .position_mining import mine_suite
from .targeted_fixtures import build_targeted_fixtures, uncovered_targeted_categories


@dataclass(frozen=True, slots=True)
class AuditConfig:
    suite_name: str = "smoke"
    node_budgets: tuple[int, ...] = (1000,)
    repeats: int = 1
    instrument: bool = False
    positions_limit: int | None = None
    span_positions: int | None = None
    max_board_size: int | None = None
    large_budget_cap: int | None = None
    out_dir: str | Path = "artifacts/native_readiness/latest"
    run_core_profiling: bool = True
    run_profiler: bool = False
    profile_fixture_count: int = 2
    tuning: SearchTuning = SearchTuning()


def ruleset_specs_for(suite_name: str) -> tuple[RuleSetFixtureSpec, ...]:
    if suite_name == "smoke":
        return smoke_ruleset_specs()
    if suite_name == "standard":
        return standard_ruleset_specs()
    if suite_name == "representative":
        return tuple(
            spec
            for spec in standard_ruleset_specs()
            if spec.fixture_id in REPRESENTATIVE_FIXTURE_IDS
        )
    raise ValueError(f"unknown suite {suite_name!r}")


def _manifest_dict(manifest) -> dict:
    return {
        "schema_version": manifest.schema_version,
        "suite_version": manifest.suite_version,
        "generator_version": manifest.generator_version,
        "commit": manifest.commit,
        "rulesets": [
            {
                "fixture_id": r.fixture_id,
                "generator_mode": r.generator_mode,
                "board_size": r.board_size,
                "ruleset_seed": r.ruleset_seed,
                "generator_options": dict(r.generator_options),
                "movement_buckets": list(r.movement_buckets),
                "promotion_buckets": list(r.promotion_buckets),
                "drop_buckets": list(r.drop_buckets),
            }
            for r in manifest.rulesets
        ],
        "positions": [
            {
                "fixture_id": p.fixture_id,
                "ruleset_fixture_id": p.ruleset_fixture_id,
                "action_prefix": [dict(a) for a in p.action_prefix],
                "expected_categories": list(p.expected_categories),
                "playout_seed": p.playout_seed,
            }
            for p in manifest.positions
        ],
    }


def write_full_suite_manifest(path: str | Path) -> dict:
    """Mine the full standard suite and write the versioned manifest JSON."""
    specs = ruleset_specs_for("standard")
    compiled_map = {s.fixture_id: build_compiled(s) for s in specs}
    classified = [
        classify_ruleset(compiled_map[s.fixture_id], s) for s in specs
    ]
    positions = mine_suite(
        tuple(classified), playout_seed=1, max_games=4, max_plies=80, max_positions=3
    )
    manifest = build_manifest("standard", tuple(classified), positions, environment_info()["commit"])
    data = _manifest_dict(manifest)
    write_json(path, data)
    return data


def environment_info() -> dict:
    try:
        commit = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            .stdout.strip()
        )
    except Exception:
        commit = "unknown"
    return {
        "os": sys.platform,
        "python": sys.version,
        "cpu": os.environ.get("PROCESSOR_IDENTIFIER") or "unknown",
        "logical_cpus": os.cpu_count(),
        "commit": commit,
        "debug_build": not __debug__,
    }


def _first_action(state, compiled) -> Action | None:
    actions = legal_actions(state, compiled)
    return actions[0] if actions else None


def _run_budget_fixture(
    compiled: CompiledRuleSet,
    player: AlphaBetaPlayer,
    spec: RuleSetFixtureSpec,
    pos: PositionFixtureSpec,
    budget: int,
    repeats: int,
    config: AuditConfig,
) -> list[dict]:
    session = build_session(spec, pos.action_prefix)[1]
    limits = SearchLimits(max_nodes=budget, max_depth=64, quiescence_max_depth=4)
    root_count = len(legal_actions(session.state, compiled))
    rows: list[dict] = []
    for repeat in range(repeats + 1):
        player.reset()
        started = time.perf_counter()
        decision = player.choose_action(session, limits)
        elapsed = time.perf_counter() - started
        if repeat == 0:
            continue  # warm-up run
        avg_branching = (
            round(decision.ordered_moves / decision.ordering_calls, 2)
            if decision.ordering_calls
            else None
        )
        rows.append(
            {
                "fixture_id": pos.fixture_id,
                "ruleset_id": spec.fixture_id,
                "board_size": compiled.board_size,
                "categories": list(pos.expected_categories),
                "movement_buckets": list(spec.movement_buckets),
                "promotion_buckets": list(spec.promotion_buckets),
                "drop_buckets": list(spec.drop_buckets),
                "budget": budget,
                "repeat": repeat,
                "nodes": decision.nodes,
                "qnodes": decision.qnodes,
                "main_nodes": decision.nodes,
                "total_nodes": decision.nodes + decision.qnodes,
                "elapsed_seconds": elapsed,
                "main_nps": round(decision.nodes / elapsed, 1) if elapsed else 0.0,
                "q_nps": round(decision.qnodes / elapsed, 1) if elapsed else 0.0,
                "total_nps": (
                    round((decision.nodes + decision.qnodes) / elapsed, 1)
                    if elapsed
                    else 0.0
                ),
                # Deprecated alias kept for old consumers; it equals total_nps.
                "nodes_per_second": (
                    round((decision.nodes + decision.qnodes) / elapsed, 1)
                    if elapsed
                    else 0.0
                ),
                "qnode_ratio": (
                    round(decision.qnodes / decision.nodes, 3)
                    if decision.nodes > 0
                    else None
                ),
                "qnode_share": (
                    round(
                        decision.qnodes
                        / (decision.nodes + decision.qnodes),
                        3,
                    )
                    if (decision.nodes + decision.qnodes) > 0
                    else 0.0
                ),
                "completed_depth": decision.completed_depth,
                "selective_depth": decision.selective_depth,
                "termination_reason": decision.termination_reason,
                "fallback": decision.termination_reason == "fallback",
                "tt_probes": decision.tt_probes,
                "tt_hits": decision.tt_hits,
                "tt_cutoffs": decision.tt_cutoffs,
                "beta_cutoffs": decision.beta_cutoffs,
                "pv_length": len(decision.principal_variation),
                "score": decision.score,
                "best_action": str(decision.action) if decision.action else None,
                "root_legal_actions": root_count,
                "avg_branching": avg_branching,
            }
        )
    return rows


def _aggregate_budget(rows: list[dict]) -> dict:
    total_nps = [r["total_nps"] for r in rows]
    main_nps = [r["main_nps"] for r in rows]
    q_nps = [r["q_nps"] for r in rows]
    depths = [r["completed_depth"] for r in rows]
    qratio = [r["qnode_ratio"] for r in rows]
    qshare = [r["qnode_share"] for r in rows]
    tt_rate = [
        r["tt_hits"] / r["tt_probes"] if r["tt_probes"] else 0.0 for r in rows
    ]
    return {
        "runs": len(rows),
        "main_nps": medians_min_max(main_nps),
        "q_nps": medians_min_max(q_nps),
        "total_nps": medians_min_max(total_nps),
        "deprecated_nodes_per_second": medians_min_max(total_nps),
        "completed_depth": medians_min_max([float(d) for d in depths]),
        "qnode_ratio": medians_min_max(qratio),
        "qnode_share": medians_min_max(qshare),
        "tt_hit_rate": medians_min_max(tt_rate),
        "fallback_runs": sum(1 for r in rows if r["fallback"]),
        "by_board_size": {
            str(size): medians_min_max(
                [r["nodes_per_second"] for r in rows if r["board_size"] == size]
            )
            for size in sorted({r["board_size"] for r in rows})
        },
        "by_movement_bucket": {
            bucket: medians_min_max(
                [
                    r["nodes_per_second"]
                    for r in rows
                    if bucket in r["movement_buckets"]
                ]
            )
            for bucket in sorted({b for r in rows for b in r["movement_buckets"]})
        },
        "by_board_size_total_nps": {
            str(size): medians_min_max(
                [r["total_nps"] for r in rows if r["board_size"] == size]
            )
            for size in sorted({r["board_size"] for r in rows})
        },
        "by_movement_bucket_total_nps": {
            bucket: medians_min_max(
                [r["total_nps"] for r in rows if bucket in r["movement_buckets"]]
            )
            for bucket in sorted({b for r in rows for b in r["movement_buckets"]})
        },
    }


def _run_instrumented(
    compiled: CompiledRuleSet,
    spec: RuleSetFixtureSpec,
    pos: PositionFixtureSpec,
    config: AuditConfig,
) -> dict:
    session = build_session(spec, pos.action_prefix)[1]
    player = AlphaBetaPlayer(
        compiled,
        use_disk_cache=False,
        tuning=config.tuning,
        profile_cache=EvaluationProfileCache(use_disk=False),
    )
    limits = SearchLimits(max_nodes=10_000, max_depth=64, quiescence_max_depth=4)
    player.reset()
    recorder = TimingAuditRecorder()
    started = time.perf_counter()
    decision = player.choose_action(session, limits, recorder=recorder)
    wall = time.perf_counter() - started
    snap = recorder.snapshot()
    times = dict(snap["times"])
    # Phase timing is inclusive: quiescence is measured around the whole
    # qsearch call tree; main_search is the remaining wall time.
    quiescence_inclusive = times.get("QUIESCENCE", 0.0)
    main_inclusive = max(0.0, wall - quiescence_inclusive)
    # Subsystem timing is direct-measured: only the specific wrapped function
    # calls (these occur in main search; qsearch-internal calls are inside the
    # quiescence phase and are not split further in this version).
    subsystem = {
        "move_generation": times.get("MOVE_GEN", 0.0),
        "position_key": times.get("TT_KEY", 0.0),
        "tt": times.get("TT_PROBE_STORE", 0.0),
        "ordering": times.get("ORDERING", 0.0),
        "evaluation": times.get("EVALUATION", 0.0),
    }
    subsystem_shares = {
        name: round(seconds / wall, 4) if wall else 0.0
        for name, seconds in subsystem.items()
    }
    return {
        "fixture_id": pos.fixture_id,
        "board_size": compiled.board_size,
        "movement_buckets": list(spec.movement_buckets),
        "nodes": decision.nodes,
        "qnodes": decision.qnodes,
        "wall_seconds": wall,
        "phase_inclusive_seconds": {
            "main_search": round(main_inclusive, 6),
            "quiescence": round(quiescence_inclusive, 6),
        },
        "subsystem_seconds": {
            name: round(seconds, 6) for name, seconds in subsystem.items()
        },
        "subsystem_shares": subsystem_shares,
        "subsystem_timing_mode": "direct_measured",
        "counts": snap["counts"],
    }


def _measure_overhead(
    compiled: CompiledRuleSet,
    spec: RuleSetFixtureSpec,
    pos: PositionFixtureSpec,
    config: AuditConfig,
) -> dict:
    session = build_session(spec, pos.action_prefix)[1]
    limits = SearchLimits(max_nodes=2000, max_depth=64, quiescence_max_depth=4)
    timings = {}
    for mode in ("off", "on"):
        player = AlphaBetaPlayer(
            compiled,
            use_disk_cache=False,
            tuning=config.tuning,
            profile_cache=EvaluationProfileCache(use_disk=False),
        )
        player.reset()
        recorder = TimingAuditRecorder() if mode == "on" else None
        started = time.perf_counter()
        player.choose_action(session, limits, recorder=recorder)
        timings[mode] = time.perf_counter() - started
    ratio = timings["on"] / timings["off"] if timings["off"] else None
    return {"fixture_id": pos.fixture_id, "seconds_off": timings["off"], "seconds_on": timings["on"], "overhead_ratio": round(ratio, 3) if ratio else None}


def _cache_timings(compiled: CompiledRuleSet, tmp_dir: Path) -> dict:
    config = EvaluationConfig()
    cache = EvaluationProfileCache(disk_dir=tmp_dir, use_disk=True)
    started = time.perf_counter()
    profile, cold_hit = cache.get_or_build(compiled, config)
    cold = time.perf_counter() - started
    started = time.perf_counter()
    _, warm_hit = cache.get_or_build(compiled, config)
    warm = time.perf_counter() - started
    cache2 = EvaluationProfileCache(disk_dir=tmp_dir, use_disk=True)
    started = time.perf_counter()
    _, disk_hit = cache2.get_or_build(compiled, config)
    disk = time.perf_counter() - started
    size = len(json.dumps(_profile_to_dict(profile), sort_keys=True))
    return {
        "ruleset_fingerprint": compiled.ruleset_fingerprint[:12],
        "piece_type_count": len(compiled.piece_types),
        "cold_seconds": cold,
        "memory_warm_seconds": warm,
        "disk_warm_seconds": disk,
        "cold_hit": cold_hit,
        "warm_hit": warm_hit,
        "disk_hit": disk_hit,
        "serialized_bytes": size,
    }


def _run_cprofile(compiled: CompiledRuleSet, session: GameSession, budget: int = 2000) -> dict:
    player = AlphaBetaPlayer(
        compiled, use_disk_cache=False, profile_cache=EvaluationProfileCache(use_disk=False)
    )
    limits = SearchLimits(max_nodes=budget, max_depth=64, quiescence_max_depth=4)
    pr = cProfile.Profile()
    pr.enable()
    player.choose_action(session, limits)
    pr.disable()
    stream = io.StringIO()
    stats = pstats.Stats(pr, stream=stream).sort_stats("cumulative")
    stats.print_stats(10)
    return {"top_cumulative": stream.getvalue()}


def _pick_spanning(positions: list[PositionFixtureSpec], cap: int) -> list[PositionFixtureSpec]:
    if len(positions) <= cap:
        return positions
    ordered = sorted(positions, key=lambda p: (p.ruleset_fixture_id, p.fixture_id))
    step = max(1, len(ordered) // cap)
    return [ordered[i] for i in range(0, len(ordered), step)][:cap]


def run_audit(config: AuditConfig) -> dict:
    out = Path(config.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    env = environment_info()
    specs = ruleset_specs_for(config.suite_name)
    if config.max_board_size is not None:
        specs = tuple(s for s in specs if s.board_size <= config.max_board_size)
    specs_by_id = {s.fixture_id: s for s in specs}

    compiled_map = {s.fixture_id: build_compiled(s) for s in specs}
    classified = {
        fid: classify_ruleset(compiled, spec)
        for fid, spec in specs_by_id.items()
        for compiled in [compiled_map[fid]]
    }
    specs = tuple(classified[fid] for fid in specs_by_id)

    positions = mine_suite(specs, playout_seed=1, max_games=4, max_plies=80, max_positions=3)
    if config.positions_limit is not None:
        positions = positions[: config.positions_limit]
    if config.span_positions is not None:
        positions = _pick_spanning(positions, config.span_positions)

    manifest = build_manifest(config.suite_name, specs, positions, env["commit"])
    write_json(out / "suite_manifest.json", _manifest_dict(manifest))

    suite_stats = _suite_statistics(manifest, positions)
    node_budget = {}
    shared_profile_cache = EvaluationProfileCache(use_disk=False)
    players: dict[str, AlphaBetaPlayer] = {}
    for budget in config.node_budgets:
        capped = positions
        if config.large_budget_cap is not None and budget > 50_000:
            capped = _pick_spanning(positions, config.large_budget_cap)
        rows: list[dict] = []
        for pos in capped:
            spec = classified[pos.ruleset_fixture_id]
            compiled = compiled_map[pos.ruleset_fixture_id]
            player = players.get(spec.fixture_id)
            if player is None:
                player = AlphaBetaPlayer(
                    compiled,
                    use_disk_cache=False,
                    profile_cache=shared_profile_cache,
                    tuning=config.tuning,
                )
                players[spec.fixture_id] = player
            rows.extend(
                _run_budget_fixture(
                    compiled, player, spec, pos, budget, config.repeats, config
                )
            )
        node_budget[str(budget)] = {
            "fixtures": len(capped),
            "results": rows,
            "summary": _aggregate_budget(rows),
        }

    instrumented = []
    overhead = []
    if config.instrument:
        instrumented_positions = _pick_spanning(positions, 6)
        for pos in instrumented_positions:
            spec = classified[pos.ruleset_fixture_id]
            compiled = compiled_map[pos.ruleset_fixture_id]
            instrumented.append(_run_instrumented(compiled, spec, pos, config))
        for pos in _pick_spanning(positions, 2):
            spec = classified[pos.ruleset_fixture_id]
            compiled = compiled_map[pos.ruleset_fixture_id]
            overhead.append(_measure_overhead(compiled, spec, pos, config))

    core_profiles = []
    if config.run_core_profiling:
        for pos in _pick_spanning(positions, 6):
            spec = classified[pos.ruleset_fixture_id]
            compiled = compiled_map[pos.ruleset_fixture_id]
            session = build_session(spec, pos.action_prefix)[1]
            core_profiles.append(
                {
                    "fixture_id": pos.fixture_id,
                    **core_profiling.core_function_timings(
                        compiled, session.state, repeats=5
                    ),
                }
            )

    cache = []
    tmp = Path(".") / f".gc_audit_cache_{uuid.uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        for spec in specs[:3]:
            cache.append(_cache_timings(compiled_map[spec.fixture_id], tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    profiler = None
    if config.run_profiler:
        profiler = _run_profiler_subset(classified, compiled_map, positions, config, out)

    targeted = [
        {
            "fixture_id": fixture.fixture_id,
            "categories": list(fixture.expected_categories),
        }
        for fixture in build_targeted_fixtures()
    ]
    summary = {
        "schema_version": 2,
        "environment": env,
        "suite": suite_stats,
        "requested_budget_tiers": list(config.node_budgets),
        "completed_budget_tiers": [int(b) for b in node_budget],
        "skipped_runs": 0,
        "timeout_runs": 0,
        "failed_runs": 0,
        "targeted_fixtures": targeted,
        "targeted_categories_uncovered": list(uncovered_targeted_categories()),
        "node_budget": node_budget,
        "instrumented": instrumented,
        "instrumentation_overhead": overhead,
        "core_profiling": core_profiles,
        "cache": cache,
        "profiler": profiler,
        "conclusions": _conclusions(node_budget, instrumented, core_profiles),
    }
    write_json(out / "audit_summary.json", summary)
    return summary


def _run_profiler_subset(classified, compiled_map, positions, config, out: Path) -> dict:
    prof_dir = out / "profiler"
    prof_dir.mkdir(parents=True, exist_ok=True)
    result = {"cprofile": [], "tracemalloc": []}
    for pos in _pick_spanning(positions, config.profile_fixture_count):
        spec = classified[pos.ruleset_fixture_id]
        compiled = compiled_map[pos.ruleset_fixture_id]
        session = build_session(spec, pos.action_prefix)[1]
        player = AlphaBetaPlayer(
            compiled, use_disk_cache=False, profile_cache=EvaluationProfileCache(use_disk=False)
        )
        limits = SearchLimits(max_nodes=1500, max_depth=64, quiescence_max_depth=4)

        pr = cProfile.Profile()
        pr.enable()
        player.reset()
        player.choose_action(session, limits)
        pr.disable()
        prof_path = prof_dir / f"{pos.fixture_id}.prof"
        pr.dump_stats(str(prof_path))
        stream = io.StringIO()
        pstats.Stats(pr, stream=stream).sort_stats("cumulative").print_stats(12)
        result["cprofile"].append(
            {"fixture_id": pos.fixture_id, "prof_file": str(prof_path), "top": stream.getvalue()}
        )

        tracemalloc.start()
        player.reset()
        player.choose_action(session, limits)
        _, peak = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        top = snapshot.statistics("lineno")[:10]
        result["tracemalloc"].append(
            {
                "fixture_id": pos.fixture_id,
                "peak_bytes": peak,
                "top_sources": [
                    {
                        "location": f"{s.traceback[0].filename}:{s.traceback[0].lineno}",
                        "size_bytes": s.size,
                        "count": s.count,
                    }
                    for s in top
                ],
            }
        )
    return result


def _suite_statistics(manifest, positions) -> dict:
    board_sizes = sorted({r.board_size for r in manifest.rulesets})
    movement = sorted({b for r in manifest.rulesets for b in r.movement_buckets})
    promotion = sorted({b for r in manifest.rulesets for b in r.promotion_buckets})
    drop = sorted({b for r in manifest.rulesets for b in r.drop_buckets})
    categories = sorted({c for p in positions for c in p.expected_categories})
    missing = [c for c in (
        "midgame", "endgame", "in_check", "multi_evasion", "low_anchor_escape",
        "immediate_capture", "immediate_promotion", "near_repetition",
        "high_branching", "low_branching", "drop_available", "checking_drop",
        "nonchecking_drop",
    ) if c not in categories]
    stats = {
        "name": manifest.suite_version,
        "ruleset_count": len(manifest.rulesets),
        "position_count": len(positions),
        "executed_ruleset_count": len({p.ruleset_fixture_id for p in positions}),
        "executed_position_count": len(positions),
        "board_sizes": board_sizes,
        "movement_buckets": movement,
        "promotion_buckets": promotion,
        "drop_buckets": drop,
        "categories_covered": categories,
        "categories_missing": missing,
    }
    full = _full_suite_stats()
    if full:
        stats["full_suite"] = full
    return stats


def _full_suite_stats() -> dict | None:
    path = Path(FULL_MANIFEST_PATH)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    rulesets = raw.get("rulesets", [])
    positions = raw.get("positions", [])
    categories = sorted({c for p in positions for c in p.get("expected_categories", [])})
    missing = [c for c in (
        "midgame", "endgame", "in_check", "multi_evasion", "low_anchor_escape",
        "immediate_capture", "immediate_promotion", "near_repetition",
        "high_branching", "low_branching", "drop_available", "checking_drop",
        "nonchecking_drop",
    ) if c not in categories]
    return {
        "ruleset_count": len(rulesets),
        "position_count": len(positions),
        "board_sizes": sorted({r.get("board_size") for r in rulesets}),
        "categories_covered": categories,
        "categories_missing": missing,
    }


def _conclusions(node_budget, instrumented, core_profiles) -> dict:
    shares: dict[str, float] = {}
    phase: dict[str, float] = {}
    if instrumented:
        wall = sum(i["wall_seconds"] for i in instrumented)
        acc: dict[str, float] = {}
        for item in instrumented:
            for name, seconds in item["subsystem_seconds"].items():
                acc[name] = acc.get(name, 0.0) + seconds
        shares = {
            name: round(seconds / wall, 4) if wall else 0.0
            for name, seconds in acc.items()
        }
        quiescence_total = sum(
            i["phase_inclusive_seconds"]["quiescence"] for i in instrumented
        )
        phase["quiescence"] = round(quiescence_total / wall, 4) if wall else 0.0
        phase["main_search"] = round(1.0 - phase["quiescence"], 4)
    key_relative = None
    successors_to_movegen = None
    if core_profiles:
        ratios = []
        movegen_ratios = []
        for item in core_profiles:
            pk = item["functions"].get("position_key", {}).get("median")
            successors = item["functions"].get("legal_successors", {}).get("median")
            movegen = item["functions"].get("move_generation_legal", {}).get("median")
            if pk is not None and successors:
                ratios.append(pk / successors)
            if successors and movegen:
                movegen_ratios.append(successors / movegen)
        if ratios:
            key_relative = round(sum(ratios) / len(ratios), 4)
        if movegen_ratios:
            successors_to_movegen = round(sum(movegen_ratios) / len(movegen_ratios), 2)
    qsearch_share = phase.get("quiescence", 0.0)
    if qsearch_share >= 0.5:
        recommendation = (
            "qsearch 占 instrumented 时间主导（>50%）：先处理 qsearch 节点爆炸与 "
            "per-child 构造成本，再做 native；建议完整 NativeSearchBackend 而非单函数 FFI。"
        )
    elif shares.get("move_gen", 0.0) >= 0.5:
        recommendation = "movegen/legality 占主导：native rule kernel 或一体化 backend 收益最大。"
    else:
        recommendation = (
            "多子系统分摊：先按 position key/evaluation/ordering 数据决定优先项，"
            "native 边界建议保持 SearchBackend 协议不变。"
        )
    return {
        "phase_inclusive_shares": phase,
        "instrumented_subsystem_shares": shares,
        "position_key_to_successors_ratio": key_relative,
        "legal_successors_to_movegen_ratio": successors_to_movegen,
        "qsearch_gross_share": round(qsearch_share, 4),
        "recommendation": recommendation,
    }
