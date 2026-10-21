"""Reachable occupancy calibration of the finite-roster diagnostic, not prices."""
from collections import Counter
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from math import comb
import json, random, sys, time

ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tests'))
from probe import events,TEMPLATES
from rule_semantics_ir_fixtures import cannon_ruleset
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleReplaceSelector,ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.core.actions import action_source_square,action_target_square,action_is_drop,action_promotion_target_id
from generic_chess.core.movegen import legal_actions

SETTINGS=tuple((seed,n) for seed,n in zip(range(731501,731507),(4,4,6,6,8,8)))
PLAN={'question':'Does fixed-count conditioning improve occupancy-opportunity prediction on actual legal trajectories?',
 'rules':SETTINGS,'policies_per_rule':4,'plies':40,'wall_cap_seconds':180,
 'producer':'Generated bilateral_random/hybrid substrate; first sorted initially present nonanchor nonpromotable type receives four orthogonal rays and replacement clear-quiet/one-screen-capture patterns. Existing promotions,drops,custody,history retained.',
 'policy':'uniform among repr-sorted complete legal actions, Random(rule_seed*100+policy); no refills or outcome filtering',
 'observations':'Each current cannon actor in every ongoing state at plies0..40; same actual source and board friend/enemy counts for A/B/C. Geometric opportunities ignore own-anchor safety; legal target subset checked separately.',
 'decision':'Retain fixed-count engineering only if pooled MAE_C<=.95*MAE_B and C improves on at least4/6 rules, all6 observed. Otherwise leave product unchanged and close counts-only route under this distribution.',
 'limits':'Exposure-weighted descriptive errors with per-rule views, correlated trajectory samples; no population/strength/price/utility inference. No auxiliary-state exposure is promised by the current generator.'}

def choose(n,k):return comb(n,k) if 0<=k<=n else 0

def predict(n,K,E,hist):
 M=n*n-1;Z=M-K;d=F(K,M);u=F(Z,M);ea=d/2;eb=F(E,M);totals=[F(0),F(0),F(0)]
 for L,count in hist.items():
  q=u**(L+1);cap=L*d*u**(L-1) if L else F(0)
  qc=F(choose(Z,L+1),choose(M,L+1));cc=eb*F((K-1)*choose(Z,L-1) if L else 0,choose(M-1,L))
  for i,v in enumerate((q+ea*cap,q+eb*cap,qc+cc)):totals[i]+=count*v
 return dict(zip('ABC',map(float,totals)))

def summarize(rows):
 if not rows:return {'observations':0}
 return {'observations':len(rows),'MAE':{k:sum(abs(r['predicted'][k]-r['actual']) for r in rows)/len(rows) for k in 'ABC'},
  'bias':{k:sum(r['predicted'][k]-r['actual'] for r in rows)/len(rows) for k in 'ABC'}}

def main():
 OUT.mkdir(exist_ok=True);(OUT/'calibration-plan.json').write_bytes((json.dumps(PLAN,indent=2)+'\n').encode())
 start=time.perf_counter();rows=[];slots=[];rules=[];exposure=Counter();invalid=[]
 template=cannon_ruleset(); pats=template.semantic_actions
 for seed,n in SETTINGS:
  if time.perf_counter()-start>=180:break
  generated=generate_game(GeneratorConfig(seed=seed,board_size=n,setup_preset='bilateral_random',allow_hybrid=True))
  definition=generated.ruleset;present={p.current_type_id for row in definition.initial_position for p in row if p}
  candidates=sorted(p.type_id for p in definition.piece_types if not p.is_anchor and not p.is_promotable and p.type_id in present)
  if not candidates:rules.append({'seed':seed,'board':n,'status':'NO_PRESENT_NONPROMOTABLE'});continue
  tid=candidates[0];types=tuple(replace(p,movement_atoms=TEMPLATES['ortho_ray']) if p.type_id==tid else p for p in definition.piece_types)
  patterns=tuple(replace(p,name='roster_probe_'+p.name,type_ids=(tid,),composition='replace_legacy',replace_selector=RuleReplaceSelector(type_ids=(tid,),action_family='board',target_relation=p.target_relation,geometry_kind='ray',replace_all_matching=True)) for p in pats)
  definition=replace(definition,piece_types=types,semantic_actions=patterns)
  compiled=compile_ruleset_for_execution(definition);rules.append({'seed':seed,'board':n,'type':tid,'definition':ruleset_to_dict(definition)})
  for policy in range(4):
   if time.perf_counter()-start>=180:break
   session=GameSession(compiled);rng=random.Random(seed*100+policy);capped=False
   for ply in range(41):
    if time.perf_counter()-start>=180:capped=True;break
    if session.result.status is not SessionStatus.ONGOING:break
    position=session.state.position;board=position.board;actions=list(legal_actions(session.state,compiled))
    for source,piece in enumerate(board):
     if piece is None or piece.current_type_id!=tid:continue
     es=events(n,TEMPLATES['ortho_screen'],source);hist=Counter(len(path) for _,path in es)
     occupied={i for i,p in enumerate(board) if p};enemies={i for i,p in enumerate(board) if p and p.owner!=piece.owner}
     targets={target for target,path in es if (target not in occupied and not any(i in occupied for i in path)) or (target in enemies and sum(i in occupied for i in path)==1)}
     if piece.owner==position.side_to_move:
      actuallegal={action_target_square(a).rank*n+action_target_square(a).file for a in actions if action_source_square(a) is not None and action_source_square(a).rank*n+action_source_square(a).file==source}
      if not actuallegal<=targets:invalid.append({'seed':seed,'policy':policy,'ply':ply,'source':source,'extra_legal':sorted(actuallegal-targets)})
     rows.append({'seed':seed,'policy':policy,'ply':ply,'source':source,'owner':piece.owner,'occupied':len(occupied),'enemy':len(enemies),'actual':len(targets),'predicted':predict(n,len(occupied)-1,len(enemies),hist)})
    exposure['sampled_states']+=1
    exposure['states_with_hands']+=int(any(h.counts for h in position.hands))
    if ply==40:break
    if not actions:raise RuntimeError('Ongoing state has no legal actions')
    action=rng.choice(sorted(actions,key=repr));exposure['drops']+=int(action_is_drop(action));exposure['promotions']+=int(action_promotion_target_id(action) is not None);exposure[type(action).__name__]+=1
    session.submit(action)
   record=serialize_game_record(session.to_record());replayed=GameSession.replay(compiled,deserialize_game_record(record));assert replayed.state==session.state and replayed.result==session.result
   slots.append({'seed':seed,'policy':policy,'plies':session.state.ply_count,'status':session.result.status.value,'wall_capped':capped,'record':json.loads(record) if isinstance(record,str) else record})
 by_rule={str(seed):summarize([r for r in rows if r['seed']==seed]) for seed,_ in SETTINGS};overall=summarize(rows)
 usable=[v for v in by_rule.values() if v['observations']];improved=sum(v['MAE']['C']<v['MAE']['B'] for v in usable)
 decision='RETAIN_CANDIDATE' if len(usable)==6 and overall['MAE']['C']<=.95*overall['MAE']['B'] and improved>=4 and not invalid else 'NO_COUNT_LAW_ENGINEERING'
 result={'plan':PLAN,'decision':decision,'overall':overall,'by_rule':by_rule,'rules_improved_C_vs_B':improved,'exposure':dict(exposure),'invalid_legal_subsets':invalid,'planned_slots':24,'completed_slots':len(slots),'missing_slots':24-len(slots),'elapsed_seconds':time.perf_counter()-start,'rules':rules,'slots':slots,'observations':rows}
 (OUT/'calibration-result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in result.items() if k not in ('rules','slots','observations','plan')},indent=2));assert not invalid,invalid[:3]

if __name__=='__main__':main()
