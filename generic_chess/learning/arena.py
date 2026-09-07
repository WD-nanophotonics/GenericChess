"""Integrity-preserving paired arena.

Measurement rules:
* every game replays one corpus opening (identical within a pair);
* every game creates **fresh** parent and child engines (TT never crosses
  games);
* engine failures are raised, never counted as draws;
* the primary statistic is the paired score with a pair-level bootstrap CI.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
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


ARENA_PROGRESS_SCHEMA = "generic-chess-arena-progress-v1"


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
    declaration_id = None
    search_metrics = []
    while session.result.status.value == "ongoing":
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
