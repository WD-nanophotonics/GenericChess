"""Complete empirical objective versus strict learner on the tested {2,4} edge."""
from pathlib import Path
from collections import defaultdict,Counter
import json
OUT=Path('results/dev_aux/task1909')
def run():
 folder=Path('results/dev_aux/task1904');games=[json.loads(x) for x in (folder/'games.jsonl').read_text().splitlines()];moves=defaultdict(list)
 for line in (folder/'moves.jsonl').read_text().splitlines():
  m=json.loads(line);moves[m['slot']].append(m['choice'])
 assert len(games)==64 and {g['ratio'] for g in games}=={2.,4.}
 totals={ratio:sum(g['finite_event_score'] for g in games if g['ratio']==ratio) for ratio in (2.,4.)};assert totals=={2.:11,4.:11};maximum=max(totals.values());optima=[r for r,v in totals.items() if v==maximum];learners=[]
 for initial in (2.,4.):
  better=[r for r in (2.,4.) if totals[r]>totals[initial]];chosen=min(better,key=lambda r:(-totals[r],r)) if better else initial
  learners.append(dict(initial=initial,strict_path=[initial] if chosen==initial else [initial,chosen],chosen=chosen,objective=totals[chosen],empirical_regret=maximum-totals[chosen]))
 index={(g['family'],g['candidate_side'],g['ratio']):g for g in games};categories=Counter();pairs=[]
 for family in range(16):
  for role in (0,1):
   a=index[family,role,2.];b=index[family,role,4.];samepath=moves[a['slot']]==moves[b['slot']];sameevent=a['finite_event_score']==b['finite_event_score'];category='same_path_same_event' if samepath and sameevent else 'different_path_same_event' if sameevent else a['outcome']+'->'+b['outcome'];categories[category]+=1
   assert not samepath or a['outcome']==b['outcome'];pairs.append(dict(family=family,role=role,category=category,outcomes=[a['outcome'],b['outcome']],scores=[a['finite_event_score'],b['finite_event_score']]))
 assert all(x['empirical_regret']==0 for x in learners)
 out=dict(status='PASS_COMPLETE_TESTED_EMPIRICAL_OBJECTIVE_CONSISTENCY',candidate_set=[2.,4.],all64_actual_games_used=True,global_total_scores=totals,global_empirical_optimal_set=optima,strict_learners=learners,categories=dict(categories),paired_details=pairs,interpretation='No missedstrictimprovement oroptimizationfailure onTHISobservedtwo-pointedge. Nonuniqueempiricaloptimum/weakfiniteeventsignal, not proof ofpopulation/structuralnonidentifiability or globaloptimum; pricesoutsidegrid/15UNKNOWNperprice remainunresolved. No per-familywinnerselection, revisedglobalprice/DEVrepair or largeroptimizer.',dot_scope='Adopted source-read suggestion from reply1792081894.957649; Dot didnotexecute originalstudies. This audit actually executes locally oncompletepaidrecords.',new_games=0,new_proof_or_native_calls=0,artifact_scope='Late directGit supplement; allrawinputs in sealed EVIDENCE62.')
 with (OUT/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({k:v for k,v in out.items() if k!='paired_details'}))
if __name__=='__main__':run()
