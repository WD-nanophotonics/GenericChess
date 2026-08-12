"""Learning Phase 1.6: signal diagnostics for the material-only TDLeaf
learner.

This module only *measures* the frozen learning pipeline: it never changes
``tdleaf.py``/``features.py``/``selfplay.py``.  It provides:

* ``LearningDiagnosticCorpus``: a fixed, deterministic, checkpoint-independent
  holdout of reachable positions;
* TD-error instrumentation that recomputes the frozen TDLeaf math and proves
  (in tests) that it does not change the learned checkpoint;
* evaluator-change, search-decision-sensitivity, deeper-search teacher and
  arena-sensitivity audits.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.profile import build_ruleset_profile
from ..ai.limits import SearchLimits
from ..core.actions import Action, action_from_dict, action_to_dict
from ..core.identity import position_identity_key
from ..native.compiler import compile_native_evaluation
from ..native.compiler import compile_native_rules
from ..native.engine import NativeSearchEngine
from ..session.session import GameSession
from .features import linear_value, material_features, non_anchor_type_ids
from .material import LearnableMaterialCheckpoint
from .openings import ArenaOpeningCorpus
from .selfplay import SelfPlayConfig, collect_self_play
from .serialization import canonical_json, stable_sha256
from .statistics import bootstrap_pair_mean_ci
from .tdleaf import TDLeafConfig, tdleaf_update


# ---------------------------------------------------------------- corpus


@dataclass(frozen=True, slots=True)
class DiagnosticPosition:
    index: int
    action_history: tuple[Action, ...]
    position_key: str
    side_to_move: int
    ply: int

    def phase(self) -> str:
        if self.ply <= 6:
            return "opening"
        if self.ply <= 12:
            return "early"
        if self.ply <= 24:
            return "mid"
        return "late"


@dataclass(frozen=True, slots=True)
class LearningDiagnosticCorpus:
    schema_version: int = 1
    ruleset_fingerprint: str = ""
    source_opening_corpus_id: str = ""
    seed: int = 0
    positions: tuple[DiagnosticPosition, ...] = ()

    @property
    def corpus_id(self) -> str:
        return stable_sha256(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "ruleset_fingerprint": self.ruleset_fingerprint,
            "source_opening_corpus_id": self.source_opening_corpus_id,
            "seed": self.seed,
            "positions": [
                {
                    "index": p.index,
                    "action_history": [action_to_dict(a) for a in p.action_history],
                    "position_key": p.position_key,
                    "side_to_move": p.side_to_move,
                    "ply": p.ply,
                }
                for p in self.positions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LearningDiagnosticCorpus":
        if data.get("schema_version") != 1:
            raise ValueError(
                f"unsupported diagnostic corpus schema {data.get('schema_version')}"
            )
        return cls(
            ruleset_fingerprint=str(data["ruleset_fingerprint"]),
            source_opening_corpus_id=str(data["source_opening_corpus_id"]),
            seed=int(data["seed"]),
            positions=tuple(
                DiagnosticPosition(
                    index=int(p["index"]),
                    action_history=tuple(
                        action_from_dict(a) for a in p["action_history"]
                    ),
                    position_key=str(p["position_key"]),
                    side_to_move=int(p["side_to_move"]),
                    ply=int(p["ply"]),
                )
                for p in data["positions"]
            ),
        )

    def validate(self, compiled) -> None:
        if self.ruleset_fingerprint != compiled.ruleset_fingerprint:
            raise ValueError(
                "diagnostic corpus fingerprint does not match the compiled ruleset"
            )
        for pos in self.positions:
            session = GameSession(compiled)
            for action in pos.action_history:
                session.submit(action)
            key = position_identity_key(session.state.position, compiled)
            if key != pos.position_key:
                raise ValueError(
                    f"position {pos.index}: replay key mismatch"
                )
            if session.state.position.side_to_move != pos.side_to_move:
                raise ValueError(f"position {pos.index}: side mismatch")
            if session.state.ply_count != pos.ply:
                raise ValueError(f"position {pos.index}: ply mismatch")

    def nonterminal_positions(self, compiled) -> list[DiagnosticPosition]:
        out = []
        for pos in self.positions:
            session = GameSession(compiled)
            for action in pos.action_history:
                session.submit(action)
            if session.result.status.value == "ongoing":
                out.append(pos)
        return out


def _canonical_order_key(action: Action) -> str:
    import json

    return json.dumps(action_to_dict(action), sort_keys=True)


def generate_diagnostic_corpus(
    compiled,
    openings: ArenaOpeningCorpus,
    *,
    count: int,
    seed: int,
    min_plies: int = 2,
    max_plies: int = 40,
    max_attempts: int = 50,
) -> LearningDiagnosticCorpus:
    """Generate ``count`` reachable, non-terminal positions using only Core
    legal actions and deterministic per-position PRNGs."""
    openings.validate(compiled)
    base_rng = random.Random(seed)
    positions: list[DiagnosticPosition] = []
    candidates = list(openings.openings)
    index = 0
    while len(positions) < count:
        opening = candidates[index % len(candidates)]
        attempt = 0
        generated = None
        while attempt < max_attempts:
            target = base_rng.randint(min_plies, max_plies)
            pos_seed = seed * 10_000 + index * 100 + attempt
            rng = random.Random(pos_seed)
            session = GameSession(compiled)
            for action in opening.actions:
                session.submit(action)
            history = list(opening.actions)
            ok = True
            while len(history) < target:
                legal = session.legal_actions()
                if not legal or session.result.status.value != "ongoing":
                    ok = False
                    break
                ordered = sorted(legal, key=_canonical_order_key)
                action = ordered[rng.randrange(len(ordered))]
                session.submit(action)
                history.append(action)
            if ok and session.result.status.value == "ongoing":
                generated = DiagnosticPosition(
                    index=index,
                    action_history=tuple(history),
                    position_key=position_identity_key(session.state.position, compiled),
                    side_to_move=session.state.position.side_to_move,
                    ply=session.state.ply_count,
                )
                break
            attempt += 1
        if generated is None:
            raise RuntimeError(
                f"could not generate a non-terminal diagnostic position for "
                f"index {index} after {max_attempts} attempts"
            )
        positions.append(generated)
        index += 1
    return LearningDiagnosticCorpus(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        source_opening_corpus_id=openings.corpus_id,
        seed=seed,
        positions=tuple(positions),
    )


# ---------------------------------------------------------------- TD signal


@dataclass(frozen=True, slots=True)
class TDUpdateRecord:
    trajectory_id: str
    game_id: int
    ply: int
    delta: float
    abs_delta: float
    value_before: float
    value_next: float
    terminal_target: float | None
    feature_norm: float
    trace_norm: float
    update_l2: float
    terminal_result: str
    perspective: int


def td_signal_diagnostics(trajectories, checkpoint, config: TDLeafConfig):
    """Recompute the frozen TDLeaf math per update point and return records
    plus a summary.  The recomputed weight deltas are verified (in tests) to
    match ``tdleaf_update`` exactly, proving the instrumentation does not
    change the learner."""
    value_scale = config.value_scale or checkpoint.value_scale
    alpha = config.alpha or 0.01 * max(checkpoint.reference_median, 1.0)
    records: list[TDUpdateRecord] = []
    board_delta: dict[str, float] = {}
    hand_delta: dict[str, float] = {}
    for game_id, trajectory in enumerate(trajectories):
        points = trajectory.points
        if not points:
            continue
        values = [
            math.tanh(
                linear_value(
                    trajectory.leaf_features_at(p),
                    checkpoint.board_weights,
                    checkpoint.hand_weights,
                )
                / value_scale
            )
            for p in points
        ]
        elig_board: dict[str, float] = {}
        elig_hand: dict[str, float] = {}
        for t, point in enumerate(points):
            u_t = values[t]
            u_next = (
                trajectory.terminal_z
                if t == len(points) - 1
                else values[t + 1]
            )
            delta = u_next - u_t
            grad_scale = (1.0 - u_t * u_t) / value_scale
            features = trajectory.leaf_features_at(point)
            feature_norm = math.sqrt(
                sum(v * v for v in features.array())
            )
            for tid, bc in zip(trajectory.type_ids, point.leaf_feature_board):
                elig_board[tid] = (
                    config.lambd * elig_board.get(tid, 0.0) + grad_scale * bc
                )
            for tid, hc in zip(trajectory.type_ids, point.leaf_feature_hand):
                elig_hand[tid] = (
                    config.lambd * elig_hand.get(tid, 0.0) + grad_scale * hc
                )
            trace_norm = math.sqrt(
                sum(v * v for v in list(elig_board.values()) + list(elig_hand.values()))
            )
            update_l2 = 0.0
            for tid in trajectory.type_ids:
                bd = alpha * delta * elig_board.get(tid, 0.0)
                hd = alpha * delta * elig_hand.get(tid, 0.0)
                board_delta[tid] = board_delta.get(tid, 0.0) + bd
                hand_delta[tid] = hand_delta.get(tid, 0.0) + hd
                update_l2 += bd * bd + hd * hd
            records.append(
                TDUpdateRecord(
                    trajectory_id=trajectory.trajectory_id,
                    game_id=game_id,
                    ply=point.ply,
                    delta=delta,
                    abs_delta=abs(delta),
                    value_before=u_t,
                    value_next=u_next,
                    terminal_target=(
                        trajectory.terminal_z if t == len(points) - 1 else None
                    ),
                    feature_norm=feature_norm,
                    trace_norm=trace_norm,
                    update_l2=math.sqrt(update_l2),
                    terminal_result=trajectory.terminal,
                    perspective=0,
                )
            )
    deltas = [r.delta for r in records]
    if deltas:
        ordered = sorted(deltas)
        summary = {
            "n": len(records),
            "mean_delta": sum(deltas) / len(deltas),
            "median_delta": _percentile(ordered, 0.50),
            "std_delta": _std(deltas),
            "mean_abs_delta": sum(r.abs_delta for r in records) / len(records),
            "percentiles": {
                p: _percentile(ordered, p / 100.0)
                for p in (10, 25, 50, 75, 90, 95, 99)
            },
            "positive_fraction": sum(1 for d in deltas if d > 0) / len(deltas),
            "zero_fraction": sum(1 for d in deltas if d == 0.0) / len(deltas),
            "negative_fraction": sum(1 for d in deltas if d < 0) / len(deltas),
            "mean_feature_norm": sum(r.feature_norm for r in records) / len(records),
            "mean_trace_norm": sum(r.trace_norm for r in records) / len(records),
            "mean_update_l2": sum(r.update_l2 for r in records) / len(records),
            "weight_l2_delta": math.sqrt(
                sum(v * v for v in board_delta.values())
                + sum(v * v for v in hand_delta.values())
            ),
        }
    else:
        summary = {"n": 0}
    return records, summary, dict(board_delta), dict(hand_delta)


def _percentile(ordered: list[float], q: float) -> float:
    if not ordered:
        return 0.0
    idx = int(q * (len(ordered) - 1))
    return ordered[idx]


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def _delta_summary(deltas: list[float]) -> dict:
    if not deltas:
        return {"n": 0}
    ordered = sorted(deltas)
    return {
        "n": len(deltas),
        "mean_delta": sum(deltas) / len(deltas),
        "mean_abs_delta": sum(abs(d) for d in deltas) / len(deltas),
        "positive_fraction": sum(1 for d in deltas if d > 0) / len(deltas),
        "zero_fraction": sum(1 for d in deltas if d == 0.0) / len(deltas),
        "negative_fraction": sum(1 for d in deltas if d < 0) / len(deltas),
        "p50": _percentile(ordered, 0.5),
    }


def _group_by_game(records) -> dict:
    groups: dict[int, list[float]] = {}
    for r in records:
        groups.setdefault(r.game_id, []).append(r.delta)
    return {str(k): _delta_summary(v) for k, v in sorted(groups.items())}


def _phase_of(ply: int) -> str:
    if ply <= 6:
        return "opening"
    if ply <= 12:
        return "early"
    if ply <= 24:
        return "mid"
    return "late"


def _group_by_phase(records) -> dict:
    groups: dict[str, list[float]] = {}
    for r in records:
        groups.setdefault(_phase_of(r.ply), []).append(r.delta)
    return {k: _delta_summary(v) for k, v in sorted(groups.items())}


def _group_by_outcome(records) -> dict:
    groups: dict[str, list[float]] = {}
    for r in records:
        groups.setdefault(r.terminal_result, []).append(r.delta)
    return {k: _delta_summary(v) for k, v in sorted(groups.items())}


# ------------------------------------------------------- feature bottleneck


def feature_bottleneck_diagnostics(compiled, corpus):
    type_ids = non_anchor_type_ids(compiled)
    vectors: list[tuple[str, list[int]]] = []
    for pos in corpus.positions:
        session = GameSession(compiled)
        for action in pos.action_history:
            session.submit(action)
        features = material_features(
            session.state.position, type_ids, perspective=0
        )
        vectors.append((pos.position_key, list(features.array())))
    unique_position_keys = len({k for k, _ in vectors})
    unique = set(tuple(v) for _, v in vectors)
    counts: dict[tuple, int] = {}
    for _k, v in vectors:
        counts[tuple(v)] = counts.get(tuple(v), 0) + 1
    groups = sorted(
        [(c, v) for v, c in counts.items() if c > 1], reverse=True
    )
    total = len(vectors)
    zero = sum(1 for _k, v in vectors if all(x == 0 for x in v))
    collision_positions = sum(c for c, _ in groups)
    return {
        "total_positions": total,
        "unique_position_keys": unique_position_keys,
        "unique_feature_vectors": len(unique),
        "unique_ratio": len(unique) / total if total else 0.0,
        "collision_group_count": len(groups),
        "max_group_size": groups[0][0] if groups else 0,
        "median_group_size": _percentile(sorted(c for c, _ in groups), 0.5)
        if groups
        else 0,
        "collision_positions_fraction": collision_positions / total if total else 0.0,
        "zero_vector_fraction": zero / total if total else 0.0,
        "example_groups": [
            {"size": c, "vector": list(v)} for c, v in groups[:5]
        ],
    }


# ------------------------------------------------- evaluator / search / teacher


def _engine_for(compiled, native_rules, checkpoint, tt_mb):
    from types import SimpleNamespace

    profile = SimpleNamespace(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        promotion_gain_by_type={pt.type_id: 0 for pt in compiled.piece_types},
        evaluator_version=checkpoint.evaluator_version,
    )
    eval_tables = compile_native_evaluation(
        native_rules, profile, EvaluationConfig(), material_override=checkpoint
    )
    return NativeSearchEngine(compiled, native_rules, eval_tables, tt_mb)


def _search_position(compiled, native_rules, checkpoint, pos, nodes, tt_mb=8):
    """Fresh-engine search of one corpus position; returns best action/score."""
    from ..native.adapter import pack_native_search_position

    session = GameSession(compiled)
    for action in pos.action_history:
        session.submit(action)
    engine = _engine_for(compiled, native_rules, checkpoint, tt_mb)
    result = engine.search(
        session,
        SearchLimits(
            max_depth=64, max_nodes=nodes, quiescence_max_depth=0
        ),
    )
    return result, session


def evaluator_change_diagnostics(compiled, checkpoints, corpus):
    """V_g(s) per checkpoint over the corpus and Delta-V stats vs Gen0."""
    type_ids = non_anchor_type_ids(compiled)
    gen0 = checkpoints[0]
    values = {g: [] for g in range(len(checkpoints))}
    for pos in corpus.positions:
        session = GameSession(compiled)
        for action in pos.action_history:
            session.submit(action)
        features = material_features(
            session.state.position, type_ids, perspective=0
        )
        for g, checkpoint in enumerate(checkpoints):
            values[g].append(
                linear_value(
                    features, checkpoint.board_weights, checkpoint.hand_weights
                )
            )
    out = {}
    for g in range(1, len(checkpoints)):
        deltas = [
            values[g][i] - values[0][i] for i in range(len(values[0]))
        ]
        ordered = sorted(abs(d) for d in deltas)
        out[str(g)] = {
            "mean_delta": sum(deltas) / len(deltas) if deltas else 0.0,
            "mean_abs_delta": sum(abs(d) for d in deltas) / len(deltas)
            if deltas
            else 0.0,
            "median_abs_delta": _percentile(ordered, 0.5),
            "std_delta": _std(deltas),
            "max_abs_delta": max((abs(d) for d in deltas), default=0.0),
            "exactly_unchanged_fraction": sum(
                1 for d in deltas if d == 0.0
            )
            / len(deltas)
            if deltas
            else 0.0,
            "sign_flip_fraction": sum(
                1
                for i in range(len(deltas))
                if values[0][i] * values[g][i] < 0
            )
            / len(deltas)
            if deltas
            else 0.0,
            "weight_l2": math.sqrt(
                sum(
                    v * v
                    for v in list(checkpoints[g].board_weights.values())
                    + list(checkpoints[g].hand_weights.values())
                )
            ),
            "delta_weight_l2": math.sqrt(
                sum(
                    (
                        checkpoints[g].board_weights[t]
                        - checkpoints[0].board_weights[t]
                    )
                    ** 2
                    for t in checkpoints[0].board_weights
                )
                + sum(
                    (
                        checkpoints[g].hand_weights[t]
                        - checkpoints[0].hand_weights[t]
                    )
                    ** 2
                    for t in checkpoints[0].hand_weights
                )
            ),
        }
    return out


def search_sensitivity_diagnostics(
    compiled, native_rules, checkpoints, corpus, nodes=4000
):
    """Best-action flips and score changes per generation vs Gen0."""
    results = {}
    for g, checkpoint in enumerate(checkpoints):
        per_pos = []
        for pos in corpus.positions:
            result, session = _search_position(
                compiled, native_rules, checkpoint, pos, nodes
            )
            per_pos.append(
                {
                    "index": pos.index,
                    "best_action": str(result.action),
                    "score": result.score,
                    "pv": [str(a) for a in result.principal_variation],
                    "nodes": result.nodes,
                    "status": result.termination_reason,
                }
            )
        results[str(g)] = per_pos
    out = {}
    for g in range(1, len(checkpoints)):
        flips = sum(
            1
            for i in range(len(results["0"]))
            if results[str(g)][i]["best_action"]
            != results["0"][i]["best_action"]
        )
        score_deltas = [
            results[str(g)][i]["score"] - results["0"][i]["score"]
            for i in range(len(results["0"]))
        ]
        pv_first_flips = sum(
            1
            for i in range(len(results["0"]))
            if (results[str(g)][i]["pv"] or [None])[0]
            != (results["0"][i]["pv"] or [None])[0]
        )
        n = len(results["0"])
        out[str(g)] = {
            "positions": n,
            "move_flip_rate": flips / n if n else 0.0,
            "pv_first_disagreement_rate": pv_first_flips / n if n else 0.0,
            "mean_score_delta": sum(score_deltas) / n if n else 0.0,
            "mean_abs_score_delta": sum(abs(d) for d in score_deltas) / n
            if n
            else 0.0,
        }
    return out, results


def teacher_benchmark(
    compiled,
    native_rules,
    checkpoints,
    corpus,
    student_nodes=4000,
    teacher_nodes=40000,
    max_positions: int | None = None,
):
    """Best-move agreement of student (gen_g at student_nodes) vs teacher
    (Gen0 at teacher_nodes); also teacher self-agreement at 2x budget."""
    teacher_positions = corpus.nonterminal_positions(compiled)
    if max_positions is not None:
        teacher_positions = teacher_positions[:max_positions]
    teacher_results = {}
    for budget in (teacher_nodes, teacher_nodes * 2):
        results = []
        for pos in teacher_positions:
            result, _session = _search_position(
                compiled, native_rules, checkpoints[0], pos, budget
            )
            results.append(str(result.action))
        teacher_results[str(budget)] = results
    self_agreement = sum(
        1
        for a, b in zip(
            teacher_results[str(teacher_nodes)],
            teacher_results[str(teacher_nodes * 2)],
        )
        if a == b
    ) / len(teacher_positions)
    agreement = {}
    for g in range(len(checkpoints)):
        student = []
        for pos in teacher_positions:
            result, _session = _search_position(
                compiled, native_rules, checkpoints[g], pos, student_nodes
            )
            student.append(str(result.action))
        n = len(teacher_positions)
        agreement[str(g)] = sum(
            1 for a, b in zip(student, teacher_results[str(teacher_nodes)]) if a == b
        ) / n
    return {
        "positions": len(teacher_positions),
        "student_nodes": student_nodes,
        "teacher_nodes": teacher_nodes,
        "teacher_self_agreement": self_agreement,
        "best_move_agreement": agreement,
    }


def arena_sensitivity(
    compiled,
    native_rules,
    checkpoint,
    openings,
    budget_pairs=(("4000", "2000"), ("4000", "1000"), ("4000", "500")),
    pairs=16,
):
    """Paired arena between the same checkpoint at a strong node budget and
    the same checkpoint at a weak node budget.  If the arena is sensitive,
    the weak side scores < 0.5; all-0.5 proves insensitivity to the strength
    difference (the R2 full-game issue)."""
    from .arena import ArenaExecutionError

    def play(session, engine, nodes):
        legal = session.legal_actions()
        if not legal:
            raise ArenaExecutionError("no legal moves on ongoing position")
        result = engine.search(
            session,
            SearchLimits(
                max_depth=64, max_nodes=nodes, quiescence_max_depth=0
            ),
        )
        if result.action is None:
            raise ArenaExecutionError("engine returned no action")
        session.submit(result.action)

    def one_pair(opening, weak_owner: int, strong_nodes: int, weak_nodes: int):
        """Returns weak-side points for the given color assignment."""
        session = GameSession(compiled)
        for action in opening.actions:
            session.submit(action)
        strong_engine = _engine_for(compiled, native_rules, checkpoint, 8)
        weak_engine = _engine_for(compiled, native_rules, checkpoint, 8)
        while session.result.status.value == "ongoing":
            side = session.state.position.side_to_move
            if side == weak_owner:
                play(session, weak_engine, weak_nodes)
            else:
                play(session, strong_engine, strong_nodes)
        winner = session.result.winner
        if winner is None:
            return 0.5
        return 1.0 if winner == weak_owner else 0.0

    out = {}
    for strong, weak in budget_pairs:
        strong_n = int(strong)
        weak_n = int(weak)
        pair_scores = []
        for pair_index in range(pairs):
            opening = openings.openings[pair_index]
            a = one_pair(opening, weak_owner=1, strong_nodes=strong_n, weak_nodes=weak_n)
            b = one_pair(opening, weak_owner=0, strong_nodes=strong_n, weak_nodes=weak_n)
            pair_scores.append((a + b) / 2.0)
        mean = sum(pair_scores) / len(pair_scores)
        low, high = bootstrap_pair_mean_ci(pair_scores)
        out[f"{strong}_vs_{weak}"] = {
            "pairs": len(pair_scores),
            "weak_side_mean_pair_score": mean,
            "bootstrap_low": low,
            "bootstrap_high": high,
            "all_pairs_half": all(s == 0.5 for s in pair_scores),
        }
    return out


# ---------------------------------------------------------------- orchestrator


def load_checkpoints_from_experiment(
    compiled, seed: int, artifacts_dir
) -> list[LearnableMaterialCheckpoint]:
    """Load Gen0..Gen3 checkpoints from a Phase 1.5 experiment directory."""
    import json

    base = Path(artifacts_dir)
    gen0_file = base / f"generation_000.json"
    if gen0_file.exists():
        gen0 = LearnableMaterialCheckpoint.from_dict(
            json.loads(gen0_file.read_text(encoding="utf-8"))
        )
    else:
        gen0 = _gen0_checkpoint(compiled, seed)
    checkpoints = [gen0]
    gen = 1
    while True:
        path = base / f"generation_{gen:03d}.json"
        if not path.exists():
            break
        data = json.loads(path.read_text(encoding="utf-8"))
        checkpoints.append(
            LearnableMaterialCheckpoint.from_dict(data["child"])
        )
        gen += 1
    return checkpoints


def _gen0_checkpoint(compiled, seed):
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    return LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=seed
    )


def run_diagnostics(
    compiled,
    native_rules,
    openings,
    seed: int,
    artifacts_dir,
    *,
    corpus_count: int = 512,
    corpus_seed: int = 42,
    selfplay_cfg: SelfPlayConfig | None = None,
    student_nodes: int = 4000,
    teacher_nodes: int = 40000,
    arena_budgets=("2000", "1000", "500"),
    experiment_dir=None,
) -> dict:
    """Run the full Phase 1.6 diagnostic stack and write machine-readable
    artifacts under ``artifacts_dir``."""
    from pathlib import Path

    out = Path(artifacts_dir)
    out.mkdir(parents=True, exist_ok=True)
    commit = _git_head()
    meta = {
        "schema_version": 1,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "commit": commit,
        "project_version": "0.8.0a3",
        "opening_corpus_id": openings.corpus_id,
    }

    # Diagnostic holdout corpus.
    corpus = generate_diagnostic_corpus(
        compiled, openings, count=corpus_count, seed=corpus_seed
    )
    corpus.validate(compiled)
    (out / "diagnostic_corpus.json").write_text(
        canonical_json(corpus.to_dict()) + "\n", encoding="utf-8"
    )

    if experiment_dir is not None:
        checkpoints = load_checkpoints_from_experiment(
            compiled, seed, Path(experiment_dir)
        )
    else:
        checkpoints = load_checkpoints_from_experiment(compiled, seed, out.parent)
    if len(checkpoints) < 2:
        checkpoints = _train_calibrated_checkpoints(
            compiled, native_rules, seed, selfplay_cfg
        )
    checkpoint_ids = [c.checkpoint_id for c in checkpoints]
    meta["checkpoint_ids"] = checkpoint_ids

    # TD signal (re-run deterministic training to obtain trajectories).
    if selfplay_cfg is None:
        selfplay_cfg = SelfPlayConfig(
            games=8, nodes_per_move=2000, max_depth=12, seed=seed
        )
    trajectories = collect_self_play(
        compiled, native_rules, checkpoints[0], selfplay_cfg
    )
    td_cfg = TDLeafConfig(gamma=1.0, lambd=0.7, alpha=None)
    records, td_summary, _bd, _hd = td_signal_diagnostics(
        trajectories, checkpoints[0], td_cfg
    )
    td_out = {
        "summary": td_summary,
        "by_game": _group_by_game(records),
        "by_phase": _group_by_phase(records),
        "by_outcome": _group_by_outcome(records),
        "per_update_sample": [
            {
                "ply": r.ply,
                "delta": r.delta,
                "abs_delta": r.abs_delta,
                "value_before": r.value_before,
                "value_next": r.value_next,
                "terminal_target": r.terminal_target,
                "feature_norm": r.feature_norm,
                "trace_norm": r.trace_norm,
                "update_l2": r.update_l2,
                "terminal_result": r.terminal_result,
            }
            for r in records[:200]
        ],
        "records_total": len(records),
    }
    (out / "td_signal_summary.json").write_text(
        canonical_json({**meta, **td_out}) + "\n", encoding="utf-8"
    )

    # Feature bottleneck.
    bottleneck = feature_bottleneck_diagnostics(compiled, corpus)
    (out / "feature_bottleneck.json").write_text(
        canonical_json({**meta, **bottleneck}) + "\n", encoding="utf-8"
    )

    # Evaluator change.
    eval_change = evaluator_change_diagnostics(compiled, checkpoints, corpus)
    (out / "evaluator_change.json").write_text(
        canonical_json({**meta, "by_generation": eval_change}) + "\n",
        encoding="utf-8",
    )

    # Search decision sensitivity.
    search, raw_search = search_sensitivity_diagnostics(
        compiled, native_rules, checkpoints, corpus, nodes=student_nodes
    )
    (out / "search_sensitivity.json").write_text(
        canonical_json({**meta, "student_nodes": student_nodes, "by_generation": search})
        + "\n",
        encoding="utf-8",
    )

    # Teacher benchmark.
    teacher = teacher_benchmark(
        compiled,
        native_rules,
        checkpoints,
        corpus,
        student_nodes=student_nodes,
        teacher_nodes=teacher_nodes,
        max_positions=64,
    )
    (out / "teacher_benchmark.json").write_text(
        canonical_json({**meta, **teacher}) + "\n", encoding="utf-8"
    )

    # Arena sensitivity.
    sens = arena_sensitivity(
        compiled,
        native_rules,
        checkpoints[0],
        openings,
        budget_pairs=tuple((f"4000", b) for b in arena_budgets),
    )
    (out / "arena_sensitivity.json").write_text(
        canonical_json({**meta, **sens}) + "\n", encoding="utf-8"
    )

    verdict = {
        "td_signal": _verdict_td(td_summary),
        "representation": _verdict_representation(bottleneck),
        "search_effect": _verdict_search(search),
        "teacher_alignment": _verdict_teacher(teacher),
        "arena_sensitivity": _verdict_arena(sens),
        "next_phase_decision": _verdict_next_phase(
            td_summary, bottleneck, search, teacher, sens
        ),
    }
    (out / "final_verdict.json").write_text(
        canonical_json({**meta, "verdict": verdict}) + "\n", encoding="utf-8"
    )
    return {"meta": meta, "verdict": verdict, "td_summary": td_summary}


def _train_calibrated_checkpoints(compiled, native_rules, seed, selfplay_cfg):
    profile = build_ruleset_profile(compiled, EvaluationConfig())
    gen0 = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=seed
    )
    out = [gen0]
    parent = gen0
    if selfplay_cfg is None:
        selfplay_cfg = SelfPlayConfig(
            games=8, nodes_per_move=2000, max_depth=12, seed=seed
        )
    calibration_trajectories = collect_self_play(
        compiled, native_rules, parent, selfplay_cfg
    )
    nominal = tdleaf_update(
        calibration_trajectories, parent, TDLeafConfig(alpha=None)
    )
    median = parent.reference_median
    nominal_alpha = 0.01 * max(median, 1.0)
    target_l2 = 0.10 * median
    measured_l2 = max(nominal.weight_l2_delta, 1e-9)
    calibrated_alpha = min(
        nominal_alpha * (target_l2 / measured_l2), nominal_alpha * 200.0
    )
    calibrated_alpha = max(calibrated_alpha, nominal_alpha)
    used = calibration_trajectories
    for _ in range(3):
        trajectories = used
        update = tdleaf_update(
            trajectories, parent, TDLeafConfig(alpha=calibrated_alpha)
        )
        child = parent.child_checkpoint(
            board_weights=update.board_weights,
            hand_weights=update.hand_weights,
            games_seen_delta=len(trajectories),
            positions_seen_delta=update.positions_seen,
            training_updates_delta=1,
            training_config_hash="diagnostic-rerun",
            training_seed=seed,
        )
        out.append(child)
        parent = child
        used = collect_self_play(compiled, native_rules, parent, selfplay_cfg)
    return out


def _git_head() -> str:
    import subprocess

    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def _verdict_td(td_summary: dict) -> str:
    if td_summary.get("n", 0) == 0:
        return "INCONCLUSIVE"
    if td_summary["mean_abs_delta"] < 1e-12 and td_summary["max_abs_delta"] < 1e-12:
        return "ABSENT"
    positive = td_summary["positive_fraction"]
    negative = td_summary["negative_fraction"]
    if positive > 0.95 or negative > 0.95:
        return "DEGENERATE"
    return "PRESENT"


def _verdict_representation(bottleneck: dict) -> str:
    if bottleneck["total_positions"] == 0:
        return "INCONCLUSIVE"
    if bottleneck["unique_ratio"] < 0.5 or bottleneck["collision_positions_fraction"] > 0.5:
        return "MATERIAL_BOTTLENECK"
    return "SUFFICIENT_FOR_MEASURED_SIGNAL"


def _verdict_search(search: dict) -> str:
    flips = [search[str(g)]["move_flip_rate"] for g in range(1, len(search) + 1)]
    if all(f == 0.0 for f in flips):
        return "NO_MEASURABLE_DECISION_CHANGE"
    return "DECISIONS_CHANGED"


def _verdict_teacher(teacher: dict) -> str:
    if teacher.get("teacher_self_agreement", 0.0) < 0.8:
        return "TEACHER_UNSTABLE"
    g0 = teacher["best_move_agreement"]["0"]
    g3 = teacher["best_move_agreement"].get("3", g0)
    if g3 > g0 + 0.02:
        return "IMPROVED"
    if g3 < g0 - 0.02:
        return "WORSENED"
    return "UNCHANGED"


def _verdict_arena(sens: dict) -> str:
    values = [v["weak_side_mean_pair_score"] for v in sens.values()]
    if all(v == 0.5 for v in values):
        return "INSENSITIVE"
    if any(v < 0.45 for v in values):
        return "ADEQUATE"
    return "LOW_SENSITIVITY"


def _verdict_next_phase(td, bottleneck, search, teacher, sens) -> str:
    """Decision gate for the next phase, based only on measured evidence."""
    td_present = td.get("n", 0) > 0 and td.get("mean_abs_delta", 0.0) > 1e-12
    representation_bottleneck = (
        bottleneck["unique_ratio"] < 0.5
        or bottleneck["collision_positions_fraction"] > 0.5
    )
    flips = [
        search.get(str(g), {}).get("move_flip_rate", 0.0)
        for g in range(1, len(search) + 1)
    ]
    decisions_changed = any(f > 0.0 for f in flips)
    arena_sensitive = not all(
        v.get("weak_side_mean_pair_score", 0.5) == 0.5 for v in sens.values()
    )
    teacher_changed = teacher.get("teacher_self_agreement", 0.0) < 0.8
    if teacher_changed:
        return "INCONCLUSIVE"
    if td_present and representation_bottleneck and decisions_changed:
        return "PROCEED_TO_PST"
    if not td_present:
        return "FIX_LEARNING_SIGNAL_FIRST"
    if not arena_sensitive:
        return "FIX_MEASUREMENT_FIRST"
    # TD signal present, representation not a severe alias, decisions barely
    # change and the arena is sensitive: the material update does not reach
    # the search decision layer on this ruleset — cannot cleanly attribute
    # the break to one subsystem yet.
    return "INCONCLUSIVE"


def _resolve_cli_profile(args) -> dict:
    """Resolve CLI defaults; ``--smoke`` shrinks the profile so the full
    pipeline can be exercised quickly (48 positions, low search budgets)."""
    if args.smoke:
        defaults = {
            "corpus_count": 48,
            "student_nodes": 500,
            "teacher_nodes": 1500,
            "artifacts": "artifacts/learning_phase1_6_smoke",
        }
    else:
        defaults = {
            "corpus_count": 512,
            "student_nodes": 4000,
            "teacher_nodes": 40000,
            "artifacts": "artifacts/learning_phase1_6",
        }
    return {
        "corpus_count": (
            args.corpus_count if args.corpus_count is not None else defaults["corpus_count"]
        ),
        "student_nodes": (
            args.student_nodes
            if args.student_nodes is not None
            else defaults["student_nodes"]
        ),
        "teacher_nodes": (
            args.teacher_nodes
            if args.teacher_nodes is not None
            else defaults["teacher_nodes"]
        ),
        "artifacts": (
            args.artifacts if args.artifacts is not None else defaults["artifacts"]
        ),
    }


def main(argv=None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(prog="generic_chess.learning.diagnostics")
    parser.add_argument("--ruleset", default="R2_weird_generic")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--corpus-count", type=int, default=None)
    parser.add_argument("--corpus-seed", type=int, default=42)
    parser.add_argument("--student-nodes", type=int, default=None)
    parser.add_argument("--teacher-nodes", type=int, default=None)
    parser.add_argument("--artifacts", default=None)
    parser.add_argument("--experiment-dir", default=None)
    args = parser.parse_args(argv)
    profile = _resolve_cli_profile(args)

    from ..ai.benchmark.audit_suite import standard_ruleset_specs
    from ..ai.benchmark.audit_suite import build_compiled
    from .openings import ArenaOpeningCorpus, generate_arena_openings

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    label_to_fid = {
        "R1_classic_like": "gen_classic_like_4_101",
        "R2_weird_generic": "gen_free_random_4_102",
    }
    fid = label_to_fid[args.ruleset]
    compiled = build_compiled(specs[fid])
    native_rules = compile_native_rules(compiled)
    openings_path = (
        Path(profile["artifacts"]).parent
        / "learning_phase1_5"
        / f"{args.ruleset}_openings.json"
    )
    if openings_path.exists():
        openings = ArenaOpeningCorpus.from_dict(
            json.loads(openings_path.read_text(encoding="utf-8"))
        )
    else:
        openings = generate_arena_openings(
            compiled, count=16, seed=314159, min_plies=2, max_plies=6
        )
    openings.validate(compiled)
    out_dir = Path(profile["artifacts"]) / args.ruleset / f"seed{args.seed}"
    if args.experiment_dir is None:
        candidate = (
            Path("artifacts")
            / "learning_phase1_5"
            / args.ruleset
            / f"{args.ruleset}_seed{args.seed}"
        )
        args.experiment_dir = str(candidate) if candidate.exists() else None
    result = run_diagnostics(
        compiled,
        native_rules,
        openings,
        seed=args.seed,
        artifacts_dir=out_dir,
        corpus_count=profile["corpus_count"],
        corpus_seed=args.corpus_seed,
        student_nodes=profile["student_nodes"],
        teacher_nodes=profile["teacher_nodes"],
        experiment_dir=args.experiment_dir,
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
