"""Minimal scientific checks: representation invariance and valid teacher labels."""
from dataclasses import replace
import pytest

torch=pytest.importorskip('torch')
from scripts.leaper_neural_model import LeaperValueNet,graph_from_session,batch_graphs
from scripts.leaper_neural_experiment import make_rules,solve_teacher
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession


def example(size=4):
    r=make_rules(size,1,[(0,0,'K'),(size*size-1,1,'K'),(1,0,'A'),(size*size-2,1,'B')])
    return r,GameSession(compile_ruleset(r))


def test_structure_not_names_and_same_parameters_across_sizes():
    torch.manual_seed(11);model=LeaperValueNet();r,s=example();before=[(n,tuple(p.shape)) for n,p in model.named_parameters()]
    renamed=replace(r,piece_types=tuple(replace(p,type_id='renamed_'+p.type_id,name='unrelated',movement_atoms=tuple(reversed(p.movement_atoms))) for p in reversed(r.piece_types)),
        initial_position=tuple(tuple(None if p is None else replace(p,base_type_id='renamed_'+p.base_type_id,current_type_id='renamed_'+p.current_type_id) for p in row) for row in r.initial_position),
        drop_allowed={'renamed_'+key:value for key,value in r.drop_allowed.items()})
    t=GameSession(compile_ruleset(renamed))
    a=model(batch_graphs([graph_from_session(r,s)]));b=model(batch_graphs([graph_from_session(renamed,t)]))
    torch.testing.assert_close(a,b,atol=1e-6,rtol=1e-5)
    r5,s5=example(5);assert model(batch_graphs([graph_from_session(r5,s5)])).shape==(1,3)
    assert before==[(n,tuple(p.shape)) for n,p in model.named_parameters()]
    assert len(graph_from_session(r,s).nodes)==16 and len(graph_from_session(r5,s5).nodes)==25
    # More types and pieces still share the same architecture. Rectangular
    # execution is not yet admitted by Core's current compiler, so the actual
    # first experiment remains square4x4/5x5 rather than faking a second engine.
    rows=[list(row) for row in r5.initial_position];rows[4][0]=Piece(0,'novel','novel')
    richer=replace(r5,piece_types=r5.piece_types+(PieceType('novel','not-a-channel',(LeapAtom((1,0)),LeapAtom((2,-1)),LeapAtom((-1,2)))),),
        initial_position=tuple(tuple(row) for row in rows),drop_allowed={key:((False,)*25,)*2 for key in ('A','B','novel')})
    rs=GameSession(compile_ruleset(richer));g=graph_from_session(richer,rs)
    assert len(g.nodes)==25 and len(g.type_features)==4 and model(batch_graphs([g])).shape==(1,3)
    assert before==[(n,tuple(p.shape)) for n,p in model.named_parameters()]



def test_teacher_respects_clock_and_known_royal_mate():
    r,s=example();r=replace(r,max_ply=1);s=GameSession(compile_ruleset(r))
    assert solve_teacher(s,1000)[0]=='DRAW'
    s.submit(s.legal_actions()[0]);assert s.result.status.value=='max_ply'
    assert solve_teacher(s,1000)[0]=='DRAW'
    royal=PieceType('K','K',tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)),is_anchor=True)
    queen=PieceType('Q','irrelevant',tuple(LeapAtom((dx,dy)) for d in (1,2,3) for dx,dy in ((d,0),(-d,0),(0,d),(0,-d),(d,d),(d,-d),(-d,d),(-d,-d))))
    board=[None]*16;board[9]=Piece(0,'K','K');board[15]=Piece(1,'K','K');board[4]=Piece(0,'Q','Q')
    mate=replace(r,piece_types=(royal,queen),initial_position=tuple(tuple(board[y*4:y*4+4]) for y in range(4)),drop_allowed={'Q':((False,)*16,)*2},max_ply=4)
    ms=GameSession(compile_ruleset(mate));assert ms.result.status.value=='ongoing'
    assert solve_teacher(ms,3000)[0]=='WIN'
    from scripts.leaper_neural_teacher import solve_session
    limited=solve_session(mate,ms,max_nodes=1)
    assert limited['label']=='WIN' and limited['basis']=='proven_winning_action'
    assert limited['bounds']==[1,1]
    assert not limited['all_root_actions_solved']
    fresh_rules,fresh=example()
    unknown=solve_session(fresh_rules,fresh,max_nodes=0)
    assert unknown['status']=='UNKNOWN' and unknown['bounds']==[-1,1]


def test_core_terminal_overrides_neural_value():
    r,s=example();r=replace(r,max_ply=1);s=GameSession(compile_ruleset(r));s.submit(s.legal_actions()[0])
    assert LeaperValueNet().probabilities(r,s).tolist()==[0.,1.,0.]


def test_partial_nonloss_proof_is_not_an_exact_draw():
    from scripts.leaper_neural_teacher import solve_session
    r,_=example();r=replace(r,max_ply=2);s=GameSession(compile_ruleset(r))
    partial=solve_session(r,s,max_nodes=2)
    assert partial['label'] is None and partial['status']=='UNKNOWN'
    assert partial['bounds']==[0,1]
    complete=solve_session(r,s,max_nodes=1000)
    assert complete['label']=='DRAW' and complete['bounds']==[0,0]
