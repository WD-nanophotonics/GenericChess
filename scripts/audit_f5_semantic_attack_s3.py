"""Bounded F5 audit for semantic attack and S3 legality work.

This module is deliberately an audit-only layer.  It wraps the existing F4
corpus/search runner and instruments the semantic executor in a spawned worker;
the production executor is not changed by the baseline harness.
"""

from __future__ import annotations

import argparse
import inspect
import json
import multiprocessing as mp
import sys
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from scripts.audit_f4_runtime_cost import (  # noqa: E402
    FINGERPRINT,
    corpus_specs,
    make_session,
    run_once,
    safe_run as f4_safe_run,
)
from generic_chess.core import semantic_executor as se  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402


DEFAULT_TIMEOUT = 180.0


def _roles_for_attack_trace():
    """Resolve loop line numbers from source, avoiding brittle line literals."""
    source, start = inspect.getsourcelines(SemanticEngine.is_square_attacked)
    roles = {}
    needles = {
        "patterns_visited": "for pattern in self._patterns:",
        "type_ids_visited": "for tid in pattern.type_ids:",
        "board_slots_inspected": "for source, piece in enumerate(position.board):",
        "geometry_ids_inspected": "for gid in pattern.geometry_ids:",
        "geometry_candidates_generated": "for target, path in geometry_candidates(",
        "target_matches": "if target != square:",
    }
    for role, needle in needles.items():
        matches = [start + i for i, line in enumerate(source) if needle in line]
        if len(matches) != 1:
            raise AssertionError(f"cannot resolve trace line for {role}: {matches}")
        roles[role] = matches[0]
    return roles


class F5Counters:
    def __init__(self) -> None:
        self.values = Counter()

    def count(self, key: str, amount: int = 1) -> None:
        self.values[key] += amount

    def snapshot(self) -> dict[str, int]:
        return dict(sorted(self.values.items()))


@contextmanager
def instrument_semantic_executor(counters: F5Counters):
    """Install reversible, test-only wrappers and a targeted line tracer."""
    original_attack = SemanticEngine.is_square_attacked
    original_in_check = SemanticEngine.in_check
    original_iter_board = SemanticEngine._iter_board_candidates
    original_trial = SemanticEngine._trial_child_if_s3_legal
    original_exists = SemanticEngine._exists_s3_reply
    original_path = SemanticEngine._path_holds
    original_guards = SemanticEngine._guards_hold
    original_anchor = se._own_anchor
    original_geometry = se.geometry_candidates
    roles = _roles_for_attack_trace()

    def attack(self, position, square, by_owner, checkpoint=None):
        counters.count("attack_queries")
        result = original_attack(self, position, square, by_owner, checkpoint=checkpoint)
        counters.count("successful_attack_early_exits" if result else "failed_full_scans")
        return result

    def in_check(self, position, side, checkpoint=None):
        counters.count("in_check_calls")
        result = original_in_check(self, position, side, checkpoint=checkpoint)
        return result

    def iter_board(self, pattern, position, checkpoint=None):
        for item in original_iter_board(self, pattern, position, checkpoint=checkpoint):
            counters.count("s0_s1_candidates")
            yield item

    def trial(self, pattern, position, action, binding, checkpoint=None):
        counters.count("s3_trial_transitions")
        result = original_trial(self, pattern, position, action, binding, checkpoint=checkpoint)
        counters.count("s3_accepted" if result is not None else "s3_rejected")
        return result

    def exists(self, position, checkpoint=None):
        counters.count("s3_reply_probes")
        return original_exists(self, position, checkpoint=checkpoint)

    def path(self, predicates, position, binding, perspective, checkpoint=None):
        counters.count("path_checks")
        return original_path(self, predicates, position, binding, perspective, checkpoint=checkpoint)

    def guards(self, pattern, position, binding, perspective, checkpoint=None):
        counters.count("guard_checks")
        return original_guards(self, pattern, position, binding, perspective, checkpoint=checkpoint)

    def anchor(position, support, side):
        counters.count("own_anchor_lookup_calls")
        return original_anchor(position, support, side)

    def geometry(*args, **kwargs):
        generated = 0
        try:
            for item in original_geometry(*args, **kwargs):
                generated += 1
                yield item
        finally:
            counters.count("geometry_candidates_generated", generated)
            counters.count("geometry_candidate_calls")

    def trace(frame, event, arg):
        if frame.f_code is original_attack.__code__ and event == "line":
            for role, line in roles.items():
                if frame.f_lineno == line:
                    counters.count(role)
        return trace

    SemanticEngine.is_square_attacked = attack
    SemanticEngine.in_check = in_check
    SemanticEngine._iter_board_candidates = iter_board
    SemanticEngine._trial_child_if_s3_legal = trial
    SemanticEngine._exists_s3_reply = exists
    SemanticEngine._path_holds = path
    SemanticEngine._guards_hold = guards
    se._own_anchor = anchor
    se.geometry_candidates = geometry
    old_trace = sys.gettrace()
    sys.settrace(trace)
    try:
        yield
    finally:
        sys.settrace(old_trace)
        SemanticEngine.is_square_attacked = original_attack
        SemanticEngine.in_check = original_in_check
        SemanticEngine._iter_board_candidates = original_iter_board
        SemanticEngine._trial_child_if_s3_legal = original_trial
        SemanticEngine._exists_s3_reply = original_exists
        SemanticEngine._path_holds = original_path
        SemanticEngine._guards_hold = original_guards
        se._own_anchor = original_anchor
        se.geometry_candidates = original_geometry


def semantic_specs():
    return [spec for spec in corpus_specs() if spec["kind"] == "semantic"]


def attack_micro_specs():
    return [
        {
            "id": spec["id"],
            "source": spec,
            "squares": "all",
            "owners": [0, 1],
        }
        for spec in semantic_specs()
    ]


def _run_attack_micro(spec):
    session = make_session(spec["source"])
    engine = se.semantic_engine_for(session.compiled)
    if engine is None:
        raise AssertionError("semantic micro corpus did not produce a semantic engine")
    position = session.state.position
    counters = F5Counters()
    started = time.perf_counter()
    with instrument_semantic_executor(counters):
        results = []
        for square in range(engine.support.board_size * engine.support.board_size):
            for owner in spec["owners"]:
                results.append(engine.is_square_attacked(position, square, owner))
    return {
        "case_id": spec["id"],
        "fingerprint": session.compiled.ruleset_fingerprint,
        "query_count": len(results),
        "true_count": sum(results),
        "wall_s": time.perf_counter() - started,
        "counters": counters.snapshot(),
    }


def _run_s3_micro(spec):
    session = make_session(spec)
    engine = se.semantic_engine_for(session.compiled)
    counters = F5Counters()
    started = time.perf_counter()
    with instrument_semantic_executor(counters):
        actions = tuple(engine.iter_legal_actions(session.state.position))
    return {
        "case_id": spec["id"],
        "fingerprint": session.compiled.ruleset_fingerprint,
        "legal_action_count": len(actions),
        "legal_actions": [str(action) for action in actions],
        "wall_s": time.perf_counter() - started,
        "counters": counters.snapshot(),
    }


def _worker(payload, queue):
    try:
        mode = payload["mode"]
        if mode == "attack_micro":
            result = _run_attack_micro(payload["spec"])
        elif mode == "s3_micro":
            result = _run_s3_micro(payload["spec"])
        elif mode == "search":
            counters = F5Counters()
            with instrument_semantic_executor(counters):
                result = run_once(
                    payload["spec"],
                    payload["profile_name"],
                    "timing",
                )
            result["f5_counters"] = counters.snapshot()
        else:
            raise ValueError(mode)
        queue.put({"ok": True, "result": result})
    except BaseException as exc:  # pragma: no cover - controller evidence
        queue.put({"ok": False, "error": repr(exc)})


def safe_run(payload, timeout: float = DEFAULT_TIMEOUT):
    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_worker, args=(payload, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join(5)
        raise RuntimeError(f"RUNTIME_SAFETY_ABORT: {payload.get('mode')}")
    if queue.empty():
        raise RuntimeError(f"worker failed without result: {payload.get('mode')}")
    message = queue.get()
    if not message["ok"]:
        raise RuntimeError(message["error"])
    return message["result"]


def run_micro(mode: str):
    if mode == "attack":
        return [safe_run({"mode": "attack_micro", "spec": spec}) for spec in attack_micro_specs()]
    if mode == "s3":
        return [safe_run({"mode": "s3_micro", "spec": spec}) for spec in semantic_specs()]
    raise ValueError(mode)


def run_search(profile_name: str, reps: int = 1):
    rows = []
    for spec in corpus_specs():
        for repetition in range(reps):
            row = safe_run({"mode": "search", "spec": spec, "profile_name": profile_name})
            row["repetition"] = repetition + 1
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("attack", "s3", "search"), required=True)
    parser.add_argument("--profile", choices=("A", "B"), default="A")
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "search":
        payload = run_search(args.profile, args.reps)
    else:
        payload = run_micro(args.mode)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
