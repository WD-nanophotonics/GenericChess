"""F71 causal probe for a learned root move-ordering hint.

This is deliberately an experiment-local harness.  It replays the twenty
stable F62 development roots with fresh Gen1 D0 engines and injects one
depth-zero, score-free root TT entry for the seed-59011 policy action.  The
native semantic engine has no public TT-store API, so the narrow capsule
bridge below is guarded by the native structure sizes and writes no production
search state outside the fresh experiment engine.
"""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
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
from generic_chess.native.adapter import pack_semantic_search_position  # noqa: E402
from generic_chess.native.mirror import pack_semantic_action  # noqa: E402
from generic_chess.native.semantic_engine import SemanticSearchEngine  # noqa: E402
from generic_chess.native import _module  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402


WORK_ORDER = "GENERICCHESS-F71-CAUSAL-ROOT-HINT-PROBE"
PARENT_SHA = "a180486b6a709a456d4a55a44a35ef716d4e4e20"
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
OUT = ROOT / ".generic_chess_flow" / "f71-causal-root-hint-probe"
PROGRESS = OUT / "progress"
RESULT_PATH = OUT / "f71_results.json"
F62_ROOT_INDICES = tuple(range(96))
EXPECTED_STABLE_ROOTS = 20
TT_MEGABYTES = 8
TT_HINT_DEPTH = 0
_MASK64 = (1 << 64) - 1


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


class _SemAux(ctypes.Structure):
    _fields_ = [
        ("kind", ctypes.c_uint8), ("has_value", ctypes.c_uint8),
        ("supplied", ctypes.c_uint8), ("bool_value", ctypes.c_int32),
        ("square", ctypes.c_uint16),
    ]


class _SemPosition(ctypes.Structure):
    _fields_ = [
        ("rules_fingerprint", ctypes.c_char * 65),
        ("board", ctypes.c_uint8 * (256 * 8)),
        ("hand_counts", ctypes.c_uint16 * (2 * 64)),
        ("side_to_move", ctypes.c_uint8), ("ply", ctypes.c_uint16),
        ("aux", _SemAux * (8 * 3)),
        ("history_lo", ctypes.c_uint64 * 1025),
        ("history_hi", ctypes.c_uint64 * 1025),
        ("history_digest", (ctypes.c_uint64 * 4) * 1025),
        ("history_actor", ctypes.c_uint8 * 1025),
        ("history_gave_check", ctypes.c_uint8 * 1025),
        ("history_len", ctypes.c_uint16),
        ("history_exact", ctypes.c_uint8),
        ("history_events_exact", ctypes.c_uint8),
    ]


class _SemEntry(ctypes.Structure):
    _fields_ = [
        ("position_digest", ctypes.c_uint64 * 4),
        ("history_context", ctypes.c_uint64 * 4),
        ("history_len", ctypes.c_uint16), ("depth", ctypes.c_uint16),
        ("score", ctypes.c_int32), ("best_action", ctypes.c_uint64),
        ("generation", ctypes.c_uint32), ("bound", ctypes.c_uint8),
        ("occupied", ctypes.c_uint8), ("has_action", ctypes.c_uint8),
    ]


class _SemBucket(ctypes.Structure):
    _fields_ = [("entries", _SemEntry * 4)]


class _SemTable(ctypes.Structure):
    _fields_ = [
        ("buckets", ctypes.c_void_p), ("bucket_count", ctypes.c_size_t),
        ("requested_bytes", ctypes.c_size_t), ("allocated_bytes", ctypes.c_size_t),
        ("generation", ctypes.c_uint32), ("occupied_entries", ctypes.c_uint64),
    ]


class _SemEngine(ctypes.Structure):
    _fields_ = [
        ("rules", ctypes.c_void_p), ("rules_capsule", ctypes.c_void_p),
        ("board_values", ctypes.c_void_p), ("hand_values", ctypes.c_void_p),
        ("dynamic_values", ctypes.c_void_p), ("spatial_values", ctypes.c_void_p),
        ("localized_control_values", ctypes.c_void_p), ("compact_values", ctypes.c_void_p),
        ("evaluator_scale", ctypes.c_uint), ("_padding", ctypes.c_uint),
        ("tt", ctypes.c_void_p), ("busy", ctypes.c_int),
    ]


def _capsule_pointer(capsule, name: str) -> int:
    getter = ctypes.pythonapi.PyCapsule_GetPointer
    getter.argtypes = [ctypes.py_object, ctypes.c_char_p]
    getter.restype = ctypes.c_void_p
    pointer = getter(capsule, name.encode("ascii"))
    if not pointer:
        raise RuntimeError(f"F71 failed to unwrap {name}")
    return int(pointer)


def _mix(value: int) -> int:
    value ^= value >> 30
    value = (value * 0xBF58476D1CE4E5B9) & _MASK64
    value ^= value >> 27
    value = (value * 0x94D049BB133111EB) & _MASK64
    return (value ^ (value >> 31)) & _MASK64


def _root_context(position: _SemPosition) -> tuple[int, ...]:
    context = [0, 0, 0, 0]
    for index in range(int(position.history_len)):
        event = (int(position.history_actor[index]) << 8) | int(position.history_gave_check[index])
        digest = position.history_digest[index]
        next_context = []
        for lane in range(4):
            value = context[lane] ^ int(digest[lane]) ^ event
            value ^= index * 0x9E3779B97F4A7C15
            value ^= (lane + 1) * 0xD6E8FEB86659FD93
            next_context.append(_mix((value + context[(lane + 1) & 3]) & _MASK64))
        context = next_context
    return tuple(context)


def _search_arm_fixed(compiled, native, gen1, record, *, hint=None):
    """Search arm with the hint pack performed from the exact Python root."""
    session = f59._session(compiled, record)
    engine = SemanticSearchEngine(compiled, native, checkpoint=gen1, tt_megabytes=TT_MEGABYTES)
    injection = None
    if hint is not None:
        position = pack_semantic_search_position(compiled, native, session)
        injection = _inject_root_hint_with_action(engine, position, session.state.position, hint, native)
    result = engine.search(session, SearchLimits(max_depth=MAX_DEPTH, max_nodes=NODES, quiescence_max_depth=0))
    return _result_payload(result, injection)


def _inject_root_hint_with_action(engine, position_capsule, python_position, action, native):
    expected_size = int(_module().semantic_search_runtime_sizes()["position_bytes"])
    expected_entry = int(engine.tt_info()["entry_size"])
    if ctypes.sizeof(_SemPosition) != expected_size or ctypes.sizeof(_SemEntry) != expected_entry:
        raise RuntimeError("F71 native capsule layout mismatch")
    engine_pointer = _capsule_pointer(engine._capsule, "generic_chess._native_core.gc_semantic_engine")
    position_pointer = _capsule_pointer(position_capsule, "generic_chess._native_core.gc_semantic_position")
    native_position = _SemPosition.from_address(position_pointer)
    native_engine = _SemEngine.from_address(engine_pointer)
    if not native_engine.tt:
        raise RuntimeError("F71 hinted arm unexpectedly has no TT")
    table = _SemTable.from_address(int(native_engine.tt))
    context = _root_context(native_position)
    history_len = int(native_position.history_len)
    digest = tuple(int(value) for value in native_position.history_digest[history_len - 1])
    mixed = history_len
    for lane in range(4):
        mixed = _mix(mixed ^ digest[lane] ^ context[lane])
    bucket_index = mixed & (int(table.bucket_count) - 1)
    bucket = _SemBucket.from_address(int(table.buckets) + bucket_index * ctypes.sizeof(_SemBucket))
    target = next((entry for entry in bucket.entries if not entry.occupied), bucket.entries[0])
    packed = int(pack_semantic_action(native, python_position, action))
    for lane in range(4):
        target.position_digest[lane] = digest[lane]
        target.history_context[lane] = context[lane]
    target.history_len = history_len
    target.depth = TT_HINT_DEPTH
    target.score = 0
    target.best_action = packed
    target.generation = int(table.generation)
    target.bound = 0
    target.occupied = 1
    target.has_action = 1
    return {
        "entry_depth": TT_HINT_DEPTH,
        "entry_score": 0,
        "entry_bound": "NONE",
        "entry_has_action": True,
        "entry_generation": int(table.generation),
        "bucket_index": int(bucket_index),
        "packed_action": packed,
        "history_len": history_len,
    }


def _result_payload(result, injection=None):
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
        "hint_injection": injection,
    }


def _arm_contract(arm: dict, *, hinted: bool) -> list[str]:
    failures = []
    if arm["nodes"] != NODES:
        failures.append(f"{'hinted' if hinted else 'baseline'} nodes={arm['nodes']} != {NODES}")
    if arm["qnodes"] != 0:
        failures.append(f"{'hinted' if hinted else 'baseline'} qnodes is nonzero")
    if hinted:
        if not arm.get("hint_injection"):
            failures.append("hint injection missing")
        else:
            injection = arm["hint_injection"]
            for key, expected in (("entry_depth", 0), ("entry_score", 0), ("entry_bound", "NONE"), ("entry_has_action", True)):
                if injection.get(key) != expected:
                    failures.append(f"hint entry {key} contract failed")
    return failures


def _classify(rows: list[dict], failures: list[str]) -> str:
    if failures:
        return "HARNESS_MISMATCH"
    baseline = sum(row["baseline_deep_agreement"] for row in rows)
    hinted = sum(row["hinted_deep_agreement"] for row in rows)
    if hinted > baseline:
        return "ROOT_HINT_CAUSAL_SUPPORTED"
    if hinted == baseline:
        return "ROOT_HINT_CAUSAL_NEUTRAL"
    return "ROOT_HINT_CAUSAL_NEGATIVE"


def _code_provenance() -> dict[str, str]:
    paths = ("scripts/f71_causal_root_hint_probe.py", "scripts/f59_action_spectrum_diagnosis.py", "generic_chess/native/semantic_engine.py")
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
        if hinted["hint_injection"]["packed_action"] != hint_meta["packed_action"]:
            root_failures.append("hint packed action mismatch")
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
        "schema": "generic-chess-f71-causal-root-hint-v1",
        "work_order": WORK_ORDER,
        "classification": classification,
        "baseline_sha": PARENT_SHA,
        "f62_stage_identity_sha256": F62_STAGE_SHA,
        "f62_records_sha256": F62_RECORDS_SHA,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "hint_scorer": {"seed": HINT_SEED, "checkpoint_id": scorer.checkpoint_id, "model_sha256": scorer_row["model_sha256"]},
        "config": {"root_count": len(rows), "requested_root_count": EXPECTED_STABLE_ROOTS, "nodes": NODES, "max_depth": MAX_DEPTH, "tt_megabytes": TT_MEGABYTES, "tt_hint_depth": TT_HINT_DEPTH, "fresh_runtime_per_arm": True, "smoke": smoke},
        "code_provenance": _code_provenance(),
        "aggregate": {
            "baseline_deep_agreement": sum(row["baseline_deep_agreement"] for row in rows),
            "hinted_deep_agreement": sum(row["hinted_deep_agreement"] for row in rows),
            "decision_changes": sum(row["decision_changed"] for row in rows),
            "toward_deep": sum(row["decision_relation"] == "toward-deep" for row in rows),
            "away_from_deep": sum(row["decision_relation"] == "away-from-deep" for row in rows),
            "lateral": sum(row["decision_relation"] == "lateral" for row in rows),
            "unchanged": sum(row["decision_relation"] == "unchanged" for row in rows),
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
