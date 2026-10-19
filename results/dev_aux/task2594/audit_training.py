"""Independent replay of DEV_AUX2594 training updates and histories."""
import hashlib,json,math
from collections import defaultdict
from pathlib import Path
from results.dev_aux.task2492.learning import Model,transformed
from results.dev_aux.task2565.train import restore
T=Path(__file__).resolve().parent; ROOT=T.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b):return math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-10)
def main():
 p=json.loads((T/'train'/'plan.json').read_text());r=json.loads((T/'train'/'result.json').read_text())
 for name,h in p['pins'].items():assert sha(ROOT/name)==h,name
 qf=iter((T/'train'/'queries.jsonl').open(encoding='utf-8'));games=[json.loads(x)for x in (T/'train'/'games.jsonl').open(encoding='utf-8')]
 counts=defaultdict(lambda:{'games':0,'nodes':0,'targets':0,'observed':0,'terms':0,'actual':0,'unknown':0})
 query_total=node_total=observed_total=term_total=terminal_targets=0
 for g in games:
  qs=[]
  while True:
   try:q=json.loads(next(qf))
   except StopIteration:break
   if q['gameid']!=g['gameid']:
    # Keep a one-row lookahead without losing stream position.
    qf=iter([json.dumps(q),*qf]);break
   qs.append(q)
  assert len(qs)==g['queries'],(g['gameid'],len(qs),g['queries'])
  assert (qs[0]['record_before'] if qs else g['initial_record'])==g['initial_record']
  prev=g['initial_record']
  for q in qs:
   assert q['record_before']==prev,(g['gameid'],q['ply'])
   assert q['observed']==(q['actor']==g['color'] and q['complete'])
   if q['observed']: assert q['weights']==g['played_weights']
   prev=q['record_after'];query_total+=1;node_total+=q['nodes']
  assert prev==g['record'],g['gameid']
  replay=restore(0,None,g['record']);assert replay.record()==g['record'] and replay.terminal()==g['outcome']
  obs=[q for q in qs if q['observed']]
  model=Model(g['initial_weights']);rows=[]
  for q in obs:
   pred=transformed(q['value'],model.scale)
   grad=[0.0]*len(model.weights) if q['pv_terminal'] else list(model.gradient(q['pv_phi']))
   rows.append((pred,grad,bool(q['pv_terminal'])))
  delta=[0.0]*len(model.weights);loss=0.0;terms=0;targets=0
  for i,(prediction,_,_) in enumerate(rows):
   if i+1<len(rows):
    target,_,is_terminal=rows[i+1];lam=1.0 if is_terminal else p['lambda'];targets+=is_terminal
   else:
    target=g['outcome'];lam=p['lambda']
   if target is None:break
   error=float(target)-prediction;loss+=error*error/2.0;terms+=1
   eligibility=[sum((lam**(i-j))*rows[j][1][k]for j in range(i+1))for k in range(len(delta))]
   for k,e in enumerate(eligibility):delta[k]+=error*e
  model.apply([p['eta']*x for x in delta])
  assert all(close(a,b)for a,b in zip(model.weights,g['weights'])),g['gameid']
  assert terms==g['stats']['samples'] and bool(g['outcome']is None)==g['stats']['censored'],g['gameid']
  assert bool(any(delta))==g['stats']['changed'],g['gameid']
  c=counts[g['seed']];c['games']+=1;c['nodes']+=g['nodes'];c['targets']+=targets;c['observed']+=len(obs);c['terms']+=terms;c['actual']+=g['outcome']is not None;c['unknown']+=g['outcome']is None
  observed_total+=len(obs);term_total+=terms;terminal_targets+=targets
 try:next(qf);raise AssertionError('orphan query records')
 except StopIteration:pass
 assert query_total==r['counts']['queries'] and node_total==r['nodes'] and observed_total==r['counts']['observed'] and term_total==r['counts']['terms']
 base=json.loads((ROOT/'results/dev_aux/task2568/credit-sources.json').read_text())
 base_targets=sum(base['by_arm'][f"({s}, 'TD')"]['target_source_counts']['terminal_PV_search']for s in p['seeds'])
 audit={'status':'PASS_INDEPENDENT_UPDATE_HISTORY_AND_COST_REPLAY','candidate_status':r['status'],'nodes':node_total,'queries':query_total,'games':len(games),'actual_terminal':r['counts']['actual_terminal'],'unknown':r['counts']['unknown'],'observed_searches':observed_total,'td_residual_terms':term_total,'candidate_terminal_target_residuals_pooled':terminal_targets,'candidate_terminal_target_residuals_by_seed':{str(s):counts[s]['targets']for s in p['seeds']},'baseline_terminal_target_residuals_pooled':base_targets,'per_seed':{str(s):counts[s]for s in p['seeds']},'training_wall_seconds':r['seconds'],'cap_seconds':p['cap_seconds'],'source_pins_pass':True,'scope':'Finite training trace/cost/history audit only; no strength or transfer claim.'}
 (T/'training-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
