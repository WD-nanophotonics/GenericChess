from pathlib import Path
import json,collections,importlib.util,hashlib,sys
R=Path.cwd();P=R/sys.argv[1];S=R/sys.argv[2];O=R/sys.argv[3];O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1538';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));orig=json.loads((G/'values.json').read_bytes())['value'];rows=[json.loads(x) for x in (G/'edges.jsonl').read_text().splitlines()];edges=[x['moves'] for x in rows];checked=[x['checked'] for x in rows];cache={};count=collections.Counter();sample={}
for tid in [1541]:
 for line in (R/f'results/dev_aux/task{tid}/choices.jsonl').open():
  x=json.loads(line);sample[x['node_budget'],x['leafR'],x['state_id']]=x
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
def stable(lines):
 out=[]
 for line in lines:
  fs=line.split();rr=[];i=0
  while i<len(fs):
   if fs[i] in ['nps','time']:i+=2
   else:rr.append(fs[i]);i+=1
  out.append(' '.join(rr))
 return out
for line in (P/'choices.jsonl').open():
 x=json.loads(line);budget=x.get('node_budget',16);price=x['leafR'];sid=x['state_id'];key=(budget,price);d=cache.setdefault(key,{});assert sid not in d;ll=dict(edges[sid])
 if x['basis']=='ACTUAL_COLD_MATURE_SEARCH':
  assert len(ll)>1 and x['position']=='position fen '+T.fen(states[sid]) and x['command']==f'go nodes {budget}' and x['move'] in ll and x['child_id']==ll[x['move']];count['actual_go']+=1
  for info in x['uci_info']:
   fs=info.split()
   if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0
   if 'pv' in fs:
    z=states[sid]
    for u in fs[fs.index('pv')+1:]:m=dict(T.moves(z));assert u in m;z=m[u];count['PVmoves']+=1
  old=sample.get((budget,price,sid))
  if old:assert old['move']==x['move'] and stable(old['uci_info'])==stable(x['uci_info']);count['sampled_exact_nontime_nps_query_matches']+=1
 elif x['basis']=='SOLE_LEGAL_ACTION':assert len(ll)==1 and (x['move'],x['child_id'])==next(iter(ll.items()));count['forced_no_go']+=1
 elif x['basis']=='ACTUAL_TERMINAL':assert not ll and x['move'] is None and x['child_id'] is None;count['terminal_no_go']+=1
 else:raise AssertionError('unexpected cachebasis')
 d[sid]=x['child_id'];count['policy_rows']+=1
producer=json.loads((P/'result.json').read_bytes());assert producer['status']=='COMPLETE' and count['actual_go']==producer['actual_go']
for (budget,price),policy in cache.items():
 assert len(policy)==len(states)
 for color in [0,1]:
  d=json.loads((S/f'B{budget}_R{price}_C{color}.json').read_bytes());v=d['value'];rank=d['rank'];assert len(v)==len(states)
  for i,s in enumerate(states):
   adj=[policy[i]] if s[6]==color and edges[i] else [j for u,j in edges[i]];cvalue=v[i]*(1 if s[6]==color else -1);child=[v[j]*(1 if states[j][6]==color else -1) for j in adj]
   if not adj:
    expected=( -1 if s[6]==color else 1) if checked[i] else 0;assert cvalue==expected and rank[i]==0
   elif s[6]==color:
    assert len(adj)==1 and cvalue==child[0]
    if cvalue:assert rank[adj[0]]<rank[i]
   else:
    assert cvalue==min(child)
    if cvalue==1:assert all(rank[j]<rank[i] for j in adj)
    elif cvalue==-1:assert any(child[k]==-1 and rank[j]<rank[i] for k,j in enumerate(adj))
   if cvalue==0 and adj:assert (child[0]==0 if s[6]==color else all(y>=0 for y in child) and 0 in child)
   assert cvalue<=orig[i]*(1 if s[6]==color else -1);count['candidate_centric_response_states']+=1
out={'status':'PASS_ALL_CACHE_PV_SAMPLED_REPLAY_AND_INDEPENDENT_CANDIDATE_CENTRIC_FULL_POLICY_WDL','counts':dict(count),'scope':'Independent candidate-centric min at opponent/maxtrivial at fixedown, strictmate ranks and draw-preserving edges; not merely repeating originalside-negamax recurrence. Allactualcache/solelegal/terminalbasis distinguished. ALLliteral geometry plus1024 native qualification; every actualPV checked, no ALLnative claim.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
