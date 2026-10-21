"""Observed duplicate child projection: finite readonly reuse boundaries."""
from dataclasses import replace
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.native import native_available
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.search_backend_comparison import CASES,CoreBoard
from scripts.native_core_probe import NativeCoreProbe
pytestmark=pytest.mark.skipif(not native_available(),reason='native extension unavailable')
@pytest.mark.parametrize('case_id',['chess-ep','chess-promotion','shogi-promotion','shogi-drop'])
def test_exact_child_projection_shared_only_by_readonly_same_position(case_id):
    case=next(x for x in CASES if x['id']==case_id)
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess' if case['game']=='chess' else 'standard_shogi'))
    rt=CoreBoard(case,c).runtime;probe=NativeCoreProbe(c,shared=True);engine=semantic_engine_for(c)
    positions=[rt.position]
    for action in rt.legal_actions()[:8]:
        rt.push(action)
        try:positions.append(rt.position)
        finally:rt.pop()
    for position in positions:
        before=probe.imports
        assert probe.check(position)==engine.in_check(position,position.side_to_move)
        assert probe.for_position(position)==engine.has_legal_action(position)
        assert probe.imports==before+1
        # Equal content with a distinct immutable object must not reuse its capsule.
        clone=replace(position)
        assert clone is not position and clone==position
        assert probe.for_position(clone)==engine.has_legal_action(clone)
        assert probe.imports==before+2
    assert probe.reuses==len(positions)

def test_one_entry_reuse_reimports_older_position_and_checks_compiled_identity():
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    a=CoreBoard(next(x for x in CASES if x['id']=='chess-ep'),c).runtime.position
    b=CoreBoard(next(x for x in CASES if x['id']=='chess-promotion'),c).runtime.position
    probe=NativeCoreProbe(c,shared=True)
    for position in (a,b,a):probe.check(position);probe.for_position(position)
    assert probe.imports==3 and probe.reuses==3
    other=CoreBoard(next(x for x in CASES if x['id']=='shogi-drop'),compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))).runtime.position
    with pytest.raises(ValueError,match='source mismatch'):probe.check(other)

@pytest.mark.parametrize('shared',[False,True])
def test_probe_is_checkpointed_and_does_not_mutate_position(shared):
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    rt=CoreBoard(next(x for x in CASES if x['id']=='chess-ep'),c).runtime
    from scripts.full_q_refresh_comparison import runtime_state
    saved=runtime_state(rt);polls=[];probe=NativeCoreProbe(c,shared=shared)
    probe.check(rt.position,checkpoint=lambda:polls.append(1));probe.for_position(rt.position,checkpoint=lambda:polls.append(1))
    assert len(polls)==4 and runtime_state(rt)==saved
    assert probe.imports==(1 if shared else 2)
    def fail():raise RuntimeError('interrupted')
    with pytest.raises(RuntimeError,match='interrupted'):probe.check(rt.position,checkpoint=fail)
    assert runtime_state(rt)==saved

@pytest.mark.parametrize('max_ply',[1,2])
def test_reply_cutoff_keeps_core_availability_fallback_with_native_check(max_ply):
    c=compile_ruleset_for_execution(replace(build_builtin_ruleset('standard_shogi'),max_ply=max_ply))
    rt=CoreBoard(next(x for x in CASES if x['id']=='shogi-drop'),c).runtime
    probe=NativeCoreProbe(c,shared=True);engine=semantic_engine_for(c)
    assert probe.check(rt.position)==engine.in_check(rt.position,rt.position.side_to_move)
    assert probe.for_position(rt.position)==engine.has_legal_action(rt.position)
    assert probe.fallbacks==int(max_ply==1)
    assert probe.queries==int(max_ply!=1)
    assert probe.imports==1
