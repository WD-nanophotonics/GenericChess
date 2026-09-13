"""Small, ruleset-parameterized F61 Gen0 -> Gen1 strength triage.

This driver deliberately reuses the existing F59 spectrum, F61 residual fit,
and equal-budget role-swapped Arena path.  It runs one D0/PAIRWISE_RANKING
training seed and four Arena pairs per ruleset; Standard Shogi and canonical
Chess are evaluated first, and the generated control is opened only when
Shogi is not a directional failure.  Raw results stay under
``.generic_chess_flow``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from generic_chess.ai.benchmark.audit_suite import build_compiled, standard_ruleset_specs  # noqa: E402
from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.learning.arena import ArenaConfig, run_arena  # noqa: E402
from generic_chess.learning.material import LearnableMaterialCheckpoint  # noqa: E402
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
from generic_chess.rules.compiler import (  # noqa: E402
    _build_semantic_support,
    compile_ruleset_for_execution,
    compile_semantic_ruleset,
    lower_legacy_to_ir,
)
from generic_chess.rules.ir import CompiledSemanticRuleset  # noqa: E402
from scripts import f50_generic_learnable_evaluator as f50  # noqa: E402
from scripts import f54_direct_capacity_and_gradient_geometry_diagnosis as f54  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f61_strength_first_triage as f61  # noqa: E402


WORK_ORDER = "GENERICCHESS-GEN0-GEN1-STRENGTH-TRIAGE"
TRAINING_SEED = 59012
ROOT_COUNT = 24
ARENA_PAIRS = 4
ARENA_NODES = 2_000
ARENA_MAX_DEPTH = 12
ARENA_TT_MB = 8
RULESET_ORDER = (
    "B_CANONICAL_STANDARD_SHOGI",
    "A_CANONICAL_WESTERN_CHESS",
    "GEN_CLASSIC_LIKE_4_101",
)
OUT = ROOT / ".generic_chess_flow" / "f61-gen0-gen1-strength-triage"


def _generated_context():
    spec = next(item for item in standard_ruleset_specs() if item.fixture_id == "gen_classic_like_4_101")
    legacy = build_compiled(spec)
    # Generator fixtures are legacy CompiledRuleSets.  Lower that exact
    # generated ruleset into the same semantic IR/native path used by F59/F61;
    # do not substitute a hand-written semantic fixture.
    ir = lower_legacy_to_ir(legacy)
    ir = replace(
        ir,
        capabilities=replace(ir.capabilities, new_ir_core_executable=True),
    )
    compiled = CompiledSemanticRuleset(
        ir=ir,
        _legacy_compiled=legacy,
        support=_build_semantic_support(legacy),
    )
    native = compile_native_semantic_rules(compiled)
    profile = build_ruleset_profile(legacy, EvaluationConfig())
    parent = LearnableMaterialCheckpoint.from_profile(compiled, profile, training_seed=5400000)
    return compiled, native, parent, spec.fixture_id


def _context(label: str):
    if label == "GEN_CLASSIC_LIKE_4_101":
        return _generated_context()
    compiled, native, _profile = f50._ruleset(label)
    return compiled, native, f54._parent(label), label


def _record(position) -> dict:
    return {
        "index": position.index,
        "action_history": [f59.action_to_dict(action) for action in position.action_history],
        "position_key": position.position_key,
        "side_to_move": position.side_to_move,
        "ply": position.ply,
    }


def _d0_records(compiled, seed: int, *, count: int, smoke: bool) -> list[dict]:
    openings = generate_arena_openings(compiled, count=max(8, count), seed=seed, min_plies=2, max_plies=6)
    from generic_chess.learning.diagnostics import generate_diagnostic_corpus

    corpus = generate_diagnostic_corpus(
        compiled, openings, count=count, seed=seed + 1,
        min_plies=4 if smoke else 8, max_plies=12 if smoke else 40,
    )
    return [_record(position) for position in corpus.positions]


def _fit_one(compiled, native, parent, records: list[dict], *, smoke: bool):
    rows = []
    for record in records:
        spectrum, _meta = f59._spectrum_for_root(
            compiled, native, parent, parent, record, smoke=smoke
        )
        usable = [row for row in spectrum if row.q_20k is not None]
        if len(usable) >= 2:
            rows.append(usable)
    if not rows:
        raise RuntimeError("D0 produced no trainable action spectra")
    features = __import__("numpy").vstack([row.features for root in rows for row in root])
    base = __import__("numpy").asarray([row.base_q for root in rows for row in root])
    targets = __import__("numpy").asarray([row.q_20k for root in rows for row in root])
    groups = []
    cursor = 0
    for root in rows:
        groups.append(__import__("numpy").arange(cursor, cursor + len(root)))
        cursor += len(root)
    model = f61._fit_serializable(
        features, base, targets, groups, "PAIRWISE_RANKING", TRAINING_SEED
    )
    spec = {
        "candidate_id": "F61_D0_PAIRWISE_SEED_59012",
        "training_distribution": "D0_RANDOM_REACHABLE",
        "objective": "PAIRWISE_RANKING",
        "seed": TRAINING_SEED,
    }
    child, model_payload = f61._candidate_checkpoint(parent, compiled, model, spec)
    return child, {
        "training_seed": TRAINING_SEED,
        "training_roots": len(rows),
        "training_actions": int(len(features)),
        "objective": "PAIRWISE_RANKING",
        "model_width": f61.MODEL_WIDTH,
        "regularization": f61.MODEL_REGULARIZATION,
        "model_sha256": f61.stable_sha256(model_payload),
    }


def _arena(compiled, native, parent, child, *, seed: int, smoke: bool) -> dict:
    pairs = 2 if smoke else ARENA_PAIRS
    openings = generate_arena_openings(compiled, count=pairs, seed=seed, min_plies=2, max_plies=6)
    summary = run_arena(
        compiled, native, parent, child,
        ArenaConfig(
            pairs=pairs, nodes_per_move=100 if smoke else ARENA_NODES,
            max_depth=4 if smoke else ARENA_MAX_DEPTH,
            tt_megabytes=2 if smoke else ARENA_TT_MB,
            opening_seed=seed, opening_count=pairs, min_plies=2, max_plies=6,
            workers=1,
        ),
        openings=openings,
    )
    return {
        "pair_count": summary.pair_count,
        "pair_scores": list(summary.pair_scores),
        "mean_pair_score": summary.mean_pair_score,
        "child_better_pairs": summary.child_better_pairs,
        "tied_pairs": summary.tied_pairs,
        "child_worse_pairs": summary.child_worse_pairs,
        "game_wins": summary.game_wins,
        "game_draws": summary.game_draws,
        "game_losses": summary.game_losses,
        "bootstrap_low": summary.bootstrap_low,
        "bootstrap_high": summary.bootstrap_high,
    }


def _directional_failure(arena: dict) -> bool:
    return (
        arena["mean_pair_score"] < 0.5
        and arena["child_worse_pairs"] > arena["child_better_pairs"]
    )


def run(*, smoke: bool = False, root_count: int = ROOT_COUNT) -> dict:
    started = time.perf_counter()
    results = []
    for index, label in enumerate(RULESET_ORDER):
        if label == "GEN_CLASSIC_LIKE_4_101" and any(
            row.get("label") == "B_CANONICAL_STANDARD_SHOGI" and row.get("directional_failure")
            for row in results
        ):
            break
        compiled, native, parent, ruleset_id = _context(label)
        records = _d0_records(compiled, 620000 + index * 100, count=3 if smoke else root_count, smoke=smoke)
        child, training = _fit_one(compiled, native, parent, records, smoke=smoke)
        arena = _arena(compiled, native, parent, child, seed=620700 + index, smoke=smoke)
        results.append({
            "label": label,
            "ruleset_id": ruleset_id,
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
            "parent_checkpoint_id": parent.checkpoint_id,
            "child_checkpoint_id": child.checkpoint_id,
            "training": training,
            "arena": arena,
            "directional_failure": _directional_failure(arena),
        })
    return {
        "schema": "generic-chess-f61-gen0-gen1-strength-triage-v1",
        "work_order": WORK_ORDER,
        "ruleset_order": list(RULESET_ORDER),
        "root_count": 3 if smoke else root_count,
        "arena_pairs": 2 if smoke else ARENA_PAIRS,
        "arena_gate": "actual_equal_budget_parent_child_strength",
        "teacher_metrics_are_diagnostic_only": True,
        "results": results,
        "wall_seconds": time.perf_counter() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--root-count", type=int, default=ROOT_COUNT)
    parser.add_argument("--output-name", default="f61_gen0_gen1_strength_triage.json")
    args = parser.parse_args()
    if not args.smoke and args.root_count != ROOT_COUNT:
        raise ValueError(f"root-count is frozen at {ROOT_COUNT} outside smoke mode")
    OUT.mkdir(parents=True, exist_ok=True)
    payload = run(smoke=args.smoke, root_count=args.root_count)
    (OUT / args.output_name).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "work_order": WORK_ORDER,
        "rulesets_run": [row["label"] for row in payload["results"]],
        "directional_failures": [row["label"] for row in payload["results"] if row["directional_failure"]],
        "wall_seconds": payload["wall_seconds"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
