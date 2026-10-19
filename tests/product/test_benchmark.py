"""Benchmark harness smoke tests (tiny budgets, never part of CI strength claims)."""

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from generic_chess.ai.benchmark.profiles import all_profiles, profile_by_name
from generic_chess.ai.benchmark.runner import (
    GameOutcome,
    RunConfig,
    _adjudicate,
    play_game,
    run_benchmark,
    summarize,
)
from generic_chess.ai.benchmark.suite import SuitePosition, build_position
from generic_chess.generation.config import GeneratorConfig
from generic_chess.session.result import SessionResult, SessionStatus


def test_benchmark_adjudicates_stalemate_winner_not_draw():
    session = type(
        "SessionStub",
        (),
        {"result": SessionResult(SessionStatus.STALEMATE, winner=1)},
    )()
    assert _adjudicate(session, candidate_color=1) == "candidate_win"
    assert _adjudicate(session, candidate_color=0) == "candidate_loss"
    drawn = type(
        "SessionStub",
        (),
        {"result": SessionResult(SessionStatus.STALEMATE, winner=None)},
    )()
    assert _adjudicate(drawn, candidate_color=0) == "rule_draw"


@pytest.mark.parametrize(
    "status, winner, expected",
    (
        (SessionStatus.CHECKMATE, 0, "candidate_win"),
        (SessionStatus.STALEMATE, 1, "candidate_loss"),
        (SessionStatus.STALEMATE, None, "rule_draw"),
        (SessionStatus.PERPETUAL_CHECK, 1, "candidate_loss"),
        (SessionStatus.RULE_LOSS, 0, "candidate_win"),
        (SessionStatus.REPETITION, None, "rule_draw"),
        (SessionStatus.MAX_PLY, None, "rule_draw"),
        (SessionStatus.ACTION_CLASS_DRAW, None, "rule_draw"),
        (SessionStatus.NO_PROGRESS_DRAW, None, "rule_draw"),
        (SessionStatus.NO_CONTEST, None, "unresolved"),
        (SessionStatus.ONGOING, None, "unresolved"),
        (SessionStatus.DECLARATION, 0, "candidate_win"),
        (SessionStatus.DECLARATION, None, "unresolved"),
        (SessionStatus.RESIGNATION, 1, "candidate_loss"),
    ),
)
def test_benchmark_adjudicates_all_generic_terminal_categories(status, winner, expected):
    resigned_by = 0 if status is SessionStatus.RESIGNATION else None
    session = type(
        "SessionStub",
        (),
        {"result": SessionResult(status, winner=winner, resigned_by=resigned_by)},
    )()
    assert _adjudicate(session, candidate_color=0) == expected


@pytest.mark.parametrize(
    "candidate_color, expected",
    ((0, "candidate_win"), (1, "candidate_loss")),
)
def test_benchmark_executes_and_scores_root_declaration(candidate_color, expected):
    from generic_chess import compile_ruleset_for_execution
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from test_generic_declaration_semantics import _claim_ruleset

    compiled = compile_ruleset_for_execution(_claim_ruleset())
    player = AlphaBetaPlayer(
        compiled, use_native_semantic_legality=False, use_disk_cache=False
    )
    outcome, events = play_game(
        compiled, (), "declaration-root", "declaration-win", candidate_color,
        player, player, _tiny_config(),
    )

    assert outcome.result == expected
    assert outcome.plies == 0
    assert len(events) == 1
    assert events[0].action == "<declaration:opaque_claim:WIN>"
    assert events[0].ply == 0
    assert events[0].termination_reason == "root_declaration_win"


def test_benchmark_does_not_score_restart_declaration_as_draw_or_failure():
    from dataclasses import replace

    from generic_chess import compile_ruleset_for_execution
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.rules.schema import RuleDeclarationOutcomeBand
    from test_generic_declaration_semantics import _claim_ruleset

    ruleset = _claim_ruleset()
    declaration = replace(
        ruleset.declarations[0],
        outcome_bands=(RuleDeclarationOutcomeBand(7, "RESTART"),),
    )
    compiled = compile_ruleset_for_execution(
        replace(ruleset, declarations=(declaration,))
    )
    class ConstantEvaluator:
        def evaluate(self, _state):
            return 1

        def capture_order_value(self, _mover, _victim):
            return 0

        def type_value(self, _type_id):
            return 0

    player = AlphaBetaPlayer(
        compiled,
        evaluator_override=ConstantEvaluator(),
        use_native_semantic_legality=False,
        use_disk_cache=False,
    )
    outcome, events = play_game(
        compiled, (), "declaration-root", "declaration-restart", 0,
        player, player, _tiny_config(),
    )

    assert outcome.result == "unresolved"
    assert outcome.plies == 0
    assert len(events) == 1
    assert events[0].action == "<declaration:opaque_claim:RESTART>"


def test_benchmark_scores_a_full_history_no_progress_cycle_as_rule_draw():
    from generic_chess.core.actions import action_source_square, action_target_square
    from generic_chess.core.coordinates import Square
    from generic_chess.core.movegen import legal_actions
    from generic_chess.session.session import GameSession
    from test_generic_no_progress_draw import _compiled

    compiled = _compiled(
        (
            (0, "K", Square(0, 0)),
            (1, "K", Square(7, 7)),
            (0, "N", Square(1, 0)),
            (1, "N", Square(6, 7)),
        ),
        semantic=True,
    )
    session = GameSession(compiled)
    opening = []
    for source, target in (
        (Square(1, 0), Square(0, 2)),
        (Square(6, 7), Square(7, 5)),
        (Square(0, 2), Square(1, 0)),
        (Square(7, 5), Square(6, 7)),
    ):
        action = next(
            item
            for item in legal_actions(session.state, compiled)
            if action_source_square(item) == source
            and action_target_square(item) == target
        )
        opening.append(action)
        session.submit(action)

    assert session.result.status is SessionStatus.NO_PROGRESS_DRAW
    outcome, events = play_game(
        compiled, tuple(opening), "no-progress-cycle", "no-progress-cycle", 0,
        None, None, _tiny_config(),
    )

    assert outcome.result == "rule_draw"
    assert outcome.plies == 4
    assert events == []


@pytest.fixture()
def bench_tmp_dir():
    base = Path(__file__).resolve().parents[2]
    tmp = base / f".gc_bench_tmp_{uuid.uuid4().hex}"
    os.makedirs(tmp, mode=0o777)
    yield tmp
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)


def _tiny_config():
    pos = SuitePosition(
        "tiny",
        GeneratorConfig(seed=5, board_size=4, setup_preset="classic_like"),
        0,
    )
    return RunConfig(
        control=profile_by_name("baseline"),
        candidate=profile_by_name("pvs"),
        suite=(pos,),
        seconds=None,
        nodes=80,
        max_plies=3,
    )


def test_profiles_list_stable():
    names = [p.name for p in all_profiles()]
    assert names == [
        "baseline",
        "pvs",
        "pvs_aspiration",
        "staged_picker",
        "countermove",
        "mate_distance",
        "full_candidate",
    ]


def test_build_position_is_deterministic():
    pos = SuitePosition(
        "det",
        GeneratorConfig(seed=42, board_size=4, setup_preset="classic_like"),
        8,
    )
    a = build_position(pos)
    b = build_position(pos)
    assert a[0].ruleset_fingerprint == b[0].ruleset_fingerprint
    assert [str(x) for x in a[1]] == [str(x) for x in b[1]]


def test_benchmark_smoke_writes_artifacts(bench_tmp_dir):
    summary = run_benchmark(_tiny_config(), bench_tmp_dir)
    for name in ("manifest.json", "games.jsonl", "events.jsonl", "summary.json"):
        path = bench_tmp_dir / name
        assert path.exists()
        assert path.stat().st_size > 0
    assert summary["games_total"] == 2  # both colors
    assert summary["unresolved"] == 2  # max_plies=3, no rule result yet
    assert summary["eligible_games"] == 0  # unresolved excluded from score
    events = [
        json.loads(line)
        for line in (bench_tmp_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events
    assert all("game_key" in e and "nodes" in e for e in events)


def test_benchmark_resume_skips_completed(bench_tmp_dir):
    run_benchmark(_tiny_config(), bench_tmp_dir)
    before = sum(1 for _ in (bench_tmp_dir / "games.jsonl").read_text(encoding="utf-8").splitlines())
    run_benchmark(_tiny_config(), bench_tmp_dir, resume=True)
    after = sum(1 for _ in (bench_tmp_dir / "games.jsonl").read_text(encoding="utf-8").splitlines())
    assert after == before


def test_summary_eligibility_rules():
    games = [
        GameOutcome("g1", "p1", 0, "candidate_win", 10, False, False, False, False),
        GameOutcome("g2", "p1", 1, "candidate_loss", 10, False, False, False, False),
        GameOutcome("g3", "p2", 0, "unresolved", 120, False, False, False, False),
        GameOutcome("g4", "p2", 1, "candidate_win", 5, True, False, False, False),
        GameOutcome("g5", "p3", 0, "rule_draw", 40, False, False, False, False),
        GameOutcome("g6", "p3", 1, "candidate_win", 3, False, True, False, False),
    ]
    summary = summarize(games)
    assert summary["eligible_games"] == 3  # g1, g2, g5
    assert summary["candidate_score"] == pytest.approx((1 + 0 + 0.5) / 3)
    assert summary["unresolved"] == 1
    assert summary["fallback_games"] == 2
    assert summary["by_color"][0] == {"wins": 1, "losses": 0, "draws": 1}
    assert summary["by_color"][1] == {"wins": 0, "losses": 1, "draws": 0}


def test_benchmark_cli_list_profiles(capsys):
    from generic_chess.ai.benchmark.__main__ import main

    assert main(["--list-profiles"]) == 0
    out = capsys.readouterr().out
    assert "baseline" in out
    assert "full_candidate" in out


def test_alpha_beta_cli_executes_and_counts_a_root_win_declaration(capsys):
    from generic_chess import compile_ruleset_for_execution
    from generic_chess.ai.cli.benchmark_alphabeta import _vs_random
    from test_generic_declaration_semantics import _claim_ruleset

    compiled = compile_ruleset_for_execution(_claim_ruleset())
    _vs_random(compiled, games=2, nodes=80, seed=1)

    output = capsys.readouterr().out
    assert "AB wins: 1" in output
    assert "draws: 0" in output
    assert "unresolved: 1" in output
    assert "avg plies: 200.0" in output


def test_alpha_beta_cli_search_report_names_a_root_declaration(monkeypatch, capsys):
    from generic_chess import compile_ruleset_for_execution
    from generic_chess.ai.cli import benchmark_alphabeta
    from test_generic_declaration_semantics import _claim_ruleset

    compiled = compile_ruleset_for_execution(_claim_ruleset())
    monkeypatch.setattr(benchmark_alphabeta, "_load_compiled", lambda _args: compiled)

    assert benchmark_alphabeta.main(
        ["--nodes", "80", "--repeat", "1", "--no-disk"]
    ) == 0
    assert "action=<declaration:opaque_claim:WIN>" in capsys.readouterr().out


@pytest.mark.parametrize(
    "status,winner,expected",
    (
        (SessionStatus.CHECKMATE, 0, "ab"),
        (SessionStatus.STALEMATE, 1, "random"),
        (SessionStatus.STALEMATE, None, "draw"),
        (SessionStatus.PERPETUAL_CHECK, 1, "random"),
        (SessionStatus.RULE_LOSS, 0, "ab"),
        (SessionStatus.DECLARATION, None, "unresolved"),
        (SessionStatus.DECLARATION, 1, "random"),
        (SessionStatus.REPETITION, None, "draw"),
        (SessionStatus.MAX_PLY, None, "draw"),
        (SessionStatus.ACTION_CLASS_DRAW, None, "draw"),
        (SessionStatus.NO_PROGRESS_DRAW, None, "draw"),
        (SessionStatus.RESIGNATION, 1, "random"),
        (SessionStatus.NO_CONTEST, None, "unresolved"),
        (SessionStatus.ONGOING, None, "unresolved"),
    ),
)
def test_alpha_beta_cli_result_buckets_respect_generic_session_outcomes(
    status, winner, expected
):
    from generic_chess.ai.cli.benchmark_alphabeta import _result_bucket

    result = SessionResult(status, winner=winner)
    assert _result_bucket(result, ai_color=0) == expected
