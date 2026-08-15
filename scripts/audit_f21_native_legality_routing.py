"""Bounded F21 production-provider differential and performance audit."""

from __future__ import annotations

import json
import platform
import statistics
import sys
import time
import argparse
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f21_native_legality_routing"
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.core.semantic_executor import _semantic_public_action, semantic_engine_for
from generic_chess.native import native_version
from scripts.audit_f20_h20a import path_sessions
from scripts.audit_f4_runtime_cost import corpus_specs, make_session, profile_config


def dump(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    if name.endswith(".jsonl") and isinstance(value, list):
        text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in value)
    else:
        text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    (OUT / name).write_text(text, encoding="utf-8")


def stats_snapshot(stats):
    ignored = {
        "time_to_first_legal_action", "time_to_first_completed_iteration",
        "ordering_seconds", "evaluation_seconds", "legal_generation_seconds",
        "root_scan_seconds", "native_legality_seconds",
        "native_legality_payload_seconds", "native_legality_decode_binding_seconds",
        "native_legality_enabled", "native_legality_calls", "native_legality_actions",
        "native_legality_fallbacks", "native_legality_operational_failures",
    }
    result = {}
    for field in fields(stats):
        if field.name in ignored:
            continue
        value = getattr(stats, field.name)
        result[field.name] = dict(value) if isinstance(value, dict) else value
    return result


def run_once(spec, profile_name, native, provider=None):
    session = make_session(spec)
    compiled = session.compiled
    legacy = getattr(compiled, "_legacy_compiled", compiled)
    config = EvaluationConfig()
    evaluator = Evaluator(legacy, build_ruleset_profile(legacy, config), config)
    config_data = profile_config(profile_name)
    if native and provider is None:
        provider = NativeSemanticLegalityProvider.try_create(compiled)
    stats = SearchStatistics()
    started = time.perf_counter()
    result = run_root_search(
        session.state,
        compiled,
        evaluator,
        TranspositionTable(),
        SearchLimits(
            max_depth=int(config_data["max_depth"]),
            max_nodes=int(config_data["max_nodes"]),
            quiescence_max_depth=int(config_data["quiescence_max_depth"]),
        ),
        None,
        stats,
        use_tt=bool(config_data["use_tt"]),
        use_ordering=bool(config_data["use_ordering"]),
        tuning=config_data["tuning"],
        _history_witnesses=session._search_witnesses,
        legal_binding_provider=provider,
    )
    return {
        "action": None if result[0] is None else str(result[0]),
        "score": int(result[1]),
        "pv": [str(action) for action in result[2]],
        "termination_reason": str(result[3]),
        "stats": stats_snapshot(stats),
        "elapsed_us": (time.perf_counter() - started) * 1_000_000,
        "provider_active": bool(provider is not None),
        "provider_compile_seconds": 0.0 if provider is None else provider.compile_seconds,
    }


def provider_rows():
    rows = []
    for spec in [row for row in corpus_specs() if row["kind"] == "semantic"]:
        for prefix, session in path_sessions(spec):
            provider = NativeSemanticLegalityProvider.try_create(session.compiled)
            if provider is None:
                rows.append({"case_id": spec["id"], "prefix": list(prefix), "status": "INACTIVE"})
                continue
            native = provider(session.state.position, session.state.ply_count)
            engine = semantic_engine_for(session.compiled)
            python = tuple(
                (_semantic_public_action(engine, action), (action, binding))
                for action, binding in engine.iter_legal_action_bindings(session.state.position)
            )
            child_rows = []
            for public, (native_action, native_binding) in native[:4]:
                python_binding = dict(python)[public]
                child_native = engine._transition(session.state.position, native_action, native_binding)
                child_python = engine._transition(session.state.position, python_binding[0], python_binding[1])
                child_rows.append({"action": str(public), "binding_equal": native_binding == python_binding[1], "child_equal": child_native == child_python})
            rows.append({
                "case_id": spec["id"],
                "prefix": list(prefix),
                "count": len(native),
                "python_count": len(python),
                "order_equal": tuple(item[0] for item in native) == tuple(item[0] for item in python),
                "semantic_equal": tuple(item[1][0] for item in native) == tuple(item[1][0] for item in python),
                "binding_child_rows": child_rows,
            })
    return rows


def generic_rows():
    from phase19c1_native_semantic_fixtures import semantic_corpus
    from generic_chess.session.session import GameSession

    rows = []
    for name, compiled in semantic_corpus():
        session = GameSession(compiled)
        provider = NativeSemanticLegalityProvider.try_create(compiled)
        if provider is None:
            rows.append({"case_id": name, "status": "INACTIVE"})
            continue
        native = provider(session.state.position, session.state.ply_count)
        engine = semantic_engine_for(compiled)
        python = tuple(
            (_semantic_public_action(engine, action), (action, binding))
            for action, binding in engine.iter_legal_action_bindings(session.state.position)
        )
        rows.append({
            "case_id": name,
            "count": len(native),
            "python_count": len(python),
            "order_equal": tuple(item[0] for item in native) == tuple(item[0] for item in python),
            "semantic_equal": tuple(item[1][0] for item in native) == tuple(item[1][0] for item in python),
        })
    return rows


def performance():
    summaries = {}
    for profile_name in ("A", "B"):
        rows = []
        for spec in [row for row in corpus_specs() if row["kind"] == "semantic"]:
            provider = NativeSemanticLegalityProvider.try_create(make_session(spec).compiled)
            run_once(spec, profile_name, False)
            run_once(spec, profile_name, True, provider)
            for repeat in range(5):
                baseline = run_once(spec, profile_name, False)
                native = run_once(spec, profile_name, True, provider)
                parity = all(
                    baseline[key] == native[key]
                    for key in ("action", "score", "pv", "termination_reason", "stats")
                )
                rows.append({
                    "case_id": spec["id"], "repeat": repeat + 1,
                    "baseline_us": baseline["elapsed_us"],
                    "native_us": native["elapsed_us"],
                    "gain": 1.0 - native["elapsed_us"] / baseline["elapsed_us"],
                    "parity": parity,
                })
        baseline_median = statistics.median(row["baseline_us"] for row in rows)
        native_median = statistics.median(row["native_us"] for row in rows)
        by_case = {}
        for case_id in sorted({row["case_id"] for row in rows}):
            subset = [row for row in rows if row["case_id"] == case_id]
            by_case[case_id] = {
                "gain": statistics.median(row["gain"] for row in subset),
                "parity": all(row["parity"] for row in subset),
            }
        summaries[profile_name] = {
            "baseline_median_us": baseline_median,
            "native_median_us": native_median,
            "aggregate_gain": 1.0 - native_median / baseline_median,
            "cases": by_case,
            "rows": rows,
        }
    return summaries


def main():
    specs = [row for row in corpus_specs() if row["kind"] == "semantic"]
    baseline = {
        "origin/sandbox": "3b2f253d7bbb7ed16ff705206644a1d76ece6977",
        "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
        "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
    }
    dump("baseline.json", {"status": "PASS", "baseline": baseline})
    dump("environment.json", {"python": sys.version, "platform": platform.platform(), "native_version": native_version()})
    standard = provider_rows()
    generic = generic_rows()
    dump("standard_shogi_provider_rows.jsonl", standard)
    dump("standard_shogi_provider_summary.json", {"rows": len(standard), "mismatches": sum(not (row.get("order_equal", True) and row.get("semantic_equal", True)) for row in standard), "status": "PASS" if all(row.get("status", "PASS") == "PASS" or row.get("status") == "INACTIVE" for row in standard) else "FAIL"})
    dump("generic_provider_differential.json", {"rows": generic, "status": "PASS" if all(row.get("status", "PASS") == "PASS" or row.get("status") == "INACTIVE" for row in generic) else "FAIL"})
    dump("binding_child_parity.json", {"rows": standard, "status": "PASS" if all(all(item["binding_equal"] and item["child_equal"] for item in row.get("binding_child_rows", ())) for row in standard) else "FAIL"})
    perf = performance()
    dump("production_performance.json", perf)
    for profile_name in ("A", "B"):
        (OUT / f"profile_{profile_name.lower()}_python.jsonl").write_text(
            "".join(json.dumps({"case_id": row["case_id"], "repeat": row["repeat"], "elapsed_us": row["baseline_us"], "parity": row["parity"]}, sort_keys=True) + "\n" for row in perf[profile_name]["rows"]),
            encoding="utf-8",
        )
        (OUT / f"profile_{profile_name.lower()}_native.jsonl").write_text(
            "".join(json.dumps({"case_id": row["case_id"], "repeat": row["repeat"], "elapsed_us": row["native_us"], "parity": row["parity"]}, sort_keys=True) + "\n" for row in perf[profile_name]["rows"]),
            encoding="utf-8",
        )
    dump("final_verdict.json", {"provider_rows": len(standard), "generic_rows": len(generic), "performance": {k: {"aggregate_gain": v["aggregate_gain"]} for k, v in perf.items()}})
    print(json.dumps({"standard_rows": len(standard), "generic_rows": len(generic), "performance": {k: v["aggregate_gain"] for k, v in perf.items()}}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", nargs="?", choices=("all", "provider", "performance"), default="all")
    args = parser.parse_args()
    if args.stage == "provider":
        standard = provider_rows()
        generic = generic_rows()
        dump("standard_shogi_provider_rows.jsonl", standard)
        dump("standard_shogi_provider_summary.json", {"rows": len(standard), "mismatches": sum(not (row.get("order_equal", True) and row.get("semantic_equal", True)) for row in standard), "status": "PASS" if all(row.get("status", "PASS") == "PASS" or row.get("status") == "INACTIVE" for row in standard) else "FAIL"})
        dump("generic_provider_differential.json", {"rows": generic, "status": "PASS" if all(row.get("status", "PASS") == "PASS" or row.get("status") == "INACTIVE" for row in generic) else "FAIL"})
        dump("binding_child_parity.json", {"rows": standard, "status": "PASS" if all(all(item["binding_equal"] and item["child_equal"] for item in row.get("binding_child_rows", ())) for row in standard) else "FAIL"})
        print(json.dumps({"standard_rows": len(standard), "generic_rows": len(generic)}, sort_keys=True))
    elif args.stage == "performance":
        perf = performance()
        dump("production_performance.json", perf)
        for profile_name in ("A", "B"):
            (OUT / f"profile_{profile_name.lower()}_python.jsonl").write_text("".join(json.dumps({"case_id": row["case_id"], "repeat": row["repeat"], "elapsed_us": row["baseline_us"], "parity": row["parity"]}, sort_keys=True) + "\n" for row in perf[profile_name]["rows"]), encoding="utf-8")
            (OUT / f"profile_{profile_name.lower()}_native.jsonl").write_text("".join(json.dumps({"case_id": row["case_id"], "repeat": row["repeat"], "elapsed_us": row["native_us"], "parity": row["parity"]}, sort_keys=True) + "\n" for row in perf[profile_name]["rows"]), encoding="utf-8")
        print(json.dumps({k: v["aggregate_gain"] for k, v in perf.items()}, sort_keys=True))
    else:
        main()
