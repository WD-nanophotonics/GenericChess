from pathlib import Path
import json,sys,importlib.util,collections,hashlib
R=Path.cwd();P=R/'results/dev_aux/task1615';O=R/sys.argv[1];O.mkdir(exist_ok=False);phase_filter=sys.argv[2] if len(sys.argv)>2 else None
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1581/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
G=R/'results/dev_aux/task1583';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};oracle=json.loads((G/'values.json').read_bytes())['value'];study=json.loads((R/'results/dev_aux/task1612/study.json').read_bytes());cache={};counts=collections.Counter()
for f in sorted((R/'results/dev_aux/task1587').glob('*_choices.jsonl'))+sorted((R/'results/dev_aux/task1606').glob('*_choices.jsonl'))+sorted(P.glob('*_choices.jsonl')):
 for line in f.open():
  x=json.loads(line);key=(x['R'],x['B'],x['sid']);assert key not in cache;cache[key]=x;s=states[x['sid']];assert dict(T.moves(s))[x['move']]==states[x['child']];assert T.fen(s)==x['position'];counts['queries']+=1
  for line in x['uci_info']:
   ss=line.split()
   if 'pv' in ss:
    q=s
    for u in ss[ss.index('pv')+1:]:q=dict(T.moves(q))[u];counts['PVmoves']+=1
summaries=[]
for f in sorted(P.glob('*_result.json')):
 d=json.loads(f.read_bytes())
 if phase_filter is not None and f.stem.removesuffix('_result')!=phase_filter:continue
 prefix=f.name.removesuffix('_result.json');g=json.loads((P/(prefix+'_graph.json')).read_bytes());z=json.loads((P/(prefix+'_values.json')).read_bytes());keys=[tuple(x) for x in g['keys']];index={x:i for i,x in enumerate(keys)};v=z['value'];rank=z['rank'];assert len(index)==len(keys)
 for i,(sid,c) in enumerate(keys):
  s=states[sid];ll=T.moves(s);basis=g['basis'][i];adj=g['adj'][i];counts['state_proofs']+=1
  if basis=='COMMON_RULE_ORACLE':assert sum(x!=12 for x in s[:8])<=4;assert adj is None and g['payoff'][i]==oracle[sid]*(1 if s[8]==c else -1)
  elif basis=='TERMINAL':assert not ll;assert adj==[] and g['payoff'][i]==((-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0)
  elif basis=='ACTUAL_OWN':assert s[8]==c;assert sum(x!=12 for x in s[4*c:4*c+4])==3;x=cache[d['R'],d['B'],sid];assert adj==[index[x['child'],c]]
  elif basis=='SOLE_OWN':assert s[8]==c and len(ll)==1;assert adj==[index[ix[ll[0][1]],c]]
  else:assert basis=='ALL_OPPONENT' and s[8]!=c;assert adj==[index[ix[t],c] for u,t in ll]
  if adj:
   child=[v[j] for j in adj];assert v[i]==(max(child) if s[8]==c else min(child))
   if v[i]:
    exists=(s[8]==c and v[i]==1) or (s[8]!=c and v[i]==-1)
    assert any(v[j]==v[i] and rank[j]<rank[i] for j in adj) if exists else all(v[j]==v[i] and rank[j]<rank[i] for j in adj)
   else:assert 0 in child and (all(y<=0 for y in child) if s[8]==c else all(y>=0 for y in child))
  else:assert v[i]==g['payoff'][i] and rank[i]==0
  assert v[i]<=oracle[sid]*(1 if s[8]==c else -1)
 expected=[]
 for fam in study['families']:
  if fam['phase']==d['phase']:
   for sid in fam['state_ids']:expected.append([fam['family'],index[sid,states[sid][8]]])
 assert g['roots']==expected;root=[[fam,v[i]] for fam,i in expected];assert d['root_values']==root and d['mean']==sum(x for fam,x in root)/len(root);assert d['WDL']=={str(k):n for k,n in collections.Counter(x for fam,x in root).items()}
 summaries.append({'profile':prefix,'states':len(keys),'mean':d['mean']})
assert summaries, 'EmptyprofileauditcannotPASS'
run=json.loads((P/'result.json').read_bytes());assert run['status']=='COMPLETE' and run['all_owned_engines_closed'] and run['actual_new_go']==sum(sum(1 for _ in f.open()) for f in P.glob('*_choices.jsonl'))
out={'status':'PASS_INDEPENDENT_COMPLETED_PROFILE_CONTROL_BOUNDARY_RANK_PV','counts':dict(counts),'profiles':summaries,'scope':'1615threecompleteprofiles; qualified1587/1606cache and4570newqueries, notextraenginego fromrepeatedaudit. Independentliteral geometry alreadyALLqualified1584; draw safety and decisive ranks candidateframe checked here.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(dict(counts),summaries)
