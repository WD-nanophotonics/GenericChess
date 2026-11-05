"""Opt-in conditional counts: semantic units and actual q0/PV consumers."""
from dataclasses import replace
import json
from pathlib import Path
import pytest
from generic_chess.core.position import Hands
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE,AlphaBeta
from generic_chess.learning.mainline_search import search
from generic_chess.session.session import GameSession
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleDeclaration
from product.test_learning_features import _compiled,_position
from scripts.generic_proof_fixtures import krk_ruleset
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore


def env_and_position():
    c=_compiled();env=FixedScaleSessionEnv(GameSession(c),unit_type='A',feature_mode='count_pairs')
    pos=_position(c,[('A',0,0,1),('A',0,1,1),('B',0,2,1),('A',1,0,2),('B',1,1,2),('B',1,2,2)],
        hands=(Hands((('A',2),('B',1))),Hands((('A',1),('B',3)))))
    return env,pos


def test_distinct_actor_pairs_board_and_hand_units_and_owner_antisymmetry():
    env,pos=env_and_position();values=dict(zip(env.names,env.features_at(pos)))
    assert env.names[0]==('board','A') and len(env.names)==14
    assert values[('board','A')]==1 and values[('hand','B')]==-2
    assert values[('pair','board','A','board','A')]==1
    assert values[('pair','board','B','board','B')]==-1
    assert values[('pair','board','A','board','B')]==0
    assert values[('pair','board','A','hand','A')]==3
    assert values[('pair','hand','A','hand','B')]==-1
    assert values[('pair','hand','B','hand','B')]==-3
    flipped=replace(pos,board=tuple(None if p is None else replace(p,owner=1-p.owner) for p in pos.board),
        hands=tuple(reversed(pos.hands)),side_to_move=1-pos.side_to_move)
    assert env.features_at(flipped)==tuple(-x for x in env.features_at(pos))
    single=_position(env.session.compiled,[('A',0,0,1)])
    assert dict(zip(env.names,env.features_at(single)))[('pair','board','A','board','A')]==0


def test_zero_pair_initialization_preserves_linear_critic_and_fixed_unit():
    env,pos=env_and_position();linear=FixedScaleSessionEnv(env.session,unit_type='A')
    base=Model([1.,.7,.2,-.4]);extended=Model(base.weights+[0.]*(len(env.names)-len(base.weights)))
    assert base.raw(linear.features_at(pos))==extended.raw(env.features_at(pos))
    gradient=extended.gradient(env.features_at(pos))
    assert gradient[0]==0 and any(gradient[len(base.weights):])
    extended.apply([.01*g for g in gradient]);assert extended.weights[0]==1.


@pytest.mark.parametrize('prefix', (0,1))
def test_mainline_q0_and_literal_pv_keep_nonzero_pair_basis_and_replay_mode(prefix):
    p=Path(__file__).resolve().parents[2]/'docs/research/data/aux_capture_material_20261105/plan.json'
    row=json.loads(p.read_bytes())['worlds']['0']['train']
    env=FixedScaleSessionEnv(restore(L.compile_rule(L.ruleset_from_dict(row['RuleSet'])),row['record']),unit_type='A',feature_mode='count_pairs')
    if prefix:
        env.push(env.actions()[0])
        assert env.terminal() is None and env.player()==1
    w=[1.,1.,1.,0.,0.,0.]+[.03*(i+1) for i in range(21)]
    model=Model(w);before=env.record()
    r=search(env,model,depth=2,nodes=2048,seconds=10)
    assert r.complete and r.completed_depth==2 and not r.pv_terminal
    leaf=env.replay();assert leaf.feature_mode=='count_pairs' and leaf.names==env.names
    for a in r.pv_choices:leaf.push(a)
    assert tuple(r.pv_phi)==leaf.features() and len(r.pv_phi)==27
    assert r.value==model.raw(leaf.features()) and env.record()==before
    # Fractional nonlinear critics must retain the independent complete q0
    # value, including on the opposite seat; PV ties may choose differently.
    reference=AlphaBeta(2,0).search(env,model,nodes=16384,seconds=10,seed=4321)
    assert reference.complete and reference.value==pytest.approx(r.value,abs=1e-12)
    assert env.record()==before
    assert leaf.search_view().features()==leaf.features()


@pytest.mark.parametrize('outcome,expected', [('WIN',MATE),('LOSS',-MATE)])
def test_literal_terminal_bypasses_pair_model_and_unknown_mode_rejects(outcome,expected):
    rules=replace(krk_ruleset(4),declarations=(RuleDeclaration('claim',0,require_not_in_check=False,failure_outcome=outcome),))
    s=GameSession(compile_ruleset_for_execution(rules));s.declare('claim')
    env=FixedScaleSessionEnv(s,unit_type='R',feature_mode='count_pairs')
    model=Model([1.]*len(env.names))
    def forbidden(*args):raise AssertionError('terminal used approximate pair critic')
    model.raw=forbidden
    r=search(env,model,depth=2)
    assert r.complete and r.pv_terminal and r.value==expected and r.pv_phi is None and r.nodes==0
    with pytest.raises(ValueError,match='feature mode'):
        FixedScaleSessionEnv(s,unit_type='R',feature_mode='made_up')


def test_type_renaming_preserves_physical_interactions_and_declared_unit():
    from native_test_helpers import simple_ruleset
    env,pos=env_and_position();compiled=env.session.compiled
    rename={'A':'Z','B':'A','K':'K'};inverse={v:k for k,v in rename.items()}
    def piece(p):
        return None if p is None else replace(p,base_type_id=rename[p.base_type_id],current_type_id=rename[p.current_type_id])
    initial=compiled.initial_position.board
    rows=[[piece(initial[r*4+f]) for f in range(4)] for r in range(4)]
    types=[replace(t,type_id=rename[t.type_id],name=rename[t.type_id]) for t in compiled.piece_types]
    renamed=simple_ruleset(types,rows,drop_types=('Z','A'))
    other=FixedScaleSessionEnv(GameSession(renamed),unit_type='Z',feature_mode='count_pairs')
    target=replace(pos,board=tuple(map(piece,pos.board)),
        hands=tuple(Hands(tuple(sorted((rename[t],n) for t,n in h.counts))) for h in pos.hands),ruleset_fingerprint=renamed.ruleset_fingerprint)
    def canonical(name,back):
        if name[0]=='pair':
            left=(name[1],back.get(name[2],name[2]));right=(name[3],back.get(name[4],name[4]))
            return ('pair',)+tuple(sorted((left,right)))
        return (name[0],back.get(name[1],name[1]))
    original={canonical(n,{}):x for n,x in zip(env.names,env.features_at(pos))}
    transformed={canonical(n,inverse):x for n,x in zip(other.names,other.features_at(target))}
    assert original==transformed
    assert other.names[0]==('board','Z')  # SAME physical unit, not lexical A.
