"""Real public-search/learner boundary risks; no second search implementation."""
from dataclasses import replace

import pytest

from generic_chess.learning.incremental import (
    AlphaBeta, BudgetEnd, FixedScaleSessionEnv, Model, TDLeafEpisode, play_episode,
)
from generic_chess.learning.mainline_search import search
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleDeclaration, RuleNoProgressDraw
from generic_chess.session.session import GameSession
from scripts.generic_proof_fixtures import krk_ruleset
from rule_semantics_ir_fixtures import weird_rulesets


@pytest.mark.parametrize('which', [0, 1, 2])
def test_shared_q0_float_target_matches_literal_generic_pv_and_reference(which):
    compiled = compile_ruleset_for_execution(weird_rulesets()[which])
    unit = next(t.type_id for t in compiled.support.type_metadata.values() if not t.is_anchor)
    env = FixedScaleSessionEnv(GameSession(compiled), unit_type=unit)
    before = env.record()
    model = Model([1.] + [.731 + .013 * i for i in range(len(env.names) - 1)])
    public = search(env, model, depth=2, nodes=20000, seconds=10)
    reference = AlphaBeta(2, 0).search(env, model, nodes=20000, seconds=10, seed=73)
    assert public.complete and reference.complete
    assert public.value == pytest.approx(reference.value, abs=1e-10)
    if not public.pv_terminal:
        assert public.value == pytest.approx(model.raw(public.pv_phi), abs=1e-10)
    assert env.record() == before
    assert public.nodes == sum(a.nodes for a in public.attempts)
    assert public.completed_depth == 2
    literal=FixedScaleSessionEnv(env.session,unit_type=unit)
    for step in public.pv_choices:literal.push(step)
    assert public.pv_choices[0]==public.action
    if public.pv_terminal:
        assert literal.terminal()*1_000_000==public.value
    else:
        assert len(public.pv_choices)==2
        assert literal.features()==public.pv_phi


@pytest.mark.parametrize('nodes', [1, 3, 100])
def test_shared_q0_pays_aborted_work_without_a_fallback_target(nodes):
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))),unit_type='R')
    before = env.record()
    receipt = search(env, Model([1., .731]), depth=4, nodes=nodes, seconds=10)
    assert receipt.nodes <= nodes
    assert receipt.nodes == sum(a.nodes for a in receipt.attempts)
    if not receipt.complete:
        assert receipt.action is receipt.value is receipt.pv_phi is None
        assert receipt.samples == ()
    assert env.record() == before


def test_shared_q0_cancel_after_search_discards_target_and_preserves_paid_nodes(monkeypatch):
    from generic_chess.learning import mainline_search
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))),unit_type='R')
    before = env.record()
    real = mainline_search.AlphaBetaPlayer.choose_action
    done = [False]
    def wrapped(*args, **kwargs):
        result = real(*args, **kwargs)
        done[0] = True
        return result
    def cancel():
        if done[0]: raise BudgetEnd('STOPPED_USER')
    monkeypatch.setattr(mainline_search.AlphaBetaPlayer,'choose_action',wrapped)
    receipt = search(env, Model([1., .731]), depth=1, cancel=cancel)
    assert not receipt.complete and receipt.value is None
    assert receipt.reason == 'STOPPED_USER' and receipt.nodes > 0
    assert env.record() == before


@pytest.mark.parametrize('fraction,usable',[(0.,False),(.1,True)])
def test_opt_in_pv_reserve_uses_same_deadline_for_a_literal_last_iteration(monkeypatch,fraction,usable):
    from generic_chess.learning import mainline_search
    env=FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))),unit_type='R')
    before=env.record();clock=[0.];seen=[]
    monkeypatch.setattr(mainline_search,'perf_counter',lambda:clock[0])
    real=mainline_search.AlphaBetaPlayer.choose_action
    def finish_near_allocated_deadline(player,session,limits,**kwargs):
        seen.append(limits.max_time_seconds)
        decision=real(player,session,limits,**kwargs)
        # Simulate a bounded search returning just after its own time slice.
        clock[0]=limits.max_time_seconds+.01
        return decision
    monkeypatch.setattr(mainline_search.AlphaBetaPlayer,'choose_action',finish_near_allocated_deadline)
    receipt=search(env,Model([1.,.731]),depth=1,seconds=1.,pv_reserve_fraction=fraction)
    assert seen==[1-fraction]and receipt.complete==usable
    assert env.record()==before
    if usable:
        assert receipt.seconds<1 and receipt.pv_choices
        leaf=FixedScaleSessionEnv(env.session,unit_type='R')
        for step in receipt.pv_choices:leaf.push(step)
        assert receipt.pv_terminal or leaf.features()==receipt.pv_phi
    else:
        assert receipt.reason=='PV_REPLAY_TIME_CAP'
        assert receipt.action is receipt.value is receipt.pv_phi is None


@pytest.mark.parametrize('fraction',[-.1,1.,float('nan')])
def test_invalid_pv_reserve_is_rejected_before_search(fraction):
    env=FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))),unit_type='R')
    with pytest.raises(ValueError,match='PV reserve'):
        search(env,Model([1.,.731]),pv_reserve_fraction=fraction)


@pytest.mark.parametrize('outcome', ['RESTART', 'NO_CONTEST'])
def test_neutral_public_search_score_never_becomes_draw_label(outcome):
    rules = replace(krk_ruleset(4), declarations=(RuleDeclaration(
        'neutral',0,require_not_in_check=False,failure_outcome=outcome),))
    env = FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(rules)),unit_type='R')
    receipt = search(env,Model([1.,.731]),depth=2)
    assert not receipt.complete and receipt.value is None
    assert 'UNKNOWN' in receipt.reason
    model=Model([1.,.731]);learner=TDLeafEpisode()
    learner.observe(model,receipt)
    assert learner.finish(model,None)['observed_searches']==0


@pytest.mark.parametrize('owner', [0, 1])
def test_public_winning_declaration_is_rule_verified_player0_terminal(owner):
    rules = replace(krk_ruleset(4), declarations=(RuleDeclaration(
        'win',owner,require_not_in_check=False,failure_outcome='WIN'),))
    session=GameSession(compile_ruleset_for_execution(rules))
    if owner==1:session.submit(session.legal_actions()[0])
    env=FixedScaleSessionEnv(session,unit_type='R')
    receipt=search(env,Model([1.,.731]),depth=2)
    assert receipt.complete and receipt.pv_terminal
    assert receipt.value==(1 if owner==0 else -1)*1_000_000
    assert receipt.action.declaration_id=='win'
    env.push(receipt.action)
    assert env.terminal()==(1 if owner==0 else -1)


def test_shared_search_uses_real_no_progress_history_instead_of_horizon_zero():
    rules=replace(krk_ruleset(4),no_progress_draw=RuleNoProgressDraw(1,True))
    env=FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(rules)),unit_type='R')
    receipt=search(env,Model([1.,.731]),depth=2)
    assert receipt.complete and receipt.pv_terminal and receipt.value==0
    env.push(receipt.action)
    assert env.terminal()==0 and env.replay().record()==env.record()


def test_nonliteral_public_score_is_rejected_without_a_fitted_leaf(monkeypatch):
    from generic_chess.learning import mainline_search
    env=FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))),unit_type='R')
    real=mainline_search.AlphaBetaPlayer.choose_action
    def changed(*args,**kwargs):
        decision=real(*args,**kwargs)
        return replace(decision,score=decision.score+.25)
    monkeypatch.setattr(mainline_search.AlphaBetaPlayer,'choose_action',changed)
    receipt=search(env,Model([1.,.731]),depth=1)
    assert not receipt.complete and receipt.reason=='PV_VALUE_MISMATCH'
    assert receipt.value is receipt.pv_phi is None and receipt.nodes>0


def test_full_history_reuse_keeps_same_board_distinct_draw_frontiers(monkeypatch):
    from pathlib import Path
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'product'))
    from test_native_history import _cycle_ruleset, _session_at_ply
    compiled=_cycle_ruleset()
    values=[]
    for ply in (3,11):
        env=FixedScaleSessionEnv(_session_at_ply(compiled,ply),unit_type='F')
        before=env.record()
        model=Model([1.]+[.731]*(len(env.names)-1))
        receipt=search(env,model,depth=1)
        assert receipt.complete and env.record()==before
        values.append((receipt.pv_terminal,receipt.value))
    assert values[0][0] is False and values[1]==(True,0)


def test_generic_episode_defaults_to_public_search_and_updates_same_learner(monkeypatch):
    from generic_chess.learning import mainline_search
    calls=[]
    real=mainline_search.AlphaBetaPlayer.choose_action
    def observed(*args,**kwargs):
        decision=real(*args,**kwargs)
        calls.append(decision)
        return decision
    monkeypatch.setattr(mainline_search.AlphaBetaPlayer,'choose_action',observed)
    env=FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))),unit_type='R')
    model=Model([1.,.731])
    result=play_episode(env,model,opponent=Model([1.,1.]),learner=TDLeafEpisode(),
                        depth=2,horizon=8,max_nodes=2000)
    assert calls and result.queries==len(calls)
    assert result.nodes==sum(d.nodes+d.qnodes for d in calls)<=2000
    assert result.update['observed_searches']<=result.queries
    assert env.replay().record()==env.record()


def test_model_epoch_and_shallower_request_do_not_reuse_a_previous_player():
    env=FixedScaleSessionEnv(GameSession(compile_ruleset_for_execution(krk_ruleset(4))),unit_type='R')
    before=env.record()
    old=Model([1.,.731])
    search(env,old,depth=3,nodes=20000,seconds=10)
    new=Model([1.,-2.31])
    fresh=search(env,new,depth=1,nodes=20000,seconds=10)
    control=search(env,new,depth=1,nodes=20000,seconds=10,use_tt=False,use_ordering=False)
    assert fresh.complete and control.complete
    assert fresh.value==pytest.approx(control.value,abs=1e-10)
    assert fresh.completed_depth==1 and env.record()==before
    if not fresh.pv_terminal:
        assert fresh.value==pytest.approx(new.raw(fresh.pv_phi),abs=1e-10)


@pytest.mark.parametrize('tt,ordering', [(False,False),(False,True),(True,False),(True,True)])
def test_existing_search_switches_preserve_full_depth_material_value(tt,ordering):
    compiled=compile_ruleset_for_execution(weird_rulesets()[0])
    unit=next(t.type_id for t in compiled.support.type_metadata.values() if not t.is_anchor)
    env=FixedScaleSessionEnv(GameSession(compiled),unit_type=unit)
    model=Model([1.]+[.731+.013*i for i in range(len(env.names)-1)])
    result=search(env,model,depth=3,nodes=20000,seconds=10,use_tt=tt,use_ordering=ordering)
    reference=AlphaBeta(3,0).search(env,model,nodes=20000,seconds=10,seed=73)
    assert result.complete and reference.complete and result.completed_depth==3
    assert result.value==pytest.approx(reference.value,abs=1e-10)


def test_completed_root_win_from_interrupted_deeper_layer_is_not_a_td_target(monkeypatch):
    from scripts.leaper_microgames import make_rules
    from generic_chess.learning import mainline_search
    compiled=compile_ruleset_for_execution(make_rules(width=4,horizon=101281,layouts=[(7,11,0,15)]))
    env=FixedScaleSessionEnv(GameSession(compiled),unit_type='M');seen=[]
    real=mainline_search.AlphaBetaPlayer.choose_action
    def observed(*args,**kwargs):
        decision=real(*args,**kwargs);seen.append(decision);return decision
    monkeypatch.setattr(mainline_search.AlphaBetaPlayer,'choose_action',observed)
    receipt=search(env,Model([1.,1.]),depth=12,nodes=8192,seconds=10)
    assert seen[0].result_source=='completed_root_win'
    assert seen[0].completed_depth>0 and receipt.nodes==8192
    assert not receipt.complete
    assert receipt.action is receipt.value is receipt.pv_phi is None
    assert receipt.reason=='NO_LITERAL_COMPLETED_RESULT:completed_root_win'
    assert receipt.pv_choices==()
