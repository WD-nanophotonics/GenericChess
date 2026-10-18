"""Prepare one valid full four-effect recombination after the current evidence seal."""
from pathlib import Path
from dataclasses import replace,asdict
import sys,json,time,hashlib
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
D=Path('.local_agent/compound-recombined-next-20261019');D.mkdir(exist_ok=True);assert not(D/'prepared.json').exists();start=time.perf_counter()
for n in('rollout','advisor','slack'):
 f=json.loads(Path('.local_agent',n+'.json').read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
cfg=GeneratorConfig(seed=671001,board_size=12,setup_preset='classic_like',movement_symmetry='none',allow_hybrid=True,max_generation_attempts=64);g=generate_game(cfg);target=sorted(t.type_id for t in g.ruleset.piece_types if not t.is_anchor and not t.is_promotable)[0]
action=RuleSemanticAction(name='mixed_pair_right',type_ids=tuple(t.type_id for t in g.ruleset.piece_types if not t.is_anchor),geometry=RuleGeometrySpec(kind='leap',offset=(1,2),owner_relative=True),target_relation='empty',composition='augment',aux_state=(RuleAuxState('pair_right','bool','per_owner','persistent',1),),slot_guards=(RuleSlotGuard('pair_right',value=1),),effects=(RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')),RuleActionEffect('shift',from_ref=RuleSquareRef('offset_from_source',offset=(0,1),owner_relative=True),to_ref=RuleSquareRef('offset_from_source',offset=(0,2),owner_relative=True),piece_owner='self'),RuleActionEffect('set_current_type',square_ref=RuleSquareRef('target'),type_ref=RuleTypeRef('explicit',target)),RuleActionEffect('set_bool',slot_name='pair_right',value=0)),invariants=(RuleInvariant('own_anchor_safe'),))
rule=replace(g.ruleset,semantic_actions=(action,),metadata={**g.ruleset.metadata,'research_recipe':'four_effect_pair_type_right'});c=compile_semantic_ruleset(rule);out=dict(status='PREPARED',config=asdict(cfg),rule=ruleset_to_dict(rule),effects=4,target=target,parents=[],Native_searches=0,Core_searches=0,new_games=0,optimizer_updates=0)
try:compile_native_semantic_rules(c);out['Native_admission']='SUPPORTED'
except NativeUnsupportedRuleError as exc:out.update(Native_admission='REFUSED',refusal=str(exc))
e=ExecutableSemanticRuleset.from_compiled(c);report=run_soft_filters(replace(cfg,require_no_opening_win_in_one=True),e,{t.type_id:t for t in rule.piece_types});out['optional_final_preference']=record_value(report);out['optional_final_preference_passed']=all(x.passed for x in report)
v=build_ruleset_profile(g.compiled_ruleset,EvaluationConfig());anchors={t.type_id for t in rule.piece_types if t.is_anchor};out['board_values']={t:0 if t in anchors else round(x*.256)for t,x in v.board_value_by_type.items()};out['hand_values']={t:0 if t in anchors else round(x*.256)for t,x in v.hand_value_by_base_type.items()}
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
s=GameSession(c);special={p.pattern_id for p in c.ir.patterns if p.name=='mixed_pair_right'}
for phase in range(3):
 assert time.perf_counter()-start<60
 aa=s.legal_actions();out['parents'].append(dict(phase=phase,record=json.loads(serialize_game_record(s.to_record())),state_sha256=digest(s.state),witness_sha256=digest(s._search_witnesses),state=record_value(s.state),special_legal=sum(getattr(a,'pattern_id',None)in special for a in aa)))
 if phase==0:
  choices=[a for a in aa if getattr(a,'pattern_id',None)in special and a.actor_type_id!=target]
  if not choices:out['status']='NO_TYPE_CHANGING_TRIGGER';break
  a=sorted(choices,key=repr)[0];before=s.state.position;s.submit(a);out['actual_trigger']=record_value(a);out['trigger_changed_squares']=sum(x!=y for x,y in zip(before.board,s.state.position.board));out['trigger_aux_changed']=before.aux_state!=s.state.position.aux_state;assert out['trigger_changed_squares']==4 and out['trigger_aux_changed']
 elif phase==1:
  if not aa:out['status']='TERMINAL_AFTER_TRIGGER';break
  s.submit(sorted(aa,key=repr)[0])
out.update(seconds=time.perf_counter()-start,scope='OneNEW671001/12 completefour-effect rule combinesactualtwoactor movement,currenttypechange andpersistentper-owner oneuse right. PreferencecheckedAFTERcomposition, rejectedcandidatewouldberetained/no regeneration. Preparationonly, no query/game/train; staticpricesremaincheapcandidate notpricingnewrights.')
write_json(D/'prepared.json',out);pub=Path('docs/research/data/compound_recombined_next_20261019');pub.mkdir(parents=True,exist_ok=True);(pub/'prepared.json').write_bytes((D/'prepared.json').read_bytes().replace(b'\r\n',b'\n'))
print('NEXT_RECOMBINATION',out['status'],out['Native_admission'],len(out['parents']),out['optional_final_preference_passed'],out.get('trigger_changed_squares'),out.get('trigger_aux_changed'),out['seconds'])
