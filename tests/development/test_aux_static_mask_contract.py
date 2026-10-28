"""Concrete static dependency and frozen-reader falsifications; no new search."""
import copy,gzip,json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import verify_aux_static_mask_packet as V
from scripts.leaper_mask_evaluator import PureLeaperMaskEvaluator
from generic_chess.ai.evaluation.config import EvaluationConfig,MAX_STATIC_EVAL
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.errors import RuleSetMismatchError

@pytest.fixture(scope='module')
def data():return json.loads(gzip.decompress(Path('tests/fixtures/aux_static_mask_contract_20261029.json.gz').read_bytes()))
@pytest.fixture(scope='module')
def compiled(data):return compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(data['input']['RuleSet']))
def evaluators(c,cfg,profile=None):
    base=Evaluator(c,profile or build_ruleset_profile(c,cfg),cfg);return base,PureLeaperMaskEvaluator(c,base)
def state(c,board,hands=None,side=0):return SimpleNamespace(position=replace(c.initial_position,board=tuple(board),hands=hands or (Hands(),Hands()),side_to_move=side))

def test_census_is_not_first_cost_group(data):
    d=copy.deepcopy(data);g=d['root_census']+d['root_cost'][:1]
    p=copy.deepcopy(d['root_plan']);p['cost_ids']=[p['cost_ids'][0]]
    with pytest.raises(AssertionError):V.check_groups(g,p,d['root_assessment'])

def test_wrong_arm_with_legal_same_root_is_not_abba(data):
    rows=copy.deepcopy(data['cold_all']);rows[1]['on']=False
    with pytest.raises(AssertionError):V.check_groups(rows,data['cold_plan'],data['cold_assessment'],True)

def test_same_values_but_changed_untimed_work_rejected(data):
    rows=copy.deepcopy(data['cold_all']);rows[1]['decision']['legal_actions_generated']+=1
    with pytest.raises(AssertionError):V.check_groups(rows,data['cold_plan'],data['cold_assessment'],True)

def test_zero_individual_cpu_is_not_zero_off_group(data):
    rows=data['cold_all'];assert any(q['cpu_seconds']==0 for q in rows)
    result=V.check_groups(rows,data['cold_plan'],data['cold_assessment'],True)
    assert result['zero_OFF_CPU_groups']==['ce7-f4-h0']
    assert result['original_gate']=='NO_GO_OR_INCONCLUSIVE_LIFECYCLE'

def test_group_mean_cannot_replace_declared_total_ratio(data):
    reported=copy.deepcopy(data['cold_assessment']);groups=V.check_groups(data['cold_all'],data['cold_plan'],reported,True)['groups']
    reported['wall_ratio']=sum(x['wall_ON']/x['wall_OFF'] for x in groups)/len(groups)
    with pytest.raises(AssertionError):V.check_groups(data['cold_all'],data['cold_plan'],reported,True)

def test_enriched_score_cannot_change_raw_return(data):
    rows=copy.deepcopy(data['cold_all']);raw=copy.deepcopy(rows[0]);raw.pop('Core_verified');members={'cold-lifecycle/queries.json':json.dumps(rows).encode()}
    for q in rows:
        r=copy.deepcopy(q);r.pop('Core_verified');members[f"cold-lifecycle/query-{q['slot']:02d}.json"]=json.dumps(r).encode()
    rows[0]['decision']['score']+=1;members['cold-lifecycle/queries.json']=json.dumps(rows).encode()
    with pytest.raises(AssertionError):V.check_raw(members,'cold-lifecycle',48,True)

def test_two_anchors_first_scan_not_last_or_sum(compiled):
    cfg=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=5,promotion_potential_weight=0);base,mask=evaluators(compiled,cfg)
    board=[None]*49
    for index,piece in [(0,Piece(0,'K','K')),(32,Piece(0,'K','K')),(48,Piece(1,'K','K')),(7,Piece(1,'A','A'))]:board[index]=piece
    s=state(compiled,board);first=base.evaluate(s);assert mask.evaluate(s)==first
    board[0]=None;last=base.evaluate(state(compiled,board));assert first!=last
    # Anchors have zero material; choosing last changes this raw heuristic75.
    assert last-first==75

def test_overlapping_attacks_are_union_not_actor_sum(compiled):
    cfg=EvaluationConfig(dynamic_mobility_weight=1,anchor_escape_weight=0,promotion_potential_weight=0);base,mask=evaluators(compiled,cfg)
    board=[None]*49;board[1]=Piece(0,'A','A');board[7]=Piece(0,'A','A');s=state(compiled,board)
    u=set(compiled.empty_mobility['A'][0][1])|set(compiled.empty_mobility['A'][0][7]);summed=sum(len(compiled.empty_mobility['A'][0][i]) for i in (1,7))
    assert len(u)<summed;assert mask.evaluate(s)==base.evaluate(s)==2*base.type_value('A')+len(u)

@pytest.mark.parametrize('weights',[(0,0),(2,5)])
def test_fingerprint_error_contract_depends_on_dynamic_terms(compiled,weights):
    cfg=EvaluationConfig(dynamic_mobility_weight=weights[0],anchor_escape_weight=weights[1]);base,mask=evaluators(compiled,cfg)
    s=SimpleNamespace(position=replace(compiled.initial_position,ruleset_fingerprint='foreign'))
    if any(weights):
        for ev in (base,mask):
            with pytest.raises(RuleSetMismatchError):ev.evaluate(s)
    else:assert mask.evaluate(s)==base.evaluate(s)

def test_material_hand_and_side_and_raw_clamp_are_preserved(compiled):
    cfg=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0);base,mask=evaluators(compiled,cfg)
    board=[None]*49;board[4]=Piece(0,'A','A');hands=(Hands((('B',10**9),)),Hands((('C',3),)))
    s=state(compiled,board,hands);expected=base.type_value('A')+10**9*base._profile.hand_value_by_base_type['B']-3*base._profile.hand_value_by_base_type['C']
    assert mask.evaluate(s)==base.evaluate(s)==expected and expected>MAX_STATIC_EVAL
    assert mask.evaluate(state(compiled,board,hands,1))==-expected
    from generic_chess.ai.alphabeta.search import _bounded_static_score
    assert _bounded_static_score(expected)==_bounded_static_score(expected+1)==MAX_STATIC_EVAL
    # Equality after clipping would hide the deliberate raw+1 difference.

def test_default_mask_is_not_a_learned_material_adapter(compiled):
    class Material:
        def evaluate(self,s):return 0
        def capture_order_value(self,a,b):return 0
    with pytest.raises(ValueError):PureLeaperMaskEvaluator(compiled,Material())


def test_actual_dormant_type_counterexample_is_not_a_mask_mismatch(data):
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    r=data['dormant_counterexample'];rule=r['augmented_RuleSet'];original=copy.deepcopy(rule);original['piece_types']=[t for t in original['piece_types'] if t['type_id']!='UNUSED'];original['drop_allowed'].pop('UNUSED')
    ca=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(original));cb=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(rule));cfg=EvaluationConfig();ea,fa=evaluators(ca,cfg);eb,fb=evaluators(cb,cfg)
    sa=GameSession.replay(ca,deserialize_game_record(json.dumps(r['witness']['original_record'])));sb=GameSession.replay(cb,deserialize_game_record(json.dumps(r['witness']['augmented_record'])))
    assert sa.state.position.board==sb.state.position.board and sa.state.position.hands==sb.state.position.hands
    assert not sa.state.terminal_status.is_terminal and sa.state.terminal_status==sb.state.terminal_status
    assert ea.evaluate(sa.state)==fa.evaluate(sa.state)==-444
    assert eb.evaluate(sb.state)==fb.evaluate(sb.state)==-615
    assert ea._profile.piece_profiles['C'].raw_capability_score==eb._profile.piece_profiles['C'].raw_capability_score
    assert eb._profile.board_value_by_type['C']==607 and ea._profile.board_value_by_type['C']==436

def test_relabelled_pattern_is_not_reusable_as_old_action_identity(data):
    from generic_chess.session.session import GameSession
    from generic_chess.core.errors import IllegalActionError
    r=data['dormant_counterexample'];rule=r['augmented_RuleSet'];original=copy.deepcopy(rule);original['piece_types']=[t for t in original['piece_types'] if t['type_id']!='UNUSED'];original['drop_allowed'].pop('UNUSED')
    ca=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(original));cb=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(rule));a=GameSession(ca);b=GameSession(cb);mapping=r['pattern_id_mapping']
    action=next(x for x in a.legal_actions() if mapping[x.pattern_id]!=x.pattern_id);transported=replace(action,pattern_id=mapping[action.pattern_id])
    assert action not in b.legal_actions() and transported in b.legal_actions()
    before=b.to_record()
    with pytest.raises(IllegalActionError):b.submit(action)
    assert b.to_record()==before
    a.submit(action);b.submit(transported);assert a.state.position.board==b.state.position.board


def test_bool_arm_cannot_be_replaced_by_numeric_one(data):
    rows=copy.deepcopy(data['cold_all']);rows[1]['on']=1
    with pytest.raises(AssertionError):V.check_groups(rows,data['cold_plan'],data['cold_assessment'],True)

def test_coherent_family_annotation_must_still_bind_source(data):
    root=data['input'];row=copy.deepcopy(data['root_cost'][0]);row['family']+=1
    with pytest.raises(AssertionError):V.bind_call_families([row],[root])
