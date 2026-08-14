"""F20 test-only AlphaBeta shadow route using Native legality only."""

from __future__ import annotations

import importlib.util
import json
import os
import statistics
import sys
import time
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f20_native_legality_kernel"
EXTENSION = Path(os.environ["F20_NATIVE_EXTENSION"])
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

spec = importlib.util.spec_from_file_location("generic_chess._native_core", EXTENSION)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load {EXTENSION}")
module = importlib.util.module_from_spec(spec)
sys.modules["generic_chess._native_core"] = module
spec.loader.exec_module(module)

from generic_chess.ai.alphabeta import search as search_module  # noqa: E402
from generic_chess.ai.alphabeta.search import run_root_search  # noqa: E402
from generic_chess.ai.alphabeta.statistics import SearchStatistics  # noqa: E402
from generic_chess.ai.alphabeta.transposition import TranspositionTable  # noqa: E402
from generic_chess.ai.alphabeta.search import SearchAborted  # noqa: E402
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.ai.limits import SearchLimits  # noqa: E402
from generic_chess.ai.alphabeta.tuning import SearchTuning  # noqa: E402
from generic_chess.core.search_runtime import SearchPathRuntime  # noqa: E402
from generic_chess.core.semantic_executor import _semantic_public_action  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.native.semantic import pack_position, transient_legal_actions, unpack_action  # noqa: E402
from scripts.audit_f4_runtime_cost import corpus_specs, make_session, profile_config  # noqa: E402
from scripts.audit_f20_h20b import internal_semantic, state_only_payload  # noqa: E402


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class NativeLegalityShadowRuntime(SearchPathRuntime):
    """Audit-only runtime; no production class or route is changed."""

    _native_by_fingerprint = {}

    @classmethod
    def from_state(cls, state, compiled, *, hash_override=None, history_witnesses=None):
        native = cls._native_by_fingerprint[compiled.ruleset_fingerprint]
        return cls(state, compiled, native, hash_override=hash_override, history_witnesses=history_witnesses)

    def __init__(self, state, compiled, native, *, hash_override=None, history_witnesses=None):
        super().__init__(state, compiled, hash_override=hash_override, history_witnesses=history_witnesses)
        self._shadow_native = native

    def legal_actions(self, checkpoint=None):
        if self._legal_cache is not None:
            return self._legal_cache
        if self.terminal_status.status.value != "ongoing":
            self._legal_cache = ()
            return self._legal_cache
        if checkpoint is not None:
            checkpoint()
        position = pack_position(self._shadow_native, state_only_payload_from_runtime(self, self._shadow_native))
        raw = transient_legal_actions(self._shadow_native, position)
        engine = __import__("generic_chess.core.semantic_executor", fromlist=["semantic_engine_for"]).semantic_engine_for(self.compiled)
        pattern_by_id = {pattern.pattern_id: pattern for pattern in engine._patterns}
        actions = []
        bindings = {}
        for packed in raw:
            fields = unpack_action(packed)
            semantic = internal_semantic(self._shadow_native, fields)
            pattern = pattern_by_id[semantic.pattern_id]
            binding = engine._make_binding_from_action(self.position, semantic, pattern)
            public = _semantic_public_action(engine, semantic)
            actions.append(public)
            bindings[public] = (semantic, binding)
        self._bindings = bindings
        self._legal_cache = tuple(actions)
        if checkpoint is not None:
            checkpoint()
        return self._legal_cache


def state_only_payload_from_runtime(runtime, native):
    type_map = {type_id: index for index, type_id in enumerate(native.type_ids)}
    board = []
    for piece in runtime.position.board:
        if piece is None:
            board.append(None)
        else:
            board.append([type_map[piece.base_type_id], type_map[piece.current_type_id], int(piece.owner), int(bool(piece.promoted))])
    hands = []
    for hand in runtime.position.hands:
        row = [0] * len(type_map)
        for type_id, count in hand.counts:
            row[type_map[type_id]] = int(count)
        hands.append(row)
    return {"side": int(runtime.position.side_to_move), "ply": int(runtime.ply_count), "board": board, "hands": hands, "aux_state": tuple(runtime.position.aux_state)}


def stats_snapshot(stats):
    ignored = {"time_to_first_legal_action", "time_to_first_completed_iteration"}
    out = {}
    for field in fields(stats):
        name = field.name
        if name in ignored or name.endswith("_seconds"):
            continue
        value = getattr(stats, name)
        out[name] = dict(value) if isinstance(value, dict) else value
    return out


def run_one(session, profile_name, shadow):
    compiled = session.compiled
    legacy = getattr(compiled, "_legacy_compiled", compiled)
    config = EvaluationConfig()
    evaluator = Evaluator(legacy, build_ruleset_profile(legacy, config), config)
    cfg = profile_config(profile_name)
    stats = SearchStatistics()
    started = time.perf_counter()
    original = search_module.SearchPathRuntime
    if shadow:
        search_module.SearchPathRuntime = NativeLegalityShadowRuntime
    try:
        result = run_root_search(
            session.state, compiled, evaluator, TranspositionTable(),
            SearchLimits(max_depth=int(cfg["max_depth"]), max_nodes=int(cfg["max_nodes"]), quiescence_max_depth=int(cfg["quiescence_max_depth"])),
            None, stats, use_tt=bool(cfg["use_tt"]), use_ordering=bool(cfg["use_ordering"]),
            tuning=cfg["tuning"], _history_witnesses=session._search_witnesses,
        )
    finally:
        search_module.SearchPathRuntime = original
    return {
        "action": None if result[0] is None else str(result[0]),
        "score": int(result[1]),
        "pv": [str(action) for action in result[2]],
        "termination_reason": str(result[3]),
        "stats": stats_snapshot(stats),
        "elapsed_us": (time.perf_counter() - started) * 1_000_000,
    }


def main():
    specs = [row for row in corpus_specs() if row["kind"] == "semantic"]
    for spec in specs:
        session = make_session(spec)
        native = compile_native_semantic_rules(session.compiled)
        NativeLegalityShadowRuntime._native_by_fingerprint[session.compiled.ruleset_fingerprint] = native

    parity_rows = []
    profile_rows = {"A": [], "B": []}
    for profile_name in ("A", "B"):
        for spec in specs:
            warm = make_session(spec)
            run_one(warm, profile_name, False)
            run_one(make_session(spec), profile_name, True)
            for repeat in range(5):
                baseline = run_one(make_session(spec), profile_name, False)
                native = run_one(make_session(spec), profile_name, True)
                equal = {
                    "action": baseline["action"] == native["action"],
                    "score": baseline["score"] == native["score"],
                    "pv": baseline["pv"] == native["pv"],
                    "termination_reason": baseline["termination_reason"] == native["termination_reason"],
                    "stats": baseline["stats"] == native["stats"],
                }
                row = {"case_id": spec["id"], "profile": profile_name, "repeat": repeat + 1, "baseline": baseline, "native_legality": native, "parity": equal, "all_equal": all(equal.values())}
                parity_rows.append(row)
                profile_rows[profile_name].append({"case_id": spec["id"], "repeat": repeat + 1, "baseline_us": baseline["elapsed_us"], "native_legality_us": native["elapsed_us"], "gain": 1 - native["elapsed_us"] / baseline["elapsed_us"], "all_equal": row["all_equal"]})

    write_json("search_shadow_parity.json", {"rows": parity_rows, "mismatches": sum(not row["all_equal"] for row in parity_rows), "status": "PASS" if all(row["all_equal"] for row in parity_rows) else "FAIL", "production_search_routing_changed": False})
    for profile_name in ("A", "B"):
        (OUT / f"profile_{profile_name.lower()}_baseline.jsonl").write_text("".join(json.dumps({"case_id": row["case_id"], "repeat": row["repeat"], "elapsed_us": row["baseline_us"], "all_equal": row["all_equal"]}, sort_keys=True) + "\n" for row in profile_rows[profile_name]), encoding="utf-8")
        (OUT / f"profile_{profile_name.lower()}_native_legality.jsonl").write_text("".join(json.dumps({"case_id": row["case_id"], "repeat": row["repeat"], "elapsed_us": row["native_legality_us"], "all_equal": row["all_equal"]}, sort_keys=True) + "\n" for row in profile_rows[profile_name]), encoding="utf-8")
    summary = {}
    for profile_name, rows in profile_rows.items():
        baseline = statistics.median(row["baseline_us"] for row in rows)
        native = statistics.median(row["native_legality_us"] for row in rows)
        by_case = {}
        for case in specs:
            subset = [row for row in rows if row["case_id"] == case["id"]]
            by_case[case["id"]] = {"baseline_us": statistics.median(row["baseline_us"] for row in subset), "native_legality_us": statistics.median(row["native_legality_us"] for row in subset), "gain": statistics.median(row["gain"] for row in subset), "all_equal": all(row["all_equal"] for row in subset)}
        summary[profile_name] = {"baseline_us": baseline, "native_legality_us": native, "gain": 1 - native / baseline, "cases": by_case}
    write_json("end_to_end_search_performance.json", summary)
    print(json.dumps({"parity": all(row["all_equal"] for row in parity_rows), "profile_summary": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
