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
import os
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
from generic_chess.learning.arena import ArenaConfig, run_arena_game_resumable  # noqa: E402
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
CHECKPOINT_SCHEMA = "generic-chess-f61-training-root-v1"


def _training_budget_signature(*, smoke: bool) -> dict[str, int]:
    """The frozen search budgets that make a completed root resumable."""
    return {
        "root_2k_nodes": 50 if smoke else 2_000,
        "root_80k_nodes": 200 if smoke else 80_000,
        "cheap_nodes": 50 if smoke else 1_000,
        "target_nodes": 200 if smoke else 20_000,
        "max_depth": 12,
        "tt_megabytes": 8,
    }


def _checkpoint_path(compiled, record: dict, *, smoke: bool) -> Path:
    fingerprint = str(compiled.ruleset_fingerprint)
    record_digest = f61.stable_sha256(record)
    return OUT / "checkpoints" / fingerprint[:16] / (
        f"{record_digest[:32]}-{'smoke' if smoke else 'full'}.json"
    )


def _checkpoint_metadata(compiled, parent, record: dict, *, smoke: bool) -> dict:
    return {
        "schema": CHECKPOINT_SCHEMA,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "root_position_identity": record["position_key"],
        "root_record_sha256": f61.stable_sha256(record),
        "parent_checkpoint_id": parent.checkpoint_id,
        "training_seed": TRAINING_SEED,
        "budget_signature": _training_budget_signature(smoke=smoke),
    }


def _serialize_spectrum(rows) -> list[dict]:
    return [
        {
            "action": row.action,
            "action_key": row.action_key,
            "features": row.features.tolist(),
            "base_q": row.base_q,
            "q_1k": row.q_1k,
            "q_10k": row.q_10k,
            "q_20k": row.q_20k,
        }
        for row in rows
    ]


def _deserialize_spectrum(payload: list[dict]):
    np = __import__("numpy")
    return [
        f59.SpectrumRow(
            row["action"], row["action_key"], np.asarray(row["features"], dtype=float),
            float(row["base_q"]), row.get("q_1k"), row.get("q_10k"), row.get("q_20k"),
        )
        for row in payload
    ]


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _load_root_checkpoint(compiled, parent, record: dict, *, smoke: bool):
    path = _checkpoint_path(compiled, record, smoke=smoke)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    expected = _checkpoint_metadata(compiled, parent, record, smoke=smoke)
    if any(payload.get(key) != value for key, value in expected.items()):
        return None
    rows = payload.get("spectrum")
    return _deserialize_spectrum(rows) if isinstance(rows, list) else None


def _save_root_checkpoint(compiled, parent, record: dict, rows, *, smoke: bool) -> None:
    payload = _checkpoint_metadata(compiled, parent, record, smoke=smoke)
    payload["spectrum"] = _serialize_spectrum(rows)
    _write_json_atomic(_checkpoint_path(compiled, record, smoke=smoke), payload)


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


def _lean_spectrum_for_root(compiled, native, parent, record: dict, *, smoke: bool):
    """Training-only F59-equivalent spectrum without diagnostic-only searches.

    F61 consumes only the ordered action rows, features, base Q, and q20.  The
    root-40k and selected-action q10k diagnostics are therefore omitted.  In
    this driver observer is parent, so its 2k decision is exactly root_2k and
    is reused rather than searched a second time.
    """
    session = f59._session(compiled, record)
    legal = sorted(
        session.legal_actions(),
        key=lambda action: json.dumps(f59.action_to_dict(action), sort_keys=True),
    )
    budgets = _training_budget_signature(smoke=smoke)
    root_2k = f59._root_search(compiled, native, parent, record, budgets["root_2k_nodes"])
    root_80k = f59._root_search(compiled, native, parent, record, budgets["root_80k_nodes"])
    cheap = f59._parallel_children(
        compiled, native, parent, record,
        [f59.action_to_dict(action) for action in legal], budgets["cheap_nodes"],
    )
    order = sorted(
        range(len(legal)),
        key=lambda index: (
            -cheap[index],
            json.dumps(f59.action_to_dict(legal[index]), sort_keys=True),
        ),
    )
    selected = [f59.action_to_dict(legal[index]) for index in order[:3 if smoke else 6]]
    selected_keys = {f59._action_key(action) for action in selected}
    for payload in (root_2k["action"], root_80k["action"]):
        if payload is not None and f59._action_key(payload) not in selected_keys:
            selected.append(payload)
            selected_keys.add(f59._action_key(payload))
    prepared = []
    for payload in selected:
        features, base_q, _side = f59._child_features(
            compiled, native, parent, record, payload
        )
        prepared.append(f59.SpectrumRow(
            payload, f59._action_key(payload), features, base_q,
        ))
    q20 = f59._parallel_children(
        compiled, native, parent, record,
        [row.action for row in prepared], budgets["target_nodes"],
    )
    cheap_by_key = {
        f59._action_key(f59.action_to_dict(action)): float(value)
        for action, value in zip(legal, cheap)
    }
    return [
        f59.SpectrumRow(
            row.action, row.action_key, row.features, row.base_q,
            cheap_by_key.get(row.action_key), None, target,
        )
        for row, target in zip(prepared, q20)
    ]


def _training_rows_equivalent(reference, candidate) -> bool:
    """Compare exactly the ordered rows consumed by the F61 fit."""
    np = __import__("numpy")
    if len(reference) != len(candidate):
        return False
    for expected, actual in zip(reference, candidate):
        if expected.action_key != actual.action_key:
            return False
        if not np.array_equal(expected.features, actual.features):
            return False
        if expected.base_q != actual.base_q or expected.q_20k != actual.q_20k:
            return False
    return True


def _fit_one(compiled, native, parent, records: list[dict], *, smoke: bool):
    rows = []
    for record in records:
        spectrum = _load_root_checkpoint(compiled, parent, record, smoke=smoke)
        if spectrum is None:
            spectrum = _lean_spectrum_for_root(
                compiled, native, parent, record, smoke=smoke
            )
            _save_root_checkpoint(compiled, parent, record, spectrum, smoke=smoke)
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
    resumable = run_arena_game_resumable(
        compiled, native, parent, child,
        ArenaConfig(
            pairs=pairs, nodes_per_move=100 if smoke else ARENA_NODES,
            max_depth=4 if smoke else ARENA_MAX_DEPTH,
            tt_megabytes=2 if smoke else ARENA_TT_MB,
            opening_seed=seed, opening_count=pairs, min_plies=2, max_plies=6,
            workers=1,
        ),
        progress_dir=(
            OUT / "arena-progress" / str(compiled.ruleset_fingerprint) / "seed-59012"
        ),
        openings=openings,
        stop_on_decision=False,
    )
    if resumable.status != "COMPLETE" or resumable.summary is None:
        raise RuntimeError(
            f"F61 Arena incomplete: status={resumable.status} "
            f"completed_games={resumable.completed_games}/{resumable.total_games} "
            f"reason={resumable.reason}"
        )
    summary = resumable.summary
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


def _partial_payload(results: list[dict], *, smoke: bool, root_count: int, started: float) -> dict:
    return {
        "schema": "generic-chess-f61-gen0-gen1-strength-triage-v1",
        "work_order": WORK_ORDER,
        "ruleset_order": [row["label"] for row in results],
        "root_count": 3 if smoke else root_count,
        "arena_pairs": 2 if smoke else ARENA_PAIRS,
        "arena_gate": "actual_equal_budget_parent_child_strength",
        "teacher_metrics_are_diagnostic_only": True,
        "results": results,
        "wall_seconds": time.perf_counter() - started,
    }


def run(*, smoke: bool = False, root_count: int = ROOT_COUNT,
        ruleset: str | None = None) -> dict:
    started = time.perf_counter()
    results = []
    selected_rulesets = (ruleset,) if ruleset else RULESET_ORDER
    invalid = [label for label in selected_rulesets if label not in RULESET_ORDER]
    if invalid:
        raise ValueError(f"unknown ruleset selector: {', '.join(invalid)}")
    for index, label in enumerate(selected_rulesets):
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
        partial = _partial_payload(results, smoke=smoke, root_count=root_count, started=started)
        _write_json_atomic(OUT / f"{label.lower()}_result.json", partial)
    return _partial_payload(results, smoke=smoke, root_count=root_count, started=started)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--root-count", type=int, default=ROOT_COUNT)
    parser.add_argument("--ruleset", choices=RULESET_ORDER)
    parser.add_argument("--output-name", default="f61_gen0_gen1_strength_triage.json")
    args = parser.parse_args()
    if not args.smoke and args.root_count != ROOT_COUNT:
        raise ValueError(f"root-count is frozen at {ROOT_COUNT} outside smoke mode")
    OUT.mkdir(parents=True, exist_ok=True)
    payload = run(smoke=args.smoke, root_count=args.root_count, ruleset=args.ruleset)
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
