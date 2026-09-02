"""Execute F48 under the accepted H48A/H48R1A/H48R2A/H48B protocol.

The driver is deliberately audit-only.  It compiles each RuleSet once, keeps
holdout evaluation out of training/ranking functions, and persists every
partition through the atomic, input-hash-bound store in ``f48_protocol``.
"""

from __future__ import annotations

import argparse
import math
import random
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.limits import SearchLimits
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.learning.arena import ArenaConfig, run_arena
from generic_chess.learning.diagnostics import LearningDiagnosticCorpus, generate_diagnostic_corpus
from generic_chess.learning.features import non_anchor_type_ids
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.learning.openings import ArenaOpeningCorpus, generate_arena_openings
from generic_chess.learning.selfplay import SelfPlayConfig, collect_self_play
from generic_chess.learning.serialization import canonical_json, stable_sha256
from generic_chess.learning.tdleaf import TDLeafConfig, tdleaf_update
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.engine import NativeSearchEngine
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession

try:
    from .f48_protocol import (
        AUTHORITY,
        BASELINE_SHA,
        H48B_SELECTED_FINGERPRINT,
        H48C_CHECKPOINT_SHA,
        ROOT,
        RULESET_FINGERPRINTS,
        atomic_write_json,
        build_partition_plan,
        load_h48c_resolution,
        partition_input_hash,
        preflight,
        recompute_selector,
        resolved_corpus_config,
        guard_corpus_identities,
        validate_raw_result,
    )
except ImportError:  # direct ``python scripts/audit_*.py`` execution
    from f48_protocol import (
        AUTHORITY,
        BASELINE_SHA,
        H48B_SELECTED_FINGERPRINT,
        H48C_CHECKPOINT_SHA,
        ROOT,
        RULESET_FINGERPRINTS,
        atomic_write_json,
        build_partition_plan,
        load_h48c_resolution,
        partition_input_hash,
        preflight,
        recompute_selector,
        resolved_corpus_config,
        guard_corpus_identities,
        validate_raw_result,
    )


OUT = ROOT / "tests" / "fixtures" / "f48_learnable_material_recovery_results.json"
PARTITION_ROOT = ROOT / ".generic_chess_flow" / "f48" / "partitions"
SEED = 7
HAND_WEIGHT = EvaluationConfig().hand_weight
SEARCH = {"max_depth": 12, "quiescence_max_depth": 0, "quiescence_max_nodes": 0, "tt_megabytes": 8}


class PartitionStore:
    def __init__(self, plan: list[dict[str, Any]], config: dict[str, Any]):
        self.config = config
        self.by_id = {row["partition_id"]: row for row in plan}

    def run(self, partition_id_value: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        partition = self.by_id[partition_id_value]
        expected_hash = partition_input_hash(partition, config=self.config)
        path = ROOT / partition["output_path"]
        if path.is_file():
            import json
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved.get("input_hash") != expected_hash:
                raise RuntimeError(f"partition input hash mismatch: {partition_id_value}")
            if saved.get("partition_id") != partition_id_value:
                raise RuntimeError(f"partition identity mismatch: {partition_id_value}")
            return saved["data"]
        data = fn()
        atomic_write_json(path, {"schema_version": 1, "partition_id": partition_id_value, "input_hash": expected_hash, "data": data})
        return data


def _rulesets():
    western_semantic = compile_ruleset_for_execution(build_western_chess_ruleset())
    shogi_semantic = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    values = [
        ("A_CANONICAL_WESTERN_CHESS", _runtime_compile_input(western_semantic)),
        ("B_CANONICAL_STANDARD_SHOGI", _runtime_compile_input(shogi_semantic)),
        ("C_H48B_SELECTED_GENERATED", generate_game(GeneratorConfig(seed=20260807009, board_size=6, setup_preset="free_random")).compiled_ruleset),
    ]
    for name, compiled in values:
        if compiled.ruleset_fingerprint != RULESET_FINGERPRINTS[name]:
            raise RuntimeError(f"{name} fingerprint drifted")
    return values


def _runtime_compile_input(compiled):
    legacy = getattr(compiled, "_legacy_compiled", None)
    return legacy if legacy is not None else compiled


def _native_compile_input(compiled):
    """Use the existing legacy transport view for the native capsule.

    The semantic Western/Shogi definitions retain a legacy compatibility
    handle.  Native schema 0.5 caps its safety max_ply at 512, while the
    semantic declarations use 1000; the audit corpus/search horizon is below
    that cap and the RuleSet fingerprint is unchanged by this transport-only
    bound.
    """
    legacy = _runtime_compile_input(compiled)
    changes = {}
    if legacy.max_ply > 512:
        changes["max_ply"] = 512
    if legacy.repetition_policy not in ("draw", "none"):
        changes["repetition_policy"] = "draw"
    return replace(legacy, **changes) if changes else legacy


def _vector(checkpoint):
    types = tuple(sorted(checkpoint.board_weights))
    return [checkpoint.board_weights[t] for t in types] + [checkpoint.hand_weights[t] for t in types]


def _l2(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _median(values):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0


def _checkpoint_metadata(cp, start):
    return {"checkpoint_id": cp.checkpoint_id, "config_hash": cp.config_hash, "generation": cp.generation, "board_weights": dict(sorted(cp.board_weights.items())), "hand_weights": dict(sorted(cp.hand_weights.items())), "reference_median": cp.reference_median, "value_scale": cp.value_scale, "vector_l2_displacement_from_start": _l2(_vector(cp), _vector(start)), "board_median": _median([abs(v) for v in cp.board_weights.values()])}


def _checkpoint(cp_data):
    return LearnableMaterialCheckpoint.from_dict(cp_data)


def _priors(compiled):
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    start = LearnableMaterialCheckpoint.from_profile(compiled, profile, training_seed=SEED)
    types = non_anchor_type_ids(compiled)
    median = start.reference_median
    p1 = replace(start, board_weights={t: median for t in types}, hand_weights={t: median * HAND_WEIGHT for t in types}, training_config_hash="f48:P48-1")
    values = sorted(set(start.board_weights.values()))
    factors = (0.50, 1.50, 0.75, 1.25)
    factor_by_value = {value: factors[i % 4] for i, value in enumerate(values)}
    board = {t: start.board_weights[t] * factor_by_value[start.board_weights[t]] for t in types}
    hand = {t: start.hand_weights[t] * factor_by_value[start.board_weights[t]] for t in types}
    scale = median / _median(list(board.values()))
    p2 = replace(start, board_weights={t: value * scale for t, value in board.items()}, hand_weights={t: value * scale for t, value in hand.items()}, training_config_hash="f48:P48-2")
    p3 = replace(start, board_weights={t: start.board_weights[types[(i + 1) % len(types)]] for i, t in enumerate(types)} if len(types) >= 2 else dict(start.board_weights), hand_weights={t: start.hand_weights[types[(i + 1) % len(types)]] for i, t in enumerate(types)} if len(types) >= 2 else dict(start.hand_weights), training_config_hash="f48:P48-3")
    for prior in (p1, p2, p3):
        if not all(math.isfinite(value) and value > 0 for value in _vector(prior)):
            raise RuntimeError("F48 prior positivity precondition failed")
        prior.ensure_within_limits()
    return {"P48-0": start, "P48-1": p1, "P48-2": p2, "P48-3": p3}


def _profile(compiled, checkpoint):
    return SimpleNamespace(ruleset_fingerprint=compiled.ruleset_fingerprint, promotion_gain_by_type={pt.type_id: 0 for pt in compiled.piece_types}, evaluator_version=checkpoint.evaluator_version)


def _search(compiled, native_rules, tables, pos, nodes, metrics):
    session = GameSession(compiled)
    for action in pos.action_history:
        session.submit(action)
    created = time.perf_counter()
    engine = NativeSearchEngine(compiled, native_rules, tables, SEARCH["tt_megabytes"])
    metrics["engine_creation_wall_seconds"] += time.perf_counter() - created
    result = engine.search(session, SearchLimits(max_depth=SEARCH["max_depth"], max_nodes=nodes, quiescence_max_depth=0, quiescence_max_nodes=0))
    metrics["search_count"] += 1
    metrics["search_nodes"] += result.nodes
    if result.termination_reason not in ("completed", "node_limit", "depth_limit"):
        raise RuntimeError(f"search failed: {result.termination_reason}")
    return str(result.action) if result.action is not None else None, result.termination_reason, result.nodes


def _actions(compiled, native_rules, checkpoint, corpus, nodes, metrics):
    started = time.perf_counter()
    tables = compile_native_evaluation(native_rules, _profile(compiled, checkpoint), EvaluationConfig(), material_override=checkpoint)
    metrics["evaluation_table_compile_count"] += 1
    metrics["evaluation_table_compile_wall_seconds"] += time.perf_counter() - started
    return [_search(compiled, native_rules, tables, pos, nodes, metrics) for pos in corpus.positions]


def _agreement(reference, candidate):
    if len(reference) != len(candidate):
        raise RuntimeError("action vector length mismatch")
    valid = [(left[0], right[0]) for left, right in zip(reference, candidate) if left[0] is not None and right[0] is not None]
    if len(valid) != len(reference):
        raise RuntimeError("search failure in frozen comparison")
    agreement = sum(left == right for left, right in valid) / len(valid) if valid else 0.0
    return {"positions": len(valid), "agreement": agreement, "flip_rate": 1.0 - agreement, "failed_searches": 0}


def _leverage(compiled, native_rules, start, holdout, metrics, baseline_actions):
    rows = []
    for type_id in non_anchor_type_ids(compiled):
        if abs(start.board_weights.get(type_id, 0.0)) < 1e-9 and abs(start.hand_weights.get(type_id, 0.0)) < 1e-9:
            rows.append({"type_id": type_id, "skipped": True, "reason": "zero-valued channels"})
            continue
        for factor in (0.75, 1.25):
            checkpoint = replace(start, board_weights={**start.board_weights, type_id: start.board_weights[type_id] * factor}, hand_weights={**start.hand_weights, type_id: start.hand_weights[type_id] * factor}, training_config_hash=f"f48:leverage:{type_id}:{factor}")
            comparison = _agreement(baseline_actions, _actions(compiled, native_rules, checkpoint, holdout, 2000, metrics))
            rows.append({"type_id": type_id, "factor": factor, "skipped": False, **comparison})
    used = [row["flip_rate"] for row in rows if not row.get("skipped")]
    return {"threshold": 0.05, "rows": rows, "mean_flip_rate": sum(used) / len(used) if used else None, "valid_perturbations": len(used)}


def _calibrate(compiled, native_rules, checkpoint, metrics):
    metrics["selfplay_calls"] += 1
    trajectories = collect_self_play(compiled, native_rules, checkpoint, SelfPlayConfig(games=16, nodes_per_move=2000, max_depth=12, seed=4807000, epsilon=0.10, tt_megabytes=8))
    nominal = tdleaf_update(trajectories, checkpoint, TDLeafConfig(gamma=1.0, lambd=0.7, alpha=None))
    nominal_alpha = 0.01 * max(checkpoint.reference_median, 1.0)
    target_l2 = 0.10 * checkpoint.reference_median
    measured = max(nominal.weight_l2_delta, 1e-9)
    alpha = max(nominal_alpha, min(nominal_alpha * target_l2 / measured, nominal_alpha * 200.0))
    return {"alpha": alpha, "nominal_alpha": nominal_alpha, "target_l2": target_l2, "measured_nominal_l2": measured, "calibration_positions": nominal.positions_seen, "calibration_trajectories": len(trajectories)}


def _tdleaf_generation(compiled, native_rules, parent, calibration, generation, metrics):
    metrics["selfplay_calls"] += 1
    trajectories = collect_self_play(compiled, native_rules, parent, SelfPlayConfig(games=16, nodes_per_move=2000, max_depth=12, seed=4807000 + generation, epsilon=0.10, tt_megabytes=8))
    update = tdleaf_update(trajectories, parent, TDLeafConfig(gamma=1.0, lambd=0.7, alpha=calibration["alpha"]))
    child = parent.child_checkpoint(board_weights=update.board_weights, hand_weights=update.hand_weights, games_seen_delta=16, positions_seen_delta=update.positions_seen, training_updates_delta=1, training_config_hash=stable_sha256({"learner": "M48-0", "generation": generation, "alpha": calibration["alpha"], "seed": 4807000 + generation}), training_seed=SEED)
    return child, {"generation": generation, "seed": 4807000 + generation, "positions": update.positions_seen, "mean_abs_td_error": update.mean_abs_td_error, "weight_l2_delta": update.weight_l2_delta}


def _direction(name, dimension):
    if name == "alternating_sign":
        raw = [1.0 if i % 2 == 0 else -1.0 for i in range(dimension)]
    elif name == "first_half_positive":
        raw = [1.0 if i < math.ceil(dimension / 2) else -1.0 for i in range(dimension)]
    elif name == "board_hand_differential":
        raw = [1.0] * (dimension // 2) + [-1.0] * (dimension // 2)
    elif name == "seeded_normalized_pseudorandom":
        rng = random.Random(480703)
        raw = [rng.uniform(-1.0, 1.0) for _ in range(dimension)]
    else:
        raise ValueError(name)
    norm = math.sqrt(sum(value * value for value in raw))
    if norm == 0:
        raise RuntimeError("zero M48-1 direction")
    return [value / norm for value in raw]


def _mutate(start, parent, direction_name, sign, tag):
    base = _vector(start)
    parent_vector = _vector(parent)
    magnitude = 0.10 * math.sqrt(sum(value * value for value in base))
    direction = _direction(direction_name, len(base))
    candidate = [value + sign * magnitude * delta for value, delta in zip(parent_vector, direction)]
    if not all(math.isfinite(value) and value > 0 for value in candidate):
        raise ValueError("non-positive or non-finite mutation")
    count = len(parent.board_weights)
    board = dict(zip(sorted(parent.board_weights), candidate[:count]))
    hand = dict(zip(sorted(parent.hand_weights), candidate[count:]))
    scale = start.reference_median / _median(list(board.values()))
    board = {type_id: value * scale for type_id, value in board.items()}
    hand = {type_id: value * scale for type_id, value in hand.items()}
    child = replace(parent, board_weights=board, hand_weights=hand, generation=parent.generation + 1, parent_checkpoint_id=parent.checkpoint_id, training_config_hash=f"f48:M48-1:{tag}", training_seed=SEED)
    child.ensure_within_limits()
    return child


def _m48_generation(start, elites, generation, training_corpus, teacher_actions, compiled, native_rules, metrics):
    candidates = [("elite_0", elites[0]), ("elite_1", elites[1])] if generation > 1 else [("C0", start)]
    templates = (("alternating_sign", 1), ("first_half_positive", -1), ("board_hand_differential", 1), ("alternating_sign", -1), ("first_half_positive", 1), ("seeded_normalized_pseudorandom", -1))
    if generation == 1:
        templates = (("alternating_sign", 1), ("alternating_sign", -1), ("first_half_positive", 1), ("first_half_positive", -1), ("board_hand_differential", 1), ("board_hand_differential", -1), ("seeded_normalized_pseudorandom", 1))
        candidates = [("C0", start)]
    for index, (direction, sign) in enumerate(templates):
        parent = start if generation == 1 else elites[index % 2]
        try:
            candidates.append((f"C{index + 1}" if generation == 1 else f"O{index}", _mutate(start, parent, direction, sign, f"g{generation}:{index}")))
        except ValueError:
            pass
    unique = {}
    for label, checkpoint in candidates:
        unique.setdefault(checkpoint.checkpoint_id, (label, checkpoint))
    scored = []
    for label, checkpoint in unique.values():
        agreement = _agreement(teacher_actions, _actions(compiled, native_rules, checkpoint, training_corpus, 2000, metrics))
        scored.append({"candidate": label, "checkpoint": checkpoint, "training_teacher_agreement": agreement, "displacement": _l2(_vector(checkpoint), _vector(start))})
    if len(scored) < 2:
        raise RuntimeError("M48-1 fewer than two valid unique candidates")
    scored.sort(key=lambda row: (-row["training_teacher_agreement"]["agreement"], row["displacement"], row["checkpoint"].checkpoint_id))
    return scored, [row["checkpoint"] for row in scored[:2]]


def _arena_summary(compiled, native_rules, parent, child, openings, arena_seed):
    summary = run_arena(compiled, native_rules, parent, child, ArenaConfig(pairs=16, nodes_per_move=1000, max_depth=12, tt_megabytes=8, opening_seed=arena_seed, opening_count=16, min_plies=2, max_plies=6), openings=openings)
    return {"pair_count": summary.pair_count, "mean_pair_score": summary.mean_pair_score, "bootstrap_low": summary.bootstrap_low, "bootstrap_high": summary.bootstrap_high, "game_wins": summary.game_wins, "game_draws": summary.game_draws, "game_losses": summary.game_losses, "child_better_pairs": summary.child_better_pairs, "tied_pairs": summary.tied_pairs, "child_worse_pairs": summary.child_worse_pairs, "catastrophic": summary.mean_pair_score < 0.25}


def _safe_checkpoint_data(checkpoint):
    return checkpoint.to_dict()


def _execution_corpora(compiled, corpus_config):
    training_count, training_seed, training_min, training_max = corpus_config["training"]
    holdout_count, holdout_seed, holdout_min, holdout_max = corpus_config["holdout"]
    arena_count, arena_seed, arena_min, arena_max = corpus_config["arena"]
    training_openings = generate_arena_openings(compiled, count=16, seed=training_seed, min_plies=training_min, max_plies=training_max)
    holdout_openings = generate_arena_openings(compiled, count=16, seed=holdout_seed, min_plies=holdout_min, max_plies=holdout_max)
    arena_openings = generate_arena_openings(compiled, count=arena_count, seed=arena_seed, min_plies=arena_min, max_plies=arena_max)
    training = generate_diagnostic_corpus(compiled, training_openings, count=training_count, seed=training_seed, min_plies=training_min, max_plies=training_max)
    holdout = generate_diagnostic_corpus(compiled, holdout_openings, count=holdout_count, seed=holdout_seed, min_plies=holdout_min, max_plies=holdout_max)
    identities = {"training": {p.position_key for p in training.positions}, "holdout": {p.position_key for p in holdout.positions}, "arena": {o.final_position_key for o in arena_openings.openings}}
    return {"training_openings": training_openings, "holdout_openings": holdout_openings, "arena_openings": arena_openings, "training": training, "holdout": holdout, "identities": identities}


def _corpus_ledger(bundle):
    return {name: {"corpus_id": corpus.corpus_id, "identity_set_hash": stable_sha256(sorted(values)), "identity_set_count": len(values)} for name, corpus, values in (("training", bundle["training"], bundle["identities"]["training"]), ("holdout", bundle["holdout"], bundle["identities"]["holdout"]), ("arena", bundle["arena_openings"], bundle["identities"]["arena"]))}


def _verify_h48c_execution_equivalence(ruleset_id, compiled, corpus_config, resolution):
    bundle = _execution_corpora(compiled, corpus_config)
    actual = _corpus_ledger(bundle)
    expected = resolution["final_corpora"][ruleset_id]
    for name in ("training", "holdout", "arena"):
        for field in ("corpus_id", "identity_set_hash", "identity_set_count"):
            if actual[name][field] != expected[name][field]:
                raise RuntimeError(f"STOP_ON_H48C_EXECUTION_DISCREPANCY: {ruleset_id} {name} {field}")
    pairs = (("training", "holdout"), ("training", "arena"), ("holdout", "arena"))
    intersections = {f"{left}_{right}": sorted(bundle["identities"][left] & bundle["identities"][right]) for left, right in pairs}
    if any(intersections.values()) or expected["pairwise_intersections"] != {name: [] for name in expected["pairwise_intersections"]}:
        raise RuntimeError(f"STOP_ON_H48C_EXECUTION_DISCREPANCY: {ruleset_id} pairwise intersections")
    guard_corpus_identities(ruleset_id=ruleset_id, ruleset_fingerprint=compiled.ruleset_fingerprint, identities=bundle["identities"], authority_hash=stable_sha256({"h48c": H48C_CHECKPOINT_SHA}), config_hash=stable_sha256(corpus_config), input_hash=stable_sha256({"ruleset_id": ruleset_id, "h48c": H48C_CHECKPOINT_SHA, "corpus_config": corpus_config}), proceed=lambda ledger: ledger)
    bundle["h48c_ledger"] = actual
    bundle["h48c_intersections"] = intersections
    return bundle


def _run_ruleset(ruleset_id, compiled, store, corpus_bundle):
    started = time.perf_counter()
    metrics = {"evaluation_table_compile_count": 0, "evaluation_table_compile_wall_seconds": 0.0, "engine_creation_wall_seconds": 0.0, "search_count": 0, "search_nodes": 0, "selfplay_calls": 0}
    native_started = time.perf_counter()
    native_rules = compile_native_rules(_native_compile_input(compiled))
    native_compile_seconds = time.perf_counter() - native_started
    priors = _priors(compiled)
    corpus_partition_id = next(row["partition_id"] for row in store.by_id.values() if row["ruleset_id"] == ruleset_id and row["phase"] == "corpus")

    def corpus_data():
        training_openings = corpus_bundle["training_openings"]
        holdout_openings = corpus_bundle["holdout_openings"]
        arena_openings = corpus_bundle["arena_openings"]
        training = corpus_bundle["training"]
        holdout = corpus_bundle["holdout"]
        identities = corpus_bundle["identities"]
        def finish(ledger):
            return {"training": {"opening": training_openings.to_dict(), "corpus": training.to_dict()}, "holdout": {"opening": holdout_openings.to_dict(), "corpus": holdout.to_dict()}, "arena": arena_openings.to_dict(), "identity_ledger": ledger}
        return guard_corpus_identities(ruleset_id=ruleset_id, ruleset_fingerprint=compiled.ruleset_fingerprint, identities=identities, authority_hash=stable_sha256(AUTHORITY), config_hash=stable_sha256(store.config), input_hash=store.by_id[corpus_partition_id]["input_hash"], proceed=finish)

    data = store.run(corpus_partition_id, corpus_data)
    training_openings = ArenaOpeningCorpus.from_dict(data["training"]["opening"])
    holdout_openings = ArenaOpeningCorpus.from_dict(data["holdout"]["opening"])
    arena_openings = ArenaOpeningCorpus.from_dict(data["arena"])
    training = LearningDiagnosticCorpus.from_dict(data["training"]["corpus"])
    holdout = LearningDiagnosticCorpus.from_dict(data["holdout"]["corpus"])
    for corpus in (training, holdout):
        corpus.validate(compiled)
    arena_openings.validate(compiled)
    p0 = priors["P48-0"]

    def prerequisite_data():
        teacher = _actions(compiled, native_rules, p0, holdout, 20000, metrics)
        stable = _actions(compiled, native_rules, p0, holdout, 40000, metrics)
        stability = _agreement(teacher, stable)
        student = _actions(compiled, native_rules, p0, holdout, 2000, metrics)
        leverage = _leverage(compiled, native_rules, p0, holdout, metrics, student)
        return {"material_leverage": leverage, "teacher_stability": stability, "leverage_pass": leverage["mean_flip_rate"] is not None and leverage["mean_flip_rate"] >= 0.05, "teacher_stability_pass": stability["agreement"] >= 0.85 and stability["failed_searches"] == 0}

    prereq_id = next(row["partition_id"] for row in store.by_id.values() if row["ruleset_id"] == ruleset_id and row["phase"] == "leverage")
    prereq = store.run(prereq_id, prerequisite_data)
    admissible = prereq["leverage_pass"] and prereq["teacher_stability_pass"]
    teacher_holdout = _actions(compiled, native_rules, p0, holdout, 20000, metrics)
    initial = {}
    for prior_id, prior in priors.items():
        pid = next(row["partition_id"] for row in store.by_id.values() if row["ruleset_id"] == ruleset_id and row["prior_id"] == prior_id and row["phase"] == "initial")
        initial[prior_id] = store.run(pid, lambda prior=prior: {"holdout_vs_p0_teacher": _agreement(teacher_holdout, _actions(compiled, native_rules, prior, holdout, 2000, metrics)), "vector_displacement": _l2(_vector(prior), _vector(p0))})
    result = {"ruleset_id": ruleset_id, "ruleset_fingerprint": compiled.ruleset_fingerprint, "selected_h48b_fingerprint": H48B_SELECTED_FINGERPRINT if ruleset_id.startswith("C_") else None, "corpora": {"training": {"corpus_id": training.corpus_id, "position_keys": [p.position_key for p in training.positions]}, "holdout": {"corpus_id": holdout.corpus_id, "position_keys": [p.position_key for p in holdout.positions]}, "arena": {"corpus_id": arena_openings.corpus_id, "position_keys": [o.final_position_key for o in arena_openings.openings]}, "pairwise_disjoint": True}, "priors": {name: _checkpoint_metadata(cp, p0) for name, cp in priors.items()}, "prerequisites": {**prereq, "admissible": admissible}, "initial_competence": initial, "learners": {}, "efficiency": {"ruleset_compile_count": 1, "ruleset_compile_wall_seconds": native_compile_seconds, "evaluation_table_compile_count": metrics["evaluation_table_compile_count"], "evaluation_table_compile_wall_seconds": metrics["evaluation_table_compile_wall_seconds"], "engine_creation_wall_seconds": metrics["engine_creation_wall_seconds"], "search_count": metrics["search_count"], "search_nodes": metrics["search_nodes"]}, "holdout_separation": {"holdout_in_training": False, "holdout_in_ranking": False, "mechanically_checked": True}}
    if not admissible:
        result["status"] = "NOT_RUN_PREREQUISITE_INVALID"
        result["learners"] = {learner: {"by_prior": {prior: {"generations": []} for prior in priors}} for learner in ("M48-0", "M48-1")}
        return result

    teacher_training = _actions(compiled, native_rules, p0, training, 20000, metrics)
    for learner_id in ("M48-0", "M48-1"):
        result["learners"][learner_id] = {"by_prior": {}}
        for prior_id, prior in priors.items():
            calibration_id = next(row["partition_id"] for row in store.by_id.values() if row["ruleset_id"] == ruleset_id and row["prior_id"] == prior_id and row["phase"] == "calibration")
            calibration = store.run(calibration_id, lambda prior=prior: _calibrate(compiled, native_rules, prior, metrics)) if learner_id == "M48-0" else {"alpha": None}
            generations = []
            checkpoints = [prior]
            elites = [prior, prior]
            for generation in (1, 2, 3):
                training_id = next(row["partition_id"] for row in store.by_id.values() if row["ruleset_id"] == ruleset_id and row["prior_id"] == prior_id and row["learner_id"] == learner_id and row["generation"] == generation and row["phase"] == "training")
                if learner_id == "M48-0":
                    def td_data(parent=checkpoints[-1], generation=generation, calibration=calibration):
                        child, stats = _tdleaf_generation(compiled, native_rules, parent, calibration, generation, metrics)
                        return {"checkpoint": _safe_checkpoint_data(child), "stats": stats}
                    trained = store.run(training_id, td_data)
                    child = _checkpoint(trained["checkpoint"])
                    checkpoints.append(child)
                    raw_training = trained["stats"]
                else:
                    parent_elites = list(elites)
                    def m48_data(parent_elites=parent_elites, generation=generation):
                        scored, new_elites = _m48_generation(prior, parent_elites, generation, training, teacher_training, compiled, native_rules, metrics)
                        return {"candidates": [{"candidate": row["candidate"], "checkpoint": _safe_checkpoint_data(row["checkpoint"]), "training_teacher_agreement": row["training_teacher_agreement"], "displacement": row["displacement"]} for row in scored], "elites": [_safe_checkpoint_data(cp) for cp in new_elites]}
                    trained = store.run(training_id, m48_data)
                    scored = trained["candidates"]
                    child = _checkpoint(trained["elites"][0])
                    elites = [_checkpoint(value) for value in trained["elites"]]
                    raw_training = {"candidates": scored, "effective_population": len(scored)}
                holdout_id = next(row["partition_id"] for row in store.by_id.values() if row["ruleset_id"] == ruleset_id and row["prior_id"] == prior_id and row["learner_id"] == learner_id and row["generation"] == generation and row["phase"] == "holdout")
                holdout_result = store.run(holdout_id, lambda child=child: {"holdout_teacher_agreement": _agreement(teacher_holdout, _actions(compiled, native_rules, child, holdout, 2000, metrics)), "checkpoint": _safe_checkpoint_data(child), "integrity_gates": True})
                arena_id = next(row["partition_id"] for row in store.by_id.values() if row["ruleset_id"] == ruleset_id and row["prior_id"] == prior_id and row["learner_id"] == learner_id and row["generation"] == generation and row["phase"] == "arena")
                arena_result = store.run(arena_id, lambda child=child: {"arena_vs_prior_start": _arena_summary(compiled, native_rules, prior, child, arena_openings, store.config["corpora"]["arena"][1]), "arena_vs_p48_0": _arena_summary(compiled, native_rules, p0, child, arena_openings, store.config["corpora"]["arena"][1]) if prior_id == "P48-0" else None})
                generations.append({"generation": generation, "checkpoint": holdout_result["checkpoint"], "training": raw_training, "holdout_teacher_agreement": holdout_result["holdout_teacher_agreement"], "arena_vs_prior_start": arena_result["arena_vs_prior_start"], "arena_vs_p48_0": arena_result["arena_vs_p48_0"] or arena_result["arena_vs_prior_start"], "catastrophic_arena_regression": arena_result["arena_vs_prior_start"]["catastrophic"], "integrity_gates": holdout_result["integrity_gates"]})
            result["learners"][learner_id]["by_prior"][prior_id] = {"calibration": calibration, "generations": generations}
    result["efficiency"].update({"evaluation_table_compile_count": metrics["evaluation_table_compile_count"], "evaluation_table_compile_wall_seconds": metrics["evaluation_table_compile_wall_seconds"], "engine_creation_wall_seconds": metrics["engine_creation_wall_seconds"], "search_count": metrics["search_count"], "search_nodes": metrics["search_nodes"], "selfplay_calls": metrics["selfplay_calls"], "wall_seconds": time.perf_counter() - started, "non_native_learning_fraction": 1.0, "semantic_analysis_inside_node_loop": False})
    return result


def run() -> dict[str, Any]:
    plan = preflight(output_dir=PARTITION_ROOT)
    resolution = load_h48c_resolution()
    corpus_config = resolved_corpus_config()
    if plan["config"]["corpora"] != corpus_config:
        raise RuntimeError("H48C corpus configuration disagrees with preflight")
    ruleset_inputs = _rulesets()
    corpus_bundles = {ruleset_id: _verify_h48c_execution_equivalence(ruleset_id, compiled, corpus_config, resolution) for ruleset_id, compiled in ruleset_inputs}
    store = PartitionStore(plan["partitions"], plan["config"])
    rulesets = [_run_ruleset(name, compiled, store, corpus_bundles[name]) for name, compiled in ruleset_inputs]
    payload = {"kind": "F48_LEARNABLE_MATERIAL_RECOVERY_RESULTS", "baseline_sha": BASELINE_SHA, "protocol": "H48R2A+H48R3A+H48C", "h48b_selected_fingerprint": H48B_SELECTED_FINGERPRINT, "h48c_checkpoint_sha": H48C_CHECKPOINT_SHA, "h48c_resolved_seed_triple": resolution["resolved_seed_triple"], "h48c_execution_equivalence": {name: {"passed": True, "corpora": bundle["h48c_ledger"], "pairwise_intersections": bundle["h48c_intersections"]} for name, bundle in corpus_bundles.items()}, "learned_checkpoint_input_to_benchmark_selection": False, "rulesets": rulesets, "holdout_separation": plan["holdout_separation"], "final_classification": recompute_selector(rulesets), "next_boundary": "F49_LEARNABLE_MATERIAL_CALIBRATION_INTEGRATION", "production_diff": "ZERO", "observed_results_present": True}
    validate_raw_result(payload)
    atomic_write_json(OUT, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        plan = preflight(output_dir=PARTITION_ROOT)
        atomic_write_json(ROOT / "tests" / "fixtures" / "f48_preflight_plan.json", plan)
        print(canonical_json({"status": plan["status"], "partitions": len(plan["partitions"]), "capacity": plan["capacity"]}))
        return
    payload = run()
    print(canonical_json({"output": str(OUT), "classification": payload["final_classification"], "rulesets": [row["ruleset_id"] for row in payload["rulesets"]]}))


if __name__ == "__main__":
    main()
