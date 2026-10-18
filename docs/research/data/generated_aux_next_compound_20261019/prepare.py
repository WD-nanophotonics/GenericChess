"""Begin the next complete compound consumer; prepare real states, no search."""
from pathlib import Path
from dataclasses import replace,asdict
import json,sys,time,hashlib
sys.path.insert(0,str(Path.cwd()))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.generation.filters import run_soft_filters
from generic_chess.rules.schema import RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleInvariant,ruleset_to_dict
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.execution import ExecutableSemanticRuleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.native.compiler import compile_native_semantic_rules,NativeUnsupportedRuleError
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
R=Path.cwd();start=time.perf_counter();D=R/'.local_agent/generated-aux-next-compound-20261019';D.mkdir(exist_ok=True)
for n in ('rollout','advisor','slack'):
 f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused'))
cfg=GeneratorConfig(seed=641001,board_size=6,setup_preset='classic_like',movement_symmetry='none',allow_hybrid=True,max_generation_attempts=64);g=generate_game(cfg)
action=RuleSemanticAction(name='generated_pair_shift',type_ids=tuple(t.type_id for t in g.ruleset.piece_types if not t.is_anchor),geometry=RuleGeometrySpec(kind='leap',offset=(1,2),owner_relative=True),target_relation='empty',composition='augment',effects=(RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')),RuleActionEffect('shift',from_ref=RuleSquareRef('offset_from_source',offset=(0,1),owner_relative=True),to_ref=RuleSquareRef('offset_from_source',offset=(0,2),owner_relative=True),piece_owner='self')),invariants=(RuleInvariant('own_anchor_safe'),))
rule=replace(g.ruleset,semantic_actions=(action,),metadata={**g.ruleset.metadata,'research_recipe':'twoactorcompoundshift'});c=compile_semantic_ruleset(rule);e=ExecutableSemanticRuleset.from_compiled(c)
out=dict(status='PREPARED',config=asdict(cfg),rule=ruleset_to_dict(rule),parents=[],new_Native_searches=0,new_Core_searches=0,new_games=0,new_training=0)
try:compile_native_semantic_rules(c);out['Native_admission']='SUPPORTED'
except NativeUnsupportedRuleError as exc:out.update(Native_admission='REFUSED',refusal=str(exc))
out['optional_opening_preferences']=record_value(run_soft_filters(replace(cfg,require_no_opening_win_in_one=True),e,{t.type_id:t for t in rule.piece_types}))
profile=build_ruleset_profile(g.compiled_ruleset,EvaluationConfig());anchors={t.type_id for t in rule.piece_types if t.is_anchor};out['board_values']={t.type_id:0 if t.type_id in anchors else round(profile.board_value_by_type[t.type_id]*.256)for t in rule.piece_types};out['hand_values']={t.type_id:0 if t.type_id in anchors else round(profile.hand_value_by_base_type[t.type_id]*.256)for t in rule.piece_types}
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
s=GameSession(c);ids={p.pattern_id for p in c.ir.patterns if p.name=='generated_pair_shift'}
for phase in range(3):
 out['parents'].append(dict(phase=phase,record=json.loads(serialize_game_record(s.to_record())),state_sha256=digest(s.state),witness_sha256=digest(s._search_witnesses),state=record_value(s.state)))
 if phase==0:
  aa=[a for a in s.legal_actions()if getattr(a,'pattern_id',None)in ids]
  if not aa:out['status']='NO_LEGAL_TRIGGER';break
  before=s.state.position;s.submit(sorted(aa,key=repr)[0]);out['trigger_changed_squares']=sum(a!=b for a,b in zip(before.board,s.state.position.board))
 elif phase==1:
  aa=s.legal_actions()
  if not aa:out['status']='TERMINAL_AFTER_TRIGGER';break
  s.submit(sorted(aa,key=repr)[0])
out.update(seconds=time.perf_counter()-start,scope='Nextstepactuallybegun AFTERthe67payloadseal: oneNEWfullgeneratedrule641001/6 withtwoactorcompoundshift, actualSessiontrigger/reply, fullpromotion/drop/history. Existingstatic256tables remaincheapcandidate, notpricingcompoundeffects. No search/games/learning orall-domainclaim.')
write_json(D/'prepared.json',out);pub=R/'docs/research/data/generated_aux_next_compound_20261019';pub.mkdir(parents=True,exist_ok=True);(pub/'prepared.json').write_bytes((D/'prepared.json').read_bytes())
print('NEXT_COMPOUND',out['status'],out.get('Native_admission'),len(out['parents']),out.get('trigger_changed_squares'),out['seconds'])
