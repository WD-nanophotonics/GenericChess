"""Teacher result admission only: stub search, no Player/native/game calls."""
from types import SimpleNamespace
import pytest
from generic_chess.learning import diagnostics as D

class Corpus:
    def __init__(self, n=2): self.n=n
    def validate(self, compiled): pass
    def nonterminal_positions(self, compiled): return list(range(self.n))

def result(action='a', depth=1, fallback=False, reason='node_limit'):
    return SimpleNamespace(action=action, completed_depth=depth,
                           used_fallback=fallback, termination_reason=reason)

def bench(monkeypatch, outcome, n=2):
    calls=[]
    def search(c,r,cp,pos,nodes):
        calls.append((cp,pos,nodes)); return outcome(cp,pos,nodes),None
    monkeypatch.setattr(D,'_search_position',search)
    return D.teacher_benchmark(None,None,[0,1],Corpus(n),student_nodes=4,teacher_nodes=8),calls

def test_missing_actions_never_establish_teacher_agreement(monkeypatch):
    out,calls=bench(monkeypatch,lambda *args:result(None,0,True))
    assert len(calls)==8
    assert out['teacher_self_agreement'] is None
    assert out['best_move_agreement']=={'0':None,'1':None}
    assert out['comparison_coverage']['teacher_self']['valid_pairs']==0
    assert D._verdict_teacher(out)=='INCONCLUSIVE'

def test_empty_corpus_is_unknown_not_zero_or_perfect(monkeypatch):
    out,calls=bench(monkeypatch,lambda *args:pytest.fail('search on empty corpus'),n=0)
    assert calls==[] and out['positions']==0
    assert out['teacher_self_agreement'] is None
    assert out['best_move_agreement']=={'0':None,'1':None}
    assert D._verdict_teacher(out)=='INCONCLUSIVE'

@pytest.mark.parametrize('bad',[result('a',0,True),result('a',0,False),result('a',1,True)])
def test_fallback_or_uncompleted_action_is_not_a_completed_teacher_decision(monkeypatch,bad):
    out,_=bench(monkeypatch,lambda cp,pos,nodes:bad if nodes==16 and pos==1 else result())
    assert out['teacher_self_agreement'] is None
    assert out['comparison_coverage']['teacher_self']['valid_pairs']==1
    # The low teacher/student comparison itself is complete, so preserve it.
    assert out['best_move_agreement']=={'0':1.,'1':1.}
    assert D._verdict_teacher(out)=='INCONCLUSIVE'

def test_completed_last_iteration_at_node_cap_remains_valid(monkeypatch):
    out,_=bench(monkeypatch,lambda cp,pos,nodes:result('b' if cp==1 and pos==0 else 'a',2,False))
    assert out['teacher_self_agreement']==1.
    assert out['best_move_agreement']=={'0':1.,'1':.5}
    assert out['comparison_coverage']['1']['valid_pairs']==2

def test_one_invalid_student_does_not_shrink_denominator_to_perfect_score(monkeypatch):
    out,_=bench(monkeypatch,lambda cp,pos,nodes:result(None,0,True) if cp==1 and pos==1 else result())
    assert out['teacher_self_agreement']==1.
    assert out['best_move_agreement']=={'0':1.,'1':None}
    assert out['comparison_coverage']['1']=={'positions':2,'valid_pairs':1,'matching_pairs':1}

@pytest.mark.parametrize('maximum',[-1,True,1.5])
def test_invalid_max_positions_rejected_before_search(monkeypatch,maximum):
    monkeypatch.setattr(D,'_search_position',lambda *args:pytest.fail('invalid request searched'))
    with pytest.raises(ValueError,match='max_positions'):
        D.teacher_benchmark(None,None,[0],Corpus(),max_positions=maximum)


def test_downstream_retest_cannot_compare_unknown_generation_to_baseline():
    from generic_chess.learning.leverage import verdict_learning_retest
    retest={'teacher':{'best_move_agreement':{'0':.6,'1':None}},
            'paired_arena':{'1':{'mean_pair_score':.7}}}
    assert verdict_learning_retest(retest)=='INCONCLUSIVE'

def test_next_phase_remains_unknown_when_teacher_has_no_completed_reference():
    assert D._verdict_next_phase({'n':1,'mean_abs_delta':1.},
        {'unique_ratio':.1,'collision_positions_fraction':.9},
        {'1':{'move_flip_rate':.3}},
        {'teacher_self_agreement':None,'best_move_agreement':{'0':None}},
        {'strong_vs_weak':{'weak_side_mean_pair_score':.2}})=='INCONCLUSIVE'

def test_empty_teacher_checkpoint_list_is_rejected(monkeypatch):
    monkeypatch.setattr(D,'_search_position',lambda *args:pytest.fail('missing teacher searched'))
    with pytest.raises(ValueError,match='teacher checkpoint'):
        D.teacher_benchmark(None,None,[],Corpus())


def checkpoint(fingerprint):
    from generic_chess.learning.material import LearnableMaterialCheckpoint
    return LearnableMaterialCheckpoint(ruleset_fingerprint=fingerprint,
        board_weights={'A':1.,'B':2.},hand_weights={'A':0.,'B':0.})

@pytest.mark.parametrize('mismatch',['root','child'])
def test_diagnostic_checkpoint_loader_rejects_wrong_rule_even_with_same_type_names(tmp_path,mismatch):
    import json
    target=SimpleNamespace(ruleset_fingerprint='rule-target')
    root=checkpoint('other' if mismatch=='root' else 'rule-target')
    child=checkpoint('other' if mismatch=='child' else 'rule-target')
    (tmp_path/'generation_000.json').write_text(json.dumps(root.to_dict()))
    (tmp_path/'generation_001.json').write_text(json.dumps({'child':child.to_dict()}))
    with pytest.raises(ValueError,match='fingerprint'):
        D.load_checkpoints_from_experiment(target,7,tmp_path)

def test_diagnostic_checkpoint_loader_keeps_matching_rule_checkpoints(tmp_path):
    import json
    target=SimpleNamespace(ruleset_fingerprint='rule-target');cp=checkpoint('rule-target')
    (tmp_path/'generation_000.json').write_text(json.dumps(cp.to_dict()))
    (tmp_path/'generation_001.json').write_text(json.dumps({'child':cp.to_dict()}))
    loaded=D.load_checkpoints_from_experiment(target,7,tmp_path)
    assert [c.checkpoint_id for c in loaded]==[cp.checkpoint_id,cp.checkpoint_id]

def test_engine_binding_rejects_wrong_checkpoint_before_native_compile(monkeypatch):
    monkeypatch.setattr(D,'compile_native_evaluation',lambda *args,**kw:pytest.fail('invalid rule reached native compile'))
    with pytest.raises(ValueError,match='fingerprint'):
        D._engine_for(SimpleNamespace(ruleset_fingerprint='rule-target',piece_types=()),
                      None,checkpoint('other'),8)


@pytest.mark.parametrize('corruption', ['fingerprint', 'position_key', 'side', 'ply'])
def test_direct_teacher_entry_rejects_invalid_corpus_before_search(monkeypatch, corruption):
    from dataclasses import replace
    from native_test_helpers import generated_compiled
    from generic_chess.session.session import GameSession
    from generic_chess.core.identity import position_identity_key

    compiled = generated_compiled(size=4, seed=7)
    root = GameSession(compiled)
    pos = D.DiagnosticPosition(0, (),
        position_identity_key(root.state.position, compiled),
        root.state.position.side_to_move, root.state.ply_count)
    corpus = D.LearningDiagnosticCorpus(
        ruleset_fingerprint=compiled.ruleset_fingerprint, positions=(pos,))
    if corruption == 'fingerprint':
        corpus = replace(corpus, ruleset_fingerprint='different-rules')
    else:
        field, value = {'position_key': ('position_key', 'wrong-key'),
                        'side': ('side_to_move', 1-root.state.position.side_to_move),
                        'ply': ('ply', root.state.ply_count+1)}[corruption]
        corpus = replace(corpus, positions=(replace(pos, **{field: value}),))
    monkeypatch.setattr(D, '_search_position',
        lambda *args: pytest.fail('invalid corpus reached search'))
    with pytest.raises(ValueError, match='fingerprint|key mismatch|side mismatch|ply mismatch'):
        D.teacher_benchmark(compiled, None, [object()], corpus, max_positions=0)


def test_wrong_rule_corpus_cannot_earn_agreement_with_legal_actions(monkeypatch):
    from dataclasses import replace
    from native_test_helpers import generated_compiled
    from generic_chess.session.session import GameSession
    from generic_chess.core.identity import position_identity_key
    compiled = generated_compiled(size=4, seed=7)
    root = GameSession(compiled)
    action = root.legal_actions()[0]
    pos = D.DiagnosticPosition(0, (),
        position_identity_key(root.state.position, compiled),
        root.state.position.side_to_move, 0)
    valid = D.LearningDiagnosticCorpus(
        ruleset_fingerprint=compiled.ruleset_fingerprint, positions=(pos,))
    calls=[]
    def search(*args):
        calls.append(args)
        return result(action), root
    monkeypatch.setattr(D, '_search_position', search)
    assert D.teacher_benchmark(compiled, None, [object()], valid)['teacher_self_agreement']==1.
    calls.clear()
    with pytest.raises(ValueError, match='fingerprint'):
        D.teacher_benchmark(compiled, None, [object()],
                            replace(valid, ruleset_fingerprint='other-rules'))
    assert calls == []
