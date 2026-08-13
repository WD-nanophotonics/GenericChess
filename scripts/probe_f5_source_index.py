"""Probe Option A: a position-local owner/current-type source index.

This is an opt-in candidate probe.  It monkeypatches only spawned workers and
does not alter product source until the evidence gate authorizes the change.
The two candidate methods preserve pattern, type, source, geometry, target,
and promotion loop order; only the repeated full-board source scan changes.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from scripts.audit_f4_runtime_cost import (  # noqa: E402
    corpus_specs,
    make_session,
    run_once,
)
from generic_chess.core import semantic_executor as se  # noqa: E402
from generic_chess.core.semantic_executor import SemanticEngine  # noqa: E402

DEFAULT_TIMEOUT = 180.0


def _source_index(position):
    index = {}
    for source, piece in enumerate(position.board):
        if piece is not None:
            index.setdefault((piece.owner, piece.current_type_id), []).append((source, piece))
    return {key: tuple(value) for key, value in index.items()}


def fast_is_square_attacked(self, position, square, by_owner, checkpoint=None):
    self._ensure_match(position)
    sources = _source_index(position)
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
                    for target, path in se.geometry_candidates(geometry, str(by_owner), source):
                        se._checkpoint(checkpoint)
                        if target != square:
                            continue
                        binding = self._make_binding(
                            pattern, gid, tid, piece, source, square, None, path, position
                        )
                        if self._path_holds(
                            pattern.path, position, binding, by_owner, checkpoint=checkpoint
                        ) and self._guards_hold(
                            pattern, position, binding, by_owner, checkpoint=checkpoint
                        ):
                            return True
    return False


def fast_iter_board_candidates(self, pattern, position, checkpoint=None):
    side = position.side_to_move
    sources = _source_index(position)
    for tid in pattern.type_ids:
        se._checkpoint(checkpoint)
        for source, piece in sources.get((side, tid), ()):
            se._checkpoint(checkpoint)
            for gid in pattern.geometry_ids:
                se._checkpoint(checkpoint)
                geometry = self.ir.geometry.get(gid)
                if geometry is None or geometry.kind == "drop":
                    continue
                if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                    continue
                for target, path in se.geometry_candidates(geometry, str(side), source):
                    se._checkpoint(checkpoint)
                    if not self._target_holds(pattern.target.kind, position, target, side):
                        continue
                    promotions = self._promotion_choices(pattern, piece, source, target)
                    for promotion_target in promotions:
                        se._checkpoint(checkpoint)
                        binding = self._make_binding(
                            pattern, gid, tid, piece, source, target,
                            promotion_target, path, position,
                        )
                        if not self._path_holds(
                            pattern.path, position, binding, side, checkpoint=checkpoint
                        ):
                            continue
                        if not self._guards_hold(
                            pattern, position, binding, side, checkpoint=checkpoint
                        ):
                            continue
                        yield se.SemanticAction(
                            pattern_id=pattern.pattern_id,
                            source=source,
                            target=target,
                            promotion_target_id=promotion_target,
                            actor_type=tid,
                            geometry_id=gid,
                        ), binding


def install_candidate():
    SemanticEngine.is_square_attacked = fast_is_square_attacked
    SemanticEngine._iter_board_candidates = fast_iter_board_candidates


def candidate_search(spec, profile):
    session = make_session(spec)
    baseline_actions = None
    if se.semantic_engine_for(session.compiled) is not None:
        engine = se.semantic_engine_for(session.compiled)
        baseline_actions = tuple(str(action) for action in engine.iter_legal_actions(session.state.position))
    install_candidate()
    if baseline_actions is not None:
        engine = se.semantic_engine_for(session.compiled)
        candidate_actions = tuple(str(action) for action in engine.iter_legal_actions(session.state.position))
        parity = baseline_actions == candidate_actions
    else:
        parity = True
    started = time.perf_counter()
    result = run_once(spec, profile, "timing")
    result["probe_wall_s"] = time.perf_counter() - started
    result["legal_order_parity"] = parity
    return result


def candidate_attack_differential(spec):
    session = make_session(spec)
    engine = se.semantic_engine_for(session.compiled)
    position = session.state.position
    baseline = [
        engine.is_square_attacked(position, square, owner)
        for square in range(engine.support.board_size * engine.support.board_size)
        for owner in (0, 1)
    ]
    baseline_actions = tuple(str(action) for action in engine.iter_legal_actions(position))
    install_candidate()
    candidate = [
        engine.is_square_attacked(position, square, owner)
        for square in range(engine.support.board_size * engine.support.board_size)
        for owner in (0, 1)
    ]
    candidate_actions = tuple(str(action) for action in engine.iter_legal_actions(position))
    mismatches = sum(before != after for before, after in zip(baseline, candidate))
    return {
        "case_id": spec["id"],
        "query_count": len(baseline),
        "attack_mismatches": mismatches,
        "baseline_true_count": sum(baseline),
        "candidate_true_count": sum(candidate),
        "legal_order_parity": baseline_actions == candidate_actions,
        "legal_action_count": len(baseline_actions),
    }


def _worker(payload, queue):
    try:
        if payload["mode"] == "attack_diff":
            result = candidate_attack_differential(payload["spec"])
        else:
            result = candidate_search(payload["spec"], payload["profile"])
        queue.put({"ok": True, "result": result})
    except BaseException as exc:  # pragma: no cover - bounded probe evidence
        queue.put({"ok": False, "error": repr(exc)})


def safe_run(payload):
    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_worker, args=(payload, queue))
    process.start()
    process.join(DEFAULT_TIMEOUT)
    if process.is_alive():
        process.terminate()
        process.join(5)
        raise RuntimeError(f"RUNTIME_SAFETY_ABORT: {payload['spec']['id']}")
    if queue.empty():
        raise RuntimeError(f"worker failed: {payload['spec']['id']}")
    message = queue.get()
    if not message["ok"]:
        raise RuntimeError(message["error"])
    return message["result"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("search", "attack_diff"), default="search")
    parser.add_argument("--profile", choices=("A", "B"))
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    specs = [spec for spec in corpus_specs() if spec["kind"] == "semantic"] if args.mode == "attack_diff" else corpus_specs()
    for spec in specs:
        for repetition in range(args.reps):
            row = safe_run({"mode": args.mode, "spec": spec, "profile": args.profile})
            row["repetition"] = repetition + 1
            rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
