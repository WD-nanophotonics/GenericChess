"""Legacy-only sampler feasibility on existing roots, no games or integration."""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import json,random,statistics,time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.movegen import _expanded_pseudo_actions,_is_legal,legal_actions
from generic_chess.core.semantic_executor import semantic_engine_for

OUT=Path(__file__).resolve().parent
plan={'question':'Can a unique-candidate rejection sampler reduce the current uniform-random caller cost, and would sampling raw hybrid atoms change the intended action distribution?',
 'consumer':'generic_chess.ai.cli.benchmark_alphabeta._vs_random and future nonfrozen uniform prefix acquisition; no mutation of frozen benchmark openings',
 'inputs':'Reuse the21ongoing roots in fallback-cost/result.json; all roots and three repeats retained, no generated games or outcome fit',
 'candidate':'Explicit legacy-only _expanded_pseudo_actions, deduplicate public Actions, uniformly shuffle and accept the first _is_legal; reject semantic rules at entry. Return choice only, normal Session owns execution/history.',
 'gate':'Only a feasibility lead if at least4/6 rules show>=20percent median reduction in complete generation+shuffle+safety choice cost; not a public API/default activation or claim for semantic/auxiliary rules',
 'caps':'60seconds total,3repeats per existing ongoing state, exact multiplicity bias arithmetic before timed trials',
 'distribution':'A uniform permutation of unique pseudo Actions has a uniformly distributed first legal member by symmetry. Raw duplicate multiplicity instead gives probability m_i/sum_j m_j. This changes PRNG tapes and never substitutes frozen opening histories.'}
(OUT/'uniform-sampler-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
data=json.loads((OUT/'fallback-cost/result.json').read_text());compiled={r['seed']:compile_ruleset_for_execution(ruleset_from_dict(r['definition'])) for r in data['rules']};start=time.perf_counter();rows=[]
for root in data['roots']:
 if root['status']!='ongoing':continue
 c=compiled[root['seed']];assert semantic_engine_for(c) is None,'prototype intentionally excludes semantic rules'
 s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));position=s.state.position;before=s.state
 full=legal_actions(s.state,c);raw=list(_expanded_pseudo_actions(position,c));unique=list(dict.fromkeys(raw));counts=Counter(raw);legal_set=set(full)
 assert all(_is_legal(position,a,c)==(a in legal_set) for a in unique)
 assert legal_set=={a for a in unique if _is_legal(position,a,c)}
 legal_mass=sum(counts[a] for a in full);tvd=sum(abs(Fraction(counts[a],legal_mass)-Fraction(1,len(full))) for a in full)/2
 trials=[]
 for rep in range(3):
  assert time.perf_counter()-start<60
  rng_a=random.Random(root['seed']*1000+root['requested_prefix']*10+rep)
  rng_b=random.Random(root['seed']*1000+root['requested_prefix']*10+rep)
  def bulk():
   t=time.perf_counter();a=rng_a.choice(legal_actions(s.state,c));return a,time.perf_counter()-t
  def rejection():
   t=time.perf_counter();choices=list(dict.fromkeys(_expanded_pseudo_actions(position,c)));generated=time.perf_counter()-t;rng_b.shuffle(choices);tested=0
   for a in choices:
    tested+=1
    if _is_legal(position,a,c):return a,time.perf_counter()-t,generated,tested
   raise AssertionError('ongoing state lost all legal candidates')
  if rep%2:a,ta=bulk();b,tb,gen,tested=rejection()
  else:b,tb,gen,tested=rejection();a,ta=bulk()
  assert a in legal_set and b in legal_set and s.state==before
  trials.append({'repeat':rep,'bulk_seconds':ta,'rejection_seconds':tb,'candidate_generation_seconds':gen,'safety_tests':tested,'bulk_action':repr(a),'rejection_action':repr(b)})
 rows.append({'seed':root['seed'],'prefix':root['requested_prefix'],'board':root['board'],'raw_candidates':len(raw),'unique_candidates':len(unique),'unique_legal':len(full),'raw_multiplicity_TVD':float(tvd),'raw_multiplicity_TVD_exact':str(tvd),'expected_safety_trials_without_replacement':float(Fraction(len(unique)+1,len(full)+1)),'trials':trials})
byrule=[]
for seed in compiled:
 rs=[r for r in rows if r['seed']==seed];tr=[t for r in rs for t in r['trials']]
 if not tr:continue
 a=statistics.median(t['bulk_seconds'] for t in tr);b=statistics.median(t['rejection_seconds'] for t in tr)
 byrule.append({'seed':seed,'roots':len(rs),'bulk_median_seconds':a,'rejection_median_seconds':b,'fractional_reduction':1-b/a})
summary={'roots':len(rows),'rules':len(byrule),'choice_calls':sum(len(r['trials'])*2 for r in rows),'roots_with_raw_distribution_bias':sum(r['raw_multiplicity_TVD']>0 for r in rows),'max_raw_TVD':max(r['raw_multiplicity_TVD'] for r in rows),'by_rule':byrule,'feasibility_gate':sum(r['fractional_reduction']>=.2 for r in byrule)>=4,'elapsed_seconds':time.perf_counter()-start,'product_changes':False,'scope':'Legacy generated states only; no semantic,auxiliary or general sampler equivalence claim.'}
(OUT/'uniform-sampler-result.json').write_text(json.dumps({'plan':plan,'summary':summary,'roots':rows},indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
