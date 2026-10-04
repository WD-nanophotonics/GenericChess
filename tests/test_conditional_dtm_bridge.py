from types import SimpleNamespace as NS

import pytest

from generic_chess.core.terminal import TerminalResult, TerminalStatus as T
from scripts.conditional_dtm_bridge import PREMISES, dtm_horizon_interval, terminal_first_interval


def args(**overrides):
    return {'side': 0, 'ply': 10, 'max_ply': 20, 'repetition_limit': 100000,
            'max_repetition_count': 1, 'wdl_stm': 1, 'signed_dtm': 10,
            'premises': dict.fromkeys(PREMISES, True)} | overrides


def test_finite_bridge_matches_independent_minimax_horizon_truncation():
    # Abstract signed-terminal DAG, not Chess positions or tablebase labels.
    # Every defended branch eventually ends for the same winner. Defender chooses
    # between lengths D and D-2, winner between D and D+2. Dynamic program uses
    # terminal-first truncation and owner-zero minimax, not distance comparison.
    def line(depth, horizon, winner):
        if depth == 0:
            return 1 if winner == 0 else -1
        if horizon == 0:
            return 0
        return line(depth-1, horizon-1, winner)
    for side in (0, 1):
        for sign in (-1, 1):
            winner = side if sign > 0 else 1-side
            for distance in range(3, 11):
                for horizon in range(1, 13):
                    choose = max if side == 0 else min
                    options = (distance, distance+2) if winner == side else (distance, distance-2)
                    exact = choose(line(d, horizon, winner) for d in options)
                    got = dtm_horizon_interval(**args(side=side, max_ply=10+horizon,
                                                   wdl_stm=sign, signed_dtm=sign*distance))
                    assert got['interval'] == (exact, exact)
    assert dtm_horizon_interval(**args(wdl_stm=0, signed_dtm=0))['interval'] == (0, 0)


def test_unverified_distance_history_and_ambiguous_zero_stay_unknown():
    cases = [args(distance_kind='DTZ'), args(wdl_stm=-1, signed_dtm=5),
             args(wdl_stm=1, signed_dtm=0), args(wdl_stm=0, signed_dtm=3),
             args(wdl_stm=None, signed_dtm=None), args(max_repetition_count=99990),
             args(premises={}), args(premises=dict.fromkeys(PREMISES, False))]
    for case in cases:
        assert dtm_horizon_interval(**case)['interval'] == (-1, 1)
    for case in (args(side=True), args(ply=20), args(max_repetition_count=0)):
        with pytest.raises(ValueError):
            dtm_horizon_interval(**case)


def test_authoritative_terminal_first_and_unresolved_claim_censoring():
    class Game:
        def terminal(self, state):
            return state
    for status, winner, value in ((T.CHECKMATE, 0, 1), (T.CHECKMATE, 1, -1),
                                  (T.MAX_PLY, None, 0), (T.STALEMATE, None, 0)):
        result = terminal_first_interval(TerminalResult(status, winner), Game(), {})
        assert result['interval'] == (value, value)
    for terminal in (TerminalResult(T.NO_CONTEST),
                     NS(status='declaration', is_terminal=True, winner=None, unresolved=True)):
        assert terminal_first_interval(terminal, Game(), {})['interval'] == (-1, 1)
    assert terminal_first_interval(TerminalResult(T.STALEMATE), Game(), {},
                                   censored_statuses=(T.STALEMATE,))['interval'] == (-1, 1)
    assert terminal_first_interval(TerminalResult(T.ONGOING), Game(), args())['interval'] == (1, 1)
