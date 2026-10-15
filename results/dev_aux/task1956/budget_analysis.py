"""Actual lower-proof resource curve; no chosen budget/price or new validation."""
from pathlib import Path
from collections import Counter
import json,time
from results.dev_aux.task1953.audit import contrast
from results.dev_aux.task1928.audit import lines,read
O=Path('results/dev_aux/task1956')
def run():
 beg=time.perf_counter();low=lines('results/dev_aux/task1954/games.jsonl');off=lines('results/dev_aux/task1943/games.jsonl');high=lines('results/dev_aux/task1944/games.jsonl');ix={(g['opponent_nodes'],g['family'],g['candidate_side'],g['ratio'],cap):g for cap,gs in [(0,off),(16384,high),(1024,[g for g in low if g['candidate_proof_nodes']==1024]),(4096,[g for g in low if g['candidate_proof_nodes']==4096])] for g in gs};assert len(ix)==1024;panels=[];retention=[]
 for opp in (512,4096):
  cells=[];effects={}
  for cap in (0,1024,4096,16384):
   for ratio in (1.,2.):
    gs=[ix[opp,f,s,ratio,cap] for f in range(32) for s in (0,1)];cells.append(dict(proof_nodes=cap,ratio=ratio,outcomes=dict(Counter(g['outcome'] for g in gs)),net=sum(g['finite_event_score'] for g in gs),sum_game_seconds=sum(g['seconds'] for g in gs)))
   effects[str(cap)]=contrast(ix,opp,[(cap,2.,1),(cap,1.,-1)])
   if cap:
    for ratio in (1.,2.):effects[f'proof{cap}_at{ratio}']=contrast(ix,opp,[(cap,ratio,1),(0,ratio,-1)])
  panels.append(dict(opponent_nodes=opp,cells=cells,effects=effects))
 for cap in (1024,4096):
  counts=Counter();cases=[]
  for opp in (512,4096):
   for f in range(32):
    for s in (0,1):
     for r in (1.,2.):
      a,b,c=ix[opp,f,s,r,0],ix[opp,f,s,r,16384],ix[opp,f,s,r,cap];counts['same_outcome_as16k']+=b['outcome']==c['outcome'];counts['same_full_path_as16k']+=b['record']==c['record'];counts[a['outcome']+'->'+c['outcome']]+=1
      if a['outcome']=='UNKNOWN' and b['outcome']=='WIN':cases.append(dict(opponent_nodes=opp,family=f,role=s,ratio=r,cheap_outcome=c['outcome']))
  retention.append(dict(proof_nodes=cap,counts=dict(counts),old16k_marginal8_cases=cases,marginal8_still_actual_win=sum(c['cheap_outcome']=='WIN' for c in cases)))
 costs={cap:sum(ix[opp,f,s,r,cap]['seconds'] for opp in (512,4096) for f in range(32) for s in (0,1) for r in (1.,2.)) for cap in (0,1024,4096,16384)}
 out=dict(status='PASS_ALL_PREDECLARED_CHEAP_BUDGET_CELLS',panels=panels,retention=retention,sum_game_seconds=costs,actual_512_protocol_seconds=read('results/dev_aux/task1954/completion.json')['seconds'],scope='Allsame32EXPOSEDfamilies/roles/2fixedopponents/locked1,2; developmentresourcecurve, NOTfreshvalidation or selectingbudgetfromDEV. Fourcaps varyONLYcandidatePN allowance/bankkey, samefullrule/cursorverification/normalcap; actualstates/paths canchange. Game-time sums omitinitialprotocoloverhead andordinaryload differs; noexclusiveequalcostoruniversal speedup. UNKNOWNdistinct, onlyactualrulesWIN/LOSSscore. Previouslyobserved8marginalcasesretentionisdescriptive, notthefilterfornewcases.',seconds=time.perf_counter()-beg)
 (O/'budget-result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(costs=costs,retention=[{k:v for k,v in q.items() if k!='old16k_marginal8_cases'} for q in retention],price_means=[dict(opp=p['opponent_nodes'],values={cap:p['effects'][str(cap)]['mean'] for cap in (0,1024,4096,16384)}) for p in panels],seconds=out['seconds'])))
if __name__=='__main__':run()
