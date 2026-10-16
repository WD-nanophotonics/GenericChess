"""Existing cohort phase/work/outcome-density decomposition, no new search."""
from pathlib import Path
from collections import Counter,defaultdict
import json,statistics
OUT=Path('results/dev_aux/task2035')
def lines(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def audit(folder):
 p=Path(folder);g=lines(p/'games.jsonl');m=lines(p/'moves.jsonl');by=defaultdict(list)
 for x in m:by[x['slot']].append(x)
 phase={k:sum(x[k] for x in m) for k in ('admission_seconds','proof_seconds','verification_seconds','normal_seconds','seconds','commit_seconds')}
 groups={}
 for outcome in ('WIN','LOSS','DRAW','UNKNOWN'):
  gs=[x for x in g if x['outcome']==outcome];ms=[x for a in gs for x in by[a['slot']]]
  if gs:groups[outcome]=dict(games=len(gs),moves=sum(x['moves'] for x in gs),mean_game_seconds=statistics.mean(x['seconds'] for x in gs),mean_plies=statistics.mean(x['moves'] for x in gs),PN_nodes=sum(x['proof_nodes'] for x in ms),normal_nodes=sum(x['search_nodes'] for x in ms),PN_seconds=sum(x['proof_seconds'] for x in ms),normal_seconds=sum(x['normal_seconds'] for x in ms),terminal_causes=dict(Counter(x['result']['status'] for x in gs)))
 first=[min((x['ply'] for x in by[a['slot']] if x['source']=='PROOF'),default=None) for a in g]
 decisive=sum(x['outcome'] in ('WIN','LOSS') for x in g)
 return dict(games=len(g),moves=len(m),actual_decisive=decisive,decisive_fraction=decisive/len(g),phase_seconds=phase,outcomes=groups,proof_adopting_games=sum(x is not None for x in first),first_proof_plies=[x for x in first if x is not None],proof_reason=dict(Counter(x['proof_reason'] for x in m)),bank_hits=sum(x['bank_hit'] for x in m),mean_decision_seconds=statistics.mean(x['seconds'] for x in m),mean_game_seconds=statistics.mean(x['seconds'] for x in g),mean_plies=len(m)/len(g))
def main():
 result=dict(status='PASS_EXISTING_COST_DENSITY_DECOMPOSITION',cohorts={k:audit('results/dev_aux/'+v) for k,v in dict(KRN4='task2016',KRNB4='task2020',KRNB6='task2027',KRN4_UNITS='task2030').items()},scope='Different frozen input distributions/type inventories. Measured descriptive cost decomposition, not causal board-size or pure backend speed comparison. Max96 is actual declared rule draw. Low decisive density differs from UNKNOWN. No new Native/proof calls or reruns, no4census transfer.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:{x:v[x] for x in ('games','moves','actual_decisive','mean_game_seconds','mean_plies','mean_decision_seconds','bank_hits')} for k,v in result['cohorts'].items()}))
if __name__=='__main__':main()
