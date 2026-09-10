"""F71-R1 causal probe for a learned root move-ordering hint.

This is deliberately an experiment-local harness. It replays the twenty
stable F62 development roots with fresh Gen1 D0 engines and passes one
score-free root-only ordering hint for the seed-59011 policy action through the
narrow internal Native search capability. The result records the first root
action searched at every attempted iterative-deepening depth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.native.mirror import pack_semantic_action  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402


WORK_ORDER = "GENERICCHESS-F71-R1-ROOT-HINT-HARNESS-CORRECTIVE"
PARENT_SHA = "1f378782db9c1b1c314abdf863d4a94d37294cd4"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
GEN1_CANDIDATE = "F60_D0_PAIRWISE_SEED_59012"
HINT_SEED = 59011
NODES = 2_000
MAX_DEPTH = 12
F62_STAGE_SHA = "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
F62_RECORDS_SHA = "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"
F62_OUT = ROOT / ".generic_chess_flow" / "f62-learned-champion-repeatability"
F63_CANDIDATES = ROOT / ".generic_chess_flow" / "f63-champion-loop-causal-triage" / "candidates.json"
OUT = ROOT / ".generic_chess_flow" / "f71-r1-root-hint-harness-corrective"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f71_results.json"
F62_ROOT_INDICES = tuple(range(96))
EXPECTED_STABLE_ROOTS = 20
TT_MEGABYTES = 8


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _action_key(action: Any) -> str:
    return json.dumps(f59.action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _action_payload(action: Any) -> dict | None:
    return None if action is None else f59.action_to_dict(action)


def _load_gen1(compiled):
    data = json.loads(f62_model_params().read_text(encoding="utf-8"))
    row = next(item for item in data["corrected_candidates"] if item["candidate_id"] == GEN1_CANDIDATE)
    parent = f59._parent(LABEL)
    gen1 = f61r2._candidate_checkpoint(parent, row)
    if gen1.checkpoint_id != GEN1_ID or row["corrected_checkpoint_id"] != GEN1_ID:
        raise RuntimeError("F71 Gen1 durable champion identity mismatch")
    gen1.validate_ruleset(compiled)
    return gen1


def f62_model_params() -> Path:
    return ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json"


def _load_hint_scorer(compiled):
    payload = json.loads(F63_CANDIDATES.read_text(encoding="utf-8"))
    row = next(item for item in payload["candidates"] if item.get("seed") == HINT_SEED)
    checkpoint = LearnableMaterialCheckpoint.from_dict(row["checkpoint"])
    if row["checkpoint_id"] != checkpoint.checkpoint_id or row["parent_checkpoint_id"] != GEN1_ID:
        raise RuntimeError("F71 seed-59011 scorer identity mismatch")
    checkpoint.validate_ruleset(compiled)
    return checkpoint, row


def _load_stable_roots(limit: int | None = None) -> list[dict]:
    roots = []
    for index in F62_ROOT_INDICES:
        path = F62_OUT / "progress" / "spectrum" / f"root-{index:03d}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        identity = payload["identity"]
        metadata = payload["root_metadata"]
        record = identity["record"]
        if record.get("source_split") != "development":
            continue
        if metadata["root_40k"]["action_key"] != metadata["root_80k"]["action_key"]:
            continue
        roots.append({
            "root_index": index,
            "record": record,
            "metadata": metadata,
            "source_identity_sha256": payload["identity_sha256"],
        })
    if len(roots) != EXPECTED_STABLE_ROOTS:
        raise RuntimeError(f"F71 expected {EXPECTED_STABLE_ROOTS} stable development roots, found {len(roots)}")
    return roots if limit is None else roots[:limit]


def _scorer_hint(compiled, native, gen1, scorer, record: dict):
    session = f59._session(compiled, record)
    legal = sorted(session.legal_actions(), key=_action_key)
    model = CompactNonlinearResidual.from_dict(scorer.compact_nonlinear)
    scored = []
    for action in legal:
        features, base_q, _root_side = f59._child_features(
            compiled, native, gen1, record, f59.action_to_dict(action)
        )
        residual = float(model.predict(np.asarray([features], dtype=float))[0])
        scored.append((float(base_q) + residual, _action_key(action), action))
    if not scored:
        raise RuntimeError("F71 root has no legal actions")
    _score, _key, action = sorted(scored, key=lambda row: (-row[0], row[1]))[0]
    return action, {
        "action": _action_payload(action),
        "action_key": _action_key(action),
        "score": _score,
        "legal_action_count": len(legal),
        "scorer_checkpoint_id": scorer.checkpoint_id,
        "scorer_seed": HINT_SEED,
        "packed_action": int(pack_semantic_action(native, session.state.position, action)),
    }


def _search_arm_fixed(compiled, native, gen1, record, *, hint=None):
    """Search one fresh arm, optionally passing a root-only ordering hint."""
    session = f59._session(compiled, record)
    engine = SemanticSearchEngine(compiled, native, checkpoint=gen1, tt_megabytes=TT_MEGABYTES)
    result = engine.search(
        session,
        SearchLimits(max_depth=MAX_DEPTH, max_nodes=NODES, quiescence_max_depth=0),
        root_order_hint=hint,
        root_window_pruning=False,
    )
    return _result_payload(result)


def _result_payload(result):
    first_actions = tuple(result.root_iteration_first_actions)
    return {
        "action": _action_payload(result.action),
        "action_key": None if result.action is None else _action_key(result.action),
        "score": int(result.score),
        "nodes": int(result.nodes),
        "qnodes": int(result.qnodes),
        "completed_depth": int(result.completed_depth),
        "selective_depth": int(result.selective_depth),
        "termination_mode": str(result.termination_reason),
        "used_fallback": bool(result.used_fallback),
        "tt_status": str(result.tt_status),
        "tt_probes": int(result.tt_probes),
        "tt_hits": int(result.tt_hits),
        "tt_cutoffs": int(result.tt_cutoffs),
        "tt_stores": int(result.tt_stores),
        "tt_replacements": int(result.tt_replacements),
        "tt_entry_bytes": int(result.tt_entry_bytes),
        "tt_allocated_bytes": int(result.tt_allocated_bytes),
        "root_hint_requested": _action_payload(result.root_hint_requested),
        "root_hint_requested_action_key": (
            None if result.root_hint_requested is None else _action_key(result.root_hint_requested)
        ),
        "root_hint_legal": bool(result.root_hint_legal),
        "root_hint_apply_count": int(result.root_hint_apply_count),
        "root_iterations_attempted": int(result.root_iterations_attempted),
        "root_iteration_first_actions": [_action_payload(action) for action in first_actions],
        "root_iteration_first_action_keys": [
            None if action is None else _action_key(action) for action in first_actions
        ],
    }


def _arm_contract(arm: dict, *, hinted: bool) -> list[str]:
    failures = []
    if arm["nodes"] != NODES:
        failures.append(f"{'hinted' if hinted else 'baseline'} nodes={arm['nodes']} != {NODES}")
    if arm["qnodes"] != 0:
        failures.append(f"{'hinted' if hinted else 'baseline'} qnodes is nonzero")
    if hinted:
        if not arm.get("root_hint_requested_action_key"):
            failures.append("root hint request missing")
        if not arm.get("root_hint_legal"):
            failures.append("root hint was not found in the legal root action list")
        attempted = int(arm.get("root_iterations_attempted", 0))
        first = arm.get("root_iteration_first_action_keys", [])[:attempted]
        if len(first) != attempted:
            failures.append("root first-action telemetry length mismatch")
        if any(action_key != arm.get("root_hint_requested_action_key") for action_key in first):
            failures.append("hinted iteration did not search the requested root action first")
        if int(arm.get("root_hint_apply_count", 0)) != attempted:
            failures.append("root hint apply count did not cover every attempted iteration")
    return failures


def _classify(rows: list[dict], failures: list[str]) -> str:
    if failures:
        return "HARNESS_MISMATCH"
    baseline = sum(row["baseline_deep_agreement"] for row in rows)
    hinted = sum(row["hinted_deep_agreement"] for row in rows)
    if hinted > baseline:
        return "SUPPORTED"
    if hinted == baseline:
        return "NEUTRAL"
    return "NEGATIVE"


def _code_provenance() -> dict[str, str]:
    paths = (
        "scripts/f71_causal_root_hint_probe.py",
        "scripts/f59_action_spectrum_diagnosis.py",
        "generic_chess/native/semantic_engine.py",
        "generic_chess/_native/native_module.c",
    )
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}


def run(*, smoke: bool = False) -> dict:
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = _load_gen1(compiled)
    scorer, scorer_row = _load_hint_scorer(compiled)
    roots = _load_stable_roots(2 if smoke else None)
    rows = []
    failures = []
    for root in roots:
        metadata = root["metadata"]
        record = root["record"]
        cached = metadata["root_2k"]["action_key"]
        deep = metadata["root_80k"]["action_key"]
        root_failures = []
        baseline = _search_arm_fixed(compiled, native, gen1, record)
        if baseline["action_key"] != cached:
            root_failures.append("baseline did not reproduce cached F62 root_2k action")
        hint_action, hint_meta = _scorer_hint(compiled, native, gen1, scorer, record)
        if hint_meta["action_key"] not in {_action_key(action) for action in f59._session(compiled, record).legal_actions()}:
            root_failures.append("seed-59011 hint is not legal at root")
        hinted = _search_arm_fixed(compiled, native, gen1, record, hint=hint_action)
        root_failures.extend(_arm_contract(baseline, hinted=False))
        root_failures.extend(_arm_contract(hinted, hinted=True))
        if hinted["root_hint_requested_action_key"] != hint_meta["action_key"]:
            root_failures.append("hint action mismatch")
        repeat = _search_arm_fixed(compiled, native, gen1, record, hint=hint_action)
        if any(repeat[key] != hinted[key] for key in ("action_key", "score", "nodes", "qnodes", "completed_depth", "termination_mode")):
            root_failures.append("hinted repeatability mismatch")
        row = {
            "root_index": root["root_index"],
            "position_key": record["position_key"],
            "cached_root_2k_action": cached,
            "rerun_baseline_action": baseline["action_key"],
            "seed_59011_hint": hint_meta,
            "deep_consensus_action": deep,
            "hinted_2k_action": hinted["action_key"],
            "baseline_deep_agreement": baseline["action_key"] == deep,
            "hinted_deep_agreement": hinted["action_key"] == deep,
            "decision_changed": baseline["action_key"] != hinted["action_key"],
            "decision_relation": (
                "toward-deep" if baseline["action_key"] != deep and hinted["action_key"] == deep
                else "away-from-deep" if baseline["action_key"] == deep and hinted["action_key"] != deep
                else "lateral" if baseline["action_key"] != hinted["action_key"] else "unchanged"
            ),
            "baseline": baseline,
            "hinted": hinted,
            "hinted_repeat": repeat,
            "contract_failures": root_failures,
        }
        rows.append(row)
        failures.extend(f"root-{root['root_index']}: {failure}" for failure in root_failures)
        _atomic_json(PROGRESS / f"root-{root['root_index']:03d}.json", row)
    classification = _classify(rows, failures)
    result = {
        "schema": "generic-chess-f71-r1-root-hint-harness-corrective-v1",
        "work_order": WORK_ORDER,
        "classification": classification,
        "baseline_sha": PARENT_SHA,
        "f62_stage_identity_sha256": F62_STAGE_SHA,
        "f62_records_sha256": F62_RECORDS_SHA,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "hint_scorer": {"seed": HINT_SEED, "checkpoint_id": scorer.checkpoint_id, "model_sha256": scorer_row["model_sha256"]},
        "config": {"root_count": len(rows), "requested_root_count": EXPECTED_STABLE_ROOTS, "nodes": NODES, "max_depth": MAX_DEPTH, "tt_megabytes": TT_MEGABYTES, "fresh_runtime_per_arm": True, "root_only_hint": True, "smoke": smoke},
        "code_provenance": _code_provenance(),
        "aggregate": {
            "baseline_deep_agreement": sum(row["baseline_deep_agreement"] for row in rows),
            "hinted_deep_agreement": sum(row["hinted_deep_agreement"] for row in rows),
            "decision_changes": sum(row["decision_changed"] for row in rows),
            "toward_deep": sum(row["decision_relation"] == "toward-deep" for row in rows),
            "away_from_deep": sum(row["decision_relation"] == "away-from-deep" for row in rows),
            "lateral": sum(row["decision_relation"] == "lateral" for row in rows),
            "unchanged": sum(row["decision_relation"] == "unchanged" for row in rows),
            "root_hint_requested": sum(
                row["hinted"]["root_hint_requested_action_key"] is not None for row in rows
            ),
            "root_hint_legal": sum(row["hinted"]["root_hint_legal"] for row in rows),
            "root_hint_apply_count": sum(
                row["hinted"]["root_hint_apply_count"] for row in rows
            ),
            "root_iterations_attempted": sum(
                row["hinted"]["root_iterations_attempted"] for row in rows
            ),
            "root_hint_first_action_mismatches": sum(
                sum(
                    action_key != row["hinted"]["root_hint_requested_action_key"]
                    for action_key in row["hinted"]["root_iteration_first_action_keys"][:row["hinted"]["root_iterations_attempted"]]
                )
                for row in rows
            ),
        },
        "contract_failures": failures,
        "rows": rows,
    }
    _atomic_json(RESULT_PATH if not smoke else OUT / "f71_smoke_results.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    result = run(smoke=args.smoke)
    print(json.dumps({"classification": result["classification"], "aggregate": result["aggregate"], "contract_failures": result["contract_failures"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
