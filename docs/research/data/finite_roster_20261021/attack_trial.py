"""Prospective attack-authority utility diagnostic; existing evaluators only."""
from __future__ import annotations
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, random, subprocess, sys, time

ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent/'attack-utility'
sys.path.insert(0,str(ROOT/'tests'))
from rule_semantics_ir_fixtures import cannon_ruleset
from generic_chess.core.movement import RayAtom
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleReplaceSelector,ruleset_to_dict
from generic_chess.rules.validation import RuleValidationError
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.core.actions import action_is_drop,action_promotion_target_id

SETTINGS=tuple(zip(range(731601,731609),(4,4,5,5,6,6,8,8)))
PLAN={'question':'Does existing semantic Native attack authority improve bounded search utility versus legacy maps on generated cannon recombinations?',
 'settings':SETTINGS,'prefixes':[3,4],'candidate_owners':[0,1],'arms':['legacy','semantic_native'],'fixed_foe':'legacy',
 'profile':'Unit1000 nonanchors/0 anchors on board and hands; zero promotion gain; identical across both arms',
 'evaluation':'dynamic_mobility_weight2,anchor_escape_weight5,promotion_potential_weight0; only attack authority differs',
 'search':{'max_depth':3,'max_nodes':2048,'max_time_seconds':.05,'quiescence_max_depth':0,'quiescence_hard_max_depth':0,'TT':False,'ordering':False,'root_tactical':False},
 'game_additional_ply_cap':48,'total_wall_cap_seconds':300,'planned_slots':64,
 'construction':'Current bilateral_random/hybrid generator, first sorted initially present nonanchor nonpromotable type replaced by orthogonal-ray quiet and one-screen capture. No root/action/outcome feasibility filter or refill. Full promotion/drop/history retained.',
 'root_policy':'Random(seed*10+requested_prefix), uniform over repr-sorted complete legal actions; early terminals retained',
 'resource_claim':'Equal configured per-move limits, not equal actual depth/work; cooperative wall limits and query overshoot reported',
 'gate':'Paired semantic-minus-legacy candidate reward interval lower>0 overall and lower>=0 for each owner; actual Core W/D/L only, every ongoing/missing/failed slot UNKNOWN[-1,1]. Only selects optional utility lead, never a general default/strength claim.',
 'scope':'Eight authored recombinations of generated substrates, no human labels or all-domain inference. Semantic Native root maps checked against Core before play; not a proof for every subnode.'}

def save(name,value):
 (OUT/name).write_bytes((json.dumps(value,indent=2)+'\n').encode())

def record(session):return json.loads(serialize_game_record(session.to_record()))
def restore(compiled,r):return GameSession.replay(compiled,deserialize_game_record(json.dumps(r)))
def reward(row):
 if row['status']=='ongoing' or row.get('error') or row.get('unstarted'):return (-1,1)
 winner=row['winner']; value=0 if winner is None else 1 if winner==row['candidate_owner'] else -1
 return (value,value)

def main():
 OUT.mkdir(parents=True,exist_ok=True); start=time.perf_counter()
 patch=subprocess.check_output(['git','diff','--','generic_chess']);(OUT/'source.patch').write_bytes(patch)
 PLAN['source_head']=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip();PLAN['source_patch_sha256']=hashlib.sha256(patch).hexdigest();PLAN['started_at']=datetime.now(timezone.utc).isoformat();save('plan.json',PLAN)
 cfg=EvaluationConfig(promotion_potential_weight=0)
 limits=SearchLimits(max_depth=3,max_nodes=2048,max_time_seconds=.05,quiescence_max_depth=0,quiescence_hard_max_depth=0)
 tuning=SearchTuning(use_root_tactical=False); definitions=[];prepared=[];preflight=[]
 for seed,n in SETTINGS:
  generated=generate_game(GeneratorConfig(seed=seed,board_size=n,setup_preset='bilateral_random',allow_hybrid=True));definition=generated.ruleset
  present={p.current_type_id for row in definition.initial_position for p in row if p};tid=next(iter(sorted(p.type_id for p in definition.piece_types if not p.is_anchor and not p.is_promotable and p.type_id in present)))
  types=tuple(replace(p,movement_atoms=tuple(RayAtom(x) for x in ((1,0),(-1,0),(0,1),(0,-1)))) if p.type_id==tid else p for p in definition.piece_types)
  patterns=tuple(replace(p,name='attack_probe_'+p.name,type_ids=(tid,),composition='replace_legacy',replace_selector=RuleReplaceSelector(type_ids=(tid,),action_family='board',target_relation=p.target_relation,geometry_kind='ray',replace_all_matching=True)) for p in cannon_ruleset().semantic_actions)
  definition=replace(definition,piece_types=types,semantic_actions=patterns)
  try:
   compiled=compile_ruleset_for_execution(definition)
  except RuleValidationError as exc:
   error=f'{type(exc).__name__}: {exc}'
   definitions.append({'seed':seed,'board':n,'cannon_type':tid,'definition':ruleset_to_dict(definition),'compile_error':error})
   prepared.append((seed,n,None,error,[(3,None),(4,None)]))
   continue
  profile=build_ruleset_profile(compiled,cfg);values={p.type_id:0 if p.is_anchor else 1000 for p in compiled.piece_types};gains={p.type_id:0 for p in compiled.piece_types}
  pieces={k:replace(v,normalized_board_value=values[k],normalized_hand_value=values[k],promotion_option_value=0) for k,v in profile.piece_profiles.items()}
  profile=replace(profile,piece_profiles=pieces,board_value_by_type=values,hand_value_by_base_type=values,promotion_gain_by_type=gains,median_non_anchor_value=1000)
  evaluators={'legacy':Evaluator(compiled,profile,cfg),'semantic_native':SemanticAttackEvaluator(compiled,profile,cfg,backend='native')};core=SemanticAttackEvaluator(compiled,profile,cfg,backend='core')
  roots=[]
  for prefix in (3,4):
   s=GameSession(compiled);rng=random.Random(seed*10+prefix)
   for _ in range(prefix):
    if s.result.status is not SessionStatus.ONGOING:break
    s.submit(rng.choice(sorted(s.legal_actions(),key=repr)))
   maps_core=core._attack_maps(s.state);maps_native=evaluators['semantic_native']._attack_maps(s.state);assert maps_core==maps_native,(seed,prefix)
   preflight.append({'seed':seed,'prefix':prefix,'actual_ply':s.state.ply_count,'Core_Native_map_equal':True,'map_symmetric_difference':[len(a^b) for a,b in zip(evaluators['legacy']._attack_maps(s.state),maps_core)],'scores':{k:e.evaluate(s.state) for k,e in evaluators.items()}})
   roots.append((prefix,record(s)))
  prepared.append((seed,n,compiled,evaluators,roots));definitions.append({'seed':seed,'board':n,'cannon_type':tid,'definition':ruleset_to_dict(definition)})
 save('rules.json',definitions);save('preflight.json',preflight);games=[]
 with (OUT/'games.jsonl').open('w',encoding='utf-8') as stream:
  for seed,n,compiled,evaluators,roots in prepared:
   for prefix,r in roots:
    for owner in (0,1):
     armorder=('legacy','semantic_native') if (seed+prefix+owner)%2 else ('semantic_native','legacy')
     for arm in armorder:
      if compiled is None:
       row={'seed':seed,'board':n,'prefix':prefix,'root_ply':None,'candidate_owner':owner,'arm':arm,'status':'ongoing','winner':None,'error':evaluators,'run_capped':False,'unstarted':True,'additional_plies':0,'events':[],'record':None}
       games.append(row);stream.write(json.dumps(row)+'\n');stream.flush();continue
      s=restore(compiled,r);players={side:AlphaBetaPlayer(compiled,evaluator_override=evaluators[arm if side==owner else 'legacy'],use_disk_cache=False,use_tt=False,use_ordering=False,tt_max_entries=0,tuning=tuning) for side in (0,1)}
      event=[];error=None;run_capped=False;unstarted=time.perf_counter()-start>=300
      if not unstarted:
       try:
        for step in range(48):
         if s.result.status is not SessionStatus.ONGOING:break
         if time.perf_counter()-start>=300:run_capped=True;break
         side=s.state.position.side_to_move;t=time.perf_counter();d=players[side].choose_action(s,limits);wall=time.perf_counter()-t
         if d.action is None:raise RuntimeError('ongoing caller returned no action')
         event.append({'owner':side,'candidate':side==owner,'action':repr(d.action),'nodes':d.nodes,'qnodes':d.qnodes,'depth':d.completed_depth,'termination':d.termination_reason,'caller_seconds':wall,'reported_seconds':d.elapsed_seconds,'drop':action_is_drop(d.action),'promotion':action_promotion_target_id(d.action) is not None})
         s.submit(d.action)
       except Exception as exc:error=f'{type(exc).__name__}: {exc}'
      replayed=restore(compiled,record(s));assert replayed.state==s.state and replayed.result==s.result
      row={'seed':seed,'board':n,'prefix':prefix,'root_ply':r['actions'].__len__() if 'actions' in r else None,'candidate_owner':owner,'arm':arm,'status':s.result.status.value,'winner':s.result.winner,'error':error,'run_capped':run_capped,'unstarted':unstarted,'additional_plies':len(event),'events':event,'record':record(s)}
      games.append(row);stream.write(json.dumps(row)+'\n');stream.flush()
 pairs=[]
 for seed,n in SETTINGS:
  for prefix in (3,4):
   for owner in (0,1):
    a=next(x for x in games if (x['seed'],x['prefix'],x['candidate_owner'],x['arm'])==(seed,prefix,owner,'legacy'));b=next(x for x in games if (x['seed'],x['prefix'],x['candidate_owner'],x['arm'])==(seed,prefix,owner,'semantic_native'));la,ha=reward(a);lb,hb=reward(b);pairs.append({'seed':seed,'board':n,'prefix':prefix,'owner':owner,'bounds':[lb-ha,hb-la]})
 def bounds(rows):return [sum(r['bounds'][i] for r in rows)/len(rows) for i in (0,1)]
 interval=bounds(pairs);by_owner={str(o):bounds([x for x in pairs if x['owner']==o]) for o in (0,1)}
 costs={}
 for arm in ('legacy','semantic_native'):
  es=[e for g in games if g['arm']==arm for e in g['events'] if e['candidate']];costs[arm]={'queries':len(es),'nodes':sum(e['nodes']+e['qnodes'] for e in es),'caller_seconds':sum(e['caller_seconds'] for e in es),'depth_histogram':dict(Counter(e['depth'] for e in es)),'termination_histogram':dict(Counter(e['termination'] for e in es)),'max_caller_seconds':max((e['caller_seconds'] for e in es),default=0)}
 same_patch=patch==subprocess.check_output(['git','diff','--','generic_chess']);assert same_patch,'source changed during trial'
 summary={'plan':PLAN,'decision':'UTILITY_LEAD_ONLY' if interval[0]>0 and all(v[0]>=0 for v in by_owner.values()) and not any(g['error'] for g in games) else 'NO_DEFAULT_CHANGE_NO_UNCHANGED_RERUN','slots':len(games),'unknown':sum(reward(g)==(-1,1) for g in games),'failed':sum(bool(g['error']) for g in games),'unstarted':sum(g['unstarted'] for g in games),'bounds':interval,'by_owner':by_owner,'by_board':{str(n):bounds([x for x in pairs if x['board']==n]) for n in (4,5,6,8)},'costs':costs,'elapsed_seconds':time.perf_counter()-start,'source_unchanged':same_patch,'pairs':pairs}
 save('summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ('plan','pairs')},indent=2))

if __name__=='__main__':main()
