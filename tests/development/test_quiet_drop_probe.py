"""Terminal/history boundaries for the scoped research exclusion prototype."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.quiescence import enemy_board_count,material_inventory,noisy_child
from generic_chess.core.actions import action_is_drop
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.rules.schema import RuleConsecutiveActionAdjudication,RuleNoProgressDraw,RuleRepeatedCycleTargetCondition
from scripts.search_backend_comparison import CASES,CoreBoard
from scripts.quiet_drop_probe import QuietDropProbe

def context(rules=None,capture_only=False):
    c=compile_ruleset_for_execution(rules or build_builtin_ruleset('standard_shogi'))
    core=CoreBoard(next(x for x in CASES if x['id']=='shogi-drop'),c)
    rt=core.runtime
    return SimpleNamespace(runtime=rt,compiled=c,checkpoint=lambda:None,
        tuning=SearchTuning(use_capture_only_qsearch=capture_only),stats=SearchStatistics())

@pytest.mark.parametrize('capture_only',[False,True])
def test_quiet_checking_drop_support_matches_complete_core_children(capture_only):
    ctx=context(capture_only=capture_only);rt=ctx.runtime;root=rt.position
    probe=QuietDropProbe();engine=probe.prepare(ctx);assert engine is not None, dict(probe.counts)
    enemies=enemy_board_count(root,root.side_to_move);inventory=material_inventory(root)
    actions=[a for a in rt.legal_actions() if action_is_drop(a)]
    excluded=retained=0
    for a in actions:
        decision=probe.exclude(ctx,a,engine,enemies,inventory)
        with rt.pushed(a):
            expected=not noisy_child(a,rt.state,root.side_to_move,enemies,inventory,
                lambda:rt.in_check(1-root.side_to_move),capture_only=capture_only)
        assert decision==expected
        excluded+=decision;retained+=not decision
    assert excluded>0
    if not capture_only:assert retained>0
    else:assert ctx.stats.nonchecking_drop_excluded==0
    assert rt.position is root;rt.assert_balanced()

@pytest.mark.parametrize('boundary',['max_ply','automatic','repetition','opaque'])
def test_boundary_retains_original_fullpush(boundary):
    ctx=context();rt=ctx.runtime;probe=QuietDropProbe();assert probe.prepare(ctx) is not None
    if boundary=='max_ply':rt.ply_count=511
    elif boundary=='automatic':rt.ply_count=499
    elif boundary=='repetition':
        entry=next(entry for bucket in rt._occurrences.values() for entry in bucket);entry.count=3
    else:rt._opaque_imported_keys.add('unresolved-test-key')
    assert probe.prepare(ctx) is None
    # This is a guard unit test, not a legal played history or terminal result.

@pytest.mark.parametrize('field,value',[
    ('consecutive_action_adjudications',(RuleConsecutiveActionAdjudication('pass',2,'DRAW'),)),
    ('no_progress_draw',RuleNoProgressDraw(20,True)),
    ('repeated_cycle_target_conditions',(RuleRepeatedCycleTargetCondition(0),)),
])
def test_history_sensitive_configurations_decline(field,value):
    rules=replace(build_builtin_ruleset('standard_shogi'),pass_enabled=field=='consecutive_action_adjudications',**{field:value})
    c=compile_ruleset_for_execution(rules)
    from generic_chess.session.session import GameSession
    state=GameSession(c).state
    if field=='no_progress_draw':
        # Current Core search itself rejects this configuration. Verify that
        # the exclusion gate also declines without claiming execution support.
        with pytest.raises(NotImplementedError,match='no-progress'):
            SearchPathRuntime(state,c)
        rt=SimpleNamespace(ply_count=0)
    else:
        rt=SearchPathRuntime.from_state(state,c,history_witnesses=(state.position,))
    ctx=SimpleNamespace(runtime=rt,compiled=c)
    assert QuietDropProbe().prepare(ctx) is None

def test_poll_failure_does_not_mutate_parent():
    ctx=context();rt=ctx.runtime;probe=QuietDropProbe();engine=probe.prepare(ctx)
    action=next(a for a in rt.legal_actions() if action_is_drop(a));root=rt.position
    def interrupted():raise RuntimeError('poll')
    ctx.checkpoint=interrupted
    with pytest.raises(RuntimeError,match='poll'):
        probe.exclude(ctx,action,engine,enemy_board_count(root,0),material_inventory(root))
    assert rt.position is root;rt.assert_balanced()

@pytest.mark.parametrize('effect_kind',['plain','auxiliary','transform','offtarget_capture','quantity'])
@pytest.mark.parametrize('capture_only',[False,True])
def test_actual_compound_drop_effects_retain_original_qsignals(effect_kind,capture_only):
    from conftest import make_state
    from rule_semantics_ir_fixtures import weird_rulesets
    from generic_chess.rules.schema import RuleActionEffect,RuleSquareRef,RuleTypeRef
    base=weird_rulesets()[1];promotion=weird_rulesets()[2]
    drop=base.semantic_actions[0]
    effects=drop.effects;aux=()
    if effect_kind=='auxiliary':
        aux=promotion.semantic_actions[0].aux_state
        effects+=(RuleActionEffect('set_bool',slot_name='temp_right',value=1),)
    elif effect_kind=='transform':
        effects+=(RuleActionEffect('set_current_type',square_ref=RuleSquareRef('fixed',square=(1,1)),type_ref=RuleTypeRef('explicit',type_id='TP')),)
    elif effect_kind=='offtarget_capture':
        effects+=(RuleActionEffect('remove',square_ref=RuleSquareRef('fixed',square=(2,6)),piece_owner='opponent',disposition='remove_from_game'),)
    elif effect_kind=='quantity':
        effects+=(RuleActionEffect('place',to_ref=RuleSquareRef('fixed',square=(0,2)),piece_type_ref=RuleTypeRef('action_base')),)
    rules=replace(base,piece_types=promotion.piece_types,semantic_actions=(replace(drop,effects=effects,aux_state=aux),),drop_allowed={'R':((True,)*64,)*2,'TP':((False,)*64,)*2})
    c=compile_ruleset_for_execution(rules)
    state=make_state(c,['.......k','..r.....','........','........','........','........','.R......','K.......'],hands=([('R',1)],()))
    # Explicit fresh snapshot with canonical semantic identity, rather than
    # conftest's legacy-only position_key alias (which correctly declines).
    from generic_chess.core.identity import position_identity_key
    from generic_chess.core.position import HistoryRecord
    from generic_chess.core.terminal import terminal_result
    key=position_identity_key(state.position,c)
    state=replace(state,repetition_counts=((key,1),),history=(HistoryRecord(key,-1,'',False),))
    state=replace(state,terminal_status=terminal_result(state,c))
    rt=SearchPathRuntime.from_state(state,c,history_witnesses=(state.position,))
    ctx=SimpleNamespace(runtime=rt,compiled=c,checkpoint=lambda:None,tuning=SearchTuning(use_capture_only_qsearch=capture_only),stats=SearchStatistics())
    probe=QuietDropProbe();engine=probe.prepare(ctx);assert engine is not None, dict(probe.counts)
    root=rt.position;enemies=enemy_board_count(root,0);inventory=material_inventory(root)
    actions=[a for a in rt.legal_actions() if action_is_drop(a)]
    assert actions
    excluded=0
    for a in actions:
        outcome=probe.exclude(ctx,a,engine,enemies,inventory)
        with rt.pushed(a):
            expected=not noisy_child(a,rt.state,0,enemies,inventory,lambda:rt.in_check(1),capture_only=capture_only)
            if effect_kind=='auxiliary':assert dict(rt.position.aux_state)[(0,-1)]==1
            if effect_kind=='transform':assert rt.position.board[9].current_type_id=='TP'
            if effect_kind=='offtarget_capture':assert rt.position.board[50] is None
        assert outcome==expected
        excluded+=outcome
    if effect_kind in ('transform','offtarget_capture','quantity'):assert excluded==0
    else:assert excluded>0
    assert rt.position is root;rt.assert_balanced()

@pytest.mark.parametrize('capture_only',[False,True])
def test_actual_nonchecking_drop_stalemate_is_retained(capture_only):
    from conftest import make_state
    from generic_chess.core.identity import position_identity_key
    from generic_chess.core.position import HistoryRecord
    from generic_chess.core.terminal import terminal_result,TerminalStatus
    rules=build_builtin_ruleset('western_chess')
    masks=dict(rules.drop_allowed);masks['Q']=((True,)*64,)*2
    c=compile_ruleset_for_execution(replace(rules,drop_allowed=masks))
    state=make_state(c,['k.......','........','..K.....','........','........','........','........','........'],hands=([('Q',1)],()))
    key=position_identity_key(state.position,c);state=replace(state,repetition_counts=((key,1),),history=(HistoryRecord(key,-1,'',False),))
    state=replace(state,terminal_status=terminal_result(state,c))
    rt=SearchPathRuntime.from_state(state,c,history_witnesses=(state.position,))
    ctx=SimpleNamespace(runtime=rt,compiled=c,checkpoint=lambda:None,tuning=SearchTuning(use_capture_only_qsearch=capture_only),stats=SearchStatistics())
    probe=QuietDropProbe();engine=probe.prepare(ctx);assert engine is not None
    action=next(a for a in rt.legal_actions() if action_is_drop(a) and a.to_square.file==1 and a.to_square.rank==5)
    root=rt.position;enemies=enemy_board_count(root,0);inventory=material_inventory(root)
    assert not probe.exclude(ctx,action,engine,enemies,inventory)
    assert probe.counts['retain_no_legal']==1
    with rt.pushed(action):
        assert not rt.in_check(1)
        assert rt.terminal_status.status is TerminalStatus.STALEMATE
        assert material_inventory(rt.position)==inventory
        assert noisy_child(action,rt.state,0,enemies,inventory,lambda:rt.in_check(1),capture_only=capture_only)
    assert rt.position is root;rt.assert_balanced()
