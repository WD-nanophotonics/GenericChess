"""Actual off-target capture coverage in immutable and mutable qsearch paths."""
import json
from pathlib import Path

from generic_chess.ai.alphabeta import search
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.transition import legal_successors
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.chess_development import evaluator, uci
from scripts.research_state_replay import read_game_state
from frozen_research_sources import source_digest


def root():
    record = json.loads(Path('docs/research/data/chess_qsearch_ep_score_20261006.json').read_text())
    return read_game_state(record['root']), compile_ruleset_for_execution(build_western_chess_ruleset())


def context(state, compiled, qdepth):
    stats = SearchStatistics()
    limits = SearchLimits(max_nodes=8192, quiescence_max_depth=qdepth, quiescence_hard_max_depth=8)
    runtime = SearchPathRuntime.from_state(state, compiled)
    ctx = search._Context(compiled, evaluator('geometric_half'), TranspositionTable(), stats,
                          search._Budget(limits, None), SearchTuning(), False, False,
                          qdepth, 8, 8192, runtime=runtime)
    return ctx


def test_immutable_ep_is_capture_without_occupied_target():
    state, compiled = root()
    stats = SearchStatistics()
    noisy = classify_noisy(state, legal_successors(state, compiled), compiled, stats)
    assert 'e5d6' in {uci(a) for a in noisy}
    assert stats.capture_qactions == 1


def test_runtime_ep_increases_material_and_restores_entire_root():
    state, compiled = root()
    ctx = context(state, compiled, 1)
    runtime = ctx.runtime
    before = (runtime.position, runtime.ply_count, runtime.terminal_status, runtime.search_key())
    score = search.quiescence(state, -search.INF, search.INF, 0, 0, ctx)
    assert score == ctx.evaluator.weights['P']
    assert ctx.stats.capture_qactions == 1 and ctx.stats.qnodes == 2
    assert before == (runtime.position, runtime.ply_count, runtime.terminal_status, runtime.search_key())
    assert runtime.pushes == runtime.pops


def test_noncheck_qdepth_exit_does_not_generate_legal_moves():
    state, compiled = root()
    ctx = context(state, compiled, 0)
    assert search.quiescence(state, -search.INF, search.INF, 0, 0, ctx) == ctx.evaluator.evaluate(state)
    assert ctx.stats.qdepth_cutoffs == 1 and ctx.stats.legal_generation_calls == 0


def test_historical_binding_does_not_accept_an_invented_digest():
    root_path = Path(__file__).resolve().parents[1]
    manifest = json.loads((root_path/'docs/archive/development_before_20261006_qfix/sources.json').read_text())
    name = 'generic_chess/ai/alphabeta/search.py'
    assert source_digest(root_path, name, manifest['sources'][name]['sha256']) == manifest['sources'][name]['sha256']
    assert source_digest(root_path, name, '0'*64) != '0'*64
