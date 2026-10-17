"""All-arm learning/cost trajectories; no outcome-based model selection."""
from pathlib import Path
from collections import defaultdict,Counter
from math import sqrt,tanh
import json,time
D=Path('results/dev_aux/task2539');E=Path('results/dev_aux/task2540');O=Path('results/dev_aux/task2541')
def rms(a,b):return sqrt(sum((x-y)**2 for x,y in zip(a,b))/len(a))
def run():
 began=time.perf_counter();p=json.loads((D/'plan.json').read_text());done=json.loads((D/'result.json').read_text());updates=defaultdict(list);games=defaultdict(list)
 for line in(D/'updates.jsonl').open():
  r=json.loads(line);updates[r['generator_seed'],r['method'],r['seed']].append(r)
 for line in(D/'games.jsonl').open():
  r=json.loads(line);games[r['generator_seed'],r['method'],r['seed']].append(r)
 rows=[]
 for a in done['arms']:
  key=a['generator_seed'],a['method'],a['seed'];us=updates[key];gs=games[key];tally=Counter('U'if r['reward']is None else'D'if r['reward']==0 else'W'if r['reward']==1 else'L'for r in gs);stats=[r['stats']for r in gs if r['stats']is not None];tdterms=sum(s['samples']for s in stats);loss=sum(s['loss']*s['samples']for s in stats)/max(1,tdterms)
  bins=[]
  for upper in(50000,100000,150000,200000):
   ss=[r['stats']for r in gs if r['stats']is not None and upper-50000<r['total_nodes']<=upper];nn=sum(x['samples']for x in ss);bins.append(dict(closed_game_node_bin=[upper-50000,upper],games=len(ss),terms=nn,mean_half_squared_TD_error=None if not nn else sum(x['loss']*x['samples']for x in ss)/nn))
  direction=lambda w:[x/sqrt(sum(y*y for y in w))for x in w]if any(w)else None
  rows.append(dict(rule=key[0],method=key[1],seed=key[2],nodes=a['nodes'],seconds=a['seconds'],games=a['games'],updates=a['updates'],proposal_blocks=a['blocks'],nodes_per_game=a['nodes']/max(1,a['games']),training_rewards=dict(tally),TDterms=tdterms,TDloss=loss if stats else None,TDloss_node_bins=bins,initial=a['initial'],weights=a['weights'],raw_RMS_move=rms(a['initial'],a['weights']),posthoc_L2direction=direction(a['weights']),P_min=min([a['initial'][0]]+[u['after'][0]for u in us]),P_max=max([a['initial'][0]]+[u['after'][0]for u in us]),proposal_bounds=[u['bounds']for u in us if 'bounds'in u],path=[dict(nodes=u['nodes'],weights=u['after'],changed=u['changed'])for u in us]))
 spreads=[]
 for g in p['generator_seeds']:
  for method in('TD','WDL'):
   rr=[r for r in rows if r['rule']==g and r['method']==method];ws=[r['weights']for r in rr];centroid=[sum(w[j]for w in ws)/len(ws)for j in range(6)];spreads.append(dict(rule=g,method=method,models=len(ws),final_raw_RMS_dispersion=sqrt(sum(sum((w[j]-centroid[j])**2 for j in range(6))for w in ws)/max(1,len(ws)*6)),negative_P_endpoints=sum(w[0]<0 for w in ws)))
 out=dict(status='ALL_RAW_ARMS_AND_PAID_COSTS_RETAINED',rows=rows,spreads=spreads,scope='TrainingWDL/lossdescriptiveNOTfitness or crossmethodcommensurateloss. L2directionposthocONLY/no normalizationdeployed. Differentgame/updatecountsaremethodcostconsequences. Perarmwallmeasuredincludesownjournal/replay, ordinaryconcurrencynotcontrolledspeedup. No endpoint/seed/step selection.',seconds=time.perf_counter()-began);(O/'diagnostics.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],arms=len(rows),spreads=spreads)))
if __name__=='__main__':run()
