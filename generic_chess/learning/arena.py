"""Integrity-preserving paired arena.

Measurement rules:
* every game replays one corpus opening (identical within a pair);
* every game creates **fresh** parent and child engines (TT never crosses
  games);
* engine failures are raised, never counted as draws;
* the primary statistic is the paired score with a pair-level bootstrap CI.
"""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import time

from ..ai.evaluation.config import EvaluationConfig
from ..ai.limits import SearchLimits
from ..core.actions import Action, action_from_dict, action_to_dict
from ..core.identity import position_identity_key
from ..native.compiler import compile_native_evaluation
from ..native.engine import NativeSearchEngine
from ..native.semantic_engine import SemanticSearchEngine
from ..session.session import GameSession
from .material import LearnableMaterialCheckpoint
from .openings import ArenaOpeningCorpus, generate_arena_openings
from .serialization import stable_sha256
from .statistics import bootstrap_pair_mean_ci


class ArenaExecutionError(RuntimeError):
    """Raised when the arena cannot produce a valid measurement."""


class ArenaCapHit(ArenaExecutionError):
    """A hard execution cap stopped a stage before a valid game completed."""

    def __init__(self, cap: str) -> None:
        self.cap = cap
        super().__init__(f"arena execution cap hit: {cap}")


ARENA_PROGRESS_SCHEMA = "generic-chess-arena-progress-v1"
ARENA_GAME_PROGRESS_SCHEMA = "generic-chess-arena-game-progress-v1"


def _trusted_search_elapsed(native_elapsed: float, wall_elapsed: float):
    credible = (
        native_elapsed > 0.0
        and native_elapsed <= max(wall_elapsed * 2.0, wall_elapsed + 1.0)
    )
    return (
        (native_elapsed, "native")
        if credible else (wall_elapsed, "wall_fallback")
    )


@dataclass(frozen=True, slots=True)
class ArenaConfig:
    pairs: int = 10
    nodes_per_move: int = 5000
    max_depth: int = 12
    tt_megabytes: int = 8
    opening_seed: int = 314159
    opening_count: int = 0  # 0 -> use pairs
    min_plies: int = 2
    max_plies: int = 6
    workers: int = 1
    parent_nodes_per_move: int | None = None
    child_nodes_per_move: int | None = None

    def __post_init__(self) -> None:
        if self.pairs <= 0 or self.nodes_per_move <= 0 or self.max_depth <= 0:
            raise ValueError("arena budgets must be positive")
        if self.workers <= 0:
            raise ValueError("arena workers must be positive")
        for role, budget in (
            ("parent", self.parent_nodes_per_move),
            ("child", self.child_nodes_per_move),
        ):
            if budget is not None and budget <= 0:
                raise ValueError(f"{role} nodes_per_move must be positive")


@dataclass(frozen=True, slots=True)
class ArenaExecutionCaps:
    """Hard bounds for one game and one resumable arena stage.

    ``workers`` remains the caller's requested concurrency.  The game-level
    runner applies the stricter lane cap exposed by :meth:`game_lanes`; no
    pair-level worker can create a nested executor.
    """

    per_game_wall_seconds: float | None = None
    per_game_nodes: int | None = None
    per_game_plies: int | None = None
    max_stage_games: int | None = None
    max_concurrent_games: int | None = None
    stage_wall_seconds: float | None = None
    logical_cpu_count: int = os.cpu_count() or 1

    def __post_init__(self) -> None:
        if self.logical_cpu_count <= 0:
            raise ValueError("logical_cpu_count must be positive")
        for name in (
            "per_game_wall_seconds", "per_game_nodes", "per_game_plies",
            "max_stage_games", "max_concurrent_games", "stage_wall_seconds",
        ):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive when provided")

    def game_lanes(self, requested_pairs: int, requested_workers: int) -> int:
        if requested_pairs <= 0 or requested_workers <= 0:
            raise ValueError("arena pair and worker counts must be positive")
        lanes = min(self.logical_cpu_count, 2 * requested_pairs, 16)
        lanes = min(lanes, requested_workers)
        if self.max_concurrent_games is not None:
            lanes = min(lanes, self.max_concurrent_games)
        return max(1, lanes)

    @property
    def has_per_game_caps(self) -> bool:
        return any(
            value is not None for value in (
                self.per_game_wall_seconds,
                self.per_game_nodes,
                self.per_game_plies,
            )
        )


# Short aliases keep the protocol convenient for callers without creating a
# second schema or a second implementation.
ArenaCaps = ArenaExecutionCaps


@dataclass(frozen=True, slots=True)
class ArenaGameResult:
    pair: int
    opening_id: str
    opening_position_key: str
    child_owner: int
    winner: int | None
    result: str
    plies: int
    actions: tuple[Action, ...]
    final_position_key: str
    declaration_id: str | None = None
    search_metrics: tuple[dict, ...] = ()

    @property
    def child_points(self) -> float:
        if self.winner is None:
            return 0.5
        return 1.0 if self.winner == self.child_owner else 0.0


@dataclass(frozen=True, slots=True)
class ArenaPairResult:
    pair_index: int
    opening_id: str
    game_child_owner0: ArenaGameResult
    game_child_owner1: ArenaGameResult

    @property
    def child_pair_score(self) -> float:
        return (
            self.game_child_owner0.child_points
            + self.game_child_owner1.child_points
        ) / 2.0


@dataclass(frozen=True, slots=True)
class ArenaSummary:
    pair_count: int
    pair_scores: tuple[float, ...]
    mean_pair_score: float
    child_better_pairs: int
    tied_pairs: int
    child_worse_pairs: int
    bootstrap_low: float
    bootstrap_high: float
    # Descriptive game-level aggregates.
    game_wins: int
    game_draws: int
    game_losses: int
    game_score_rate: float
    pairs: tuple[ArenaPairResult, ...]


def _engine_for(compiled, native_rules, checkpoint, tt_mb):
    from ..rules.ir import CompiledSemanticRuleset

    if isinstance(compiled, CompiledSemanticRuleset):
        return SemanticSearchEngine(
            compiled, native_rules, checkpoint=checkpoint,
            tt_megabytes=tt_mb,
        )
    eval_tables = compile_native_evaluation(
        native_rules,
        _dummy_profile(compiled, checkpoint),
        EvaluationConfig(),
        material_override=checkpoint,
    )
    return NativeSearchEngine(compiled, native_rules, eval_tables, tt_mb)


def _dummy_profile(compiled, checkpoint):
    from types import SimpleNamespace

    return SimpleNamespace(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        promotion_gain_by_type={pt.type_id: 0 for pt in compiled.piece_types},
        evaluator_version=checkpoint.evaluator_version,
    )


def _play_one_game(
    compiled,
    native_rules,
    parent,
    child,
    *,
    opening,
    child_owner: int,
    config: ArenaConfig,
    capture_search_metrics: bool = False,
    execution_caps: ArenaExecutionCaps | None = None,
) -> ArenaGameResult:
    """Replay ``opening``, then play one game with fresh engines."""
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    opening_key = position_identity_key(session.state.position, compiled)
    parent_engine = _engine_for(
        compiled, native_rules, parent, config.tt_megabytes
    )
    child_engine = _engine_for(
        compiled, native_rules, child, config.tt_megabytes
    )
    actions: list[Action] = []
    plies = 0
    searched_nodes = 0
    game_started = time.perf_counter()
    declaration_id = None
    search_metrics = []
    while session.result.status.value == "ongoing":
        if execution_caps is not None:
            if (
                execution_caps.per_game_wall_seconds is not None
                and time.perf_counter() - game_started
                >= execution_caps.per_game_wall_seconds
            ):
                raise ArenaCapHit("per_game_wall_seconds")
            if (
                execution_caps.per_game_plies is not None
                and plies >= execution_caps.per_game_plies
            ):
                raise ArenaCapHit("per_game_plies")
        legal = session.legal_actions()
        if not legal:
            raise ArenaExecutionError(
                "Core reports no legal moves but the session is ongoing"
            )
        side = session.state.position.side_to_move
        engine = child_engine if side == child_owner else parent_engine
        role = "child" if side == child_owner else "parent"
        nodes_per_move = (
            config.child_nodes_per_move if role == "child"
            else config.parent_nodes_per_move
        ) or config.nodes_per_move
        if execution_caps is not None and execution_caps.per_game_nodes is not None:
            remaining_nodes = execution_caps.per_game_nodes - searched_nodes
            if remaining_nodes <= 0:
                raise ArenaCapHit("per_game_nodes")
            nodes_per_move = min(nodes_per_move, remaining_nodes)
        wall_started = time.perf_counter()
        result = engine.search(
            session,
            SearchLimits(
                max_depth=config.max_depth,
                max_nodes=nodes_per_move,
                quiescence_max_depth=0,
            ),
        )
        wall_elapsed = time.perf_counter() - wall_started
        if (
            execution_caps is not None
            and execution_caps.per_game_wall_seconds is not None
            and time.perf_counter() - game_started
            >= execution_caps.per_game_wall_seconds
        ):
            raise ArenaCapHit("per_game_wall_seconds")
        searched_nodes += int(getattr(result, "nodes", 0))
        searched_nodes += int(getattr(result, "qnodes", 0))
        if (
            execution_caps is not None
            and execution_caps.per_game_nodes is not None
            and searched_nodes > execution_caps.per_game_nodes
        ):
            raise ArenaCapHit("per_game_nodes")
        if capture_search_metrics:
            native_elapsed = float(result.elapsed_seconds)
            elapsed, elapsed_source = _trusted_search_elapsed(
                native_elapsed, wall_elapsed
            )
            search_metrics.append({
                "side_to_move": side,
                "engine_role": role,
                "nodes_budget": nodes_per_move,
                "score": int(result.score),
                "nodes": int(result.nodes),
                "elapsed_seconds": elapsed,
                "elapsed_source": elapsed_source,
                "nps": (float(result.nodes) / elapsed if elapsed > 0.0 else None),
                "completed_depth": int(result.completed_depth),
                "selective_depth": int(result.selective_depth),
                "termination_reason": str(result.termination_reason),
                "used_fallback": bool(result.used_fallback),
                "decision_kind": (
                    "declaration"
                    if getattr(result, "declaration_id", None) is not None
                    else "action"
                ),
            })
        if getattr(result, "declaration_id", None) is not None:
            declaration_id = result.declaration_id
            session.declare(declaration_id)
            break
        if result.action is None:
            raise ArenaExecutionError(
                "engine returned no action on an ongoing position "
                f"(termination_reason={result.termination_reason})"
            )
        session.submit(result.action)
        actions.append(result.action)
        plies += 1
    return ArenaGameResult(
        pair=opening.index,
        opening_id=opening.final_position_key,
        opening_position_key=opening_key,
        child_owner=child_owner,
        winner=session.result.winner,
        result=session.result.status.value,
        plies=plies,
        actions=tuple(actions),
        final_position_key=position_identity_key(session.state.position, compiled),
        declaration_id=declaration_id,
        search_metrics=tuple(search_metrics),
    )


def _prepare_arena(
    compiled,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
    openings: ArenaOpeningCorpus | None = None,
) -> ArenaOpeningCorpus:
    parent.validate_ruleset(compiled)
    child.validate_ruleset(compiled)
    if openings is None:
        openings = generate_arena_openings(
            compiled,
            count=config.opening_count or config.pairs,
            seed=config.opening_seed,
            min_plies=config.min_plies,
            max_plies=config.max_plies,
        )
    openings.validate(compiled)
    if len(openings.openings) < config.pairs:
        raise ValueError(
            f"opening corpus has {len(openings.openings)} openings but "
            f"{config.pairs} pairs requested"
        )
    return openings


def _play_pair(
    compiled,
    native_rules,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
    openings: ArenaOpeningCorpus,
    pair_index: int,
    *,
    capture_search_metrics: bool = False,
) -> ArenaPairResult:
    opening = openings.openings[pair_index]
    game_child_owner0 = _play_one_game(
        compiled, native_rules, parent, child,
        opening=opening, child_owner=0, config=config,
        capture_search_metrics=capture_search_metrics,
    )
    game_child_owner1 = _play_one_game(
        compiled, native_rules, parent, child,
        opening=opening, child_owner=1, config=config,
        capture_search_metrics=capture_search_metrics,
    )
    return ArenaPairResult(
        pair_index=pair_index,
        opening_id=opening.final_position_key,
        game_child_owner0=game_child_owner0,
        game_child_owner1=game_child_owner1,
    )


def _summarize_pairs(pairs: list[ArenaPairResult]) -> ArenaSummary:
    pairs.sort(key=lambda pair: pair.pair_index)
    game_wins = game_draws = game_losses = 0
    for pair in pairs:
        game_child_owner0 = pair.game_child_owner0
        game_child_owner1 = pair.game_child_owner1
        game_wins += sum(
            1 for g in (game_child_owner0, game_child_owner1) if g.child_points == 1.0
        )
        game_draws += sum(
            1 for g in (game_child_owner0, game_child_owner1) if g.child_points == 0.5
        )
        game_losses += sum(
            1 for g in (game_child_owner0, game_child_owner1) if g.child_points == 0.0
        )

    pair_scores = tuple(p.child_pair_score for p in pairs)
    mean = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
    better = sum(1 for s in pair_scores if s > 0.5)
    tied = sum(1 for s in pair_scores if s == 0.5)
    worse = sum(1 for s in pair_scores if s < 0.5)
    low, high = bootstrap_pair_mean_ci(list(pair_scores))
    total_games = game_wins + game_draws + game_losses
    return ArenaSummary(
        pair_count=len(pairs),
        pair_scores=pair_scores,
        mean_pair_score=mean,
        child_better_pairs=better,
        tied_pairs=tied,
        child_worse_pairs=worse,
        bootstrap_low=low,
        bootstrap_high=high,
        game_wins=game_wins,
        game_draws=game_draws,
        game_losses=game_losses,
        game_score_rate=(
            (game_wins + 0.5 * game_draws) / total_games if total_games else 0.0
        ),
        pairs=tuple(pairs),
    )


def _game_to_dict(game: ArenaGameResult) -> dict:
    payload = {
        "pair": game.pair,
        "opening_id": game.opening_id,
        "opening_position_key": game.opening_position_key,
        "child_owner": game.child_owner,
        "winner": game.winner,
        "result": game.result,
        "plies": game.plies,
        "actions": [action_to_dict(action) for action in game.actions],
        "final_position_key": game.final_position_key,
        "declaration_id": game.declaration_id,
    }
    if game.search_metrics:
        payload["search_metrics"] = list(game.search_metrics)
    return payload


def _game_from_dict(data: dict) -> ArenaGameResult:
    required = {
        "pair", "opening_id", "opening_position_key", "child_owner", "winner",
        "result", "plies", "actions", "final_position_key", "declaration_id",
    }
    if set(data) not in (required, required | {"search_metrics"}):
        raise ValueError("arena game fields do not match the progress schema")
    winner = data["winner"]
    if winner not in (None, 0, 1) or data["child_owner"] not in (0, 1):
        raise ValueError("arena game owner/winner is invalid")
    return ArenaGameResult(
        pair=int(data["pair"]),
        opening_id=str(data["opening_id"]),
        opening_position_key=str(data["opening_position_key"]),
        child_owner=int(data["child_owner"]),
        winner=winner,
        result=str(data["result"]),
        plies=int(data["plies"]),
        actions=tuple(action_from_dict(action) for action in data["actions"]),
        final_position_key=str(data["final_position_key"]),
        declaration_id=(
            None if data["declaration_id"] is None else str(data["declaration_id"])
        ),
        search_metrics=tuple(dict(row) for row in data.get("search_metrics", ())),
    )


def _pair_to_dict(pair: ArenaPairResult, identity_sha256: str) -> dict:
    return {
        "schema": ARENA_PROGRESS_SCHEMA,
        "identity_sha256": identity_sha256,
        "pair_index": pair.pair_index,
        "opening_id": pair.opening_id,
        "game_child_owner0": _game_to_dict(pair.game_child_owner0),
        "game_child_owner1": _game_to_dict(pair.game_child_owner1),
    }


def _pair_from_dict(data: dict, *, identity_sha256: str) -> ArenaPairResult:
    required = {
        "schema", "identity_sha256", "pair_index", "opening_id",
        "game_child_owner0", "game_child_owner1",
    }
    if set(data) != required or data.get("schema") != ARENA_PROGRESS_SCHEMA:
        raise ValueError("arena pair fields do not match the progress schema")
    if data.get("identity_sha256") != identity_sha256:
        raise ValueError("arena pair identity does not match the manifest")
    pair = ArenaPairResult(
        pair_index=int(data["pair_index"]),
        opening_id=str(data["opening_id"]),
        game_child_owner0=_game_from_dict(data["game_child_owner0"]),
        game_child_owner1=_game_from_dict(data["game_child_owner1"]),
    )
    if (
        pair.game_child_owner0.child_owner != 0
        or pair.game_child_owner1.child_owner != 1
        or pair.game_child_owner0.opening_id != pair.opening_id
        or pair.game_child_owner1.opening_id != pair.opening_id
        or pair.game_child_owner0.opening_position_key
        != pair.game_child_owner1.opening_position_key
    ):
        raise ValueError("arena pair is incomplete or internally inconsistent")
    return pair


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _validate_replayed_game(compiled, opening, game: ArenaGameResult) -> None:
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    if position_identity_key(session.state.position, compiled) != game.opening_position_key:
        raise ValueError("arena game opening position does not replay")
    if len(game.actions) != game.plies:
        raise ValueError("arena game ply count does not match its actions")
    for index, action in enumerate(game.actions):
        if game.search_metrics:
            metric = game.search_metrics[index]
            if (
                metric.get("side_to_move") != session.state.position.side_to_move
                or metric.get("decision_kind") != "action"
            ):
                raise ValueError("arena game search telemetry does not replay")
        if action not in session.legal_actions():
            raise ValueError("arena game contains an illegal action")
        session.submit(action)
    if game.declaration_id is not None:
        if game.search_metrics:
            metric = game.search_metrics[-1]
            if (
                len(game.search_metrics) != game.plies + 1
                or metric.get("side_to_move") != session.state.position.side_to_move
                or metric.get("decision_kind") != "declaration"
            ):
                raise ValueError("arena declaration telemetry does not replay")
        session.declare(game.declaration_id)
    elif game.search_metrics and len(game.search_metrics) != game.plies:
        raise ValueError("arena game search telemetry count does not match plies")
    if (
        session.result.status.value != game.result
        or session.result.winner != game.winner
        or position_identity_key(session.state.position, compiled)
        != game.final_position_key
    ):
        raise ValueError("arena game result does not replay")


def _progress_identity(
    compiled,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
    openings: ArenaOpeningCorpus,
    *,
    capture_search_metrics: bool = False,
) -> dict:
    opening_rows = openings.to_dict()["openings"][:config.pairs]
    identity = {
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "parent_checkpoint_id": parent.checkpoint_id,
        "child_checkpoint_id": child.checkpoint_id,
        "config": asdict(config),
        "ordered_openings": opening_rows,
    }
    if capture_search_metrics:
        identity["capture_search_metrics"] = True
    return identity


def run_arena(
    compiled,
    native_rules,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
    openings: ArenaOpeningCorpus | None = None,
    *,
    capture_search_metrics: bool = False,
) -> ArenaSummary:
    """Paired matches over a fixed evaluator-neutral opening corpus."""
    openings = _prepare_arena(compiled, parent, child, config, openings)
    indexes = range(config.pairs)
    def execute(index: int) -> ArenaPairResult:
        args = (compiled, native_rules, parent, child, config, openings, index)
        if capture_search_metrics:
            return _play_pair(*args, capture_search_metrics=True)
        return _play_pair(*args)

    if config.workers == 1:
        pairs = [execute(index) for index in indexes]
    else:
        with ThreadPoolExecutor(max_workers=config.workers) as pool:
            pairs = list(pool.map(execute, indexes))
    return _summarize_pairs(pairs)


def run_arena_resumable(
    compiled,
    native_rules,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
    *,
    progress_dir: str | Path,
    openings: ArenaOpeningCorpus | None = None,
    capture_search_metrics: bool = False,
) -> ArenaSummary:
    """Run an arena while atomically checkpointing complete swapped-color pairs."""
    openings = _prepare_arena(compiled, parent, child, config, openings)
    directory = Path(progress_dir)
    directory.mkdir(parents=True, exist_ok=True)
    identity = _progress_identity(
        compiled, parent, child, config, openings,
        capture_search_metrics=capture_search_metrics,
    )
    identity_sha256 = stable_sha256(identity)
    expected_manifest = {
        "schema": ARENA_PROGRESS_SCHEMA,
        "identity_sha256": identity_sha256,
        "identity": identity,
    }
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        try:
            actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArenaExecutionError("arena progress manifest is corrupt") from exc
        if actual_manifest != expected_manifest:
            raise ArenaExecutionError("arena progress identity does not match this run")
    else:
        _atomic_write_json(manifest_path, expected_manifest)

    completed: dict[int, ArenaPairResult] = {}

    def require_telemetry(pair: ArenaPairResult) -> None:
        if capture_search_metrics and (
            not pair.game_child_owner0.search_metrics
            or not pair.game_child_owner1.search_metrics
        ):
            raise ArenaExecutionError(
                "arena progress pair is missing requested search telemetry"
            )

    for pair_path in directory.glob("pair-*.json"):
        try:
            data = json.loads(pair_path.read_text(encoding="utf-8"))
            pair = _pair_from_dict(data, identity_sha256=identity_sha256)
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ArenaExecutionError(f"arena progress pair is corrupt: {pair_path.name}") from exc
        expected_name = f"pair-{pair.pair_index:06d}.json"
        if pair_path.name != expected_name or not 0 <= pair.pair_index < config.pairs:
            raise ArenaExecutionError(f"arena progress pair has invalid index: {pair_path.name}")
        expected_opening = openings.openings[pair.pair_index]
        if (
            pair.opening_id != expected_opening.final_position_key
            or pair.game_child_owner0.pair != expected_opening.index
            or pair.game_child_owner1.pair != expected_opening.index
        ):
            raise ArenaExecutionError(f"arena progress opening mismatch: {pair_path.name}")
        try:
            _validate_replayed_game(compiled, expected_opening, pair.game_child_owner0)
            _validate_replayed_game(compiled, expected_opening, pair.game_child_owner1)
        except Exception as exc:
            raise ArenaExecutionError(
                f"arena progress game does not replay: {pair_path.name}"
            ) from exc
        if pair.pair_index in completed:
            raise ArenaExecutionError(f"conflicting arena progress pair: {pair.pair_index}")
        require_telemetry(pair)
        completed[pair.pair_index] = pair

    missing = [index for index in range(config.pairs) if index not in completed]
    def execute(index: int) -> ArenaPairResult:
        args = (compiled, native_rules, parent, child, config, openings, index)
        if capture_search_metrics:
            return _play_pair(*args, capture_search_metrics=True)
        return _play_pair(*args)

    if config.workers == 1:
        produced = (execute(index) for index in missing)
        for pair in produced:
            require_telemetry(pair)
            _atomic_write_json(
                directory / f"pair-{pair.pair_index:06d}.json",
                _pair_to_dict(pair, identity_sha256),
            )
            completed[pair.pair_index] = pair
    else:
        with ThreadPoolExecutor(max_workers=config.workers) as pool:
            futures = {pool.submit(execute, index): index for index in missing}
            for future in as_completed(futures):
                pair = future.result()
                require_telemetry(pair)
                _atomic_write_json(
                    directory / f"pair-{pair.pair_index:06d}.json",
                    _pair_to_dict(pair, identity_sha256),
                )
                completed[pair.pair_index] = pair
    return _summarize_pairs(list(completed.values()))


@dataclass(frozen=True, slots=True)
class ArenaDecisionBound:
    """Best/worst possible final decision from complete pair scores only."""

    requested_pairs: int
    completed_pairs: int
    remaining_pairs: int
    completed_total: float
    best_final_total: float
    worst_final_total: float
    best_final_mean: float
    worst_final_mean: float
    best_better_pairs: int
    best_tied_pairs: int
    best_worse_pairs: int
    worst_better_pairs: int
    worst_tied_pairs: int
    worst_worse_pairs: int
    decision_sufficient: bool
    strength_estimate_complete: bool


def arena_decision_bound(
    completed_pair_scores: list[float] | tuple[float, ...],
    requested_pairs: int,
    *,
    target_mean: float = 0.5,
) -> ArenaDecisionBound:
    """Return conservative bounds without inventing scores for missing pairs.

    Pair scores are always in ``[0, 1]``.  A greater-than-half decision is
    sufficient only when even the worst remaining pairs stay strictly above
    ``target_mean``.  This deliberately distinguishes a locked decision from
    a complete strength estimate.
    """
    if requested_pairs <= 0:
        raise ValueError("requested_pairs must be positive")
    scores = tuple(float(score) for score in completed_pair_scores)
    if len(scores) > requested_pairs:
        raise ValueError("more completed pairs than requested pairs")
    if any(score < 0.0 or score > 1.0 for score in scores):
        raise ValueError("pair scores must be in [0, 1]")
    if not 0.0 <= target_mean <= 1.0:
        raise ValueError("target_mean must be in [0, 1]")
    remaining = requested_pairs - len(scores)
    completed_total = sum(scores)
    best_total = completed_total + remaining
    worst_total = completed_total
    completed_better = sum(score > 0.5 for score in scores)
    completed_tied = sum(score == 0.5 for score in scores)
    completed_worse = sum(score < 0.5 for score in scores)
    return ArenaDecisionBound(
        requested_pairs=requested_pairs,
        completed_pairs=len(scores),
        remaining_pairs=remaining,
        completed_total=completed_total,
        best_final_total=best_total,
        worst_final_total=worst_total,
        best_final_mean=best_total / requested_pairs,
        worst_final_mean=worst_total / requested_pairs,
        best_better_pairs=completed_better + remaining,
        best_tied_pairs=completed_tied,
        best_worse_pairs=completed_worse,
        worst_better_pairs=completed_better,
        worst_tied_pairs=completed_tied,
        worst_worse_pairs=completed_worse + remaining,
        decision_sufficient=(
            worst_total / requested_pairs > target_mean
        ),
        strength_estimate_complete=(remaining == 0),
    )


# Descriptive aliases used by audit/report callers.
compute_arena_decision_bound = arena_decision_bound
decision_bound = arena_decision_bound


@dataclass(frozen=True, slots=True)
class ArenaRunResult:
    """A game-level run, including an explicit non-scoring partial state."""

    status: str
    summary: ArenaSummary | None
    completed_games: int
    completed_pairs: int
    total_games: int
    reason: str | None
    effective_game_lanes: int
    decision_bound: ArenaDecisionBound

    @property
    def is_complete(self) -> bool:
        return self.status == "COMPLETE"


def _game_progress_identity(
    compiled,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
    openings: ArenaOpeningCorpus,
    caps: ArenaExecutionCaps,
    *,
    stage_id: str,
    capture_search_metrics: bool,
) -> dict:
    identity = _progress_identity(
        compiled, parent, child, config, openings,
        capture_search_metrics=capture_search_metrics,
    )
    identity.update({
        "schema": ARENA_GAME_PROGRESS_SCHEMA,
        "stage_id": stage_id,
        "arena_id": getattr(
            openings, "corpus_id", stable_sha256(openings.to_dict())
        ),
        "execution_caps": asdict(caps),
        "effective_game_lanes": caps.game_lanes(config.pairs, config.workers),
    })
    return identity


def _game_progress_identity_for(
    base_identity: dict,
    config: ArenaConfig,
    caps: ArenaExecutionCaps,
    opening: dict,
    pair_index: int,
    child_owner: int,
    *,
    capture_search_metrics: bool,
) -> dict:
    parent_budget = config.parent_nodes_per_move or config.nodes_per_move
    child_budget = config.child_nodes_per_move or config.nodes_per_move
    return {
        "stage_id": base_identity["stage_id"],
        "arena_id": base_identity["arena_id"],
        "pair_index": pair_index,
        "opening": opening,
        "child_owner": child_owner,
        "parent_checkpoint_id": base_identity["parent_checkpoint_id"],
        "child_checkpoint_id": base_identity["child_checkpoint_id"],
        "node_budgets": {"parent": parent_budget, "child": child_budget},
        "max_depth": config.max_depth,
        "tt_megabytes": config.tt_megabytes,
        "capture_search_metrics": capture_search_metrics,
        "hard_caps": asdict(caps),
    }


def _game_progress_to_dict(
    game: ArenaGameResult,
    *,
    identity_sha256: str,
    game_identity: dict,
) -> dict:
    return {
        "schema": ARENA_GAME_PROGRESS_SCHEMA,
        "identity_sha256": identity_sha256,
        "game_identity": game_identity,
        "status": "completed",
        "game": _game_to_dict(game),
    }


def _game_progress_from_dict(data: dict) -> tuple[dict, ArenaGameResult]:
    required = {"schema", "identity_sha256", "game_identity", "status", "game"}
    if set(data) != required or data.get("schema") != ARENA_GAME_PROGRESS_SCHEMA:
        raise ValueError("arena game fields do not match the game progress schema")
    if data.get("status") != "completed" or not isinstance(data["game_identity"], dict):
        raise ValueError("arena game progress is not a completed game")
    return data["game_identity"], _game_from_dict(data["game"])


def _validate_game_telemetry(
    game: ArenaGameResult,
    config: ArenaConfig,
    *,
    capture_search_metrics: bool,
) -> None:
    if not capture_search_metrics:
        if game.search_metrics:
            raise ValueError("arena game has telemetry but telemetry is disabled")
        return
    if not game.search_metrics:
        raise ValueError("arena game is missing requested search telemetry")
    expected_count = game.plies + (1 if game.declaration_id is not None else 0)
    if len(game.search_metrics) != expected_count:
        raise ValueError("arena game telemetry count does not match its decisions")
    parent_budget = config.parent_nodes_per_move or config.nodes_per_move
    child_budget = config.child_nodes_per_move or config.nodes_per_move
    for index, metric in enumerate(game.search_metrics):
        if not isinstance(metric, dict):
            raise ValueError("arena game telemetry row is not an object")
        required = {
            "side_to_move", "engine_role", "nodes_budget", "nodes",
            "elapsed_seconds", "elapsed_source", "decision_kind",
        }
        if not required <= metric.keys():
            raise ValueError("arena game telemetry row is incomplete")
        role = metric["engine_role"]
        budget = child_budget if role == "child" else parent_budget if role == "parent" else None
        if budget is None or metric["nodes_budget"] != budget:
            raise ValueError("arena game telemetry node budget is invalid")
        if int(metric["nodes"]) < 0 or int(metric["nodes"]) > budget:
            raise ValueError("arena game telemetry node count is invalid")
        if metric["decision_kind"] != (
            "declaration" if index == game.plies and game.declaration_id is not None
            else "action"
        ):
            raise ValueError("arena game telemetry decision kind is invalid")


def _validate_game_progress(
    compiled,
    opening,
    payload: dict,
    *,
    expected_identity: dict,
    identity_sha256: str,
    config: ArenaConfig,
    capture_search_metrics: bool,
    pair_index: int,
    child_owner: int,
) -> ArenaGameResult:
    game_identity, game = _game_progress_from_dict(payload)
    if payload.get("identity_sha256") != identity_sha256:
        raise ValueError("arena game identity does not match the manifest")
    if game_identity != expected_identity:
        raise ValueError("arena game identity does not match the expected game")
    if game.pair != pair_index or game.child_owner != child_owner:
        raise ValueError("arena game pair or owner does not match its filename")
    if game.opening_id != opening.final_position_key:
        raise ValueError("arena game opening identity does not match the corpus")
    if game.result == "ongoing":
        raise ValueError("arena game is not terminal")
    _validate_replayed_game(compiled, opening, game)
    _validate_game_telemetry(
        game, config, capture_search_metrics=capture_search_metrics
    )
    return game


def _pair_results_from_games(
    games: dict[tuple[int, int], ArenaGameResult],
    openings: ArenaOpeningCorpus,
) -> list[ArenaPairResult]:
    pairs = []
    for pair_index in range(len(openings.openings)):
        owner0 = games.get((pair_index, 0))
        owner1 = games.get((pair_index, 1))
        if owner0 is None or owner1 is None:
            continue
        pairs.append(ArenaPairResult(
            pair_index=pair_index,
            opening_id=openings.openings[pair_index].final_position_key,
            game_child_owner0=owner0,
            game_child_owner1=owner1,
        ))
    return pairs


def run_arena_game_resumable(
    compiled,
    native_rules,
    parent: LearnableMaterialCheckpoint,
    child: LearnableMaterialCheckpoint,
    config: ArenaConfig,
    *,
    progress_dir: str | Path,
    openings: ArenaOpeningCorpus | None = None,
    capture_search_metrics: bool = False,
    execution_caps: ArenaExecutionCaps | None = None,
    caps: ArenaExecutionCaps | None = None,
    stage_id: str = "arena",
    pause_requested=None,
    pause_file: str | Path | None = None,
) -> ArenaRunResult:
    """Run one game per checkpoint and aggregate only complete pairs.

    Game files are the scheduling unit.  A crash after either swapped-color
    game leaves a valid partial pair; a later call validates and reuses it,
    then schedules only the missing game.  Hard-cap hits are returned as an
    explicit incomplete result and can never become a draw.
    """
    if execution_caps is not None and caps is not None:
        raise ValueError("pass only one of execution_caps or caps")
    caps = execution_caps or caps or ArenaExecutionCaps()
    if not isinstance(stage_id, str) or not stage_id:
        raise ValueError("stage_id must be a non-empty string")
    openings = _prepare_arena(compiled, parent, child, config, openings)
    directory = Path(progress_dir)
    directory.mkdir(parents=True, exist_ok=True)
    lanes = caps.game_lanes(config.pairs, config.workers)
    identity = _game_progress_identity(
        compiled, parent, child, config, openings, caps,
        stage_id=stage_id, capture_search_metrics=capture_search_metrics,
    )
    identity_sha256 = stable_sha256(identity)
    expected_manifest = {
        "schema": ARENA_GAME_PROGRESS_SCHEMA,
        "identity_sha256": identity_sha256,
        "identity": identity,
    }
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        try:
            actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArenaExecutionError("arena game progress manifest is corrupt") from exc
        if actual_manifest != expected_manifest:
            raise ArenaExecutionError("arena game progress identity does not match this run")
    else:
        if list(directory.glob("pair-*.json")):
            raise ArenaExecutionError(
                "pair-v1 progress cannot be mixed with game-v1 progress"
            )
        _atomic_write_json(manifest_path, expected_manifest)

    opening_rows = openings.to_dict()["openings"]
    if len(opening_rows) < config.pairs:
        raise ArenaExecutionError("arena opening identity is incomplete")
    expected_games = {
        (pair_index, owner): _game_progress_identity_for(
            identity, config, caps, opening_rows[pair_index], pair_index, owner,
            capture_search_metrics=capture_search_metrics,
        )
        for pair_index in range(config.pairs)
        for owner in (0, 1)
    }
    completed_games: dict[tuple[int, int], ArenaGameResult] = {}
    for game_path in sorted(directory.glob("game-*.json")):
        match = re.fullmatch(
            r"game-(\d{6})-owner-([01])\.json", game_path.name
        )
        if match is None:
            raise ArenaExecutionError(
                f"arena game progress has invalid filename: {game_path.name}"
            )
        key = (int(match.group(1)), int(match.group(2)))
        if key not in expected_games:
            raise ArenaExecutionError(
                f"arena game progress has invalid index: {game_path.name}"
            )
        try:
            payload = json.loads(game_path.read_text(encoding="utf-8"))
            game = _validate_game_progress(
                compiled, openings.openings[key[0]], payload,
                expected_identity=expected_games[key],
                identity_sha256=identity_sha256, config=config,
                capture_search_metrics=capture_search_metrics,
                pair_index=key[0], child_owner=key[1],
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ArenaExecutionError(
                f"arena game progress is corrupt: {game_path.name}"
            ) from exc
        if key in completed_games:
            raise ArenaExecutionError(f"conflicting arena game progress: {key}")
        completed_games[key] = game

    missing = [key for key in expected_games if key not in completed_games]
    stage_started = time.perf_counter()
    stage_deadline = (
        None if caps.stage_wall_seconds is None
        else stage_started + caps.stage_wall_seconds
    )
    stop_reason = None
    fatal_error = None

    def is_paused() -> bool:
        if pause_requested is not None:
            value = pause_requested() if callable(pause_requested) else pause_requested
            if bool(value):
                return True
        return pause_file is not None and Path(pause_file).exists()

    def launch_blocker(active_count: int) -> str | None:
        if is_paused():
            return "stage_paused"
        if stage_deadline is not None and time.perf_counter() >= stage_deadline:
            return "stage_wall_seconds"
        if (
            caps.max_stage_games is not None
            and len(completed_games) + active_count >= caps.max_stage_games
        ):
            return "max_stage_games"
        return None

    def execute_game(pair_index: int, owner: int) -> ArenaGameResult:
        kwargs = {
            "opening": openings.openings[pair_index],
            "child_owner": owner,
            "config": config,
            "capture_search_metrics": capture_search_metrics,
        }
        if caps.has_per_game_caps:
            kwargs["execution_caps"] = caps
        return _play_one_game(
            compiled, native_rules, parent, child, **kwargs
        )

    active = {}
    executor = ThreadPoolExecutor(max_workers=lanes)
    try:
        pending = iter(missing)
        exhausted = False
        while active or not exhausted:
            while not exhausted and stop_reason is None and len(active) < lanes:
                blocker = launch_blocker(len(active))
                if blocker is not None:
                    stop_reason = blocker
                    break
                try:
                    key = next(pending)
                except StopIteration:
                    exhausted = True
                    break
                active[key] = executor.submit(execute_game, *key)
            if not active:
                if exhausted or stop_reason is not None:
                    break
                continue
            done, _ = wait(tuple(active.values()), return_when=FIRST_COMPLETED)
            done_items = sorted(
                ((key, active[key]) for key in active if active[key] in done),
                key=lambda item: item[0],
            )
            for key, future in done_items:
                del active[key]
                try:
                    game = future.result()
                    _validate_game_progress(
                        compiled, openings.openings[key[0]],
                        _game_progress_to_dict(
                            game,
                            identity_sha256=identity_sha256,
                            game_identity=expected_games[key],
                        ),
                        expected_identity=expected_games[key],
                        identity_sha256=identity_sha256, config=config,
                        capture_search_metrics=capture_search_metrics,
                        pair_index=key[0], child_owner=key[1],
                    )
                    target = directory / f"game-{key[0]:06d}-owner-{key[1]}.json"
                    if target.exists():
                        raise ArenaExecutionError(
                            f"conflicting arena game progress: {target.name}"
                        )
                    _atomic_write_json(
                        target,
                        _game_progress_to_dict(
                            game,
                            identity_sha256=identity_sha256,
                            game_identity=expected_games[key],
                        ),
                    )
                    completed_games[key] = game
                except ArenaCapHit as exc:
                    stop_reason = exc.cap
                except Exception as exc:  # preserve other engine failures
                    fatal_error = exc
                    stop_reason = stop_reason or "arena_execution_error"
            if stop_reason is not None and not active:
                break
    finally:
        executor.shutdown(wait=True)

    if fatal_error is not None:
        raise fatal_error
    pairs = _pair_results_from_games(completed_games, openings)
    bound = arena_decision_bound(
        [pair.child_pair_score for pair in pairs], config.pairs
    )
    summary = _summarize_pairs(pairs) if len(pairs) == config.pairs else None
    if len(completed_games) == 2 * config.pairs:
        status = "COMPLETE"
        reason = None
    elif stop_reason == "stage_paused":
        status = "PAUSED"
        reason = stop_reason
    else:
        status = "INCOMPLETE"
        reason = stop_reason or "stage_incomplete"
    return ArenaRunResult(
        status=status,
        summary=summary,
        completed_games=len(completed_games),
        completed_pairs=len(pairs),
        total_games=2 * config.pairs,
        reason=reason,
        effective_game_lanes=lanes,
        decision_bound=bound,
    )


# Names used in early F63 notes; all route to the same game-v1 protocol.
run_arena_resumable_game_level = run_arena_game_resumable
run_arena_game_atomic_resumable = run_arena_game_resumable
