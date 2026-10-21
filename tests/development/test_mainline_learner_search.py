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
