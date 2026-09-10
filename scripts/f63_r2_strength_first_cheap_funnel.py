"""F63-R2 strength-first funnel.

This module deliberately gives each scientific boundary its own entry point.
Stage 0 is a bounded correctness/search screen; later Arena stages are
prerequisite-gated and are not silently launched by this module.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.core.actions import action_to_dict  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_r2_fresh_strength as f61r2  # noqa: E402
from scripts import f62_learned_champion_repeatability as f62  # noqa: E402
from scripts import f63_champion_loop_causal_triage as f63  # noqa: E402
from scripts import exact_generic_preference_solver_v3 as exact_solver  # noqa: E402


WORK_ORDER = "GENERICCHESS-F63-R2-STRENGTH-FIRST-CHEAP-FUNNEL"
PARENT_SHA = "0a109224311c625a635d3ecdc58e63b2a04e5586"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
CANDIDATE_SEEDS = (59011, 59012, 59013)
STAGE_NAMES = ("screen", "short64", "arena2", "arena4", "arena8")
STAGE0_ROOTS_PER_DISTRIBUTION = 1
STAGE0_NODES = 2_000
STAGE0_MAX_DEPTH = 12
EXACT_PROBE_NODES = 16
EXACT_PROBE_DEPTH = 1
OUT = ROOT / ".generic_chess_flow" / "f63-r2-strength-first-cheap-funnel"
RESULT_PATH = OUT / "screen_results.json"


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _action_key(payload: dict | None) -> str | None:
    return None if payload is None else stable_sha256(payload)


def _candidate_population(compiled):
    """Reconstruct the frozen F62 population without changing its recipe."""
    gen1, _row = f62._load_gen1(compiled)
    if gen1.checkpoint_id != GEN1_ID:
        raise RuntimeError("F63-R2 Gen1 identity mismatch")
    summary, provenance, persisted, persisted_identity = f63._load_f62_training_summary(compiled, gen1)
    rows = []
    for seed in CANDIDATE_SEEDS:
        if seed == 59012:
            candidate = persisted
            identity = {
                "seed": seed,
                "checkpoint_id": candidate.checkpoint_id,
                "parent_checkpoint_id": gen1.checkpoint_id,
                "source": "exact_persisted_f62_gen2",
                "training_records_sha256": persisted_identity["training"]["records_sha256"],
            }
        else:
            candidate, fitted = f63._fit_candidate(compiled, gen1, summary, provenance, seed)
            identity = {
                "seed": seed,
                "checkpoint_id": candidate.checkpoint_id,
                "parent_checkpoint_id": gen1.checkpoint_id,
                "source": "reconstructed_f62_training_evidence",
                "training_records_sha256": fitted["training"]["records_sha256"],
            }
        candidate.validate_ruleset(compiled)
        rows.append({"seed": seed, "checkpoint": candidate, "identity": identity})
    return gen1, rows


def historical_r10_status() -> dict[str, Any]:
    """Return historical R10 evidence without allowing it into selection."""
    progress = f63.PROGRESS
    counts = {}
    for seed in CANDIDATE_SEEDS:
        path = progress / f"candidate-{seed}-common-4-calibrated-seed-630403"
        counts[str(seed)] = len(list(path.glob("game-*.json"))) if path.is_dir() else 0
    return {
        "classification": "R10_COMMON4_USER_STOPPED_UNEQUAL_EXPOSURE",
        "counts": counts,
        "comparable": False,
        "selection_authority": "forbidden",
    }


def stage0_proxy_is_diagnostic(name: str) -> bool:
    return name in {
        "teacher_agreement", "ranking_agreement", "scalar_value_fit",
        "action_regret", "action_gap", "teacher_action",
    }


def stage0_hard_fail(*, correctness_violation: bool) -> bool:
    return bool(correctness_violation)


def short64_outcome(*, complete: bool, winner: str | None = None, max_plies: int = 64) -> dict[str, Any]:
    if not complete and max_plies == 64:
        return {"status": "UNRESOLVED", "score": None, "winner": None}
    return {"status": "COMPLETE", "score": winner, "winner": winner}


def pair_score(*, complete: bool, child_score: float | None) -> float | None:
    return None if not complete else child_score


def stage2_survives(mean_pair_score: float) -> bool:
    return mean_pair_score >= 0.5


def stage3_positive(mean_pair_score: float, better_pairs: int, worse_pairs: int) -> bool:
    return mean_pair_score > 0.5 and better_pairs > worse_pairs


def stage4_requires_complete(completed_pairs: int, required_pairs: int = 8) -> bool:
    return completed_pairs == required_pairs


def _search(compiled, native, checkpoint, record):
    return f59._root_search(compiled, native, checkpoint, record, STAGE0_NODES)


def _exact_probe(compiled, record) -> dict[str, Any]:
    session = f59._session(compiled, record)
    try:
        result = exact_solver.solve_root_threshold_v3(
            compiled,
            session.state,
            max_nodes=EXACT_PROBE_NODES,
            max_depth=EXACT_PROBE_DEPTH,
        )
    except (AttributeError, RuntimeError, ValueError, TypeError) as exc:
        return {"status": "UNRESOLVED", "backend": exact_solver.SOLVER_VERSION, "error": type(exc).__name__}
    return {
        "status": "PROVED" if result.root_value is not None else "UNRESOLVED",
        "backend": exact_solver.SOLVER_VERSION,
        "root_value": result.root_value,
        "optimal_action_count": len(result.optimal_actions),
        "nodes": result.stats.get("states_expanded", 0),
    }


def _screen_one(compiled, native, gen1, candidate, distribution, records, gen1_results, exact_results):
    rows = []
    correctness_failures = []
    for index, record in enumerate(records):
        session = f59._session(compiled, record)
        legal = {json.dumps(action_to_dict(action), sort_keys=True) for action in session.legal_actions()}
        gen1_result = gen1_results[index]
        candidate_result = _search(compiled, native, candidate, record)
        for label, result in (("gen1", gen1_result), ("candidate", candidate_result)):
            action = result["action"]
            if action is not None and json.dumps(action, sort_keys=True) not in legal:
                correctness_failures.append({"index": index, "actor": label, "reason": "illegal_selected_action"})
        repeated = _search(compiled, native, candidate, record) if index == 0 else None
        row = {
            "index": index,
            "position_key": record["position_key"],
            "selected_action": candidate_result["action"],
            "gen1_selected_action": gen1_result["action"],
            "teacher_action": gen1_result["action"],
            "teacher_agreement": candidate_result["action_key"] == gen1_result["action_key"],
            "action_regret": None,
            "action_rank": None,
            "action_gap": None,
            "search": {
                "nodes": candidate_result["nodes"],
                "completed_depth": candidate_result["completed_depth"],
                "deterministic_repeatability": (
                    None if repeated is None else candidate_result["action_key"] == repeated["action_key"]
                ),
            },
            "exact_solver": exact_results[index],
        }
        rows.append(row)
    return {
        "distribution": distribution,
        "root_count": len(rows),
        "rows": rows,
        "correctness_failures": correctness_failures,
        "hard_fail": stage0_hard_fail(correctness_violation=bool(correctness_failures)),
        "proxy_metrics_diagnostic_only": True,
    }


def run_screen(*, root_count: int = STAGE0_ROOTS_PER_DISTRIBUTION) -> dict[str, Any]:
    if root_count != STAGE0_ROOTS_PER_DISTRIBUTION:
        raise ValueError("Stage 0 correctness smoke requires exactly 1 deterministic root per named distribution")
    compiled, native, _profile = f59._ruleset(f59.LABELS[1])
    gen1, candidates = _candidate_population(compiled)
    openings = f59.generate_arena_openings(
        compiled, count=3, seed=630501, min_plies=2, max_plies=6
    )
    smoke_records = [
        f59._record_from_actions(compiled, opening.actions)
        for opening in openings.openings
    ]
    if any(record is None for record in smoke_records):
        raise RuntimeError("Stage 0 deterministic smoke opening did not produce a legal root")
    distributions = {
        name: [smoke_records[index]]
        for index, name in enumerate(("D0_RANDOM_REACHABLE", "D1_V2_SELFPLAY", "D2_V2_PV_CORRIDOR"))
    }
    provenance = {
        "mode": "minimal_correctness_smoke",
        "source": "three deterministic opening roots",
        "not_a_claim_about_distribution": True,
        "opening_seed": 630501,
    }
    screen = {name: {} for name in distributions}
    for name, records in distributions.items():
        gen1_results = [_search(compiled, native, gen1, record) for record in records]
        exact_results = [_exact_probe(compiled, record) for record in records]
        for row in candidates:
            screen[name][str(row["seed"])] = _screen_one(
                compiled, native, gen1, row["checkpoint"], name, records,
                gen1_results, exact_results,
            )
    payload = {
        "schema": "generic-chess-f63-r2-stage0-screen-v1",
        "work_order": WORK_ORDER,
        "parent_repository_sha": PARENT_SHA,
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "candidate_population": [row["identity"] for row in candidates],
        "distributions": list(distributions),
        "provenance": provenance,
        "historical_r10": historical_r10_status(),
        "selection_authority": "equal_budget_paired_strength_only",
        "proxy_gate": "diagnostic_only; cannot eliminate a candidate",
        "mode": "minimal_correctness_smoke",
        "screen": screen,
    }
    _atomic_json(RESULT_PATH, payload)
    return payload


def run_short64():
    raise RuntimeError("short64 requires the frozen Stage 0 artifact and a separate reviewed work-order boundary")


def run_arena2():
    raise RuntimeError("arena2 requires short64 prerequisites and a separate reviewed work-order boundary")


def run_arena4():
    raise RuntimeError("arena4 requires arena2 prerequisites and a separate reviewed work-order boundary")


def run_arena8():
    raise RuntimeError("arena8 requires arena4 prerequisites and a separate reviewed work-order boundary")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=STAGE_NAMES, required=True)
    parser.add_argument("--root-count", type=int, default=STAGE0_ROOTS_PER_DISTRIBUTION)
    args = parser.parse_args()
    started = time.perf_counter()
    if args.stage == "screen":
        result = run_screen(root_count=args.root_count)
        print(json.dumps({
            "work_order": WORK_ORDER,
            "stage": args.stage,
            "hard_failures": sum(
                len(value[str(seed)]["correctness_failures"])
                for value in result["screen"].values() for seed in CANDIDATE_SEEDS
            ),
            "wall_seconds": time.perf_counter() - started,
            "result_path": str(RESULT_PATH),
        }, sort_keys=True))
        return
    {"short64": run_short64, "arena2": run_arena2, "arena4": run_arena4, "arena8": run_arena8}[args.stage]()


if __name__ == "__main__":
    main()
