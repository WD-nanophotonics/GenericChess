"""Bounded F72 probe for root alpha-beta pruning leverage."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset  # noqa: E402
from generic_chess.rules.western_chess import build_western_chess_ruleset  # noqa: E402
from generic_chess.session.session import GameSession  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f71_causal_root_hint_probe as f71  # noqa: E402


WORK_ORDER = "GENERICCHESS-F72-ROOT-PRUNING-POLICY-LEVERAGE-PROBE"
PARENT_SHA = "f193983819f2b3842e18ea714a89ec2268b18b78"
LABEL = f71.LABEL
GEN1_ID = f71.GEN1_ID
GEN1_CANDIDATE = f71.GEN1_CANDIDATE
HINT_SEED = f71.HINT_SEED
NODES = 2_000
MAX_DEPTH = 12
PARITY_DEPTHS = (1, 2)
TT_MEGABYTES = 8
EXPECTED_ROOTS = 20
F62_STAGE_SHA = f71.F62_STAGE_SHA
F62_RECORDS_SHA = f71.F62_RECORDS_SHA
OUT = ROOT / ".generic_chess_flow" / "f72-root-pruning-policy-leverage-probe"
RESULT_PATH = OUT / "f72_results.json"
PROGRESS = OUT / "progress"


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _action_key(action: Any) -> str | None:
    return None if action is None else f71._action_key(action)


def _payload(result) -> dict:
    first = tuple(result.root_iteration_first_actions)
    return {
        "action": None if result.action is None else f71._action_payload(result.action),
        "action_key": _action_key(result.action),
        "score": int(result.score),
        "nodes": int(result.nodes),
        "qnodes": int(result.qnodes),
        "completed_depth": int(result.completed_depth),
        "termination_mode": str(result.termination_reason),
        "used_fallback": bool(result.used_fallback),
        "declaration_id": result.declaration_id,
        "principal_variation": [f71._action_payload(action) for action in result.principal_variation],
        "principal_variation_keys": [_action_key(action) for action in result.principal_variation],
        "decision_line": [
            item if isinstance(item, str) else f71._action_payload(item)
            for item in result.decision_line
        ],
        "tt_probes": int(result.tt_probes),
        "tt_hits": int(result.tt_hits),
        "tt_cutoffs": int(result.tt_cutoffs),
        "beta_cutoffs": int(result.beta_cutoffs),
        "root_window_pruning": bool(result.root_window_pruning),
        "root_hint_requested_action_key": _action_key(result.root_hint_requested),
        "root_hint_legal": bool(result.root_hint_legal),
        "root_hint_apply_count": int(result.root_hint_apply_count),
        "root_iterations_attempted": int(result.root_iterations_attempted),
        "root_iteration_first_action_keys": [_action_key(action) for action in first],
    }


def _parity_signature(result) -> tuple:
    row = _payload(result)
    return (
        row["action_key"], row["score"], tuple(row["principal_variation_keys"]),
        tuple(json.dumps(item, sort_keys=True) for item in row["decision_line"]),
        row["completed_depth"], row["termination_mode"], row["used_fallback"],
        row["declaration_id"],
    )


def _load_gen1(compiled):
    data = json.loads(f71.f62_model_params().read_text(encoding="utf-8"))
    row = next(item for item in data["corrected_candidates"] if item["candidate_id"] == GEN1_CANDIDATE)
    parent = f59._parent(LABEL)
    gen1 = f61r2._candidate_checkpoint(parent, row)
    if gen1.checkpoint_id != GEN1_ID:
        raise RuntimeError("F72 Gen1 identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1


def _parity_cases(compiled, native, gen1, roots):
    cases = [(f"shogi-root-{root['root_index']}", f59._session(compiled, root["record"]),
              ("checkpoint", native, gen1))
             for root in roots]
    for name, ruleset in (
        ("western-initial", build_western_chess_ruleset()),
        ("shogi-initial", build_standard_shogi_ruleset()),
    ):
        semantic = compile_semantic_ruleset(ruleset)
        semantic_native = compile_native_semantic_rules(semantic)
        zero = (0,) * len(semantic_native.type_ids)
        cases.append((name, GameSession(semantic), ("profile", semantic_native, zero)))
    return cases


def _parity_search(session, native_or_profile, depth: int, pruning: bool):
    if isinstance(native_or_profile, tuple):
        kind, native, values = native_or_profile
        if kind == "checkpoint":
            engine = SemanticSearchEngine(
                session.compiled, native, checkpoint=values, tt_megabytes=0
            )
        else:
            engine = SemanticSearchEngine(
                session.compiled, native, board_values=values,
                hand_values=values, tt_megabytes=0
            )
    else:
        engine = SemanticSearchEngine(
            session.compiled, native_or_profile, checkpoint=None, tt_megabytes=0
        )
    return engine.search(
        session,
        SearchLimits(max_depth=depth, max_nodes=None, quiescence_max_depth=0),
        root_window_pruning=pruning,
    )


def _run_parity_gate(compiled, native, gen1, roots):
    failures = []
    rows = []
    cases = _parity_cases(compiled, native, gen1, roots)
    for name, session, case_config in cases:
        search_native = case_config
        for depth in PARITY_DEPTHS:
            full = _parity_search(session, search_native, depth, False)
            pruned = _parity_search(session, search_native, depth, True)
            full_repeat = _parity_search(session, search_native, depth, False)
            pruned_repeat = _parity_search(session, search_native, depth, True)
            mismatch = []
            if _parity_signature(full) != _parity_signature(pruned):
                mismatch.append("full-window vs root-pruning semantic result mismatch")
            if _parity_signature(full) != _parity_signature(full_repeat):
                mismatch.append("full-window repeatability mismatch")
            if _parity_signature(pruned) != _parity_signature(pruned_repeat):
                mismatch.append("root-pruning repeatability mismatch")
            row = {
                "case": name,
                "depth": depth,
                "full_window": _payload(full),
                "root_pruning": _payload(pruned),
                "mismatches": mismatch,
            }
            rows.append(row)
            failures.extend(f"{name}/depth-{depth}: {item}" for item in mismatch)
    return rows, failures


def _policy_arm(compiled, native, gen1, record, *, hint=None, pruning=False):
    session = f59._session(compiled, record)
    engine = SemanticSearchEngine(
        compiled, native, checkpoint=gen1, tt_megabytes=TT_MEGABYTES
    )
    result = engine.search(
        session,
        SearchLimits(max_depth=MAX_DEPTH, max_nodes=NODES, quiescence_max_depth=0),
        root_order_hint=hint,
        root_window_pruning=pruning,
    )
    return _payload(result)


def _arm_contract(arm: dict, label: str, *, hint_key: str | None = None) -> list[str]:
    failures = []
    if arm["nodes"] != NODES:
        failures.append(f"{label} nodes={arm['nodes']} != {NODES}")
    if arm["qnodes"] != 0:
        failures.append(f"{label} qnodes is nonzero")
    if label == "A" and arm["root_window_pruning"]:
        failures.append("A unexpectedly enabled root pruning")
    if label in {"B", "C"} and not arm["root_window_pruning"]:
        failures.append(f"{label} did not enable root pruning")
    if label == "C":
        if arm["root_hint_requested_action_key"] != hint_key:
            failures.append("C requested hint mismatch")
        if not arm["root_hint_legal"]:
            failures.append("C hint is not legal at root")
        attempted = arm["root_iterations_attempted"]
        first = arm["root_iteration_first_action_keys"]
        if len(first) != attempted:
            failures.append("C first-root-action telemetry length mismatch")
        if any(action_key != hint_key for action_key in first):
            failures.append("C did not search the requested hint first on every iteration")
        if arm["root_hint_apply_count"] != attempted:
            failures.append("C root-hint apply count mismatch")
    return failures


def _classify(rows, failures):
    if failures:
        return "HARNESS_MISMATCH"
    b = sum(row["B_deep_agreement"] for row in rows)
    c = sum(row["C_deep_agreement"] for row in rows)
    if c > b:
        return "ROOT_POLICY_LEVERAGE_SUPPORTED"
    if c == b:
        return "ROOT_POLICY_LEVERAGE_NEUTRAL"
    return "ROOT_POLICY_LEVERAGE_NEGATIVE"


def _provenance():
    paths = (
        "scripts/f72_root_pruning_policy_leverage_probe.py",
        "generic_chess/_native/native_module.c",
        "generic_chess/native/semantic_engine.py",
        "scripts/f71_causal_root_hint_probe.py",
    )
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}


def run() -> dict:
    if not native_available():
        raise RuntimeError("F72 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = _load_gen1(compiled)
    scorer, scorer_row = f71._load_hint_scorer(compiled)
    roots = f71._load_stable_roots()
    parity_rows, parity_failures = _run_parity_gate(compiled, native, gen1, roots)
    result = {
        "schema": "generic-chess-f72-root-pruning-policy-leverage-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": PARENT_SHA,
        "config": {
            "root_count": len(roots), "requested_root_count": EXPECTED_ROOTS,
            "nodes": NODES, "max_depth": MAX_DEPTH, "parity_depths": PARITY_DEPTHS,
            "tt_megabytes": TT_MEGABYTES, "fresh_runtime_per_arm": True,
            "qsearch_max_depth": 0,
        },
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "hint_scorer": {
            "seed": HINT_SEED, "checkpoint_id": scorer.checkpoint_id,
            "model_sha256": scorer_row["model_sha256"],
        },
        "f62_stage_identity_sha256": F62_STAGE_SHA,
        "f62_records_sha256": F62_RECORDS_SHA,
        "code_provenance": _provenance(),
        "fixed_depth_parity": {
            "status": "FAIL" if parity_failures else "PASS",
            "case_count": len({row["case"] for row in parity_rows}),
            "depths": PARITY_DEPTHS,
            "rows": parity_rows,
            "failures": parity_failures,
        },
    }
    if parity_failures:
        result["classification"] = "ROOT_PRUNING_SEMANTICS_MISMATCH"
        result["contract_failures"] = parity_failures
        _atomic_json(RESULT_PATH, result)
        return result

    rows = []
    failures = []
    for root in roots:
        record = root["record"]
        cached = root["metadata"]["root_2k"]["action_key"]
        deep = root["metadata"]["root_80k"]["action_key"]
        hint, hint_meta = f71._scorer_hint(compiled, native, gen1, scorer, record)
        hint_key = hint_meta["action_key"]
        a = _policy_arm(compiled, native, gen1, record)
        b = _policy_arm(compiled, native, gen1, record, pruning=True)
        c = _policy_arm(compiled, native, gen1, record, hint=hint, pruning=True)
        c_repeat = _policy_arm(compiled, native, gen1, record, hint=hint, pruning=True)
        root_failures = []
        if a["action_key"] != cached:
            root_failures.append("A did not reproduce cached F62 root_2k action")
        root_failures.extend(_arm_contract(a, "A"))
        root_failures.extend(_arm_contract(b, "B"))
        root_failures.extend(_arm_contract(c, "C", hint_key=hint_key))
        if _parity_signature_from_payload(c) != _parity_signature_from_payload(c_repeat):
            root_failures.append("C repeatability mismatch")
        row = {
            "root_index": root["root_index"],
            "position_key": record["position_key"],
            "cached_root_2k_action": cached,
            "deep_consensus_action": deep,
            "seed_59011_hint": hint_meta,
            "A": a, "B": b, "C": c, "C_repeat": c_repeat,
            "A_deep_agreement": a["action_key"] == deep,
            "B_deep_agreement": b["action_key"] == deep,
            "C_deep_agreement": c["action_key"] == deep,
            "A_to_B_changed": a["action_key"] != b["action_key"],
            "B_to_C_changed": b["action_key"] != c["action_key"],
            "contract_failures": root_failures,
        }
        rows.append(row)
        failures.extend(f"root-{root['root_index']}: {item}" for item in root_failures)
        _atomic_json(PROGRESS / f"root-{root['root_index']:03d}.json", row)

    result["classification"] = _classify(rows, failures)
    result["aggregate"] = {
        "A_deep_agreement": sum(row["A_deep_agreement"] for row in rows),
        "B_deep_agreement": sum(row["B_deep_agreement"] for row in rows),
        "C_deep_agreement": sum(row["C_deep_agreement"] for row in rows),
        "A_to_B_decision_changes": sum(row["A_to_B_changed"] for row in rows),
        "B_to_C_decision_changes": sum(row["B_to_C_changed"] for row in rows),
        "C_root_hint_requested": sum(row["C"]["root_hint_requested_action_key"] is not None for row in rows),
        "C_root_hint_legal": sum(row["C"]["root_hint_legal"] for row in rows),
        "C_root_hint_apply_count": sum(row["C"]["root_hint_apply_count"] for row in rows),
        "C_root_iterations_attempted": sum(row["C"]["root_iterations_attempted"] for row in rows),
        "C_root_hint_first_action_mismatches": sum(
            sum(key != row["C"]["root_hint_requested_action_key"] for key in row["C"]["root_iteration_first_action_keys"])
            for row in rows
        ),
        "A_reproduced_cached_root_2k": sum(
            row["A"]["action_key"] == row["cached_root_2k_action"] for row in rows
        ),
    }
    result["contract_failures"] = failures
    result["rows"] = rows
    _atomic_json(RESULT_PATH, result)
    return result


def _parity_signature_from_payload(row: dict) -> tuple:
    return (
        row["action_key"], row["score"], tuple(row["principal_variation_keys"]),
        tuple(json.dumps(item, sort_keys=True) for item in row["decision_line"]),
        row["completed_depth"], row["termination_mode"], row["used_fallback"],
        row["declaration_id"],
    )


def main() -> None:
    result = run()
    print(json.dumps({
        "classification": result["classification"],
        "fixed_depth_parity": result["fixed_depth_parity"]["status"],
        "aggregate": result.get("aggregate", {}),
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
