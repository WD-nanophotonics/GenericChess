"""Semantic/work alignment and interruption contracts for the thin bridge."""
import pytest

pytest.importorskip('chess')
pytest.importorskip('cshogi')
from scripts.search_backend_comparison import (
    CASES, CoreBoard, ChessBoard, ShogiBoard, audit_pair, minimal_ab,
    build_builtin_ruleset, compile_ruleset_for_execution,
)


@pytest.fixture(scope='module')
def compiled():
    return {g: compile_ruleset_for_execution(build_builtin_ruleset(n))
            for g, n in [('chess', 'western_chess'), ('shogi', 'standard_shogi')]}


@pytest.mark.parametrize('case', CASES, ids=[c['id'] for c in CASES])
def test_paired_history_legality_material_terminal_and_search(case, compiled):
    core = CoreBoard(case, compiled[case['game']])
    other = ChessBoard(case) if case['game'] == 'chess' else ShogiBoard(case)
    assert audit_pair(core, other, 1) > 1
    a = minimal_ab(core, 2, seconds=10, trace=True)
    b = minimal_ab(other, 2, seconds=10, trace=True)
    for field in ('move', 'score', 'reason', 'work', 'trace_sha256'):
        assert a[field] == b[field], field
    assert a['reason'] == 'completed_depth'


def test_node_abort_unwinds_actual_histories_and_keeps_completed_children(compiled):
    core = CoreBoard(CASES[0], compiled['chess'])
    other = ChessBoard(CASES[0])
    a = minimal_ab(core, 2, node_limit=45, trace=True)
    b = minimal_ab(other, 2, node_limit=45, trace=True)
    for field in ('move', 'score', 'reason', 'work', 'trace_sha256'):
        assert a[field] == b[field]
    assert a['reason'] == 'budget'
    assert a['work']['root_completed'] > 0
    assert core.restored() and other.restored()


def test_noncheck_no_move_matches_explicit_product_policy(compiled):
    case = dict(id='no-move', game='shogi', setup='8k/9/7+R1/9/9/9/9/9/K8 w G 1', moves='')
    core, other = CoreBoard(case, compiled['shogi']), ShogiBoard(case)
    assert core.terminal(0) == other.terminal(0) == -1000000000
    assert not other.board.is_check() and other.board.is_game_over()


@pytest.mark.parametrize('setup,moves,score', [
    ('4k4/9/9/9/9/9/9/9/4K4 b - 1', '5i4i 5a4a 4i5i 4a5a', 0),
    ('4k4/9/4R4/9/9/9/9/9/K8 w - 1', '5a4a 5c4c 4a5a 4c5c', 1000000000),
])
def test_replayed_fourfold_and_continuous_check_history(compiled, setup, moves, score):
    case = dict(game='shogi', setup=setup, moves=' '.join([moves]*3))
    core, other = CoreBoard(case, compiled['shogi']), ShogiBoard(case)
    assert audit_pair(core, other, 0) == 1
    assert core.terminal(0) == other.terminal(0) == score
    assert len(core.initial.history) == 13


def test_common_iterative_driver_preserves_same_work_under_node_limit(compiled):
    from scripts.search_backend_comparison import iterative_minimal
    core, other = CoreBoard(CASES[0], compiled['chess']), ChessBoard(CASES[0])
    a = iterative_minimal(core, seconds=10, node_limit=600, max_depth=6)
    b = iterative_minimal(other, seconds=10, node_limit=600, max_depth=6)
    for field in ('move', 'score', 'completed_depth', 'reason', 'fallback', 'work', 'interrupted_root_completed'):
        assert a[field] == b[field]
    assert a['completed_depth'] == 2
    assert core.restored() and other.restored()


def test_inner_cooperative_deadline_preserves_fixed_work_and_unwinds(compiled):
    plain = CoreBoard(CASES[0], compiled['chess'])
    checked = CoreBoard(CASES[0], compiled['chess'])
    a = minimal_ab(plain, 2, seconds=10, trace=True)
    b = minimal_ab(checked, 2, seconds=10, trace=True, cooperative=True)
    for field in ('move', 'score', 'work', 'reason', 'trace_sha256'):
        assert a[field] == b[field]
    aborted = minimal_ab(checked, 8, seconds=0.00001, cooperative=True)
    assert aborted['reason'] == 'budget'
    assert checked.restored() and checked.checkpoint is None


def test_second_occurrence_is_not_fourfold(compiled):
    case = dict(game='shogi', setup='4k4/9/9/9/9/9/9/9/4K4 b - 1',
                moves='5i4i 5a4a 4i5i 4a5a')
    core, other = CoreBoard(case, compiled['shogi']), ShogiBoard(case)
    assert other.board.is_draw() == other.module.REPETITION_DRAW
    assert core.terminal(0) is other.terminal(0) is None


def test_deeper_promotion_trace_matches_after_strict_repetition_repair(compiled):
    case = next(c for c in CASES if c['id'] == 'shogi-promotion')
    a = minimal_ab(CoreBoard(case, compiled['shogi']), 6, seconds=10, trace=True)
    b = minimal_ab(ShogiBoard(case), 6, seconds=10, trace=True)
    for field in ('move', 'score', 'work', 'trace_sha256', 'reason'):
        assert a[field] == b[field]


def test_western_stalemate_still_draw(compiled):
    case = dict(game='chess', setup='7k/5Q2/6K1/8/8/8/8/8 b - - 0 1', moves='')
    core, other = CoreBoard(case, compiled['chess']), ChessBoard(case)
    assert core.terminal(0) == other.terminal(0) == 0
    assert not other.board.is_check() and other.board.is_stalemate()
