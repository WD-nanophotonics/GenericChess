"""Prepare one complete secondary-capture/type/right rule, without search."""
from pathlib import Path
from dataclasses import replace,asdict
import sys,json,random,time,hashlib
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.generation.filters import run_soft_filters
from generic_chess.rules.schema import *
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.execution import ExecutableSemanticRuleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.native.compiler import compile_native_semantic_rules,NativeUnsupportedRuleError
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.core.coordinates import Square,square_to_index
D=Path('.local_agent/secondary-capture-next-20261019');D.mkdir(exist_ok=True);assert not(D/'prepared.json').exists();start=time.perf_counter()
def poll():
 assert time.perf_counter()-start<120
 for n in('rollout','advisor','slack'):
  f=json.loads(Path('.local_agent',n+'.json').read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
poll();cfg=GeneratorConfig(seed=711001,board_size=8,setup_preset='classic_like',movement_symmetry='none',allow_hybrid=True,max_generation_attempts=64);g=generate_game(cfg);target=sorted(t.type_id for t in g.ruleset.piece_types if not t.is_anchor and not t.is_promotable)[0]
a=RuleSemanticAction(name='secondary_capture_type_right',type_ids=tuple(t.type_id for t in g.ruleset.piece_types if not t.is_anchor),geometry=RuleGeometrySpec(kind='leap',offset=(1,2),owner_relative=True),target_relation='empty',composition='augment',aux_state=(RuleAuxState('capture_right','bool','per_owner','persistent',1),),slot_guards=(RuleSlotGuard('capture_right',value=1),),effects=(RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')),RuleActionEffect('remove',square_ref=RuleSquareRef('offset_from_source',offset=(0,1),owner_relative=True),piece_owner='opponent',disposition='capture_to_hand'),RuleActionEffect('set_current_type',square_ref=RuleSquareRef('target'),type_ref=RuleTypeRef('explicit',target)),RuleActionEffect('set_bool',slot_name='capture_right',value=0)),invariants=(RuleInvariant('own_anchor_safe'),))
rule=replace(g.ruleset,semantic_actions=(a,),metadata={**g.ruleset.metadata,'research_recipe':'secondary_capture_type_right'});c=compile_semantic_ruleset(rule);out=dict(status='NO_TRIGGER_YET',config=asdict(cfg),rule=ruleset_to_dict(rule),target=target,parents=[],Native_searches=0,Core_root_searches=0,new_fitness_games=0,optimizer_updates=0,bounded_rule_continuations=1,continuation_cap_plies=48)
try:compile_native_semantic_rules(c);out['Native_admission']='SUPPORTED'
except NativeUnsupportedRuleError as exc:out.update(Native_admission='REFUSED',Native_refusal=str(exc))
report=run_soft_filters(replace(cfg,require_no_opening_win_in_one=True),ExecutableSemanticRuleset.from_compiled(c),{t.type_id:t for t in rule.piece_types});out['final_optional_preference']=record_value(report);out['final_optional_preference_passed']=all(x.passed for x in report)
v=build_ruleset_profile(g.compiled_ruleset,EvaluationConfig());anchors={t.type_id for t in rule.piece_types if t.is_anchor};out['board_values']={t:0 if t in anchors else round(x*.256)for t,x in v.board_value_by_type.items()};out['hand_values']={t:0 if t in anchors else round(x*.256)for t,x in v.hand_value_by_base_type.items()}
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
s=GameSession(c);ids={x.pattern_id for x in c.ir.patterns if x.name=='secondary_capture_type_right'}
def save(phase):out['parents'].append(dict(phase=phase,record=json.loads(serialize_game_record(s.to_record())),state=record_value(s.state),state_sha256=digest(s.state),witness_sha256=digest(s._search_witnesses)))
save('initial');rng=random.Random(711001120);out['ordinary_prefix_plies']=0
for ply in range(48):
 poll();aa=s.legal_actions();special=sorted((x for x in aa if getattr(x,'pattern_id',None)in ids and x.actor_type_id!=target),key=repr)
 if special:
  a=special[0];save('before_trigger');before=s.state.position;side=before.side_to_move;sign=1 if side==0 else-1;victim_sq=Square(a.from_square.file,a.from_square.rank+sign);victim=before.board[square_to_index(victim_sq,c.board_size)];assert victim is not None and victim.owner!=side
  s.submit(a);after=s.state.position;out['actual_trigger']=record_value(a);out['captured_victim']=record_value(victim);out['changed_squares']=sum(x!=y for x,y in zip(before.board,after.board));out['hand_gain_base']=victim.base_type_id;assert after.hands[side].count(victim.base_type_id)==before.hands[side].count(victim.base_type_id)+1 and out['changed_squares']==3 and before.aux_state!=after.aux_state
  save('after_trigger');reply=s.legal_actions()
  if reply:s.submit(sorted(reply,key=repr)[0]);save('after_reply')
  out['status']='PREPARED_ACTUAL_SECONDARY_CAPTURE';break
 if not aa:out['status']='TERMINAL_BEFORE_TRIGGER';break
 ordinary=[x for x in aa if getattr(x,'pattern_id',None)not in ids]
 if not ordinary:out['status']='NO_ORDINARY_CONTINUATION';break
 s.submit(rng.choice(ordinary));out['ordinary_prefix_plies']+=1
else:out['status']='NO_TRIGGER_WITHIN_FROZEN48'
if out['status']!='PREPARED_ACTUAL_SECONDARY_CAPTURE':save('bounded_prefix_end')
out.update(seconds=time.perf_counter()-start,scope='OneNEWcompletegenerated8board/foureffectsecondarycapture-to-baseHAND,currenttypechange andoneuse right. Alltypes/promotion/drop/aux/historyretained; explicitNativeadmission/refusal, no fallbackexecutionclaim. Oneboundedactualrulecontinuation, no search/evaluationgames/training/regeneration.')
write_json(D/'prepared.json',out)
pub=Path('docs/research/data/secondary_capture_next_20261019');pub.mkdir(parents=True,exist_ok=True);(pub/'prepared.json').write_bytes((D/'prepared.json').read_bytes().replace(b'\r\n',b'\n'))
print('NEXT_SECONDARY_CAPTURE',out['status'],out['Native_admission'],len(out['parents']),out['ordinary_prefix_plies'],out.get('changed_squares'),time.perf_counter()-start)
