"""Paired-control benchmark runner (pure standard library)."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from ...core.actions import Action
from ...rules.compiled import CompiledRuleSet
from ...session.result import SessionStatus
from ...session.session import GameSession
from ..alphabeta.player import AlphaBetaPlayer
from ..evaluation.cache import EvaluationProfileCache
from ..limits import SearchLimits
from .profiles import BenchmarkProfile
from .suite import SuitePosition, build_position

TIMING_TOLERANCE_SECONDS = 0.05
TIMING_TOLERANCE_FRACTION = 0.05


@dataclass(frozen=True, slots=True)
class RunConfig:
    control: BenchmarkProfile
    candidate: BenchmarkProfile
    suite: tuple[SuitePosition, ...]
    seconds: float | None = 1.0
    nodes: int | None = None
    max_plies: int = 120


@dataclass(frozen=True, slots=True)
class MoveEvent:
    game_key: str
    position_key: str
    ply: int
    side: int
    action: str
    completed_depth: int
    nodes: int
    qnodes: int
    elapsed_seconds: float
    termination_reason: str
    fallback: bool
    timing_invalid: bool
    candidate: bool


@dataclass(frozen=True, slots=True)
class GameOutcome:
    game_key: str
    position_key: str
    candidate_color: int
    result: str  # candidate_win | candidate_loss | rule_draw | unresolved | failed
    plies: int
    candidate_fallback: bool
    control_fallback: bool
    candidate_timing_invalid: bool
    control_timing_invalid: bool

    @property
    def eligible(self) -> bool:
        return not (
            self.candidate_fallback
            or self.control_fallback
            or self.candidate_timing_invalid
            or self.control_timing_invalid
        )


def _timing_invalid(elapsed: float, seconds: float | None) -> bool:
    if seconds is None:
        return False
    return elapsed > max(TIMING_TOLERANCE_SECONDS, seconds * (1.0 + TIMING_TOLERANCE_FRACTION))


def _adjudicate(session: GameSession, candidate_color: int) -> str:
    status = session.result.status
    if status is SessionStatus.CHECKMATE:
        return "candidate_win" if session.result.winner == candidate_color else "candidate_loss"
    if status in (SessionStatus.STALEMATE, SessionStatus.REPETITION, SessionStatus.MAX_PLY):
        return "rule_draw"
    if status is SessionStatus.RESIGNATION:
        return "candidate_win" if session.result.resigned_by != candidate_color else "candidate_loss"
    return "unresolved"


def play_game(
    compiled: CompiledRuleSet,
    opening: tuple[Action, ...],
    position_key: str,
    game_key: str,
    candidate_color: int,
    candidate: AlphaBetaPlayer,
    control: AlphaBetaPlayer,
    config: RunConfig,
) -> tuple[GameOutcome, list[MoveEvent]]:
    """Play one game from the position with ``candidate`` as ``candidate_color``."""
    session = GameSession(compiled)
    for action in opening:
        session.submit(action)
    events: list[MoveEvent] = []
    fallback_flags = {0: False, 1: False}
    timing_flags = {0: False, 1: False}
    failed = False

    while (
        session.result.status is SessionStatus.ONGOING
        and session.state.ply_count < config.max_plies
    ):
        side = session.state.position.side_to_move
        player = candidate if side == candidate_color else control
        limits = SearchLimits(
            max_time_seconds=config.seconds,
            max_nodes=config.nodes,
        )
        started = time.monotonic()
        decision = player.choose_action(session, limits)
        elapsed = time.monotonic() - started
        fallback = decision.termination_reason == "fallback"
        timing_invalid = _timing_invalid(elapsed, config.seconds)
        events.append(
            MoveEvent(
                game_key=game_key,
                position_key=position_key,
                ply=session.state.ply_count + 1,
                side=side,
                action=str(decision.action) if decision.action is not None else "<none>",
                completed_depth=decision.completed_depth,
                nodes=decision.nodes,
                qnodes=decision.qnodes,
                elapsed_seconds=elapsed,
                termination_reason=decision.termination_reason,
                fallback=fallback,
                timing_invalid=timing_invalid,
                candidate=side == candidate_color,
            )
        )
        fallback_flags[side] = fallback_flags[side] or fallback
        timing_flags[side] = timing_flags[side] or timing_invalid
        if decision.action is None:
            failed = True
            break
        try:
            session.submit(decision.action)
        except ValueError:
            failed = True
            break

    result = "failed" if failed else _adjudicate(session, candidate_color)
    outcome = GameOutcome(
        game_key=game_key,
        position_key=position_key,
        candidate_color=candidate_color,
        result=result,
        plies=session.state.ply_count,
        candidate_fallback=fallback_flags[candidate_color],
        control_fallback=fallback_flags[1 - candidate_color],
        candidate_timing_invalid=timing_flags[candidate_color],
        control_timing_invalid=timing_flags[1 - candidate_color],
    )
    return outcome, events


def _manifest(config: RunConfig, out_dir: Path) -> dict:
    return {
        "schema_version": 1,
        "control_profile": config.control.name,
        "candidate_profile": config.candidate.name,
        "seconds": config.seconds,
        "nodes": config.nodes,
        "max_plies": config.max_plies,
        "suite": [p.key for p in config.suite],
        "started_at": time.time(),
        "out_dir": str(out_dir),
    }


def summarize(games: list[GameOutcome]) -> dict:
    eligible = [
        g
        for g in games
        if g.eligible and g.result not in ("unresolved", "failed")
    ]
    wins = sum(1 for g in eligible if g.result == "candidate_win")
    losses = sum(1 for g in eligible if g.result == "candidate_loss")
    draws = sum(1 for g in eligible if g.result == "rule_draw")
    by_color: dict[int, dict] = {}
    for color in (0, 1):
        colored = [g for g in eligible if g.candidate_color == color]
        by_color[color] = {
            "wins": sum(1 for g in colored if g.result == "candidate_win"),
            "losses": sum(1 for g in colored if g.result == "candidate_loss"),
            "draws": sum(1 for g in colored if g.result == "rule_draw"),
        }
    paired = []
    for position_key in sorted({g.position_key for g in games}):
        by_color_games = {g.candidate_color: g for g in games if g.position_key == position_key}
        if len(by_color_games) == 2:
            g0, g1 = by_color_games[0], by_color_games[1]
            eligible_pair = g0.eligible and g1.eligible
            sweep = None
            if eligible_pair:
                if g0.result == g1.result == "candidate_win":
                    sweep = "candidate_sweep"
                elif g0.result == g1.result == "candidate_loss":
                    sweep = "control_sweep"
                elif g0.result == g1.result == "rule_draw":
                    sweep = "split_draw"
                else:
                    sweep = "split"
            paired.append(
                {
                    "position": position_key,
                    "eligible": eligible_pair,
                    "sweep": sweep,
                    "results": [g0.result, g1.result],
                }
            )
    return {
        "games_total": len(games),
        "candidate_wins": wins,
        "candidate_losses": losses,
        "rule_draws": draws,
        "unresolved": sum(1 for g in games if g.result == "unresolved"),
        "failed": sum(1 for g in games if g.result == "failed"),
        "fallback_games": sum(
            1 for g in games if g.candidate_fallback or g.control_fallback
        ),
        "timing_invalid_games": sum(
            1 for g in games if g.candidate_timing_invalid or g.control_timing_invalid
        ),
        "eligible_games": len(eligible),
        "candidate_score": (wins + 0.5 * draws) / len(eligible) if eligible else None,
        "by_color": by_color,
        "paired_results": paired,
    }


def run_benchmark(
    config: RunConfig,
    out_dir: str | Path,
    *,
    resume: bool = False,
) -> dict:
    """Run the paired suite and write JSONL/JSON artifacts; returns summary."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    games_path = out / "games.jsonl"
    events_path = out / "events.jsonl"
    manifest = _manifest(config, out)
    (out / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )

    completed_keys: set[str] = set()
    games: list[GameOutcome] = []
    if resume and games_path.exists():
        for line in games_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            completed_keys.add(raw["game_key"])
            games.append(
                GameOutcome(
                    game_key=raw["game_key"],
                    position_key=raw["position_key"],
                    candidate_color=raw["candidate_color"],
                    result=raw["result"],
                    plies=raw["plies"],
                    candidate_fallback=raw["candidate_fallback"],
                    control_fallback=raw["control_fallback"],
                    candidate_timing_invalid=raw["candidate_timing_invalid"],
                    control_timing_invalid=raw["control_timing_invalid"],
                )
            )

    with games_path.open("a", encoding="utf-8") as games_fh, events_path.open(
        "a", encoding="utf-8"
    ) as events_fh:
        for position in config.suite:
            compiled, opening = build_position(position)
            cache = EvaluationProfileCache(use_disk=False)
            candidate = AlphaBetaPlayer(
                compiled,
                profile_cache=cache,
                use_disk_cache=False,
                tuning=config.candidate.tuning,
            )
            control = AlphaBetaPlayer(
                compiled,
                profile_cache=cache,
                use_disk_cache=False,
                tuning=config.control.tuning,
            )
            for candidate_color in (0, 1):
                game_key = f"{position.key}:c{candidate_color}"
                if resume and game_key in completed_keys:
                    continue
                outcome, events = play_game(
                    compiled,
                    opening,
                    position.key,
                    game_key,
                    candidate_color,
                    candidate,
                    control,
                    config,
                )
                games.append(outcome)
                games_fh.write(json.dumps(asdict(outcome), sort_keys=True) + "\n")
                games_fh.flush()
                for event in events:
                    events_fh.write(json.dumps(asdict(event), sort_keys=True) + "\n")
                events_fh.flush()

    summary = summarize(games)
    (out / "summary.json").write_text(
        json.dumps(summary, sort_keys=True), encoding="utf-8"
    )
    return summary
