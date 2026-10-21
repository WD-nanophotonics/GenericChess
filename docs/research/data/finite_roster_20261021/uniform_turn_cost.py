"""Complete random-turn cost, including checked submit; no game campaign."""
from pathlib import Path
import json,random,statistics,time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.movegen import _expanded_pseudo_actions,_is_legal
from generic_chess.core.semantic_executor import semantic_engine_for

OUT=Path(__file__).resolve().parent
plan={'question':'Does choice-only sampler feasibility survive the live random-turn consumer including checked Session.submit at an absolute cost worth implementation?',
 'consumer':'Uniform random side of benchmark_alphabeta._vs_random; turn cost only, not AlphaBeta turns or whole games',
 'inputs':'Same21 exposed ongoing roots and6 legacy rules,3repeats,all recorded; separate clones reconstructed before timer. No new game continuations or held-out claim.',
 'arms':'Current session.legal_actions plus choice plus submit, versus unique pseudo Actions shuffle/first legal plus same public submit. Same RNG seed but different uniform draws; actual one-ply successor cost is part of the method contrast, not an isolated same-action executor estimate.',
 'gate':'Consider implementation only if>=4of6rules have both>=20percent median complete-turn reduction and>=1ms absolute median reduction; otherwise defer despite choice-only percentage. No new API/default or semantic scope expansion.',
 'caps':'60seconds total; full successor replay and unchanged parent checked outside timing; common already-held session excludes generation,clone acquisition and replay. This omission precludes whole acquisition/whole game savings claims.'}
(OUT/'uniform-turn-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
data=json.loads((OUT/'fallback-cost/result.json').read_text());compiled={r['seed']:compile_ruleset_for_execution(ruleset_from_dict(r['definition'])) for r in data['rules']};rows=[];start=time.perf_counter()
for root in data['roots']:
 if root['status']!='ongoing':continue
 c=compiled[root['seed']];assert semantic_engine_for(c) is None
 rec=deserialize_game_record(json.dumps(root['record']));parent=GameSession.replay(c,rec);state=parent.state
 for rep in range(3):
  for arm in (('bulk','rejection') if rep%2 else ('rejection','bulk')):
   assert time.perf_counter()-start<60
   s=GameSession.replay(c,rec);rng=random.Random(root['seed']*1000+root['requested_prefix']*10+rep);t=time.perf_counter()
   if arm=='bulk':action=rng.choice(s.legal_actions())
   else:
    candidates=list(dict.fromkeys(_expanded_pseudo_actions(s.state.position,c)));rng.shuffle(candidates)
    action=next(a for a in candidates if _is_legal(s.state.position,a,c))
   selected=time.perf_counter();s.submit(action);end=time.perf_counter()
   replay=GameSession.replay(c,s.to_record());assert replay.state==s.state and replay.result==s.result and parent.state==state
   rows.append({'seed':root['seed'],'prefix':root['requested_prefix'],'repeat':rep,'arm':arm,'action':repr(action),'selection_seconds':selected-t,'submit_seconds':end-selected,'total_seconds':end-t,'successor_ply':s.state.ply_count})
byrule=[]
for seed in compiled:
 q=[r for r in rows if r['seed']==seed]
 if not q:continue
 a=statistics.median(r['total_seconds'] for r in q if r['arm']=='bulk');b=statistics.median(r['total_seconds'] for r in q if r['arm']=='rejection');reduction=1-b/a
 byrule.append({'seed':seed,'bulk_turn_median_seconds':a,'rejection_turn_median_seconds':b,'absolute_saved_seconds':a-b,'fractional_reduction':reduction,'gate':reduction>=.2 and a-b>=.001})
summary={'turns':len(rows),'rules':len(byrule),'passing_rules':sum(r['gate'] for r in byrule),'by_rule':byrule,'decision':'CONSIDER_SCOPED_IMPLEMENTATION' if sum(r['gate'] for r in byrule)>=4 else 'DEFER_IMPLEMENTATION_ABSOLUTE_COST_GATE','elapsed_seconds':time.perf_counter()-start,'all_successors_replay':True,'all_parents_unchanged':True}
(OUT/'uniform-turn-result.json').write_text(json.dumps({'plan':plan,'summary':summary,'turns':rows},indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
