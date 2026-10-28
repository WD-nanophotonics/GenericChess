"""Finite observed-edge interval deduction for NEW published PVS histories."""
import json,argparse
from collections import Counter,defaultdict
from pathlib import Path
from scripts.research_record import write_record
from scripts.audit_published_leaper_exposure import _experienced_regret_mean_bounds

def fold(nodes,edges):
 outgoing=defaultdict(dict)
 for e in edges:
  assert e['parent'] in nodes and e['child'] in nodes
  assert nodes[e['child']]['ply']==nodes[e['parent']]['ply']+1
  old=outgoing[e['parent']].setdefault(e['action'],e['child']);assert old==e['child']
 bounds={}
 for k,n in sorted(nodes.items(),key=lambda kv:kv[1]['ply'],reverse=True):
  child=outgoing[k];assert len(child)<=n['legal']
  t=n['terminal']
  if t['status']!='ongoing':
   assert n['legal']==0 and not child and t['status']!='no_contest'
   v=0 if t['winner'] is None else 1 if t['winner']==0 else -1;bounds[k]=[v,v];continue
  assert n['legal']>0
  vals=[bounds[x] for x in child.values()]
  if len(child)<n['legal']:vals.append([-1,1])
  op=max if n['actor']==0 else min
  bounds[k]=[op(v[i] for v in vals) for i in (0,1)]
 return bounds,outgoing

def analyze(folder):
 games=[json.loads(p.read_bytes()) for p in sorted(Path(folder).glob('game-*.json'))];assert len(games)==24
 nodes={};edges=[]
 for g in games:
  for k,n in g['nodes'].items():assert nodes.setdefault(k,n)==n
  edges.extend(g['edges'])
 bounds,out=fold(nodes,edges)
 groups=defaultdict(list);counts=Counter();per_policy=defaultdict(Counter);all_q=[]
 for g in games:
  groups[g['case']].append(g)
  for q in g['queries']:
   p=per_policy[str(q['on'])];p['moves']+=1;p['nonforced']+=not q['forced'];p['forced']+=q['forced'];p['empty_PV']+=q['pv_length']==0
   parent=q['before_sha256'];token=json.dumps(q['action'],sort_keys=True,separators=(',',':'));child=out[parent][token];pb=bounds[parent];cb=bounds[child]
   # Actor regret V(parent)-V(child), reversed at seat1.
   rb=[max(0,pb[0]-cb[1]),pb[1]-cb[0]] if q['actor']==0 else [max(0,cb[0]-pb[1]),cb[1]-pb[0]]
   if q['forced']:rb=[0,0]
   assert rb[0]<=rb[1]
   all_q.append(dict(game=g['game_id'],case=g['case'],qid=q['qid'],on=q['on'],ply=q['ply'],parent=parent,child=child,parent_bounds=pb,child_bounds=cb,regret_bounds=rb,forced=q['forced']))
   counts['exact_parent_exposures']+=pb[0]==pb[1];counts['exact_selected_child_exposures']+=cb[0]==cb[1];counts['strict_error_exposures']+=rb[0]>0
 pairs=[]
 for case,gs in sorted(groups.items()):
  assert len(gs)==2 and {g['on_seat'] for g in gs}=={0,1};a,b=sorted(gs,key=lambda x:x['on_seat'])
  # root before hash includes the whole record/fingerprint, not board only.
  assert a['queries'][0]['before_sha256']==b['queries'][0]['before_sha256']
  common=0;div=None
  for qa,qb in zip(a['queries'],b['queries']):
   assert qa['before_sha256']==qb['before_sha256']
   if qa['action']!=qb['action']:div=common;break
   common+=1
  same=div is None
  if same:assert len(a['queries'])==len(b['queries']) and a['terminal']==b['terminal']
  value=lambda g:0 if g['terminal']['winner'] is None else 1 if g['terminal']['winner']==0 else -1
  margin=value(a)-value(b)
  candidates={str(on):[q['qid'] for g in gs for q in g['queries'][common:] if q['on']==on and not q['forced']] for on in (False,True)}
  pairs.append(dict(case=case,family=a['family'],on0_game=a['game_id'],on1_game=b['game_id'],zA=value(a),zB=value(b),OFF_minus_ON_total_WDL_regret=margin,common_prefix=common,first_divergence=div,same_complete_path=same,shared_query_contexts=common if same else common+1,nonforced_suffix_candidates=candidates,root_bounds=bounds[a['queries'][0]['before_sha256']],first_divergence_bounds=None if same else bounds[a['queries'][common]['before_sha256']]))
 off,on=per_policy['False'],per_policy['True'];margin=sum(p['OFF_minus_ON_total_WDL_regret'] for p in pairs)
 mean=_experienced_regret_mean_bounds(off['moves'],on['moves'],off['nonforced'],on['nonforced'],margin)
 hist=Counter(str(b) for b in bounds.values());nq=Counter(str(q['regret_bounds']) for q in all_q)
 return dict(source='c42f006664e028cc9792a5bea40c711005ef23c9',games=24,transitions=sum(len(g['queries']) for g in games),game_PV_plies=sum(g['pv_plies'] for g in games),distinct_nodes=len(nodes),distinct_edges=sum(len(x) for x in out.values()),bounds_histogram=dict(hist),query_counts=dict(counts),query_regret_bound_histogram=dict(nq),policy_counts=dict(per_policy),pairs=pairs,experienced_mean=mean,total_WDL_regret_contrast=margin,queries=all_q,nodes=nodes,edges=edges,bounds=bounds,scope='Only Core-checked saved edges and complete legal frontier COUNTS. Unobserved children remain[-1,1]; finite deduction,not full-game solve. New claims require independent literal certificate checker. No Player/search/new games.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=analyze(a.folder);write_record(a.output,r);print(json.dumps({k:v for k,v in r.items() if k not in ('nodes','edges','queries','bounds','pairs')},indent=2));print(json.dumps([{k:v for k,v in p.items() if k!='nonforced_suffix_candidates'} for p in r['pairs']],indent=2))
