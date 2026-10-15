"""Rule-level soundness, all-defense execution and interrupt regression checks."""
from dataclasses import replace

import pytest

from generic_chess.core.actions import BoardMove, PassAction
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.transition import initial_state, apply_action
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus
from generic_chess.rules.schema import RuleSet
from generic_chess.rules.compiler import compile_ruleset
from scripts.generic_win_proof import (
    prove_win, verify_certificate, StrategyCursor, PROVEN_WIN, UNKNOWN,
    ALREADY_TERMINAL,
)


def krk(k=1, rook=8, black=3, turn=0, **changes):
    king = PieceType('K', 'Anchor', tuple(LeapAtom((x,y)) for x in (-1,0,1)
                                      for y in (-1,0,1) if x or y), is_anchor=True)
    r = PieceType('R', 'Ray', tuple(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1))))
    baseboard = [None] * 16
    baseboard[0],baseboard[1],baseboard[15] = Piece(0,'K','K'),Piece(0,'R','R'),Piece(1,'K','K')
    rs = RuleSet(board_size=4, piece_types=(king,r),
                 initial_position=tuple(tuple(baseboard[y*4:y*4+4]) for y in range(4)),
                 drop_allowed={'R': ((False,)*16, (False,)*16)},
                 capture_disposition='remove_from_game',max_ply=64,repetition_limit=3)
    c = compile_ruleset(replace(rs, **changes))
    from generic_chess.core.position import GameState, HistoryRecord
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.terminal import terminal_result, TerminalResult
    board = [None] * 16
    board[k], board[rook], board[black] = Piece(0,'K','K'), Piece(0,'R','R'), Piece(1,'K','K')
    pos = replace(initial_state(c).position,board=tuple(board),side_to_move=turn)
    key = repetition_identity_key(pos,c)
    s = GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),
                  (HistoryRecord(key,-1,'',False),))
    s = replace(s,terminal_status=terminal_result(s,c))
    return c,s


def win(c,s,depth=5):
    r = prove_win(c,s,target=0,max_nodes=65536,seconds=10,max_depth=depth)
    assert r.status == PROVEN_WIN, r
    assert r.pushes == r.pops
    return r


def test_mate_proof_and_independent_execution():
    c,s = krk()
    r = win(c,s)
    receipt = verify_certificate(c,s,r.certificate,seconds=10)
    assert receipt['verified'] and receipt['terminal_leaves']['checkmate'] >= 1
    cursor = StrategyCursor(c,r.certificate,seconds=10)
    initial_rank = cursor.node.rank
    while cursor.node.edges:
        action = cursor.choose(cursor.state)
        if action is None:
            action = cursor.node.edges[-1][0]
        old_rank = cursor.node.rank
        cursor.advance(cursor.state,action)
        assert cursor.node.rank < old_rank
    assert cursor.state.terminal_status.winner == 0
    assert cursor.state.ply_count <= initial_rank


def test_node_zero_and_depth_cutoff_unknown_not_draw():
    c,s = krk()
    for args,reason in [({'max_nodes':0},'node_budget'),({'max_depth':0},'depth_budget'),
                        ({'seconds':0},'time_budget'),({'cancel':lambda:True},'cancelled')]:
        r=prove_win(c,s,**args)
        assert r.status == UNKNOWN and r.certificate is None and r.reason == reason
        assert r.pushes == r.pops


def test_defender_tree_must_include_every_legal_response():
    # Defender to play in a winning KRK root; there are multiple defenses.
    c,s = krk(k=0,rook=10,black=2,turn=1)
    r=win(c,s,depth=8)
    assert len(r.certificate.tree.edges)>1
    bad=replace(r.certificate,tree=replace(r.certificate.tree,edges=r.certificate.tree.edges[:1]))
    assert not verify_certificate(c,s,bad,seconds=10)['verified']
    assert verify_certificate(c,s,r.certificate,seconds=10)['verified']


def test_forged_rank_terminal_and_illegal_action_rejected():
    c,s=krk();r=win(c,s);tree=r.certificate.tree
    for badtree in [replace(tree,rank=0), replace(tree,terminal_kind='checkmate'),
                    replace(tree,edges=((PassAction(),tree.edges[0][1]),))]:
        assert not verify_certificate(c,s,replace(r.certificate,tree=badtree))['verified']


def test_stale_history_and_ruleset_rejected_by_verifier_and_cursor():
    c,s=krk();r=win(c,s)
    different=replace(s,ply_count=1)
    assert not verify_certificate(c,different,r.certificate)['verified']
    cursor=StrategyCursor(c,r.certificate,seconds=10)
    with pytest.raises(ValueError,match='history'):
        cursor.choose(different)
    c2,_=krk(max_ply=63)
    assert not verify_certificate(c2,s,r.certificate)['verified']
    with pytest.raises(ValueError,match='outside'):
        cursor.advance(s,PassAction())


def test_cancel_inside_push_restores_runtime(monkeypatch):
    c,s=krk();instances=[]
    original=SearchPathRuntime.from_state.__func__
    def factory(cls,*args,**kwargs):
        rt=original(cls,*args,**kwargs);instances.append(rt);return rt
    monkeypatch.setattr(SearchPathRuntime,'from_state',classmethod(factory))
    polls=[0]
    def cancel():
        polls[0]+=1
        return polls[0]>=25
    r=prove_win(c,s,max_nodes=65536,seconds=10,cancel=cancel)
    assert r.status==UNKNOWN and r.reason=='cancelled'
    assert instances[0].position==s.position and instances[0].depth==0
    instances[0].assert_balanced()


def test_actual_terminal_reported_separately():
    c,s=krk();r=win(c,s);cur=StrategyCursor(c,r.certificate,seconds=10)
    while cur.node.edges:
        cur.advance(cur.state,cur.node.edges[0][0])
    result=prove_win(c,cur.state)
    assert result.status==ALREADY_TERMINAL and result.winner==0
    assert result.terminal_kind=='checkmate' and result.certificate is None


@pytest.mark.parametrize('args',[{'max_nodes':-1},{'max_depth':129},{'seconds':float('inf')},{'target':2}])
def test_invalid_budget_rejected(args):
    c,s=krk()
    with pytest.raises(ValueError): prove_win(c,s,**args)


def test_stale_terminal_input_cannot_produce_an_unexecutable_certificate():
    from generic_chess.core.terminal import TerminalResult,TerminalStatus
    c,s=krk()
    stale=replace(s,terminal_status=TerminalResult(TerminalStatus.MAX_PLY))
    result=prove_win(c,stale)
    assert result.status==UNKNOWN and result.reason=='inconsistent_root_terminal'
    good=win(c,s).certificate
    forged=replace(good,root=stale)
    assert not verify_certificate(c,stale,forged)['verified']
