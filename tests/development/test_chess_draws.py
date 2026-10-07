"""Prospective claim timing and match/Core boundary regressions, no engines."""
from pathlib import Path
import pytest
from generic_chess.ai.limits import SearchLimits
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset

@pytest.fixture(scope='module')
def d():
    import scripts.chess_development as development
    return development

@pytest.fixture(autouse=True)
def library(monkeypatch):
    path=Path('.local_agent/certificate_source/python-chess')
    if path.exists():monkeypatch.syspath_prepend(str(path.resolve()))
    pytest.importorskip('chess.engine')

@pytest.fixture(scope='module')
def compiled():
    return compile_ruleset_for_execution(build_western_chess_ruleset())

class Choice:
    def __init__(self,move):self.move=move;self.calls=0
    def choose(self):
        self.calls+=1
        return self.move,dict(policy='uci_reference',move=self.move,reason='uci_bestmove',statistics={})
    def push(self,*args):pass

def test_prospective_threefold_stops_before_search_and_keeps_witness_unplayed(d,compiled):
    import chess
    prefix=['g1f3','g8f6','f3g1','f6g8','g1f3','g8f6','f3g1']
    player=Choice('f6g8')
    game=d.play_game(chess.STARTING_FEN,compiled,'unit','uci_reference',SearchLimits(),1,
                     external=player,prefix=prefix,claim_chess_draws=True)
    assert player.calls==0 and game['plies_played']==0 and game['moves']==[]
    assert game['finished'] and game['winner'] is None
    assert game['adjudication']==dict(ply=7,kind='claim',reason='THREEFOLD_REPETITION',winner=None,witness_uci='f6g8')
    assert len(game['final_state']['history'])==8
    assert game['final_state']['terminal_status']['status']=='ongoing'
    old=d.play_game(chess.STARTING_FEN,compiled,'unit','uci_reference',SearchLimits(),1,
                    external=player,prefix=prefix)
    assert player.calls==1 and old['plies_played']==1 and not old['finished']
    assert 'adjudication' not in old and old['end']=='ply_limit'

def test_prospective_fifty_move_claim_preserves_board(d):
    import chess
    a=d.ChessAdjudicator('7k/8/8/8/8/8/R7/K7 w - - 99 50')
    before=a.board.fen();decision=a.decision()
    assert decision['reason']=='FIFTY_MOVES' and decision['kind']=='claim'
    witness=chess.Move.from_uci(decision['witness_uci'])
    assert witness in a.board.legal_moves and a.board.fen()==before and not a.board.move_stack
    a.board.push(witness);assert a.board.is_fifty_moves()

def test_automatic_fivefold_takes_precedence_over_optional_claim(d):
    import chess
    a=d.ChessAdjudicator(chess.STARTING_FEN)
    for move in ['g1f3','g8f6','f3g1','f6g8']*4:a.board.push_uci(move)
    decision=a.decision()
    assert decision['kind']=='automatic' and decision['reason']=='FIVEFOLD_REPETITION'
    assert decision['witness_uci'] is None

def test_final_allowed_capture_adjudicates_insufficient_material(d,compiled):
    player=Choice('b2c3')
    game=d.play_game('7k/8/8/8/8/2n5/1B6/K7 w - - 0 1',compiled,
                     'uci_reference','unit',SearchLimits(),1,external=player,claim_chess_draws=True)
    assert player.calls==1 and game['plies_played']==1
    assert game['finished'] and game['end']=='chess_insufficient_material'
    assert game['adjudication']['ply']==1 and game['adjudication']['kind']=='automatic'
    assert game['final_state']['terminal_status']['status']=='ongoing'

def test_final_allowed_mate_retains_core_win(d,compiled):
    player=Choice('g6g7')
    game=d.play_game('7k/8/5KQ1/8/8/8/8/8 w - - 0 1',compiled,
                     'uci_reference','unit',SearchLimits(),1,external=player,claim_chess_draws=True)
    assert game['finished'] and game['winner']==0 and game['end']=='checkmate'
    assert game['adjudication']['reason']=='CHECKMATE'

def test_mate_precedes_seventyfive_moves(d):
    a=d.ChessAdjudicator('7k/8/5KQ1/8/8/8/8/8 w - - 149 75')
    a.board.push_uci('g6g7');assert a.board.halfmove_clock==150
    decision=a.decision()
    assert decision['reason']=='CHECKMATE' and decision['winner']==0
