"""Finite board-action boundaries for the research-only quiet exclusion."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.quiescence import enemy_board_count,material_inventory,noisy_child
from generic_chess.core.actions import action_is_board
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.terminal import terminal_result,TerminalStatus
from scripts.quiet_action_probe import QuietActionProbe
from conftest import make_state
from rule_semantics_ir_fixtures import castling_ruleset

def context(rules,rows):
    c=compile_ruleset_for_execution(rules);state=make_state(c,rows)
    key=position_identity_key(state.position,c)
    state=replace(state,repetition_counts=((key,1),),history=(HistoryRecord(key,-1,'',False),))
    state=replace(state,terminal_status=terminal_result(state,c))
    rt=SearchPathRuntime.from_state(state,c,history_witnesses=(state.position,))
    return SimpleNamespace(runtime=rt,compiled=c,checkpoint=lambda:None,tuning=SearchTuning(),stats=SearchStatistics())

@pytest.mark.parametrize('capture_only',[False,True])
@pytest.mark.parametrize('kind',['promotion','stalemate','compound'])
def test_complete_core_board_signals_and_restoration(kind,capture_only):
    if kind=='compound':
        rules=castling_ruleset();rows=['....k...','........','........','........','........','........','........','R...K..R']
    elif kind=='promotion':
        rules=build_builtin_ruleset('western_chess');rows=['.......k','P.......','........','........','........','........','........','.......K']
    else:
        rules=build_builtin_ruleset('western_chess');rows=['k.......','........','..K.....','........','........','........','........','.Q......']
    ctx=context(rules,rows);ctx.tuning=SearchTuning(use_capture_only_qsearch=capture_only)
    rt=ctx.runtime;root=rt.position;probe=QuietActionProbe();engine=probe.prepare(ctx);assert engine is not None
    enemies=enemy_board_count(root,0);inventory=material_inventory(root)
    quiet=promotion=terminal=compound=0
    for action in rt.legal_actions():
        if not action_is_board(action):continue
        semantic,binding=rt._bindings[action]
        expected_child=engine._transition(root,semantic,binding,checkpoint=ctx.checkpoint)
        excluded=probe.exclude(ctx,action,engine,enemies,inventory)
        with rt.pushed(action):
            assert rt.position==expected_child
            expected=not noisy_child(action,rt.state,0,enemies,inventory,lambda:rt.in_check(1),capture_only=capture_only)
            assert excluded==expected
            if material_inventory(rt.position)!=inventory:promotion+=1;assert not excluded
            if rt.terminal_status.status is TerminalStatus.STALEMATE:terminal+=1;assert not excluded
            if sum(a!=b for a,b in zip(root.board,rt.position.board))==4:compound+=1
        quiet+=excluded
    assert quiet>0
    if kind=='promotion':assert promotion>0
    if kind=='stalemate':assert terminal>0 and probe.counts['retain_no_legal']>0
    if kind=='compound':assert compound>0
    assert ctx.stats.nonchecking_drop_excluded==0
    assert rt.position is root;rt.assert_balanced()

@pytest.mark.parametrize('boundary',['repetition','max_ply','opaque'])
def test_board_history_boundaries_retain_full_core_push(boundary):
    ctx=context(build_builtin_ruleset('western_chess'),['.......k','........','........','........','........','........','........','K..R....'])
    rt=ctx.runtime;probe=QuietActionProbe();assert probe.prepare(ctx) is not None
    if boundary=='repetition':next(e for b in rt._occurrences.values() for e in b).count=ctx.compiled.support.repetition_limit-1
    elif boundary=='max_ply':rt.ply_count=ctx.compiled.support.max_ply-1
    else:rt._opaque_imported_keys.add('unknown-test-identity')
    assert probe.prepare(ctx) is None
