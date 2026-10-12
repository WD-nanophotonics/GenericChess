"""Actor witness scheduling retains full capture eligibility and fallback."""
from dataclasses import replace
import pytest
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.rules.compiler import compile_ruleset_for_execution
from rule_semantics_ir_fixtures import cannon_ruleset,castling_ruleset,uchifuzume_ruleset,weird_rulesets

@pytest.mark.parametrize('rule',[cannon_ruleset(),castling_ruleset(),uchifuzume_ruleset(),*weird_rulesets()])
def test_actor_witness_and_legal_children_keep_original_dispatch(rule):
    c=compile_ruleset_for_execution(rule);fallback=replace(c)
    object.__setattr__(fallback,'_actor_capture_patterns',None)
    a=SemanticEngine(c);b=SemanticEngine(fallback);parent=a._initial_position()
    for action in a.legal_actions(parent):
        x=a.apply(parent,action);y=b.apply(parent,action);assert x==y
        assert a._action_delivers_check(parent,x,action)==b._action_delivers_check(parent,y,action)
        def cancel():raise InterruptedError('actor poll')
        # When an actor and reply anchor exist the dispatch must poll even
        # if the type has no eligible capture pattern.
        if x.board[action.target] is not None:
            with pytest.raises(InterruptedError,match='actor poll'):
                a._action_delivers_check(parent,x,action,checkpoint=cancel)

def test_replacement_rebuilds_ordered_actor_metadata_without_duplicate_dispatch():
    c=compile_ruleset_for_execution(cannon_ruleset())
    p=next(p for p in c.ir.patterns if p.target.kind=='target_enemy')
    changed=replace(c,ir=replace(c.ir,patterns=(replace(p,type_ids=p.type_ids*2),)))
    assert changed._actor_capture_patterns is not c._actor_capture_patterns
    assert changed._actor_capture_patterns[p.type_ids[0]]==changed.ir.patterns
    assert changed.ir.fingerprint()!=c.ir.fingerprint()
