"""Bounded F73 retention matrix for Native root-window pruning."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.core.identity import position_identity_key  # noqa: E402
from generic_chess.core.position import HistoryRecord  # noqa: E402
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.semantic import semantic_iterative_search, snapshot  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset  # noqa: E402
from generic_chess.rules.western_chess import build_western_chess_ruleset  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f71_causal_root_hint_probe as f71  # noqa: E402
from test_generic_declaration_semantics import _claim_position, _claim_ruleset  # noqa: E402
from test_h50b2a_semantic_native_search import (  # noqa: E402
    _continuous_history,
    _declaration_free_shogi,
    _pack_initial,
)


WORK_ORDER = "GENERICCHESS-F73-ROOT-PRUNING-PRODUCT-RETENTION"
PARENT_SHA = "0732a9b78d7c58d7554441271133c4be8f427b8d"
LABEL = f71.LABEL
GEN1_ID = f71.GEN1_ID
GEN1_CANDIDATE = f71.GEN1_CANDIDATE
NODES = 2_048
MAX_DEPTH = 12
PARITY_DEPTHS = (1, 2)
DEPTH3_LIMIT = 8
TT_MEGABYTES = 8
MAX_ROOTS = 20
TT_CASE_LIMIT = 12
OUT = ROOT / ".generic_chess_flow" / "f73-root-pruning-product-retention"
RESULT_PATH = OUT / "f73_results.json"
PROGRESS = OUT / "progress"


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _action_key(action) -> str | None:
    return None if action is None else f71._action_key(action)


def _engine_payload(result) -> dict:
    first = tuple(result.root_iteration_first_actions)
    return {
        "action_key": _action_key(result.action),
        "score": int(result.score),
        "principal_variation_keys": [_action_key(action) for action in result.principal_variation],
        "declaration_id": result.declaration_id,
        "completed_depth": int(result.completed_depth),
        "nodes": int(result.nodes),
        "termination_mode": str(result.termination_reason),
        "beta_cutoffs": int(result.beta_cutoffs),
        "tt_probes": int(result.tt_probes),
        "tt_hits": int(result.tt_hits),
        "tt_cutoffs": int(result.tt_cutoffs),
        "root_window_pruning": bool(result.root_window_pruning),
        "root_hint_requested_action_key": _action_key(result.root_hint_requested),
        "root_hint_legal": bool(result.root_hint_legal),
        "root_hint_apply_count": int(result.root_hint_apply_count),
        "root_iterations_attempted": int(result.root_iterations_attempted),
        "root_iteration_first_action_keys": [_action_key(action) for action in first],
    }


def _signature(row: dict) -> tuple:
    return (
        row["action_key"], row["score"], tuple(row["principal_variation_keys"]),
        row["declaration_id"], row["completed_depth"], row["termination_mode"],
    )


def _load_gen1(compiled):
    data = json.loads(f71.f62_model_params().read_text(encoding="utf-8"))
    row = next(item for item in data["corrected_candidates"] if item["candidate_id"] == GEN1_CANDIDATE)
    checkpoint = f61r2._candidate_checkpoint(f59._parent(LABEL), row)
    if checkpoint.checkpoint_id != GEN1_ID:
        raise RuntimeError("F73 Gen1 identity mismatch")
    checkpoint.validate_ruleset(compiled)
    return checkpoint


def _claim_session():
    compiled = compile_semantic_ruleset(_claim_ruleset())
    position = _claim_position(compiled)
    key = str(position_identity_key(position, compiled))
    session = GameSession(compiled)
    session._state = replace(
        session.state, position=position, ply_count=0,
        repetition_counts=((key, 1),),
        history=(HistoryRecord(key, -1, "", False),),
    )
    session._search_history_witnesses = (position,)
    return compiled, compile_native_semantic_rules(compiled), session


def _engine_cases(compiled, native, gen1, roots):
    cases = [
        (f"shogi-root-{root['root_index']}", f59._session(compiled, root["record"]), native, gen1)
        for root in roots
    ]
    for name, ruleset in (
        ("western-initial", build_western_chess_ruleset()),
        ("shogi-initial", build_standard_shogi_ruleset()),
    ):
        semantic = compile_semantic_ruleset(ruleset)
        semantic_native = compile_native_semantic_rules(semantic)
        zero = (0,) * len(semantic_native.type_ids)
        cases.append((name, GameSession(semantic), semantic_native, (zero, zero)))
    claim_compiled, claim_native, claim_session = _claim_session()
    zero = (0,) * len(claim_native.type_ids)
    cases.append(("declaration-claim", claim_session, claim_native, (zero, zero)))
    return cases


def _run_engine(session, native, evaluator, *, depth, nodes=None, tt=0, pruning=False):
    if isinstance(evaluator, tuple):
        engine = SemanticSearchEngine(
            session.compiled, native, board_values=evaluator[0], hand_values=evaluator[1],
            tt_megabytes=tt,
        )
    else:
        engine = SemanticSearchEngine(session.compiled, native, checkpoint=evaluator, tt_megabytes=tt)
    result = engine.search(
        session,
        SearchLimits(max_depth=depth, max_nodes=nodes, quiescence_max_depth=0),
        root_window_pruning=pruning,
    )
    return _engine_payload(result)


def _raw_cases():
    semantic, native = _declaration_free_shogi()
    fresh = _pack_initial(semantic, native)
    return [
        ("continuous-check", native, _pack_initial(
            semantic, native, history=_continuous_history(native, fresh, 0)
        )),
        ("repetition", native, _pack_initial(
            semantic, native, history=(
                (*snapshot(native, fresh)["history"][0], 255, 0),
                (*snapshot(native, fresh)["history"][0], 0, 0),
                (*snapshot(native, fresh)["history"][0], 1, 0),
                (*snapshot(native, fresh)["history"][0], 0, 0),
            )
        )),
        ("automatic-max-ply", native, _pack_initial(
            semantic, native, ply=500,
            history=[(1, 2, 3, 4, 255, 0)] + [
                (index + 10, index + 20, index + 30, index + 40, index % 2, 0)
                for index in range(1, 501)
            ],
        )),
    ]


def _raw_result(native, position, depth, pruning):
    return dict(semantic_iterative_search(
        native, position, depth, root_window_pruning=pruning
    ))


def _raw_signature(row):
    return (
        row.get("best_action"), row.get("score"), tuple(row.get("principal_variation", ())),
        row.get("declaration_id"), row.get("termination_reason"),
    )


def _run_exactness(compiled, native, gen1, roots):
    failures = []
    rows = []
    for name, session, case_native, evaluator in _engine_cases(compiled, native, gen1, roots):
        before = str(position_identity_key(session.state.position, session.compiled))
        for depth in PARITY_DEPTHS:
            full = _run_engine(session, case_native, evaluator, depth=depth, pruning=False)
            pruned = _run_engine(session, case_native, evaluator, depth=depth, pruning=True)
            full_repeat = _run_engine(session, case_native, evaluator, depth=depth, pruning=False)
            pruned_repeat = _run_engine(session, case_native, evaluator, depth=depth, pruning=True)
            mismatch = []
            if _signature(full) != _signature(pruned):
                mismatch.append("TT-off full/pruned semantic mismatch")
            if _signature(full) != _signature(full_repeat):
                mismatch.append("TT-off full repeatability mismatch")
            if _signature(pruned) != _signature(pruned_repeat):
                mismatch.append("TT-off pruned repeatability mismatch")
            after = str(position_identity_key(session.state.position, session.compiled))
            if before != after:
                mismatch.append("root position changed")
            row = {"name": name, "depth": depth, "full": full, "pruned": pruned, "failures": mismatch}
            rows.append(row)
            failures.extend(f"{name}/depth-{depth}: {item}" for item in mismatch)
    for name, case_native, position in _raw_cases():
        before = snapshot(case_native, position)
        for depth in PARITY_DEPTHS:
            full = _raw_result(case_native, position, depth, False)
            pruned = _raw_result(case_native, position, depth, True)
            full_repeat = _raw_result(case_native, position, depth, False)
            pruned_repeat = _raw_result(case_native, position, depth, True)
            mismatch = []
            if _raw_signature(full) != _raw_signature(pruned):
                mismatch.append("TT-off full/pruned semantic mismatch")
            if _raw_signature(full) != _raw_signature(full_repeat):
                mismatch.append("TT-off full repeatability mismatch")
            if _raw_signature(pruned) != _raw_signature(pruned_repeat):
                mismatch.append("TT-off pruned repeatability mismatch")
            if snapshot(case_native, position) != before:
                mismatch.append("root position changed")
            row = {"name": name, "depth": depth, "full": _raw_compact(full), "pruned": _raw_compact(pruned), "failures": mismatch}
            rows.append(row)
            failures.extend(f"{name}/depth-{depth}: {item}" for item in mismatch)
    return rows, failures


def _raw_compact(row):
    return {
        "best_action": row.get("best_action"), "score": row.get("score"),
        "principal_variation": list(row.get("principal_variation", ())),
        "declaration_id": row.get("declaration_id"),
        "termination_reason": row.get("termination_reason"),
        "nodes": int(row.get("nodes", 0)),
        "beta_cutoffs": int(row.get("beta_cutoffs", 0)),
    }


def _run_depth3_subset(compiled, native, gen1, roots):
    rows = []
    failures = []
    for root in roots[:DEPTH3_LIMIT]:
        session = f59._session(compiled, root["record"])
        full = _run_engine(session, native, gen1, depth=3, pruning=False)
        pruned = _run_engine(session, native, gen1, depth=3, pruning=True)
        mismatch = [] if _signature(full) == _signature(pruned) else ["depth-3 full/pruned semantic mismatch"]
        rows.append({"root_index": root["root_index"], "full": full, "pruned": pruned, "failures": mismatch})
        failures.extend(f"root-{root['root_index']}: {item}" for item in mismatch)
    return rows, failures


def _run_tt_gate(compiled, native, gen1, roots):
    cases = [(f"shogi-root-{root['root_index']}", f59._session(compiled, root["record"]), native, gen1) for root in roots[:6]]
    for name, ruleset in (("western-initial", build_western_chess_ruleset()), ("shogi-initial", build_standard_shogi_ruleset())):
        semantic = compile_semantic_ruleset(ruleset)
        semantic_native = compile_native_semantic_rules(semantic)
        zero = (0,) * len(semantic_native.type_ids)
        cases.append((name, GameSession(semantic), semantic_native, (zero, zero)))
    claim_compiled, claim_native, claim_session = _claim_session()
    zero = (0,) * len(claim_native.type_ids)
    cases.append(("declaration-claim", claim_session, claim_native, (zero, zero)))
    failures = []
    rows = []
    for name, session, case_native, evaluator in cases[:TT_CASE_LIMIT]:
        for depth in PARITY_DEPTHS:
            full = _run_engine(session, case_native, evaluator, depth=depth, tt=TT_MEGABYTES, pruning=False)
            pruned_engine = SemanticSearchEngine(
                session.compiled, case_native,
                board_values=evaluator[0], hand_values=evaluator[1],
                tt_megabytes=TT_MEGABYTES,
            ) if isinstance(evaluator, tuple) else SemanticSearchEngine(
                session.compiled, case_native, checkpoint=evaluator, tt_megabytes=TT_MEGABYTES
            )
            first = pruned_engine.search(session, SearchLimits(max_depth=depth, max_nodes=None, quiescence_max_depth=0), root_window_pruning=True)
            second = pruned_engine.search(session, SearchLimits(max_depth=depth, max_nodes=None, quiescence_max_depth=0), root_window_pruning=True)
            pruned = _engine_payload(first)
            warm = _engine_payload(second)
            mismatch = []
            if _signature(full) != _signature(pruned) or _signature(pruned) != _signature(warm):
                mismatch.append("TT-on full/pruned/warm semantic mismatch")
            row = {"name": name, "depth": depth, "full": full, "pruned_cold": pruned, "pruned_warm": warm, "failures": mismatch}
            rows.append(row)
            failures.extend(f"{name}/depth-{depth}: {item}" for item in mismatch)
    return rows, failures


def _run_efficiency(compiled, native, gen1, roots):
    rows = []
    failures = []
    for root in roots:
        session = f59._session(compiled, root["record"])
        full = _run_engine(session, native, gen1, depth=2, nodes=None, tt=TT_MEGABYTES, pruning=False)
        pruned = _run_engine(session, native, gen1, depth=2, nodes=None, tt=TT_MEGABYTES, pruning=True)
        limited_full = _run_engine(session, native, gen1, depth=MAX_DEPTH, nodes=NODES, tt=TT_MEGABYTES, pruning=False)
        limited_pruned = _run_engine(session, native, gen1, depth=MAX_DEPTH, nodes=NODES, tt=TT_MEGABYTES, pruning=True)
        mismatch = [] if _signature(full) == _signature(pruned) else ["efficiency fixed-depth semantic mismatch"]
        row = {"root_index": root["root_index"], "fixed_depth_full": full, "fixed_depth_pruned": pruned, "limited_full": limited_full, "limited_pruned": limited_pruned, "failures": mismatch}
        rows.append(row)
        failures.extend(f"root-{root['root_index']}: {item}" for item in mismatch)
    return rows, failures


def _base_result(gen1, roots):
    return {
        "schema": "generic-chess-f73-root-pruning-product-retention-v1",
        "work_order": WORK_ORDER, "baseline_sha": PARENT_SHA,
        "config": {"root_count": len(roots), "parity_depths": PARITY_DEPTHS, "depth3_subset": DEPTH3_LIMIT, "tt_case_limit": TT_CASE_LIMIT, "tt_megabytes": TT_MEGABYTES, "nodes": NODES},
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "code_provenance": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in (
                "scripts/f73_root_pruning_product_retention.py",
                "generic_chess/_native/native_module.c",
                "generic_chess/native/semantic_engine.py",
                "generic_chess/native/semantic.py",
            )
        },
    }


def _efficiency_summary(rows):
    fixed_full = sum(row["fixed_depth_full"]["nodes"] for row in rows)
    fixed_pruned = sum(row["fixed_depth_pruned"]["nodes"] for row in rows)
    limited_full = sum(row["limited_full"]["completed_depth"] for row in rows)
    limited_pruned = sum(row["limited_pruned"]["completed_depth"] for row in rows)
    regressions = []
    for row in rows:
        full = row["fixed_depth_full"]["nodes"]
        pruned = row["fixed_depth_pruned"]["nodes"]
        if full and (pruned - full) / full > 0.10:
            regressions.append({"root_index": row["root_index"], "fraction": (pruned - full) / full})
    return {
        "fixed_depth_nodes_full": fixed_full,
        "fixed_depth_nodes_pruned": fixed_pruned,
        "fixed_depth_node_delta": fixed_pruned - fixed_full,
        "limited_completed_depth_sum_full": limited_full,
        "limited_completed_depth_sum_pruned": limited_pruned,
        "limited_completed_depth_delta": limited_pruned - limited_full,
        "beta_cutoffs_full": sum(row["fixed_depth_full"]["beta_cutoffs"] for row in rows),
        "beta_cutoffs_pruned": sum(row["fixed_depth_pruned"]["beta_cutoffs"] for row in rows),
        "fixed_depth_regressions_over_10_percent": regressions,
    }


def run() -> dict:
    if not native_available():
        raise RuntimeError("F73 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = _load_gen1(compiled)
    roots = f71._load_stable_roots()
    result = _base_result(gen1, roots)
    exact_rows, exact_failures = _run_exactness(compiled, native, gen1, roots)
    result["fixed_depth_parity"] = {"rows": exact_rows, "failures": exact_failures}
    if exact_failures:
        result["classification"] = "ROOT_PRUNING_PRODUCT_SEMANTICS_MISMATCH"
        result["contract_failures"] = exact_failures
        _atomic_json(RESULT_PATH, result)
        return result
    depth3_rows, depth3_failures = _run_depth3_subset(compiled, native, gen1, roots)
    result["depth3_parity"] = {"rows": depth3_rows, "failures": depth3_failures}
    if depth3_failures:
        result["classification"] = "ROOT_PRUNING_PRODUCT_SEMANTICS_MISMATCH"
        result["contract_failures"] = depth3_failures
        _atomic_json(RESULT_PATH, result)
        return result
    tt_rows, tt_failures = _run_tt_gate(compiled, native, gen1, roots)
    result["tt_on_retention"] = {"rows": tt_rows, "failures": tt_failures}
    if tt_failures:
        result["classification"] = "ROOT_PRUNING_PRODUCT_SEMANTICS_MISMATCH"
        result["contract_failures"] = tt_failures
        _atomic_json(RESULT_PATH, result)
        return result
    efficiency_rows, efficiency_failures = _run_efficiency(compiled, native, gen1, roots)
    result["efficiency"] = {"rows": efficiency_rows, "failures": efficiency_failures}
    result["efficiency_summary"] = _efficiency_summary(efficiency_rows)
    failures = efficiency_failures
    summary = result["efficiency_summary"]
    if failures:
        result["classification"] = "HARNESS_MISMATCH"
    elif (
        summary["fixed_depth_node_delta"] <= 0
        and summary["limited_completed_depth_delta"] >= 0
        and not summary["fixed_depth_regressions_over_10_percent"]
    ):
        result["classification"] = "ROOT_PRUNING_PRODUCT_SUPPORTED"
    elif summary["fixed_depth_node_delta"] > 0 or summary["limited_completed_depth_delta"] < 0 or summary["fixed_depth_regressions_over_10_percent"]:
        result["classification"] = "ROOT_PRUNING_PRODUCT_NEGATIVE"
    else:
        result["classification"] = "ROOT_PRUNING_PRODUCT_NEUTRAL"
    result["contract_failures"] = failures
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    print(json.dumps({
        "classification": result["classification"],
        "fixed_depth_failures": len(result["fixed_depth_parity"]["failures"]),
        "depth3_failures": len(result["depth3_parity"]["failures"]),
        "tt_failures": len(result["tt_on_retention"]["failures"]),
        "efficiency_failures": len(result["efficiency"]["failures"]),
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
