"""Benchmark harness smoke tests (tiny budgets, never part of CI strength claims)."""

import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from generic_chess.ai.benchmark.profiles import all_profiles, profile_by_name
from generic_chess.ai.benchmark.runner import GameOutcome, RunConfig, run_benchmark, summarize
from generic_chess.ai.benchmark.suite import SuitePosition, build_position
from generic_chess.generation.config import GeneratorConfig


@pytest.fixture()
def bench_tmp_dir():
    base = Path(__file__).resolve().parent.parent
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
