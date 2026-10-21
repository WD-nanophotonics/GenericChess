"""Finite actual Native capsule adapter state/consumer regressions."""
from dataclasses import FrozenInstanceError
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.native import native_available
from scripts.search_backend_comparison import CASES, CoreBoard
from scripts.native_capsule_runtime import CapsulePathRuntime

pytestmark = pytest.mark.skipif(not native_available(), reason='native extension unavailable')
SELECTED = {'chess-ep':'e5d6', 'chess-promotion':'a7a8q',
            'shogi-promotion':'5c5b+', 'shogi-drop':'R*5e'}


@pytest.mark.parametrize('case_id', SELECTED)
def test_effect_replies_and_cached_parent_view_restore_ply_state_history(case_id):
    case = next(c for c in CASES if c['id'] == case_id)
    compiled = compile_ruleset_for_execution(build_builtin_ruleset(
        'western_chess' if case['game']=='chess' else 'standard_shogi'))
    core = CoreBoard(case, compiled)
    runtime = CapsulePathRuntime(core.initial, compiled, core.witnesses)
    root = runtime.state
    saved = runtime.full_snapshot()
    def check():
        assert runtime.position == core.runtime.position
        assert runtime.ply_count == core.runtime.ply_count
        assert runtime.terminal_status == core.runtime.terminal_status
        assert set(runtime.legal_actions()) == set(core.runtime.legal_actions())
        # Position and ply are a single cached immutable projection.
        assert runtime.state.position is runtime.position
        assert runtime.state.ply_count == runtime.full_snapshot()['ply']
    check()
    action = next(a for a in runtime.legal_actions() if core.label(a)==SELECTED[case_id])
    runtime.push(action); core.runtime.push(action)
    try:
        check(); parent = runtime.state; parent_snapshot = runtime.full_snapshot()
        for reply in sorted(core.runtime.legal_actions(), key=repr)[:2]:
            runtime.push(reply); core.runtime.push(reply)
            try:
                check()
                assert runtime.state.ply_count == parent.ply_count+1
            finally:
                runtime.pop(); core.runtime.pop()
            assert runtime.state == parent
            assert runtime.state.position is parent.position
            assert runtime.full_snapshot() == parent_snapshot
    finally:
        runtime.pop(); core.runtime.pop()
    assert runtime.state == root and runtime.state.position is root.position
    assert runtime.full_snapshot() == saved
    runtime.assert_balanced(); core.runtime.assert_balanced()


def test_unread_child_projection_and_cancelled_push_keep_parent():
    c = compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    case = next(v for v in CASES if v['id']=='chess-ep'); core=CoreBoard(case,c)
    rt=CapsulePathRuntime(core.initial,c,core.witnesses); root=rt.state
    actions=rt.legal_actions(); original=rt.full_snapshot()
    def cancel():
        raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError, match='cancelled'):
        rt.push(actions[0], checkpoint=cancel)
    assert rt.state==root and rt.transitions==0
    rt.push(actions[0]);rt.pop()  # Never read child's Position/ply.
    assert rt.state==root and rt.full_snapshot()==original
    rt.assert_balanced()
    with pytest.raises(FrozenInstanceError):
        rt.state.ply_count=999
    assert not hasattr(rt.state, 'history')  # View never pretends to be GameState.


def test_explicit_runtime_evaluator_rejects_stale_views_and_matches_semantic_authority():
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from scripts.native_capsule_evaluator import RuntimeSemanticAttackEvaluator
    c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    case=next(v for v in CASES if v['id']=='chess-ep');core=CoreBoard(case,c)
    rt=CapsulePathRuntime(core.initial,c,core.witnesses);config=EvaluationConfig()
    profile=build_ruleset_profile(c,config)
    fast=RuntimeSemanticAttackEvaluator(c,profile,config)
    base=SemanticAttackEvaluator(c,profile,config,backend='core')
    root=rt.state
    with pytest.raises(ValueError, match='current bound view'):
        fast._attack_maps(root)
    fast.bind_runtime(rt)
    assert fast._attack_maps(root)==base._attack_maps(root)
    assert fast.evaluate(root)==base.evaluate(root)
    a=rt.legal_actions()[0];rt.push(a)
    try:
        with pytest.raises(ValueError, match='current bound view'):
            fast._attack_maps(root)
        assert fast._attack_maps(rt.state)==base._attack_maps(rt.state)
        assert fast.evaluate(rt.state)==base.evaluate(rt.state)
    finally:
        rt.pop()
    assert fast.evaluate(root)==base.evaluate(root)


@pytest.mark.parametrize('case_id', SELECTED)
def test_existing_validated_decoder_cache_preserves_exact_action_and_effect(case_id):
    from scripts.native_capsule_decode import DecodedCapsulePathRuntime
    from generic_chess.native.mirror import pack_semantic_action
    case=next(c for c in CASES if c['id']==case_id)
    compiled=compile_ruleset_for_execution(build_builtin_ruleset(
        'western_chess' if case['game']=='chess' else 'standard_shogi'))
    core=CoreBoard(case,compiled)
    ref=CapsulePathRuntime(core.initial,compiled,core.witnesses)
    rt=DecodedCapsulePathRuntime(core.initial,compiled,core.witnesses)
    root=rt.state
    assert ref.legal_actions()==rt.legal_actions()
    assert rt.legal_actions()==ref.legal_actions() and rt.public_cache_hits>0
    for action, raw in rt._rawmap.items():
        assert pack_semantic_action(rt.native,rt.position,action)==raw
    chosen=next(a for a in rt.legal_actions() if core.label(a)==SELECTED[case_id])
    ref.push(chosen);rt.push(chosen)
    try:
        assert ref.state==rt.state and ref.full_snapshot()==rt.full_snapshot()
        assert ref.legal_actions()==rt.legal_actions()
    finally:
        ref.pop();rt.pop()
    assert rt.state==root and ref.full_snapshot()==rt.full_snapshot()
    rt.assert_balanced();ref.assert_balanced()


@pytest.mark.parametrize('case_id', SELECTED)
def test_actual_material_summary_and_noisy_policy_match_all_effect_children(case_id):
    from scripts.native_capsule_inventory import InventoryCapsulePathRuntime
    from generic_chess.ai.alphabeta.quiescence import enemy_board_count,material_inventory,noisy_child
    case=next(c for c in CASES if c['id']==case_id)
    compiled=compile_ruleset_for_execution(build_builtin_ruleset(
        'western_chess' if case['game']=='chess' else 'standard_shogi'))
    core=CoreBoard(case,compiled)
    rt=InventoryCapsulePathRuntime(core.initial,compiled,core.witnesses)
    root=rt.state;full=rt.full_snapshot();side=root.position.side_to_move
    enemies=enemy_board_count(root.position,side);inventory=material_inventory(root.position)
    before=rt.material_summary()
    def check():
        summary=rt.material_summary();position=core.runtime.position
        expected=material_inventory(position)
        assert summary[0]==position.side_to_move and summary[1]==core.runtime.ply_count
        assert summary[2]==tuple(sum(p is not None and p.owner==owner for p in position.board) for owner in (0,1))
        assert summary[3]==tuple(expected.get((owner,tid),0) for owner in (0,1) for tid in rt.native.type_ids)
    check()
    for action in rt.legal_actions():
        rt.push(action);core.runtime.push(action)
        try:
            reference=noisy_child(action,core.runtime.state,side,enemies,inventory,
                lambda:core.runtime.in_check(core.runtime.position.side_to_move))
            views=rt.views
            assert rt.noisy_child(side,enemies,before[3])==reference
            assert rt.views==views  # Actual post-transition inclusion need not project Python Position.
            check()
        finally:
            rt.pop();core.runtime.pop()
        assert rt.material_summary()==before
    assert rt.state==root and rt.full_snapshot()==full
    rt.assert_balanced();core.runtime.assert_balanced()


def test_material_summary_preserves_owner_current_type_hand_base_and_large_counts():
    from dataclasses import replace
    from generic_chess.core.position import Hands
    from generic_chess.core.pieces import Piece
    from generic_chess.native.compiler import compile_native_semantic_rules
    from generic_chess.native.semantic import pack_current_position,material_summary,snapshot
    from generic_chess.ai.alphabeta.quiescence import material_inventory
    c=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    case=next(v for v in CASES if v['id']=='shogi-promotion');core=CoreBoard(case,c)
    board=list(core.initial.position.board);board[22]=Piece(0,'P','TP',True)
    pos=replace(core.initial.position,board=tuple(board),hands=(Hands((('TP',256),('P',2))),Hands((('R',3),))))
    rules=compile_native_semantic_rules(c);packed=pack_current_position(rules,pos,ply_count=17)
    saved=snapshot(rules,packed);value=material_summary(rules,packed);inventory=material_inventory(pos)
    assert value[0:2]==(pos.side_to_move,17)
    assert value[3]==tuple(inventory.get((o,t),0) for o in (0,1) for t in rules.type_ids)
    assert max(value[3])==257
    assert snapshot(rules,packed)==saved
    other=compile_native_semantic_rules(compile_ruleset_for_execution(build_builtin_ruleset('western_chess')))
    with pytest.raises(ValueError,match='fingerprint'):
        material_summary(other,packed)
