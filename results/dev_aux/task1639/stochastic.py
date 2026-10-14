from pathlib import Path
import json,time,collections,importlib.util,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task1646';O.mkdir(exist_ok=False);start=time.monotonic();plan=json.loads((R/'results/dev_aux/task1645/plan.json').read_bytes());deadline=start+900
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
def scc(adj):
 n=len(adj);seen=bytearray(n);order=[]
 for root in range(n):
  if seen[root]:continue
  seen[root]=1;stack=[(root,iter(adj[root] or []))]
  while stack:
   node,it=stack[-1];j=next(it,None)
   if j is None:order.append(node);stack.pop()
   elif not seen[j]:seen[j]=1;stack.append((j,iter(adj[j] or [])))
 rev=[[] for _ in range(n)]
 for i,ll in enumerate(adj):
  for j in ll or []:rev[j].append(i)
 comp=[-1]*n;groups=[]
 for root in reversed(order):
  if comp[root]!=-1:continue
  cid=len(groups);group=[];comp[root]=cid;stack=[root]
  while stack:
   i=stack.pop();group.append(i)
   for j in rev[i]:
    if comp[j]==-1:comp[j]=cid;stack.append(j)
  groups.append(group)
 return comp,groups
out=[]
for price in plan['profiles']:
 P.stop();prefix=f'R{price[0]}_N{price[1]}_B{price[2]}';g=json.loads((R/f'results/dev_aux/task1631/{prefix}_graph.json').read_bytes());n=len(g['keys']);assert n<=150000
 comp,groups=scc(g['adj']);closed={i for cid,group in enumerate(groups) if all(g['adj'][i] and all(comp[j]==cid for j in g['adj'][i]) for i in group) for i in group}
 (O/(prefix+'_closed.json')).write_text(json.dumps({'closed_state_ids':sorted(closed),'scc_components':len(groups)},indent=2))
 base=np.zeros((n,10));trans=[];children=[];width=[];physical_boundary=0
 for i,(s,c) in enumerate(g['keys']):
  basis=g['basis'][i];ll=g['adj'][i]
  if i in closed:base[i,2]=base[i,7]=1;continue
  if ll:trans.append(i);children.extend(ll);width.append(len(ll));base[i,4]=base[i,9]=1;continue
  if basis=='UNKNOWN_FRONTIER':base[i,3]=base[i,8]=1;continue
  pay=g['payoff'][i];base[i,0 if pay==1 else 1 if pay==-1 else 2]=1
  s=tuple(s);legal=T.moves(s)
  if not legal:
   p=((-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0);assert p==pay;base[i,5 if p==1 else 6 if p==-1 else 7]=1;physical_boundary+=1
  else:assert basis=='COMMON_PERFECT_4_ORACLE';base[i,8]=1
 trans=np.array(trans,dtype=np.int64);child=np.array(children,dtype=np.int64);width=np.array(width,dtype=np.float64);starts=np.r_[0,np.cumsum(width.astype(np.int64))[:-1]];V=base.copy();records=[]
 (O/(prefix+'_base.json')).write_text(json.dumps(base.tolist(),separators=(',',':')))
 for h in range(plan['max_iterations']+1):
  if h in plan['H']:
   roots=[{'family':f,'sid':i,'probabilities':V[i].tolist()} for f,i in g['roots']];records.append({'H':h,'roots':roots});print(prefix,h,'avg',np.mean(V[[i for f,i in g['roots']]],axis=0).tolist(),flush=True)
  if h==plan['max_iterations']:break
  P.stop();assert time.monotonic()<deadline
  V[trans]=np.add.reduceat(V[child],starts,axis=0)/width[:,None]
  assert np.all(V>=-1e-12) and np.max(np.abs(V[:,:5].sum(axis=1)-1))<1e-9 and np.max(np.abs(V[:,5:].sum(axis=1)-1))<1e-9
 (O/(prefix+'_records.json')).write_text(json.dumps(records,indent=2));(O/(prefix+'_final.npy')).write_bytes(b'')
 np.save(O/(prefix+'_final.npy'),V)
 last=records[-1];summ=[]
 for scope,offset in [('COMPOSITE_PERFECT4',0),('PHYSICAL_NONTERMINAL4_UNKNOWN',5)]:
  a=np.array([x['probabilities'][offset:offset+5] for x in last['roots']]);w,l,d,u,s=a.mean(axis=0);summ.append({'scope':scope,'W':w,'L':l,'D':d,'UNKNOWN':u,'S':s,'net_lower':max(-1,float(w-l-u-s)-1e-8),'net_upper':min(1,float(w-l+u+s)+1e-8)})
 out.append({'price':price,'states':n,'closed_states':len(closed),'physical_terminal_boundaries':physical_boundary,'last_H':last['H'],'summary':summ})
result={'status':'COMPLETED_APPROXIMATE_PROBABILITY_BOUNDS_PENDING_INDEPENDENT_AUDIT','profiles':out,'seconds':time.monotonic()-start,'actual_go':0,'numerical_reserve':1e-8,'scope':'Both scopes fixedsame5policy/uniformalllegalrandom; compositeabsorbsperfect4WDL, physicalabsorbsnonterminal4UNKNOWN. Nooracletoactualpolicybound shortcut, no capextension.'};(O/'result.json').write_text(json.dumps(result,indent=2));print(result)

