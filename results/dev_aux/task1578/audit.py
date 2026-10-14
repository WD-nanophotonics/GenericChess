from pathlib import Path
import json,sys,importlib.util,collections
R=Path.cwd();P=R/sys.argv[1];O=R/sys.argv[2];O.mkdir(exist_ok=False);states=list(map(tuple,json.loads((R/'results/dev_aux/task1532/states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};orig=json.loads((R/'results/dev_aux/task1532/values.json').read_bytes())['value'];oldids=json.loads((R/'results/dev_aux/task1538/original_ids.json').read_bytes());oldix={s:i for i,s in enumerate(oldids)};boundary={(p,c):json.loads((R/f'results/dev_aux/task1555/B64_R{p}_C{c}.json').read_bytes())['value'] for p in [720,1728] for c in [0,1]};sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);cache={};counts=collections.Counter()
for line in (P/'new_choices.jsonl').open():
 x=json.loads(line);s=states[x['state_id']];m=dict(T.moves(s));assert ix[m[x['move']]]==x['child_id'];key=x['leafR'],x['state_id'],x['color'];assert key not in cache;cache[key]=x;counts['actual_queries']+=1
 for line in x['uci_info']:
  ss=line.split()
  if 'pv' in ss:
   q=s
   for u in ss[ss.index('pv')+1:]:mm=dict(T.moves(q));assert u in mm;q=mm[u];counts['PVmoves']+=1
for price in [720,1728]:
 g=json.loads((P/f'graph_R{price}.json').read_bytes());b=json.loads((P/f'bounds_R{price}.json').read_bytes());keys=[tuple(z) for z in g['keys']];index={z:i for i,z in enumerate(keys)};assert len(index)==len(keys)
 for i,(sid,color) in enumerate(keys):
  s=states[sid];ll=T.moves(s);actual=[index[ix[t],color] for u,t in ll] if g['basis'][i]=='ALL_OPPONENT_ACTIONS' else None;adj=g['adj'][i]
  if g['basis'][i]=='SOLVED_4ACTOR_ACTUAL_POLICY':assert g['payoff'][i]==boundary[price,color][oldix[sid]]*(1 if s[6]==color else -1)
  elif g['basis'][i]=='ACTUAL_TERMINAL':assert not ll;assert g['payoff'][i]==((-1 if s[6]==color else 1) if T.attacked(s,s[3*s[6]],1-s[6]) else 0)
  elif g['basis'][i]=='ACTUAL_COLD_OWN_CHOICE':x=cache[price,sid,color];assert s[6]==color and adj==[index[x['child_id'],color]]
  elif g['basis'][i]=='SOLE_OWN_ACTION':assert s[6]==color and len(ll)==1 and adj==[index[ix[ll[0][1]],color]]
  elif g['basis'][i]=='ALL_OPPONENT_ACTIONS':assert s[6]!=color and adj==actual
  else:assert g['basis'][i]=='UNKNOWN_FRONTIER' and adj is None
  for name in ['lower','upper']:
   v=b[name];rank=b[name+'_rank'];cv=v[i]
   if adj:
    child=[v[j] for j in adj];assert cv==(max(child) if s[6]==color else min(child));exists=(s[6]==color and cv==1) or (s[6]!=color and cv==-1)
    if cv:
     assert any(v[j]==cv and rank[j]<rank[i] for j in adj) if exists else all(v[j]==cv and rank[j]<rank[i] for j in adj)
    else:assert 0 in child and (all(y<=0 for y in child) if s[6]==color else all(y>=0 for y in child))
   elif g['basis'][i]=='UNKNOWN_FRONTIER':assert cv==(-1 if name=='lower' else orig[sid]*(1 if s[6]==color else -1)) and rank[i]==0
   else:assert cv==g['payoff'][i] and rank[i]==0
   counts['bound_state_proofs']+=1
  assert b['lower'][i]<=b['upper'][i]
r=json.loads((P/'result.json').read_bytes());assert counts['actual_queries']==r['actual_saved_go'] and r['all_owned_engines_closed'];(O/'result.json').write_text(json.dumps({'status':'PASS_INDEPENDENT_REACHABLE_CONTROL_BOUNDARY_RANK_PV_PROOFS','counts':dict(counts),'scope':'Reconstructalllegalopponent edges/literalownselectedmoves and4actoractualpolicy boundary; loweruppercandidateframe proof, no unknownPASS orphysicalgame claim.'},indent=2));print(dict(counts))
