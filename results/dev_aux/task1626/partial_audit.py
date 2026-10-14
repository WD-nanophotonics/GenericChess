from pathlib import Path
import json,collections,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1636';O.mkdir(exist_ok=False);P=R/'results/dev_aux/task1631'
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
ts=list(map(tuple,json.loads((R/'results/dev_aux/task1627/states.json').read_bytes())));ix={s:i for i,s in enumerate(ts)};tv=json.loads((R/'results/dev_aux/task1627/values.json').read_bytes())['value'];counts=collections.Counter();profiles=[]
for f in sorted(P.glob('*_graph.json')):
 prefix=f.name.removesuffix('_graph.json');g=json.loads(f.read_bytes());z=json.loads((P/(prefix+'_bounds.json')).read_bytes());summary=json.loads((P/(prefix+'_result.json')).read_bytes());keys=[(tuple(s),c) for s,c in g['keys']];index={k:i for i,k in enumerate(keys)};cache={}
 for line in (P/(prefix+'_choices.jsonl')).open():
  x=json.loads(line);s=tuple(x['state']);assert T.fen(s)==x['position'];assert dict(T.moves(s))[x['move']]==tuple(x['child']);cache[s,x['color']]=tuple(x['child']);counts['queries']+=1
  for info in x['uci_info']:
   a=info.split()
   if 'pv' in a:
    q=s
    for u in a[a.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
 for i,(s,c) in enumerate(keys):
  counts['states']+=1;basis=g['basis'][i];adj=g['adj'][i];ll=T.moves(s);pay=g['payoff'][i]
  if basis=='COMMON_PERFECT_4_ORACLE':assert sum(x!=16 for x in s[:8])<=4 and adj is None;assert pay==tv[ix[s]]*(1 if s[8]==c else -1)
  elif basis=='UNKNOWN_FRONTIER':assert adj is None and pay is None and sum(x!=16 for x in s[:8])==5
  elif basis=='TERMINAL':assert not ll and adj==[];assert pay==((-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0)
  elif basis=='ACTUAL_OWN':assert s[8]==c and len(ll)>1 and adj==[index[cache[s,c],c]]
  elif basis=='SOLE_OWN':assert s[8]==c and len(ll)==1 and adj==[index[ll[0][1],c]]
  else:assert basis=='ALL_OPPONENT' and s[8]!=c and adj==[index[t,c] for u,t in ll]
  assert z['lower'][i]<=z['upper'][i]
  for name in ['lower','upper']:
   v=z[name];rank=z[name+'_rank']
   if adj:
    ch=[v[j] for j in adj];assert v[i]==(max(ch) if s[8]==c else min(ch))
    if v[i]:
     exists=(s[8]==c and v[i]==1) or (s[8]!=c and v[i]==-1)
     assert any(v[j]==v[i] and rank[j]<rank[i] for j in adj) if exists else all(v[j]==v[i] and rank[j]<rank[i] for j in adj)
    else:assert 0 in ch and (all(x<=0 for x in ch) if s[8]==c else all(x>=0 for x in ch))
   else:assert v[i]==((-1 if name=='lower' else 1) if basis=='UNKNOWN_FRONTIER' else pay) and rank[i]==0
 roots=[[fam,z['lower'][i],z['upper'][i]] for fam,i in g['roots']];assert roots==summary['root_bounds'];assert summary['mean_lower']==sum(a for f,a,b in roots)/32 and summary['mean_upper']==sum(b for f,a,b in roots)/32;profiles.append(summary)
assert counts['queries']==60000 and len(profiles)==2
a,b=profiles;gainlo=sum(y[1]-x[2] for x,y in zip(a['root_bounds'],b['root_bounds']))/32;gainhi=sum(y[2]-x[1] for x,y in zip(a['root_bounds'],b['root_bounds']))/32
out={'status':'PASS_BOTH_PARTIAL_CONTROL_BOUNDARY_BELLMAN_RANK_UNKNOWN_BOUNDS','counts':dict(counts),'transfer_gain_bounds':[gainlo,gainhi],'scope':'60000coldqueries preserved, no capextension; unknown is +/-1 notDraw, intervals overlap, no transfer gain established.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

