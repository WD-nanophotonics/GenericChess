"""Learning Phase 1.7: evaluation leverage and benchmark identification.

This module only *measures* the frozen TDLeaf pipeline and the frozen native
search.  It never changes ``tdleaf.py`` / ``features.py`` / ``selfplay.py``
and never changes native search semantics.

It implements:

* Experiment A: artificial material perturbation (global-scale control,
  single-piece relative perturbations, checkpoint-independent directional
  vectors);
* Experiment B: search-budget sweep comparing artificial-perturbation
  sensitivity with learned-checkpoint sensitivity;
* Experiment C: deterministic candidate ruleset discovery with pre-registered
  eligibility metrics (viability, first-player dominance, tactical
  determinism, evaluation leverage, branching) and a selection step that
  never receives trained checkpoints;
* Experiment D: frozen Gen0..Gen3 retest on the selected benchmarks;
* product-oriented search-budget analysis;
* pre-registered layered verdicts.

All protocol constants below are fixed before any measurement in this phase
and are emitted into ``config.json`` for audit.
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .arena import ArenaConfig, run_arena
from .diagnostics import (
    _gen0_checkpoint,
    _search_position,
    _train_calibrated_checkpoints,
    generate_diagnostic_corpus,
    load_checkpoints_from_experiment,
    search_sensitivity_diagnostics,
    teacher_benchmark,
)
from .features import linear_value, material_features, non_anchor_type_ids
from .material import LearnableMaterialCheckpoint
from ..native.compiler import compile_native_rules
from .openings import generate_arena_openings
from .serialization import canonical_json, stable_sha256
from .selfplay import SelfPlayConfig


# ================================================================ protocol

LEVERAGE_SCHEMA_VERSION = 1

# Experiment A: perturbation protocol (fixed).
GLOBAL_SCALE_FACTORS = (0.5, 0.75, 1.25, 1.5)
SINGLE_PIECE_FACTORS = (0.5, 0.75, 0.9, 1.1, 1.25, 1.5)  # +/-50/25/10 %
EVAL_LEVERAGE_FACTORS = (0.75, 1.25)  # +/-25 %
EVAL_LEVERAGE_BUDGET = 2000
DIRECTIONAL_PERTURBATIONS = (
    "alternating_sign",
    "board_hand_differential",
    "first_half_positive",
    "normalized_pseudorandom",
)
DIRECTIONAL_L2_FRACTION = 0.25

# Experiment B: budgets (fixed before looking at data).
SWEEP_BUDGETS = (250, 500, 1000, 2000, 4000, 8000)
LEARNED_BUDGETS = (250, 500, 1000, 2000, 4000)

# Corpus sizes (positions are taken positionally from the fixed
# checkpoint-independent corpus: positions[0:N]).
PERTURBATION_CORPUS_COUNT = 128
BUDGET_SWEEP_CORPUS_COUNT = 64
RETEST_CORPUS_COUNT = 64

# Experiment C: candidate discovery (fixed before screening).
CANDIDATE_MASTER_SEED = 20260807
CANDIDATE_COUNT = 32
CANDIDATE_BOARD_SIZE = 6
CANDIDATE_PRESETS = ("free_random", "bilateral_random", "classic_like")
CANDIDATE_OPENING_COUNT = 4
CANDIDATE_ARENA_PAIRS = 2
CANDIDATE_ARENA_NODES = 800
CANDIDATE_ARENA_MAX_DEPTH = 12
CANDIDATE_CORPUS_COUNT = 16
CANDIDATE_LEVERAGE_BUDGET = 1000
CANDIDATE_TACTICAL_SHALLOW = 500
CANDIDATE_TACTICAL_DEEP = 4000

# Eligibility thresholds (fixed before any candidate screening).
VIABILITY_MIN_TERMINAL_RATE = 1.0
VIABILITY_MIN_AVG_PLIES = 4
VIABILITY_MAX_AVG_PLIES = 200
VIABILITY_MAX_ENDLESS_DRAW_FRACTION = 0.5
FIRST_PLAYER_MAX_OWNER0_WIN_RATE = 0.90
FIRST_PLAYER_MIN_OWNER1_WIN_RATE = 0.05
TACTICAL_AGREEMENT_MIN = 0.30
TACTICAL_AGREEMENT_MAX = 0.98
LEVERAGE_MIN = 0.10
BRANCHING_MAX_FORCED_MOVE_FRACTION = 0.30
BRANCHING_MIN_MEAN_LEGAL_ACTIONS = 2.0

# Benchmark selection rules (fixed before screening).
MIXED_LEVERAGE_RANGE = (0.05, 0.35)
MIXED_AGREEMENT_RANGE = (0.40, 0.95)
MIXED_TARGET_LEVERAGE = 0.15

# Experiment D: frozen retest (fixed).
RETEST_SEED = 7
RETEST_STUDENT_NODES = 2000
RETEST_TEACHER_NODES = 20000
RETEST_ARENA_PAIRS = 16
RETEST_ARENA_NODES = 1000

# Product budget analysis (fixed thresholds).
PRODUCT_MIN_LEARNED_FLIP = 0.02
PRODUCT_MIN_TEACHER_AGREEMENT = 0.50
PRODUCT_CANDIDATE_BUDGETS = LEARNED_BUDGETS

R2_LABEL = "R2_weird_generic"
R2_FID = "gen_free_random_4_102"


# ================================================================ timing


class TimingRecorder:
    """Simple phase wall-clock recorder (Phase 1.6 lacked per-phase times)."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._start = time.perf_counter()

    def section(self, name: str) -> "TimedSection":
        return TimedSection(self, name)

    def record(self, name: str, elapsed: float) -> None:
        self._entries.append({"phase": name, "elapsed_seconds": round(elapsed, 4)})

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "total_elapsed_seconds": round(time.perf_counter() - self._start, 4),
            "phases": self._entries,
        }


class TimedSection:
    def __init__(self, recorder: TimingRecorder, name: str) -> None:
        self._recorder = recorder
        self._name = name
        self._start = time.perf_counter()

    def __enter__(self) -> "TimedSection":
        return self

    def __exit__(self, *exc: object) -> None:
        self._recorder.record(self._name, time.perf_counter() - self._start)


def merge_performance(
    existing: dict | None, phases: list[dict]
) -> dict:
    """Merge phase wall times so re-runs accumulate instead of overwriting."""
    merged: dict[str, float] = {}
    if existing:
        for entry in existing.get("phases", []):
            merged[str(entry["phase"])] = float(entry["elapsed_seconds"])
    for entry in phases:
        merged[str(entry["phase"])] = float(entry["elapsed_seconds"])
    entries = [
        {"phase": name, "elapsed_seconds": round(seconds, 4)}
        for name, seconds in sorted(merged.items())
    ]
    return {
        "schema_version": 1,
        "total_elapsed_seconds": round(sum(merged.values()), 4),
        "phases": entries,
    }


def _git_head() -> str:
    import subprocess

    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def _meta(compiled, extra: dict | None = None) -> dict:
    out = {
        "schema_version": LEVERAGE_SCHEMA_VERSION,
        "commit": _git_head(),
        "project_version": "0.8.0a4",
        "native_version": "0.3.0",
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "board_size": compiled.board_size,
    }
    if extra:
        out.update(extra)
    return out


def pre_registered_config() -> dict:
    """The full pre-registered protocol, emitted to config.json."""
    return {
        "schema_version": LEVERAGE_SCHEMA_VERSION,
        "phase": "learning_1.7",
        "global_scale_factors": list(GLOBAL_SCALE_FACTORS),
        "single_piece_factors": list(SINGLE_PIECE_FACTORS),
        "eval_leverage_factors": list(EVAL_LEVERAGE_FACTORS),
        "eval_leverage_budget": EVAL_LEVERAGE_BUDGET,
        "directional_perturbations": list(DIRECTIONAL_PERTURBATIONS),
        "directional_l2_fraction": DIRECTIONAL_L2_FRACTION,
        "sweep_budgets": list(SWEEP_BUDGETS),
        "learned_budgets": list(LEARNED_BUDGETS),
        "perturbation_corpus_count": PERTURBATION_CORPUS_COUNT,
        "budget_sweep_corpus_count": BUDGET_SWEEP_CORPUS_COUNT,
        "retest_corpus_count": RETEST_CORPUS_COUNT,
        "candidate_master_seed": CANDIDATE_MASTER_SEED,
        "candidate_count": CANDIDATE_COUNT,
        "candidate_board_size": CANDIDATE_BOARD_SIZE,
        "candidate_presets": list(CANDIDATE_PRESETS),
        "candidate_arena_pairs": CANDIDATE_ARENA_PAIRS,
        "candidate_arena_nodes": CANDIDATE_ARENA_NODES,
        "candidate_corpus_count": CANDIDATE_CORPUS_COUNT,
        "candidate_leverage_budget": CANDIDATE_LEVERAGE_BUDGET,
        "candidate_tactical_shallow": CANDIDATE_TACTICAL_SHALLOW,
        "candidate_tactical_deep": CANDIDATE_TACTICAL_DEEP,
        "eligibility": {
            "viability_min_terminal_rate": VIABILITY_MIN_TERMINAL_RATE,
            "viability_min_avg_plies": VIABILITY_MIN_AVG_PLIES,
            "viability_max_avg_plies": VIABILITY_MAX_AVG_PLIES,
            "viability_max_endless_draw_fraction": VIABILITY_MAX_ENDLESS_DRAW_FRACTION,
            "first_player_max_owner0_win_rate": FIRST_PLAYER_MAX_OWNER0_WIN_RATE,
            "first_player_min_owner1_win_rate": FIRST_PLAYER_MIN_OWNER1_WIN_RATE,
            "tactical_agreement_min": TACTICAL_AGREEMENT_MIN,
            "tactical_agreement_max": TACTICAL_AGREEMENT_MAX,
            "leverage_min": LEVERAGE_MIN,
            "branching_max_forced_move_fraction": BRANCHING_MAX_FORCED_MOVE_FRACTION,
            "branching_min_mean_legal_actions": BRANCHING_MIN_MEAN_LEGAL_ACTIONS,
        },
        "selection": {
            "mixed_leverage_range": list(MIXED_LEVERAGE_RANGE),
            "mixed_agreement_range": list(MIXED_AGREEMENT_RANGE),
            "mixed_target_leverage": MIXED_TARGET_LEVERAGE,
            "tactical_benchmark": f"{R2_LABEL} (existing)",
        },
        "retest": {
            "seed": RETEST_SEED,
            "student_nodes": RETEST_STUDENT_NODES,
            "teacher_nodes": RETEST_TEACHER_NODES,
            "arena_pairs": RETEST_ARENA_PAIRS,
            "arena_nodes": RETEST_ARENA_NODES,
        },
        "product_budget": {
            "min_learned_flip": PRODUCT_MIN_LEARNED_FLIP,
            "min_teacher_agreement": PRODUCT_MIN_TEACHER_AGREEMENT,
            "candidate_budgets": list(PRODUCT_CANDIDATE_BUDGETS),
            "source": (
                "evaluation-sensitive benchmark retest (learned flip from "
                "per-budget search sensitivity, Gen0 teacher agreement, no "
                "failed searches)"
            ),
        },
        "eval_leverage_definition": (
            "mean best-move flip rate over single-piece +/-25% relative "
            f"material perturbations at {EVAL_LEVERAGE_BUDGET} nodes"
        ),
        "corpus_subset_rule": (
            "positions are taken positionally (positions[0:N]) from the "
            "fixed checkpoint-independent diagnostic corpus"
        ),
    }


# ================================================================ Experiment A


@dataclass(frozen=True, slots=True)
class PerturbationSpec:
    name: str
    kind: str  # global_scale | single_piece | directional
    params: dict

    @property
    def spec_id(self) -> str:
        return stable_sha256(
            {"name": self.name, "kind": self.kind, "params": self.params}
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "params": dict(self.params),
            "spec_id": self.spec_id,
        }


def _combined_weights(checkpoint: LearnableMaterialCheckpoint) -> dict[str, float]:
    out: dict[str, float] = {}
    for tid, w in checkpoint.board_weights.items():
        out[f"board:{tid}"] = w
    for tid, w in checkpoint.hand_weights.items():
        out[f"hand:{tid}"] = w
    return out


def weight_vector_l2(checkpoint: LearnableMaterialCheckpoint) -> float:
    return math.sqrt(sum(v * v for v in _combined_weights(checkpoint).values()))


def perturbation_specs(compiled) -> list[PerturbationSpec]:
    """Pre-registered deterministic perturbation set for one ruleset."""
    type_ids = non_anchor_type_ids(compiled)
    specs: list[PerturbationSpec] = []
    for factor in GLOBAL_SCALE_FACTORS:
        specs.append(
            PerturbationSpec(
                name=f"global_scale_{factor:g}",
                kind="global_scale",
                params={"factor": factor},
            )
        )
    for tid in type_ids:
        for factor in SINGLE_PIECE_FACTORS:
            specs.append(
                PerturbationSpec(
                    name=f"single_{tid}_{factor:g}",
                    kind="single_piece",
                    params={"type_id": tid, "factor": factor},
                )
            )
    for direction in DIRECTIONAL_PERTURBATIONS:
        specs.append(
            PerturbationSpec(
                name=f"directional_{direction}",
                kind="directional",
                params={
                    "direction": direction,
                    "l2_fraction": DIRECTIONAL_L2_FRACTION,
                    "seed": CANDIDATE_MASTER_SEED,
                },
            )
        )
    return specs


def _directional_delta(
    base: LearnableMaterialCheckpoint,
    direction: str,
    l2_target: float,
    seed: int,
) -> dict[str, float]:
    type_ids = sorted(base.board_weights)
    board_signs: list[int] = []
    hand_signs: list[int] = []
    if direction == "alternating_sign":
        board_signs = [1 if i % 2 == 0 else -1 for i in range(len(type_ids))]
        hand_signs = list(board_signs)
    elif direction == "first_half_positive":
        half = len(type_ids) // 2
        board_signs = [1 if i < half else -1 for i in range(len(type_ids))]
        hand_signs = list(board_signs)
    elif direction == "board_hand_differential":
        board_signs = [1] * len(type_ids)
        hand_signs = [-1] * len(type_ids)
    elif direction == "normalized_pseudorandom":
        rng = random.Random(seed)
        board_signs = [rng.choice((1, -1)) for _ in type_ids]
        hand_signs = [rng.choice((1, -1)) for _ in type_ids]
    else:
        raise ValueError(f"unknown directional perturbation {direction!r}")
    vector: dict[str, float] = {}
    for tid, sign in zip(type_ids, board_signs):
        vector[f"board:{tid}"] = float(sign)
    for tid, sign in zip(type_ids, hand_signs):
        vector[f"hand:{tid}"] = float(sign)
    norm = math.sqrt(sum(v * v for v in vector.values()))
    if norm <= 0.0:
        return {}
    scale = l2_target / norm
    return {k: v * scale for k, v in vector.items()}


def apply_perturbation(
    base: LearnableMaterialCheckpoint, spec: PerturbationSpec
) -> tuple[LearnableMaterialCheckpoint | None, dict]:
    """Return (perturbed_checkpoint | None-if-skipped, provenance dict).

    The base checkpoint is never mutated; a new checkpoint is built with a
    distinct checkpoint_id/config_hash.
    """
    board = dict(base.board_weights)
    hand = dict(base.hand_weights)
    info: dict[str, Any] = {"spec": spec.to_dict(), "skipped": False}
    if spec.kind == "global_scale":
        factor = float(spec.params["factor"])
        board = {t: w * factor for t, w in board.items()}
        hand = {t: w * factor for t, w in hand.items()}
    elif spec.kind == "single_piece":
        tid = str(spec.params["type_id"])
        factor = float(spec.params["factor"])
        if abs(board.get(tid, 0.0)) < 1e-9:
            info["skipped"] = True
            info["reason"] = "zero_weight_type"
            return None, info
        board[tid] = board[tid] * factor
        hand[tid] = hand[tid] * factor
    elif spec.kind == "directional":
        l2_target = float(spec.params["l2_fraction"]) * weight_vector_l2(base)
        delta = _directional_delta(
            base,
            str(spec.params["direction"]),
            l2_target,
            int(spec.params.get("seed", CANDIDATE_MASTER_SEED)),
        )
        for key, dv in delta.items():
            kind, tid = key.split(":", 1)
            if kind == "board":
                board[tid] = board.get(tid, 0.0) + dv
            else:
                hand[tid] = hand.get(tid, 0.0) + dv
    else:
        raise ValueError(f"unknown perturbation kind {spec.kind!r}")
    perturbed = replace(
        base,
        board_weights=board,
        hand_weights=hand,
        training_config_hash=f"perturbation:{spec.spec_id}",
        training_seed=None,
    )
    delta_l2 = math.sqrt(
        sum(
            (perturbed.board_weights[t] - base.board_weights[t]) ** 2
            for t in base.board_weights
        )
        + sum(
            (perturbed.hand_weights[t] - base.hand_weights[t]) ** 2
            for t in base.hand_weights
        )
    )
    info.update(
        {
            "delta_weight_l2": delta_l2,
            "base_checkpoint_id": base.checkpoint_id,
            "perturbed_checkpoint_id": perturbed.checkpoint_id,
        }
    )
    return perturbed, info


def evaluator_output_deltas(compiled, base, perturbed, corpus) -> dict:
    """Mean |Delta V| and related stats over the corpus (evaluator only)."""
    from ..session.session import GameSession

    type_ids = non_anchor_type_ids(compiled)
    deltas: list[float] = []
    for pos in corpus.positions:
        session = GameSession(compiled)
        for action in pos.action_history:
            session.submit(action)
        features = material_features(
            session.state.position, type_ids, perspective=0
        )
        v0 = linear_value(features, base.board_weights, base.hand_weights)
        v1 = linear_value(
            features, perturbed.board_weights, perturbed.hand_weights
        )
        deltas.append(v1 - v0)
    n = len(deltas)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "mean_delta": sum(deltas) / n,
        "mean_abs_delta": sum(abs(d) for d in deltas) / n,
        "max_abs_delta": max(abs(d) for d in deltas),
        "nonzero_fraction": sum(1 for d in deltas if d != 0.0) / n,
    }


# ================================================================ search


def _search_evaluator(
    compiled,
    native_rules,
    checkpoint,
    corpus,
    budget: int,
    cache: dict | None = None,
) -> list[dict]:
    """Fresh-engine per-position search; results are cacheable by
    (checkpoint_id, budget) so base results are reused across specs."""
    key = (checkpoint.checkpoint_id, budget)
    if cache is not None and key in cache:
        return cache[key]
    results: list[dict] = []
    for pos in corpus.positions:
        result, _session = _search_position(
            compiled, native_rules, checkpoint, pos, budget
        )
        results.append(
            {
                "index": pos.index,
                "action": str(result.action) if result.action is not None else None,
                "score": result.score,
                "pv": [str(a) for a in result.principal_variation],
                "nodes": result.nodes,
                "status": result.termination_reason,
            }
        )
    if cache is not None:
        cache[key] = results
    return results


def compare_search_results(base: list[dict], other: list[dict]) -> dict:
    """Flip / score / PV metrics; positions where either search failed are
    excluded from ratios and counted in ``errors``."""
    n = len(base)
    compared = 0
    flips = 0
    pv_flips = 0
    score_deltas: list[float] = []
    errors = 0
    for i in range(n):
        a, b = base[i], other[i]
        if a["action"] is None or b["action"] is None:
            errors += 1
            continue
        compared += 1
        if a["action"] != b["action"]:
            flips += 1
        if (a["pv"] or [None])[0] != (b["pv"] or [None])[0]:
            pv_flips += 1
        score_deltas.append(b["score"] - a["score"])
    return {
        "positions": n,
        "compared": compared,
        "errors": errors,
        "flip_rate": flips / compared if compared else None,
        "pv_first_disagreement_rate": pv_flips / compared if compared else None,
        "mean_abs_score_delta": (
            sum(abs(d) for d in score_deltas) / len(score_deltas)
            if score_deltas
            else None
        ),
        "score_sign_flip_fraction": (
            sum(1 for d in score_deltas if d != 0.0) / len(score_deltas)
            if score_deltas
            else None
        ),
    }


def perturbation_sweep(
    compiled,
    native_rules,
    base,
    corpus,
    budget: int = EVAL_LEVERAGE_BUDGET,
) -> dict:
    """Experiment A: per-spec evaluator delta, L2, and search leverage."""
    specs = perturbation_specs(compiled)
    cache: dict = {}
    base_results = _search_evaluator(
        compiled, native_rules, base, corpus, budget, cache
    )
    rows: list[dict] = []
    for spec in specs:
        perturbed, info = apply_perturbation(base, spec)
        if perturbed is None:
            rows.append({**info, "evaluator_delta": None, "search": None})
            continue
        eval_delta = evaluator_output_deltas(compiled, base, perturbed, corpus)
        other_results = _search_evaluator(
            compiled, native_rules, perturbed, corpus, budget, cache
        )
        rows.append(
            {
                **info,
                "evaluator_delta": eval_delta,
                "search": compare_search_results(base_results, other_results),
            }
        )
    return {
        **_meta(compiled),
        "budget": budget,
        "corpus_id": corpus.corpus_id,
        "positions": len(corpus.positions),
        "base_checkpoint_id": base.checkpoint_id,
        "specs": rows,
    }


def eval_leverage(compiled, native_rules, base, corpus, budget=None) -> dict:
    """Pre-registered EVAL_LEVERAGE: mean flip rate over single-piece +/-25%
    perturbations at EVAL_LEVERAGE_BUDGET."""
    budget = budget or EVAL_LEVERAGE_BUDGET
    specs = [
        s
        for s in perturbation_specs(compiled)
        if s.kind == "single_piece"
        and float(s.params["factor"]) in EVAL_LEVERAGE_FACTORS
    ]
    cache: dict = {}
    base_results = _search_evaluator(
        compiled, native_rules, base, corpus, budget, cache
    )
    rates: list[float] = []
    rows: list[dict] = []
    for spec in specs:
        perturbed, info = apply_perturbation(base, spec)
        if perturbed is None:
            continue
        other = _search_evaluator(
            compiled, native_rules, perturbed, corpus, budget, cache
        )
        cmp = compare_search_results(base_results, other)
        if cmp["flip_rate"] is not None:
            rates.append(cmp["flip_rate"])
        rows.append({**info, "search": cmp})
    return {
        **_meta(compiled),
        "definition": (
            "mean flip rate over single-piece +/-25% perturbations at "
            f"{budget} nodes"
        ),
        "budget": budget,
        "corpus_id": corpus.corpus_id,
        "positions": len(corpus.positions),
        "perturbations_used": len(rates),
        "flip_rate": sum(rates) / len(rates) if rates else None,
        "per_perturbation": rows,
    }


# ================================================================ Experiment B


def artificial_bundle(compiled) -> list[PerturbationSpec]:
    """Fixed bundle for budget sweeps: single-piece +/-25% + directional."""
    return [
        s
        for s in perturbation_specs(compiled)
        if (
            s.kind == "single_piece"
            and float(s.params["factor"]) in EVAL_LEVERAGE_FACTORS
        )
        or s.kind == "directional"
    ]


def budget_sweep(
    compiled,
    native_rules,
    checkpoints,
    corpus,
    budgets=SWEEP_BUDGETS,
) -> dict:
    """Experiment B: per-budget artificial-bundle leverage and learned flip
    rates (Gen1..Gen3 vs Gen0)."""
    base = checkpoints[0]
    bundle = artificial_bundle(compiled)
    per_budget: dict[str, dict] = {}
    for budget in budgets:
        cache: dict = {}
        base_results = _search_evaluator(
            compiled, native_rules, base, corpus, budget, cache
        )
        artificial_cmp: list[dict] = []
        for spec in bundle:
            perturbed, _info = apply_perturbation(base, spec)
            if perturbed is None:
                continue
            other = _search_evaluator(
                compiled, native_rules, perturbed, corpus, budget, cache
            )
            artificial_cmp.append(compare_search_results(base_results, other))
        artificial_rates = [
            c["flip_rate"] for c in artificial_cmp if c["flip_rate"] is not None
        ]
        artificial_scores = [
            c["mean_abs_score_delta"]
            for c in artificial_cmp
            if c["mean_abs_score_delta"] is not None
        ]
        learned: dict[str, dict] = {}
        for g in range(1, len(checkpoints)):
            cmp = compare_search_results(
                base_results,
                _search_evaluator(
                    compiled, native_rules, checkpoints[g], corpus, budget, cache
                ),
            )
            learned[str(g)] = cmp
        per_budget[str(budget)] = {
            "artificial_specs_used": len(artificial_rates),
            "artificial_flip_rate": (
                sum(artificial_rates) / len(artificial_rates)
                if artificial_rates
                else None
            ),
            "artificial_mean_abs_score_delta": (
                sum(artificial_scores) / len(artificial_scores)
                if artificial_scores
                else None
            ),
            "learned": learned,
        }
    return {
        **_meta(compiled),
        "corpus_id": corpus.corpus_id,
        "positions": len(corpus.positions),
        "budgets": list(budgets),
        "artificial_bundle": [s.to_dict() for s in bundle],
        "checkpoint_ids": [c.checkpoint_id for c in checkpoints],
        "per_budget": per_budget,
    }


# ================================================================ Experiment C


def candidate_specs(count: int = CANDIDATE_COUNT) -> list[dict]:
    """Deterministic candidate ruleset configurations from a master seed."""
    specs: list[dict] = []
    for i in range(count):
        seed = CANDIDATE_MASTER_SEED * 1000 + i
        preset = CANDIDATE_PRESETS[i % len(CANDIDATE_PRESETS)]
        specs.append(
            {
                "index": i,
                "seed": seed,
                "board_size": CANDIDATE_BOARD_SIZE,
                "setup_preset": preset,
                "generator_options": {"setup_preset": preset},
            }
        )
    return specs


def _candidate_summary(
    compiled,
    native_rules,
    config: dict,
    generation_report,
) -> dict:
    """Screen one candidate using only structure + Gen0 + artificial
    perturbations (never learned checkpoints)."""
    from ..session.session import GameSession

    gen0 = _gen0_checkpoint(compiled, int(config["seed"]))
    openings = generate_arena_openings(
        compiled, count=CANDIDATE_OPENING_COUNT, seed=314159
    )
    corpus = generate_diagnostic_corpus(
        compiled,
        openings,
        count=CANDIDATE_CORPUS_COUNT,
        seed=42,
        max_plies=40,
    )
    arena = run_arena(
        compiled,
        native_rules,
        gen0,
        gen0,
        ArenaConfig(
            pairs=CANDIDATE_ARENA_PAIRS,
            nodes_per_move=CANDIDATE_ARENA_NODES,
            max_depth=CANDIDATE_ARENA_MAX_DEPTH,
            opening_seed=314159,
            opening_count=CANDIDATE_OPENING_COUNT,
        ),
        openings=openings,
    )
    games = [
        game
        for pair in arena.pairs
        for game in (pair.game_child_owner0, pair.game_child_owner1)
    ]
    plies = [g.plies for g in games]
    owner0_wins = sum(1 for g in games if g.winner == 0)
    owner1_wins = sum(1 for g in games if g.winner == 1)
    draws = sum(1 for g in games if g.winner is None)
    endless = sum(1 for g in games if g.result in ("repetition", "max_ply"))
    total = len(games)

    legal_counts: list[int] = []
    for pos in corpus.positions:
        session = GameSession(compiled)
        for action in pos.action_history:
            session.submit(action)
        legal_counts.append(len(session.legal_actions()))
    ordered = sorted(legal_counts)
    mean_legal = sum(legal_counts) / len(legal_counts) if legal_counts else 0.0
    p90_idx = (
        min(len(ordered) - 1, int(math.ceil(0.90 * len(ordered))) - 1)
        if ordered
        else 0
    )
    forced_fraction = (
        sum(1 for c in legal_counts if c == 1) / len(legal_counts)
        if legal_counts
        else 0.0
    )

    shallow = _search_evaluator(
        compiled, native_rules, gen0, corpus, CANDIDATE_TACTICAL_SHALLOW
    )
    deep = _search_evaluator(
        compiled, native_rules, gen0, corpus, CANDIDATE_TACTICAL_DEEP
    )
    tactical_cmp = compare_search_results(shallow, deep)
    agreement = (
        1.0 - tactical_cmp["flip_rate"]
        if tactical_cmp["flip_rate"] is not None
        else None
    )
    leverage = eval_leverage(
        compiled, native_rules, gen0, corpus, CANDIDATE_LEVERAGE_BUDGET
    )
    leverage_rate = leverage["flip_rate"]
    avg_plies = sum(plies) / total if total else 0.0
    metrics = {
        "games": total,
        "terminal_rate": 1.0 if total else 0.0,
        "average_plies": avg_plies,
        "owner0_win_rate": owner0_wins / total if total else 0.0,
        "owner1_win_rate": owner1_wins / total if total else 0.0,
        "draw_rate": draws / total if total else 0.0,
        "endless_draw_fraction": endless / total if total else 0.0,
        "mean_legal_actions": mean_legal,
        "median_legal_actions": ordered[len(ordered) // 2] if ordered else 0,
        "p90_legal_actions": p90_idx,
        "forced_move_fraction": forced_fraction,
        "tactical_shallow_deep_agreement": agreement,
        "eval_leverage": leverage_rate,
        "corpus_id": corpus.corpus_id,
        "opening_corpus_id": openings.corpus_id,
    }
    violations: list[str] = []
    if total == 0:
        violations.append("terminal_rate")
    if not (VIABILITY_MIN_AVG_PLIES <= avg_plies <= VIABILITY_MAX_AVG_PLIES):
        violations.append("average_plies")
    if total and endless / total > VIABILITY_MAX_ENDLESS_DRAW_FRACTION:
        violations.append("endless_draw_fraction")
    if total and owner0_wins / total > FIRST_PLAYER_MAX_OWNER0_WIN_RATE:
        violations.append("first_player_dominance")
    if total and owner1_wins / total < FIRST_PLAYER_MIN_OWNER1_WIN_RATE:
        violations.append("owner1_too_weak")
    if agreement is not None and not (
        TACTICAL_AGREEMENT_MIN <= agreement <= TACTICAL_AGREEMENT_MAX
    ):
        violations.append("tactical_agreement")
    if leverage_rate is None or leverage_rate < LEVERAGE_MIN:
        violations.append("eval_leverage")
    if forced_fraction > BRANCHING_MAX_FORCED_MOVE_FRACTION:
        violations.append("forced_move_fraction")
    if mean_legal < BRANCHING_MIN_MEAN_LEGAL_ACTIONS:
        violations.append("mean_legal_actions")

    return {
        "index": config["index"],
        "seed": config["seed"],
        "setup_preset": config["setup_preset"],
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "board_size": compiled.board_size,
        "type_ids": sorted(
            pt.type_id for pt in compiled.piece_types if not pt.is_anchor
        ),
        "opening_legal_move_count": (
            generation_report.opening_legal_move_count
            if generation_report is not None
            else None
        ),
        "metrics": metrics,
        "eligible": not violations,
        "violations": violations,
        "gen0_checkpoint_id": gen0.checkpoint_id,
    }


def screen_candidates(
    artifacts_dir,
    count: int = CANDIDATE_COUNT,
) -> list[dict]:
    """Generate + screen every candidate; all (including rejected/failed)
    are recorded."""
    from ..generation.config import GeneratorConfig
    from ..generation.generator import generate_game
    from ..native.compiler import compile_native_rules

    summaries: list[dict] = []
    for config in candidate_specs(count):
        try:
            game = generate_game(
                GeneratorConfig(
                    seed=config["seed"],
                    board_size=config["board_size"],
                    setup_preset=config["setup_preset"],
                )
            )
            compiled = game.compiled_ruleset
            native_rules = compile_native_rules(compiled)
            summaries.append(
                _candidate_summary(
                    compiled, native_rules, config, game.generation_report
                )
            )
        except Exception as exc:  # generation failures are recorded, not fatal
            summaries.append(
                {
                    "index": config["index"],
                    "seed": config["seed"],
                    "setup_preset": config["setup_preset"],
                    "ruleset_fingerprint": None,
                    "error": f"{type(exc).__name__}: {exc}",
                    "eligible": False,
                    "violations": ["generation_failed"],
                }
            )
    return summaries


def select_benchmarks(
    candidate_summaries: list[dict], r2_fingerprint: str
) -> dict:
    """Checkpoint-independent selection.  Takes only precomputed summaries
    (no learned checkpoint objects/results) and re-applies the fixed
    eligibility thresholds directly from the summary metrics."""

    def threshold_ok(s: dict) -> bool:
        m = s.get("metrics", {})
        if not m:
            return False
        try:
            if not (
                VIABILITY_MIN_AVG_PLIES
                <= m["average_plies"]
                <= VIABILITY_MAX_AVG_PLIES
            ):
                return False
            if m["endless_draw_fraction"] > VIABILITY_MAX_ENDLESS_DRAW_FRACTION:
                return False
            if m["owner0_win_rate"] > FIRST_PLAYER_MAX_OWNER0_WIN_RATE:
                return False
            if m["owner1_win_rate"] < FIRST_PLAYER_MIN_OWNER1_WIN_RATE:
                return False
            agreement = m["tactical_shallow_deep_agreement"]
            if agreement is None or not (
                TACTICAL_AGREEMENT_MIN <= agreement <= TACTICAL_AGREEMENT_MAX
            ):
                return False
            if (
                m["eval_leverage"] is None
                or m["eval_leverage"] < LEVERAGE_MIN
            ):
                return False
            if m["forced_move_fraction"] > BRANCHING_MAX_FORCED_MOVE_FRACTION:
                return False
            if m["mean_legal_actions"] < BRANCHING_MIN_MEAN_LEGAL_ACTIONS:
                return False
        except KeyError:
            return False
        return True

    eligible = [s for s in candidate_summaries if threshold_ok(s)]
    eval_pool = sorted(
        eligible,
        key=lambda s: (
            -float(s["metrics"]["eval_leverage"] or 0.0),
            s["metrics"]["owner0_win_rate"],
            s["ruleset_fingerprint"],
        ),
    )
    mixed_pool = sorted(
        [
            s
            for s in eligible
            if MIXED_LEVERAGE_RANGE[0]
            <= float(s["metrics"]["eval_leverage"] or 0.0)
            <= MIXED_LEVERAGE_RANGE[1]
            and MIXED_AGREEMENT_RANGE[0]
            <= float(s["metrics"]["tactical_shallow_deep_agreement"] or 0.0)
            <= MIXED_AGREEMENT_RANGE[1]
        ],
        key=lambda s: (
            abs(float(s["metrics"]["eval_leverage"]) - MIXED_TARGET_LEVERAGE),
            s["ruleset_fingerprint"],
        ),
    )
    tactical = {
        "class": "tactical",
        "source": "R2_weird_generic (existing benchmark)",
        "ruleset_fingerprint": r2_fingerprint,
    }
    eval_sensitive = (
        {
            "class": "evaluation_sensitive",
            "index": eval_pool[0]["index"],
            "seed": eval_pool[0]["seed"],
            "ruleset_fingerprint": eval_pool[0]["ruleset_fingerprint"],
        }
        if eval_pool
        else None
    )
    mixed = (
        {
            "class": "mixed",
            "index": mixed_pool[0]["index"],
            "seed": mixed_pool[0]["seed"],
            "ruleset_fingerprint": mixed_pool[0]["ruleset_fingerprint"],
        }
        if mixed_pool
        else None
    )
    return {
        "schema_version": LEVERAGE_SCHEMA_VERSION,
        "selection_rule": {
            "tactical": "R2 retained",
            "evaluation_sensitive": (
                "max eval_leverage among eligible; tie-break by owner0 win "
                "rate then fingerprint"
            ),
            "mixed": (
                "closest to target leverage inside ranges; tie-break by "
                "fingerprint"
            ),
        },
        "candidates_total": len(candidate_summaries),
        "candidates_eligible": len(eligible),
        "tactical": tactical,
        "evaluation_sensitive": eval_sensitive,
        "mixed": mixed,
    }


# ================================================================ Experiment D


def load_or_train_checkpoints(
    compiled, native_rules, seed: int, artifacts_dir=None
) -> list[LearnableMaterialCheckpoint]:
    """Reuse Phase 1.5 artifacts when present; otherwise train with the
    frozen calibrated protocol."""
    if artifacts_dir is not None:
        loaded = load_checkpoints_from_experiment(compiled, seed, Path(artifacts_dir))
        if len(loaded) >= 2:
            return loaded
    return _train_calibrated_checkpoints(
        compiled,
        native_rules,
        seed,
        SelfPlayConfig(games=8, nodes_per_move=2000, max_depth=12, seed=seed),
    )


def frozen_retest(
    compiled,
    native_rules,
    checkpoints,
    corpus,
    openings,
    label: str,
    budgets=LEARNED_BUDGETS,
) -> dict:
    """D1 search sensitivity + D2 teacher + D3 paired arena (Gen0 vs gens)."""
    search: dict[str, dict] = {}
    raw_search: dict[str, dict] = {}
    for budget in budgets:
        out, results = search_sensitivity_diagnostics(
            compiled, native_rules, checkpoints, corpus, nodes=budget
        )
        search[str(budget)] = out
        raw_search[str(budget)] = results
    teacher = teacher_benchmark(
        compiled,
        native_rules,
        checkpoints,
        corpus,
        student_nodes=RETEST_STUDENT_NODES,
        teacher_nodes=RETEST_TEACHER_NODES,
        max_positions=RETEST_CORPUS_COUNT,
    )
    arenas: dict[str, dict] = {}
    for g in range(1, len(checkpoints)):
        summary = run_arena(
            compiled,
            native_rules,
            checkpoints[0],
            checkpoints[g],
            ArenaConfig(
                pairs=RETEST_ARENA_PAIRS,
                nodes_per_move=RETEST_ARENA_NODES,
                max_depth=12,
                opening_seed=314159,
                opening_count=RETEST_ARENA_PAIRS,
            ),
            openings=openings,
        )
        arenas[str(g)] = {
            "pairs": summary.pair_count,
            "mean_pair_score": summary.mean_pair_score,
            "bootstrap_low": summary.bootstrap_low,
            "bootstrap_high": summary.bootstrap_high,
            "child_better_pairs": summary.child_better_pairs,
            "child_worse_pairs": summary.child_worse_pairs,
            "game_score_rate": summary.game_score_rate,
        }
    return {
        "label": label,
        **_meta(compiled),
        "corpus_id": corpus.corpus_id,
        "opening_corpus_id": openings.corpus_id,
        "checkpoint_ids": [c.checkpoint_id for c in checkpoints],
        "search_sensitivity": search,
        "raw_search_sensitivity": raw_search,
        "teacher": teacher,
        "paired_arena": arenas,
    }


# ================================================================ verdicts


def verdict_r2_leverage(perturbation: dict) -> str:
    rates = [
        r["search"]["flip_rate"]
        for r in perturbation.get("specs", [])
        if r.get("search")
        and r["search"]["flip_rate"] is not None
        and r["spec"]["kind"] == "single_piece"
        and float(r["spec"]["params"]["factor"]) in EVAL_LEVERAGE_FACTORS
    ]
    if not rates:
        return "INCONCLUSIVE"
    mean = sum(rates) / len(rates)
    if mean < 0.05:
        return "LOW"
    if mean < 0.20:
        return "MODERATE"
    return "HIGH"


def _mean_artificial_flip(budget_sweep: dict, budgets) -> float | None:
    vals = [
        budget_sweep["per_budget"][str(b)]["artificial_flip_rate"]
        for b in budgets
        if budget_sweep["per_budget"].get(str(b))
        and budget_sweep["per_budget"][str(b)]["artificial_flip_rate"] is not None
    ]
    return sum(vals) / len(vals) if vals else None


def verdict_budget_effect(budget_sweep: dict) -> str:
    shallow = _mean_artificial_flip(budget_sweep, (250, 500))
    deep = _mean_artificial_flip(budget_sweep, (4000, 8000))
    if shallow is None or deep is None:
        return "INCONCLUSIVE"
    diff = shallow - deep
    rates = [
        budget_sweep["per_budget"][str(b)]["artificial_flip_rate"]
        for b in SWEEP_BUDGETS
        if budget_sweep["per_budget"].get(str(b))
    ]
    deltas = [
        rates[i] - rates[i - 1]
        for i in range(1, len(rates))
        if rates[i - 1] is not None and rates[i] is not None
    ]
    sign_changes = sum(
        1 for i in range(1, len(deltas)) if deltas[i] * deltas[i - 1] < 0
    )
    if diff > 0.02:
        return "LEVERAGE_INCREASES_AT_SHALLOW_SEARCH"
    if diff < -0.02:
        return "LEVERAGE_INCREASES_AT_DEEP_SEARCH"
    if sign_changes >= 2:
        return "NON_MONOTONIC"
    return "LEVERAGE_STABLE"


def _learned_mean_flip(budget_sweep: dict, budgets) -> float | None:
    vals: list[float] = []
    for b in budgets:
        entry = budget_sweep["per_budget"].get(str(b))
        if not entry:
            continue
        for g in range(1, len(budget_sweep["checkpoint_ids"])):
            fr = entry["learned"][str(g)]["flip_rate"]
            if fr is not None:
                vals.append(fr)
    return sum(vals) / len(vals) if vals else None


def verdict_learned_direction(budget_sweep: dict) -> str:
    artificial = _mean_artificial_flip(budget_sweep, LEARNED_BUDGETS)
    learned = _learned_mean_flip(budget_sweep, LEARNED_BUDGETS)
    if artificial is None or learned is None or artificial <= 0.0:
        return "INCONCLUSIVE"
    ratio = learned / artificial
    if ratio >= 0.5:
        return "LEARNED_CHANGES_LIE_IN_HIGH_LEVERAGE_DIRECTIONS"
    if ratio <= 0.1:
        return "LEARNED_CHANGES_LIE_IN_LOW_LEVERAGE_DIRECTIONS"
    return "MIXED"


def verdict_benchmark_identification(selection: dict) -> str:
    if selection.get("evaluation_sensitive") and selection.get("mixed"):
        return "SUITABLE_BENCHMARKS_FOUND"
    if selection.get("evaluation_sensitive") or selection.get("mixed"):
        return "BENCHMARK_SET_INCOMPLETE"
    if selection.get("candidates_eligible", 0) == 0:
        return "NO_SUITABLE_BENCHMARK_FOUND"
    return "ONLY_TACTICAL_BENCHMARKS_FOUND"


def verdict_learning_retest(retest: dict) -> str:
    """Per-benchmark LEARNING_RETEST (caller reports each separately)."""
    teacher = retest.get("teacher", {})
    agreement = teacher.get("best_move_agreement", {})
    g0 = agreement.get("0")
    if g0 is None:
        return "INCONCLUSIVE"
    arena = retest.get("paired_arena", {})
    if not arena:
        return "INCONCLUSIVE"
    positive = any(v["mean_pair_score"] >= 0.55 for v in arena.values())
    negative = any(v["mean_pair_score"] <= 0.45 for v in arena.values())
    improved = any(
        agreement.get(str(g), g0) - g0 > 0.02 for g in range(1, 4)
    )
    if positive and improved:
        return "POSITIVE_SIGNAL"
    if negative:
        return "NEGATIVE_SIGNAL"
    return "NO_POSITIVE_SIGNAL"


def product_budget_analysis(
    eval_retest: dict, r2_budget_sweep: dict | None = None
) -> dict:
    """Identify PRODUCT_SEARCH_BUDGET from the evaluation-sensitive
    benchmark retest: learned flip visible, Gen0 plays reasonably, no
    failed searches.  The R2 budget sweep is included only as comparison."""
    teacher = eval_retest.get("teacher", {})
    g0_agreement = teacher.get("best_move_agreement", {}).get("0")
    search = eval_retest.get("search_sensitivity", {})
    raw = eval_retest.get("raw_search_sensitivity", {})
    rows: list[dict] = []
    found: int | None = None
    for budget in PRODUCT_CANDIDATE_BUDGETS:
        entry = search.get(str(budget))
        if not entry:
            continue
        learned_flips = [
            entry[str(g)]["move_flip_rate"]
            for g in range(1, 4)
            if entry.get(str(g), {}).get("move_flip_rate") is not None
        ]
        errors = 0
        raw_entry = raw.get(str(budget), {})
        for g in range(1, 4):
            for rec in raw_entry.get(str(g), []):
                if rec.get("best_action") == "None":
                    errors += 1
        mean_flip = (
            sum(learned_flips) / len(learned_flips) if learned_flips else 0.0
        )
        r2_flip = None
        if r2_budget_sweep is not None:
            r2_entry = r2_budget_sweep["per_budget"].get(str(budget))
            if r2_entry:
                r2_flip = r2_entry["learned"].get("3", {}).get("flip_rate")
        rows.append(
            {
                "budget": budget,
                "learned_mean_flip_rate": mean_flip,
                "r2_gen3_flip_rate": r2_flip,
                "gen0_teacher_agreement": g0_agreement,
                "search_errors": errors,
            }
        )
        if (
            found is None
            and mean_flip >= PRODUCT_MIN_LEARNED_FLIP
            and g0_agreement is not None
            and g0_agreement >= PRODUCT_MIN_TEACHER_AGREEMENT
            and errors == 0
        ):
            found = budget
    return {
        "schema_version": LEVERAGE_SCHEMA_VERSION,
        "product_budget": (
            found if found is not None else "NO_PRODUCT_BUDGET_IDENTIFIED"
        ),
        "criteria": {
            "min_learned_flip": PRODUCT_MIN_LEARNED_FLIP,
            "min_teacher_agreement": PRODUCT_MIN_TEACHER_AGREEMENT,
        },
        "source": "evaluation-sensitive benchmark retest",
        "per_budget": rows,
    }


def final_verdict(
    r2_leverage: str,
    budget_effect: str,
    learned_direction: str,
    benchmark_identification: str,
    learning_retest: dict,
    product_budget: dict,
) -> dict:
    retests = learning_retest.get("per_benchmark", {})
    eval_sensitive_verdict = retests.get("evaluation_sensitive", {}).get(
        "learning_retest", "INCONCLUSIVE"
    )
    mixed_verdict = retests.get("mixed", {}).get(
        "learning_retest", "INCONCLUSIVE"
    )
    product = product_budget.get(
        "product_budget", "NO_PRODUCT_BUDGET_IDENTIFIED"
    )

    next_phase = "INCONCLUSIVE"
    bench_ok = benchmark_identification == "SUITABLE_BENCHMARKS_FOUND"
    r2_ok = r2_leverage in ("MODERATE", "HIGH")
    positive_at_shallow = (
        eval_sensitive_verdict == "POSITIVE_SIGNAL"
        or mixed_verdict == "POSITIVE_SIGNAL"
    )
    if positive_at_shallow:
        next_phase = "USE_SHALLOWER_PRODUCT_SEARCH"
    elif bench_ok and r2_ok and eval_sensitive_verdict in (
        "NO_POSITIVE_SIGNAL",
        "NEGATIVE_SIGNAL",
    ):
        if learned_direction in (
            "LEARNED_CHANGES_LIE_IN_LOW_LEVERAGE_DIRECTIONS",
            "MIXED",
        ):
            next_phase = "KEEP_MATERIAL_AND_FIX_LEARNING_DIRECTION"
        else:
            next_phase = "PROCEED_TO_PST"
    elif not bench_ok and r2_leverage == "LOW":
        next_phase = "REDESIGN_BENCHMARKS_FIRST"

    return {
        "schema_version": LEVERAGE_SCHEMA_VERSION,
        "R2_EVAL_LEVERAGE": r2_leverage,
        "BUDGET_EFFECT": budget_effect,
        "LEARNED_DIRECTION": learned_direction,
        "BENCHMARK_IDENTIFICATION": benchmark_identification,
        "LEARNING_RETEST": {
            "evaluation_sensitive": eval_sensitive_verdict,
            "mixed": mixed_verdict,
        },
        "PRODUCT_SEARCH_BUDGET": product,
        "NEXT_PHASE_DECISION": next_phase,
    }


# ================================================================ CLI


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data) + "\n", encoding="utf-8")


def _r2_compiled():
    from ..ai.benchmark.audit_suite import build_compiled, standard_ruleset_specs

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    return build_compiled(specs[R2_FID])


def _phase15_dir(seed: int) -> Path:
    return (
        Path("artifacts")
        / "learning_phase1_5"
        / R2_LABEL
        / f"{R2_LABEL}_seed{seed}"
    )


def _build_benchmark(out, entry, cls, seed, smoke, timings):
    from ..generation.config import GeneratorConfig
    from ..generation.generator import generate_game

    compiled = generate_game(
        GeneratorConfig(
            seed=int(entry["seed"]),
            board_size=CANDIDATE_BOARD_SIZE,
            setup_preset=CANDIDATE_PRESETS[
                int(entry["index"]) % len(CANDIDATE_PRESETS)
            ],
        )
    ).compiled_ruleset
    native_rules = compile_native_rules(compiled)
    openings = generate_arena_openings(
        compiled,
        count=RETEST_ARENA_PAIRS,
        seed=314159,
        min_plies=2,
        max_plies=6,
    )
    corpus = generate_diagnostic_corpus(
        compiled,
        openings,
        count=config_corpus_count(smoke),
        seed=42,
        max_plies=40,
    )
    bench_dir = out / "benchmarks" / cls / entry["ruleset_fingerprint"]
    cp_dir = bench_dir / "checkpoints"
    checkpoints = load_or_train_checkpoints(
        compiled,
        native_rules,
        seed,
        cp_dir if cp_dir.exists() else None,
    )
    cp_dir.mkdir(parents=True, exist_ok=True)
    _write(cp_dir / "generation_000.json", checkpoints[0].to_dict())
    for g in range(1, len(checkpoints)):
        _write(
            cp_dir / f"generation_{g:03d}.json",
            {"child": checkpoints[g].to_dict()},
        )
    data = frozen_retest(
        compiled,
        native_rules,
        checkpoints,
        corpus,
        openings,
        label=cls,
        budgets=(500, 1000) if smoke else LEARNED_BUDGETS,
    )
    _write(bench_dir / "summary.json", data)
    _write(bench_dir / "corpus.json", corpus.to_dict())
    _write(bench_dir / "openings.json", openings.to_dict())
    return data


def config_corpus_count(smoke: bool) -> int:
    return 8 if smoke else RETEST_CORPUS_COUNT


def _r2_reference_retest() -> dict:
    """Phase 1.6 R2 numbers (already measured); included as reference with
    provenance instead of a fresh retest."""
    return {
        "source": "artifacts/learning_phase1_6 (Phase 1.6, seeds 7/8/9)",
        "search_sensitivity_flip_range": "0.2% - 2.9%",
        "teacher_best_move_agreement_gen0": 0.72,
        "arena_sensitivity": "ADEQUATE (4000 vs 500 weak-side 0.125)",
    }


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="generic_chess.learning.leverage")
    parser.add_argument("--phase", default="all")
    parser.add_argument("--artifacts", default="artifacts/learning_phase1_7")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--candidate-count", type=int, default=None)
    parser.add_argument("--seed", type=int, default=RETEST_SEED)
    args = parser.parse_args(argv)

    out = Path(args.artifacts)
    out.mkdir(parents=True, exist_ok=True)
    timings = TimingRecorder()
    smoke = args.smoke

    config = pre_registered_config()
    if smoke:
        config["mode"] = "smoke"
        config["effective"] = {
            "perturbation_corpus_count": 8,
            "budget_sweep_corpus_count": 8,
            "candidate_count": 2,
            "retest_corpus_count": 8,
        }
    else:
        config["mode"] = "full"
        config["effective"] = {
            "perturbation_corpus_count": PERTURBATION_CORPUS_COUNT,
            "budget_sweep_corpus_count": BUDGET_SWEEP_CORPUS_COUNT,
            "candidate_count": args.candidate_count or CANDIDATE_COUNT,
            "retest_corpus_count": RETEST_CORPUS_COUNT,
        }
    _write(out / "config.json", config)

    compiled = _r2_compiled()
    native_rules = compile_native_rules(compiled)

    phase = args.phase
    if phase in ("all", "perturbation"):
        with timings.section("perturbation_sweep"):
            checkpoints = load_checkpoints_from_experiment(
                compiled, args.seed, _phase15_dir(args.seed)
            )
            base = checkpoints[0] if not smoke else _gen0_checkpoint(compiled, args.seed)
            corpus = _r2_corpus(
                compiled, config["effective"]["perturbation_corpus_count"]
            )
            result = perturbation_sweep(
                compiled, native_rules, base, corpus
            )
            _write(out / "perturbation_sweep.json", result)
        print("perturbation_sweep done")

    if phase in ("all", "budget"):
        with timings.section("budget_sweep"):
            checkpoints = load_checkpoints_from_experiment(
                compiled, args.seed, _phase15_dir(args.seed)
            )
            if smoke:
                base = _gen0_checkpoint(compiled, args.seed)
                child = base.child_checkpoint(
                    board_weights={
                        t: v * 0.9 for t, v in base.board_weights.items()
                    },
                    hand_weights={
                        t: v * 1.1 for t, v in base.hand_weights.items()
                    },
                    games_seen_delta=0,
                    positions_seen_delta=0,
                    training_updates_delta=1,
                    training_config_hash="smoke",
                    training_seed=args.seed,
                )
                checkpoints = [base, child]
            budgets = (500, 1000) if smoke else SWEEP_BUDGETS
            corpus = _r2_corpus(
                compiled, config["effective"]["budget_sweep_corpus_count"]
            )
            result = budget_sweep(
                compiled,
                native_rules,
                checkpoints,
                corpus,
                budgets=budgets,
            )
            _write(out / "budget_sweep.json", result)
        print("budget_sweep done")

    if phase in ("all", "candidates"):
        with timings.section("candidate_generation_and_screening"):
            count = config["effective"]["candidate_count"]
            summaries = screen_candidates(out, count=count)
            _write(
                out / "candidate_rulesets.json",
                {
                    "schema_version": LEVERAGE_SCHEMA_VERSION,
                    "candidate_count_requested": count,
                    "master_seed": CANDIDATE_MASTER_SEED,
                    "candidates": summaries,
                },
            )
            selection = select_benchmarks(
                summaries, compiled.ruleset_fingerprint
            )
            _write(out / "benchmark_selection.json", selection)
        print("candidates done")

    if phase in ("all", "retest"):
        with timings.section("frozen_retest"):
            selection_path = out / "benchmark_selection.json"
            if not selection_path.exists():
                raise SystemExit(
                    "benchmark_selection.json missing; run --phase candidates first"
                )
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            per_benchmark: dict[str, dict] = {}
            for cls in ("evaluation_sensitive", "mixed"):
                entry = selection.get(cls)
                if not entry:
                    continue
                per_benchmark[cls] = _build_benchmark(
                    out, entry, cls, args.seed, smoke, timings
                )
            retest_out = {
                "schema_version": LEVERAGE_SCHEMA_VERSION,
                "per_benchmark": per_benchmark,
                "r2_reference": _r2_reference_retest(),
            }
            _write(out / "frozen_checkpoint_retest.json", retest_out)
        print("retest done")

    if phase in ("all", "final"):
        with timings.section("product_and_verdict"):
            perturbation = json.loads(
                (out / "perturbation_sweep.json").read_text(encoding="utf-8")
            )
            budget_sweep_data = json.loads(
                (out / "budget_sweep.json").read_text(encoding="utf-8")
            )
            selection = json.loads(
                (out / "benchmark_selection.json").read_text(encoding="utf-8")
            )
            retest = json.loads(
                (out / "frozen_checkpoint_retest.json").read_text(encoding="utf-8")
            )
            eval_retest = retest["per_benchmark"].get("evaluation_sensitive")
            if eval_retest is None:
                product = {
                    "schema_version": LEVERAGE_SCHEMA_VERSION,
                    "product_budget": "NO_PRODUCT_BUDGET_IDENTIFIED",
                    "reason": "no evaluation-sensitive benchmark selected",
                    "per_budget": [],
                }
            else:
                product = product_budget_analysis(
                    eval_retest, r2_budget_sweep=budget_sweep_data
                )
            _write(out / "product_budget_analysis.json", product)

            per_benchmark_verdicts = {
                cls: verdict_learning_retest(data)
                for cls, data in retest["per_benchmark"].items()
            }
            verdict = final_verdict(
                verdict_r2_leverage(perturbation),
                verdict_budget_effect(budget_sweep_data),
                verdict_learned_direction(budget_sweep_data),
                verdict_benchmark_identification(selection),
                {
                    "per_benchmark": {
                        k: {"learning_retest": v}
                        for k, v in per_benchmark_verdicts.items()
                    }
                },
                product,
            )
            _write(out / "final_verdict.json", verdict)
            print(json.dumps(verdict, indent=2, sort_keys=True))
        print("final done")

    perf_path = out / "performance.json"
    existing = (
        json.loads(perf_path.read_text(encoding="utf-8"))
        if perf_path.exists()
        else None
    )
    _write(
        perf_path,
        merge_performance(existing, timings.to_dict()["phases"]),
    )
    return 0


def _r2_corpus(compiled, count: int) -> object:
    openings = generate_arena_openings(
        compiled, count=16, seed=314159, min_plies=2, max_plies=6
    )
    return generate_diagnostic_corpus(
        compiled, openings, count=count, seed=42, max_plies=40
    )


if __name__ == "__main__":
    import sys

    sys.exit(main())
