"""Scope guards and literal terminal controls for the finite no-mate theorem."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import pytest

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import legal_successors
from scripts.leaper_single_parity_truth import admit,domain,escape_table,bind
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_explorer_truth import load


@pytest.fixture(scope='module')
def worlds():
    # The compact public packet is installed with the research result; local
    # preparation is not a prerequisite for these semantic controls.
    return load('docs/research/data/leaper_single_parity_20261023/inputs.json.gz')['worlds']


@pytest.mark.parametrize('change',[
    lambda r:r.update(metadata={'extra':'unreviewed'}),
    lambda r:r.update(stalemate_result='loss'),
    lambda r:r.update(capture_disposition='to_hand'),
    lambda r:r['piece_types'][0]['movement_atoms'].pop(),
    lambda r:r['piece_types'][1].update(is_anchor=True),
    lambda r:r['drop_allowed']['A'][0].__setitem__(0,True),
    lambda r:r.update(unknown_terminal_effect=True),
])
def test_outside_scope_not_draw(worlds,change):
    r=deepcopy(worlds[0]['rule']);change(r)
    with pytest.raises((ValueError,TypeError)):admit(r)


def test_mixed_parity_is_unknown_not_positive(worlds):
    w=next(w for w in worlds if w['masks']==[5])
    with pytest.raises(ValueError,match='one parity'):admit(w['rule'])
    assert admit(w['rule'],require_parity=False)[2]==[0,1]


def test_global_geometry_includes_all_legal_king_pairs():
    rows=escape_table()
    assert len({(k,e)for k,e,u,v in rows})==156
    assert all((abs(u%4-k%4)+abs(u//4-k//4),abs(v%4-k%4)+abs(v//4-k//4))==(1,1)for k,e,u,v in rows)


def test_extra_actor_and_hand_or_aux_are_outside_domain(worlds):
    _,c,_=admit(worlds[0]['rule']);p=c.initial_position
    board=list(p.board);board[8]=Piece(1,'A','A')
    with pytest.raises(ValueError):domain(replace(p,board=tuple(board)))
    with pytest.raises(ValueError):domain(replace(p,hands=(Hands((('A',1),)),Hands())))
    with pytest.raises(ValueError):domain(replace(p,aux_state=(((1,0),True),)))


def test_one_bit_mixed_control_is_actual_core_mate(worlds):
    w=next(w for w in worlds if w['masks']==[5]);_,c,_=admit(w['rule'],require_parity=False)
    board=[None]*16
    for i,o,t in ((0,1,'K'),(6,0,'K'),(9,0,'A')):board[i]=Piece(o,t,t)
    state=fresh_state(replace(c.initial_position,board=tuple(board),side_to_move=0),c)
    ac,ch=next((ac,ch)for ac,ch in legal_successors(state,c)if ac.from_square.file==1 and ac.from_square.rank==2 and ac.to_square.file==0 and ac.to_square.rank==2)
    assert ch.terminal_status.status.value=='checkmate'and ch.terminal_status.winner==0
    # Same physical placement, mask1 (only orbit bit2 removed) cannot mate.
    _,single,_=admit(worlds[0]['rule'])
    control=fresh_state(replace(single.initial_position,board=tuple(board),side_to_move=0),single)
    assert all(z.terminal_status.winner is None for _,z in legal_successors(control,single))


@pytest.mark.parametrize('field',['full_rule_json_sha256','full_initial_record_json_sha256','full_state_sha256'])
def test_exact_target_binding_rejects_tampering(worlds,field):
    data=load('docs/research/data/leaper_single_parity_20261023/inputs.json.gz')
    bad=deepcopy(data['handoff']);bad['rows'][0][field]='0'*64
    with pytest.raises(ValueError,match='binding mismatch'):bind(worlds,bad,{(m,):True for m in(1,2,4,8,16,6,9)})
