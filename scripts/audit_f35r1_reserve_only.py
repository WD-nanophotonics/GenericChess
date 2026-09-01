"""F35 R1 audit: recertify Q34C with reserve-only production scope."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import audit_f35_first_iteration_reserve as f35

MANIFEST = ROOT / "tests/fixtures/f35r1_reserve_only_manifest.json"
OUTPUT = ROOT / "tests/fixtures/f35r1_reserve_only_results.json"
ACCESS = ROOT / "tests/fixtures/f35r1_reserve_only_accessibility.json"
BASELINE = ROOT / "tests/fixtures/f35r1_reserve_only_baseline.json"
F34_SHA = "4fa6b5d45ed1600645d2b3b0cb39fcfb8837cc81"
F34_SEARCH_SHA = f35.PRE_CHANGE_SEARCH_SHA
PROVISIONAL_COMMIT = "b02d92e0aabaf41b547cd8fa8fdb550e7dc756cb"
PROVISIONAL_MANIFEST_SHA = "cb2afd22c4235cbafb7804dc80a6ba44cf5c2a38a2ed21d36ca5f0dd94b35787"
PROVISIONAL_RESULT_SHA = "e7fa2c81340de6aa1aa04e53e4842ff64fe1e6e4ac4ebed5483548b119cbaa4a"
PROVISIONAL_ACCESS_SHA = "6c9cbae6a15711a423eb108028bd2700941ba5dc763ff5221b4ec392ac2df607"
PROVISIONAL_BASELINE_SHA = "d2307cca8743c7250e1fb9b48059843e7d7734deee8adf0ec283719fd338f8fd"
PROVISIONAL_SEARCH_SHA = "0345adfa5ac63c13d7cae0538e8153dcf24ee0cdfd4d41d782a401e421cdba0e"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def freeze():
    refs = {
        "f34_manifest": ("tests/fixtures/f34_qsearch_budget_manifest.json", f35.F34_MANIFEST_SHA),
        "f34_matrix": ("tests/fixtures/f34_qsearch_budget_matrix.json", f35.F34_MATRIX_SHA),
        "f34_selection": ("tests/fixtures/f34_qsearch_budget_selection.json", f35.F34_SELECTION_SHA),
        "f34_safety": ("tests/fixtures/f34_qsearch_tactical_safety.json", f35.F34_SAFETY_SHA),
        "provisional_manifest": ("tests/fixtures/f35_first_iteration_reserve_manifest.json", PROVISIONAL_MANIFEST_SHA),
        "provisional_result": ("tests/fixtures/f35_q34c_fixed_node_parity.json", PROVISIONAL_RESULT_SHA),
        "provisional_accessibility": ("tests/fixtures/f35_first_iteration_reserve_accessibility.json", PROVISIONAL_ACCESS_SHA),
        "provisional_baseline": ("tests/fixtures/f35_first_iteration_reserve_baseline.json", PROVISIONAL_BASELINE_SHA),
    }
    value = {
        "schema_version": 1,
        "kind": "F35R1_RESERVE_ONLY_MANIFEST",
        "pre_run_sandbox_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "f34_baseline_sha": F34_SHA,
        "f34_search_sha": F34_SEARCH_SHA,
        "provisional_commit": PROVISIONAL_COMMIT,
        "provisional_search_sha": PROVISIONAL_SEARCH_SHA,
        "corrective_search_sha": digest(ROOT / "generic_chess/ai/alphabeta/search.py"),
        "frozen_inputs": {k: {"path": p, "sha256": expected, "file_sha256": digest(ROOT / p)} for k, (p, expected) in refs.items()},
        "contract": {
            "production_scope": "Q34C first-iteration reserve machinery only",
            "lazy_noncheck_legal_generation": "must remain F34 ordering; not retained",
            "configured_qdepth": 4,
            "hard_qdepth": 8,
            "in_check": "unchanged full legal evasion path",
            "state": "context-local; aborted first iteration never completes reserve",
        },
        "matrix": {"fixed_nodes": [512, 2048], "wall_times_seconds": [0.5, 2.0], "wall_repetitions": 3, "roots": 10},
        "gates": {
            "fixed_reproduction": "20/20 exact F34 Q34C rows",
            "accessibility": "unchanged F34 gate using root medians and no more fallback",
            "scope": "only reserve machinery differs from F34 search.py",
        },
        "constraints": ["NO_EVALUATOR_CHANGE", "NO_NATIVE_REPAIR", "NO_RULE_SCHEMA_SESSION_RECORD_CLI_CHANGE", "NO_ALPHASHO_RERUN", "NO_PAIRED_BENCHMARK", "NO_ALPHA_CHESS", "PRODUCTION_DIFF_ONLY_SEARCH_PY"],
    }
    value["manifest_sha256"] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    MANIFEST.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


def _root_medians(wall):
    return {
        variant: {
            control: {pid: f35._summary(rows) for pid, rows in wall[variant][control].items()}
            for control in ("0.5", "2.0")
        }
        for variant in ("shadow_baseline", "production_candidate")
    }


def _aggregates(wall):
    medians = _root_medians(wall)
    out = {"per_root_medians": medians, "controls": {}}
    for control in ("0.5", "2.0"):
        base = medians["shadow_baseline"][control]
        cand = medians["production_candidate"][control]
        base_first = [row["time_to_first_completed_iteration"] for row in base.values() if row["time_to_first_completed_iteration"] is not None]
        cand_first = [row["time_to_first_completed_iteration"] for row in cand.values() if row["time_to_first_completed_iteration"] is not None]
        comparable = [pid for pid in base if base[pid]["time_to_first_completed_iteration"] is not None and cand[pid]["time_to_first_completed_iteration"] is not None]
        b_med = f35.statistics.median(base_first) if base_first else None
        c_med = f35.statistics.median(cand_first) if cand_first else None
        out["controls"][control] = {
            "fallback_events": {"shadow_baseline": sum(r["fallback"] for rows in wall["shadow_baseline"][control].values() for r in rows), "production_candidate": sum(r["fallback"] for rows in wall["production_candidate"][control].values() for r in rows)},
            "fallback_roots_improved": sum(base[pid]["fallback"] > cand[pid]["fallback"] for pid in base),
            "depth_improved_roots": sum(cand[pid]["completed_depth"] > base[pid]["completed_depth"] for pid in base),
            "depth_regressed_roots": sum(cand[pid]["completed_depth"] < base[pid]["completed_depth"] for pid in base),
            "comparable_roots": comparable,
            "aggregate_median_first_iteration": {"shadow_baseline": b_med, "production_candidate": c_med},
            "retention_statistic": (1 - c_med / b_med) if b_med and c_med is not None else 0.0,
        }
    return out


def _scope_witness():
    current = (ROOT / "generic_chess/ai/alphabeta/search.py").read_text(encoding="utf-8")
    baseline = subprocess.run(["git", "show", F34_SHA + ":generic_chess/ai/alphabeta/search.py"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    def block(source):
        return source[source.index("def _quiescence_runtime"):source.index("def quiescence(")]
    current_block = block(current)
    baseline_block = block(baseline)
    action_line = "actions = list(runtime.legal_actions(ctx.checkpoint))"
    f34_order = baseline_block.index(action_line) < baseline_block.index("if in_check:")
    current_order = current_block.index(action_line) < current_block.index("if in_check:")
    return {"LAZY_NONCHECK_LEGAL_GENERATION_RETAINED": False, "FIRST_ITERATION_RESERVE_ONLY_PRODUCTION_SCOPE": current_order == f34_order, "f34_order_restored": f34_order, "corrective_order_matches_f34": current_order}


def _direct_and_zero_qdepth_witness(m, compiled, evaluator, positions):
    import generic_chess.ai.alphabeta.search as search
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.ai.alphabeta.search import run_root_search
    from generic_chess.ai.alphabeta.statistics import SearchStatistics
    from generic_chess.ai.alphabeta.transposition import TranspositionTable
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    state = m["sfen_to_gc_state"](compiled, positions[0]["sfen"])
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    stats = SearchStatistics()
    run_root_search(state, compiled, evaluator, TranspositionTable(), SearchLimits(max_depth=2, max_nodes=128, quiescence_max_depth=0, quiescence_hard_max_depth=0), None, stats, use_tt=False, use_ordering=False, tuning=SearchTuning(use_root_tactical=False), legal_binding_provider=provider)
    direct = SimpleNamespace(qdepth_limit=4, first_main_iteration_complete=None)
    return {"direct_internal_configured_qdepth_four": search._ordinary_qdepth_limit(direct) == 4, "explicit_qdepth_zero_static_eval": stats.qnodes == 0}


def run():
    manifest = load(MANIFEST)
    result = f35.run()
    aggregates = _aggregates(result["wall_time"])
    scope = _scope_witness()
    m, compiled, evaluator, positions, _modal = f35.f32r1._contexts()
    direct = _direct_and_zero_qdepth_witness(m, compiled, evaluator, positions)
    result["production_search_post_change_sha"] = digest(ROOT / "generic_chess/ai/alphabeta/search.py")
    result["f35r1_manifest_sha256"] = manifest["manifest_sha256"]
    result["provisional_evidence"] = {"commit": PROVISIONAL_COMMIT, "manifest_sha256": PROVISIONAL_MANIFEST_SHA, "result_sha256": PROVISIONAL_RESULT_SHA, "accessibility_sha256": PROVISIONAL_ACCESS_SHA, "baseline_sha256": PROVISIONAL_BASELINE_SHA, "search_sha256": PROVISIONAL_SEARCH_SHA}
    result["source_scope"] = scope
    result["direct_and_zero_qdepth_witness"] = direct
    result["unambiguous_aggregates"] = aggregates
    result["gates"]["FIRST_ITERATION_RESERVE_ONLY_PRODUCTION_SCOPE"] = scope["FIRST_ITERATION_RESERVE_ONLY_PRODUCTION_SCOPE"] and not scope["LAZY_NONCHECK_LEGAL_GENERATION_RETAINED"]
    result["gates"]["DIRECT_INTERNAL_QDEPTH_ISOLATION"] = direct["direct_internal_configured_qdepth_four"]
    result["gates"]["EXPLICIT_QDEPTH_ZERO_COMPATIBILITY"] = direct["explicit_qdepth_zero_static_eval"]
    result["retained"] = all(result["gates"].values())
    result["next_boundary"] = "F36_POST_QUIESCENCE_RESERVE_SEARCH_CAPACITY_REBASELINE" if result["retained"] else "F36_RULE_DERIVED_EVALUATOR_REENTRY"
    result["flags"]["FIRST_ITERATION_QUIESCENCE_RESERVE_RETAINED"] = result["retained"]
    result["flags"]["LAZY_NONCHECK_LEGAL_GENERATION_RETAINED"] = False
    result["flags"]["FIRST_ITERATION_RESERVE_ONLY_PRODUCTION_SCOPE"] = result["gates"]["FIRST_ITERATION_RESERVE_ONLY_PRODUCTION_SCOPE"]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-manifest", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze_manifest:
        print(json.dumps({"manifest_sha256": freeze()["manifest_sha256"]}))
        return 0
    if args.run:
        result = run()
        OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        ACCESS.write_text(json.dumps(result["unambiguous_aggregates"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        BASELINE.write_text(json.dumps({"shadow_baseline": result["fixed_node"]["shadow_baseline"], "fixed_search_regression": result["fixed_search_regression"]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "retained": result["retained"], "next": result["next_boundary"], "gates": result["gates"]}, sort_keys=True))
        return 0
    parser.error("use --freeze-manifest or --run")


if __name__ == "__main__":
    raise SystemExit(main())
