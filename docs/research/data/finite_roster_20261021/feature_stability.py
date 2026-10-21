"""Literature feasibility: role-frame stability on existing full histories only."""
from dataclasses import replace
from pathlib import Path
import json, statistics, time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator

OUT=Path(__file__).resolve().parent
plan={'question':'Can raw temporal feature stability directly select a cheap evaluation component for these generated games, and how sensitive is it to the caller perspective?',
 'source':'Clune2007 AAAI07-180 pp1136-1137; fixed-role feature variance divided by adjacent mean squared change. This probe is not his complete payoff/control/termination model.',
 'data':'Reuse all24 full calibration histories; no new games, outcomes, training, labels, fitted weights or seed selection',
 'features':['Unit full material','board-only count','hand-only count','legacy coverage','semantic coverage','semantic anchor heuristic','ply negative control'],
 'frames':['owner0 fixed','side to move'],
 'protocol':'Ongoing states only; per-rule population variance across all observed states, adjacent squared differences only within same trajectory. Zero denominator stays undefined, not infinity. Report per-rule ranks and pairwise rank changes; no cross-rule pooling.',
 'decision':'Any perspective rank reversal or dominant ply negative-control witness rules out using stability alone as the current component selector. No successor learned-evaluator implementation is authorized or warranted by this descriptive check.',
 'cap_seconds':120,'scope':'Six authored cannon recombinations, same exposed calibration histories. Feature variance is not payoff correlation, action utility or WDL. Full generic target and auxiliary role boundary unchanged.'}
(OUT/'stability-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
data=json.loads((OUT/'calibration-result.json').read_text());start=time.perf_counter();observations=[]
for rule in data['rules']:
 c=compile_ruleset_for_execution(ruleset_from_dict(rule['definition']))
 cfg=EvaluationConfig(promotion_potential_weight=0)
 profile=build_ruleset_profile(c,cfg);values={p.type_id:0 if p.is_anchor else 1000 for p in c.piece_types}
 profile=replace(profile,piece_profiles={k:replace(v,normalized_board_value=values[k],normalized_hand_value=values[k],promotion_option_value=0) for k,v in profile.piece_profiles.items()},board_value_by_type=values,hand_value_by_base_type=values,promotion_gain_by_type={k:0 for k in values},median_non_anchor_value=1000)
 covcfg=replace(cfg,dynamic_mobility_weight=1,anchor_escape_weight=0)
 anccfg=replace(cfg,dynamic_mobility_weight=0,anchor_escape_weight=1)
 staticcfg=replace(cfg,dynamic_mobility_weight=0,anchor_escape_weight=0)
 evals={'material':Evaluator(c,profile,staticcfg),'legacy_coverage':Evaluator(c,profile,covcfg),'semantic_coverage':SemanticAttackEvaluator(c,profile,covcfg,backend='core'),'semantic_anchor':SemanticAttackEvaluator(c,profile,anccfg,backend='core')}
 for slot in data['slots']:
  if slot['seed']!=rule['seed']:continue
  rec=deserialize_game_record(json.dumps(slot['record']));s=GameSession(c)
  for i in range(len(rec.actions)+1):
   assert time.perf_counter()-start<120,'bounded probe cap'
   if s.result.status is SessionStatus.ONGOING:
    sign=1 if s.state.position.side_to_move==0 else -1
    board=sum((1 if p.owner==0 else -1) for p in s.state.position.board if p and not c.types_by_id[p.current_type_id].is_anchor)
    hands=sum((1 if owner==0 else -1)*count for owner,h in enumerate(s.state.position.hands) for tid,count in h.counts)
    unit={k:e.evaluate(s.state)*sign for k,e in evals.items()}
    material=unit['material']/1000;assert material==board+hands
    fixed={'material':material,'board':board,'hands':hands,'legacy_coverage':unit['legacy_coverage']-unit['material'],'semantic_coverage':unit['semantic_coverage']-unit['material'],'semantic_anchor':unit['semantic_anchor']-unit['material'],'ply':s.state.ply_count}
    observations.append({'seed':rule['seed'],'policy':slot['policy'],'ply':i,'fixed':fixed,'stm':{k:v*sign for k,v in fixed.items()}})
   if i<len(rec.actions):s.submit(rec.actions[i])
  assert s.result.status.value==slot['status']
results=[]
for rule in data['rules']:
 rows=[r for r in observations if r['seed']==rule['seed']];quotients={}
 for frame in ('fixed','stm'):
  stats={}
  for feature in rows[0][frame]:
   vals=[r[frame][feature] for r in rows];adj=[(b[frame][feature]-a[frame][feature])**2 for a,b in zip(rows,rows[1:]) if a['policy']==b['policy'] and b['ply']==a['ply']+1]
   variance=statistics.pvariance(vals);adjvar=statistics.mean(adj) if adj else None
   stats[feature]={'states':len(vals),'adjacent_pairs':len(adj),'variance':variance,'adjacent_mse':adjvar,'quotient':variance/adjvar if adjvar else None}
  quotients[frame]=stats
 names=[k for k in rows[0]['fixed'] if k!='ply'];flips=[]
 for i,a in enumerate(names):
  for b in names[i+1:]:
   vals=[quotients[f][n]['quotient'] for f in ('fixed','stm') for n in (a,b)]
   if None not in vals and (vals[0]-vals[1])*(vals[2]-vals[3])<0:flips.append([a,b])
 fixedq=quotients['fixed'];finite={k:v['quotient'] for k,v in fixedq.items() if v['quotient'] is not None}
 results.append({'seed':rule['seed'],'board':rule['board'],'statistics':quotients,'perspective_rank_flips':flips,'fixed_largest':max(finite,key=finite.get)})
summary={'states':len(observations),'rules':len(results),'rules_with_rank_flip':sum(bool(r['perspective_rank_flips']) for r in results),'fixed_largest':{str(r['seed']):r['fixed_largest'] for r in results},'elapsed_seconds':time.perf_counter()-start,'decision':'NO_STABILITY_ONLY_COMPONENT_SELECTOR'}
(OUT/'stability-result.json').write_text(json.dumps({'plan':plan,'summary':summary,'by_rule':results},indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
