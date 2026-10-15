"""Observed root proof domination versus material-price signal; ALL TRAIN families."""
from pathlib import Path
from collections import Counter,defaultdict
import json
OUT=Path('results/dev_aux/task1993')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def lines(p):return[json.loads(x) for x in Path(p).read_text(encoding='utf-8').splitlines()]
def run():
 results=[]
 for index in (0,1):
  folder=Path('results/dev_aux/task1979')/f'cohort{index}';p=read(folder/'run-plan.json');games=lines(folder/'games.jsonl');moves=lines(folder/'moves.jsonl');first={m['slot']:m for m in moves if m['ply']==0}
  train=games[:416];assert all(g['phase'] in ('RACE','CONTROL') for g in train)
  per=[]
  for f in range(16):
   gs=[g for g in train if g['family']==f];assert len(gs)==26
   root_sources=Counter(first[g['slot']]['source'] for g in gs)
   root_proof=sum(first[g['slot']]['source']=='PROOF' for g in gs)
   one_move_all=all(g['moves']==1 and first[g['slot']]['source']=='PROOF' and g['result']['winner']==0 for g in gs)
   scores={r:sum(g['finite_event_score'] for g in gs if g['R']==r)/2 for r in p['prices']}
   nonflat=len(set(scores.values()))>1
   if one_move_all:assert not nonflat and set(scores.values())=={0}
   per.append(dict(family=f,TRAIN_opponent_R=p['train_opponent_R'][f],root_sources=dict(root_sources),root_PROOF_games=root_proof,all26price_role_games_one_move_fixedproof=one_move_all,nonflat_actual_WL=nonflat,mean_WL_by_R=scores,physical_game_seconds=sum(g['seconds'] for g in gs)))
  results.append(dict(cohort=index,families=16,all_one_move_priceflat_families=sum(x['all26price_role_games_one_move_fixedproof'] for x in per),nonflat_WL_families=sum(x['nonflat_actual_WL'] for x in per),root_PROOF_games=sum(x['root_PROOF_games'] for x in per),root_NORMAL_games=sum(x['root_sources'].get('EXTERNAL_SEARCH',0) for x in per),per_family=per))
 result=dict(status='PASS_ALL_TRAIN_ROOT_DOMINATION_AUDIT',cohorts=results,scope='Posthoc explanatory decomposition of ALL416TRAINrows percohort, no price/reward/root selection. Actualsingle-moveproof domination cannotteach thismaterialparameter despite genuine terminaldensity. This does not prove every rootPROOF multi-movegame priceinvariant: defenderchoices/time policies can differ. No new Core/PN/Native/search calls. Future price-free rootprooffilter would change conditionalmu and requires its own BEFORE-input protocol, not deleting these cases.')
 with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(status=result['status'],cohorts=[{k:v for k,v in c.items() if k!='per_family'} for c in results])))
if __name__=='__main__':run()
