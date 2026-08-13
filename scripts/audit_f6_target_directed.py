"""Bounded F6 target-directed geometry audit and opt-in candidate probe.

H6A is deliberately harness-only: the production semantic executor is never
edited by this module.  The candidate replaces only ``is_square_attacked`` in
isolated workers and derives the exact queried target/path from the compiled
path representation.  ``geometry_candidates`` remains the oracle.
"""

from __future__ import annotations

import argparse
import cProfile
import json
import multiprocessing as mp
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.core import semantic_executor as se  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.ir import geometry_candidates  # noqa: E402
from generic_chess.learning.shogi_semantic_rules import (  # noqa: E402
    build_semantic_shogi_ruleset,
)
from scripts.audit_f4_runtime_cost import (  # noqa: E402
    FINGERPRINT,
    corpus_specs,
    make_session,
    run_once,
)
from rule_semantics_ir_fixtures import (  # noqa: E402
    cannon_ruleset,
    castling_ruleset,
    en_passant_ruleset,
    nifu_ruleset,
    uchifuzume_ruleset,
    weird_rulesets,
)


DEFAULT_TIMEOUT = 60.0
BOARD_SIZE = 9


def target_directed_matches(geometry, owner: int, source: int, target: int):
    """Return the exact oracle-shaped tuple for one queried board target."""
    if geometry.kind == "drop":
        return ()
    path = geometry.paths.get(str(owner), {}).get(source, ())
    if geometry.kind == "leap":
        return ((target, ()),) if path and path[0] == target else ()
    start = max(0, (geometry.min_steps or 1) - 1)
    return tuple(
        (target, tuple(path[:index]))
        for index in range(start, len(path))
        if path[index] == target
    )


def _oracle_matches(geometry, owner: int, source: int, target: int):
    return tuple(
        (candidate_target, candidate_path)
        for candidate_target, candidate_path in geometry_candidates(
            geometry, str(owner), source
        )
        if candidate_target == target
    )


def compiled_geometry_cases():
    """Return every compiled geometry in certified and generic fixtures."""
    cases = []
    seen = set()

    def add(label, compiled):
        for geometry_id, geometry in compiled.ir.geometry.items():
            key = (label, geometry_id)
            if key in seen:
                continue
            seen.add(key)
            cases.append((label, geometry_id, geometry, compiled.support.board_size))

    for spec in corpus_specs():
        if spec["kind"] != "semantic":
            continue
        add(spec["id"], make_session(spec).compiled)
    for label, ruleset in (
        ("fixture_cannon", cannon_ruleset()),
        ("fixture_castling_min_steps", castling_ruleset()),
        ("fixture_en_passant", en_passant_ruleset()),
        ("fixture_nifu", nifu_ruleset()),
        ("fixture_uchifuzume", uchifuzume_ruleset()),
    ):
        add(label, compile_semantic_ruleset(ruleset))
    for index, ruleset in enumerate(weird_rulesets()):
        add(f"fixture_weird_{index}", compile_semantic_ruleset(ruleset))
    add(
        "certified_shogi_direct",
        compile_semantic_ruleset(build_semantic_shogi_ruleset()),
    )
    return cases


def geometry_equivalence_rows():
    rows = []
    mismatches = 0
    for label, geometry_id, geometry, board_size in compiled_geometry_cases():
        square_count = board_size * board_size
        for owner in (0, 1):
            for source in range(square_count):
                for target in range(square_count):
                    baseline = _oracle_matches(geometry, owner, source, target)
                    candidate = target_directed_matches(geometry, owner, source, target)
                    exact = baseline == candidate
                    mismatches += not exact
                    rows.append(
                        {
                            "fixture": label,
                            "geometry_id": geometry_id,
                            "kind": geometry.kind,
                            "owner": owner,
                            "source": source,
                            "target": target,
                            "baseline_matches": [
                                [target_id, list(path)] for target_id, path in baseline
                            ],
                            "candidate_matches": [
                                [target_id, list(path)] for target_id, path in candidate
                            ],
                            "exact_match": exact,
                        }
                    )
    return rows, mismatches


class Counters:
    def __init__(self):
        self.values = Counter()

    def add(self, key, amount=1):
        self.values[key] += amount

    def snapshot(self):
        return dict(sorted(self.values.items()))


def _counting_geometry(counters, original):
    def wrapped(geometry, owner, source):
        path = geometry.paths.get(owner, {}).get(source, ())
        counters.add("path_entries_inspected", len(path))
        generated = 0
        try:
            for item in original(geometry, owner, source):
                generated += 1
                yield item
        finally:
            counters.add("geometry_candidate_calls")
            counters.add("geometry_candidates_generated", generated)

    return wrapped


def _candidate_attack(counters, original_geometry):
    def attack(self, position, square, by_owner, checkpoint=None):
        self._ensure_match(position)
        counters.add("attack_queries")
        sources = se._sources_by_owner_type(position)
        for pattern in self._patterns:
            se._checkpoint(checkpoint)
            if pattern.target.kind != "target_enemy":
                continue
            for tid in pattern.type_ids:
                se._checkpoint(checkpoint)
                for source, piece in sources.get((by_owner, tid), ()):
                    se._checkpoint(checkpoint)
                    for gid in pattern.geometry_ids:
                        se._checkpoint(checkpoint)
                        geometry = self.ir.geometry.get(gid)
                        if geometry is None or geometry.kind == "drop":
                            continue
                        if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                            continue
                        path = geometry.paths.get(str(by_owner), {}).get(source, ())
                        counters.add("target_directed_probe_calls")
                        counters.add("path_entries_inspected", len(path))
                        matches = target_directed_matches(geometry, by_owner, source, square)
                        if matches:
                            counters.add("queried_targets_found")
                        else:
                            counters.add("queried_targets_not_found")
                            counters.add("unrelated_candidates_avoided", max(0, len(path) - 1))
                        for target, candidate_path in matches:
                            se._checkpoint(checkpoint)
                            binding = self._make_binding(
                                pattern, gid, tid, piece, source, square, None,
                                candidate_path, position,
                            )
                            if self._path_holds(
                                pattern.path, position, binding, by_owner,
                                checkpoint=checkpoint,
                            ) and self._guards_hold(
                                pattern, position, binding, by_owner,
                                checkpoint=checkpoint,
                            ):
                                return True
        return False

    return attack


def _run_attack_queries(spec, candidate):
    session = make_session(spec)
    engine = se.semantic_engine_for(session.compiled)
    position = session.state.position
    counters = Counters()
    original_attack = SemanticEngine.is_square_attacked
    original_geometry = se.geometry_candidates
    if candidate:
        SemanticEngine.is_square_attacked = _candidate_attack(counters, original_geometry)
    else:
        se.geometry_candidates = _counting_geometry(counters, original_geometry)
    started = time.perf_counter()
    try:
        attacks = [
            engine.is_square_attacked(position, square, owner)
            for square in range(engine.support.board_size ** 2)
            for owner in (0, 1)
        ]
        checks = [engine.in_check(position, side) for side in (0, 1)]
    finally:
        SemanticEngine.is_square_attacked = original_attack
        se.geometry_candidates = original_geometry
    return {
        "case_id": spec["id"],
        "fingerprint": session.compiled.ruleset_fingerprint,
        "attack_query_count": len(attacks),
        "attack_true_count": sum(attacks),
        "check_results": checks,
        "wall_s": time.perf_counter() - started,
        "counters": counters.snapshot(),
    }


def _run_search(spec, profile, candidate, profile_path=None):
    counters = Counters()
    original_attack = SemanticEngine.is_square_attacked
    original_geometry = se.geometry_candidates
    if candidate:
        SemanticEngine.is_square_attacked = _candidate_attack(counters, original_geometry)
    else:
        se.geometry_candidates = _counting_geometry(counters, original_geometry)
    try:
        result = run_once(spec, profile, "timing", profile_path=profile_path)
    finally:
        SemanticEngine.is_square_attacked = original_attack
        se.geometry_candidates = original_geometry
    result["f6_counters"] = counters.snapshot()
    result["candidate"] = candidate
    return result


def _worker(payload, queue):
    try:
        mode = payload["mode"]
        if mode == "attack":
            result = _run_attack_queries(payload["spec"], payload["candidate"])
        elif mode == "search":
            result = _run_search(
                payload["spec"], payload["profile"], payload["candidate"],
                payload.get("profile_path"),
            )
        else:
            raise ValueError(mode)
        queue.put({"ok": True, "result": result})
    except BaseException as exc:  # pragma: no cover - bounded evidence worker
        queue.put({"ok": False, "error": repr(exc)})


def safe_run(payload, timeout=DEFAULT_TIMEOUT):
    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_worker, args=(payload, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join(5)
        raise RuntimeError(f"RUNTIME_SAFETY_ABORT: {payload['mode']}")
    if queue.empty():
        raise RuntimeError(f"worker failed without result: {payload['mode']}")
    message = queue.get()
    if not message["ok"]:
        raise RuntimeError(message["error"])
    return message["result"]


def semantic_specs():
    return [spec for spec in corpus_specs() if spec["kind"] == "semantic"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("geometry", "attack", "search"), required=True)
    parser.add_argument("--profile", choices=("A", "B"), default="A")
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-dir", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == "geometry":
        rows, mismatches = geometry_equivalence_rows()
        jsonl = args.output.with_suffix(".jsonl")
        jsonl.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
        payload = {
            "fingerprint": FINGERPRINT,
            "row_count": len(rows),
            "mismatches": mismatches,
            "result": "PASS" if mismatches == 0 else "FAIL",
            "jsonl": str(jsonl),
        }
    elif args.mode == "attack":
        payload = [
            safe_run({"mode": "attack", "spec": spec, "candidate": args.candidate})
            for spec in semantic_specs()
        ]
    else:
        rows = []
        for spec in corpus_specs():
            profile_path = None
            if args.profile_dir:
                args.profile_dir.mkdir(parents=True, exist_ok=True)
                profile_path = str(args.profile_dir / f"{spec['id']}.prof")
            rows.append(
                safe_run({
                    "mode": "search", "spec": spec, "profile": args.profile,
                    "candidate": args.candidate, "profile_path": profile_path,
                })
            )
        payload = rows
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
