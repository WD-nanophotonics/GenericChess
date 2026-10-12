import sys,json,time,hashlib,math
from pathlib import Path
from fractions import Fraction
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G;sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V;A.EXE=R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe';A.validate_search=V.query
O=R/'results/dev_aux/task406';O.mkdir(exist_ok=True);declpath=R/'results/dev_aux/task405/declaration.json';d=json.loads(declpath.read_text(encoding='utf-8'));assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];t0=time.monotonic();cache={};newgames=0;newgo=0;hits=0;logical=0;rounds=[];updates=[];ends=[];diagnostics=[];acks=[]
axes=d['axes'];train=[f for f in d['roots'] if f['phase']=='train'];dev=[f for f in d['roots'] if f['phase']=='development']
def key(w,f,c):return json.dumps([w,f['initial_sfen'],f['history'],c,d['nodes'],d['cap'],d['goal'],d['executable_sha256']],separators=(',',':'))
def progress():
 (O/'progress.json').write_text(json.dumps(dict(seconds=time.monotonic()-t0,new_games=newgames,new_go=newgo,cache_hits=hits,logical_games=logical,rounds=rounds,updates=updates,endpoints=ends,diagnostics=diagnostics),indent=2),encoding='utf-8')
def batch(w,roots):
 global newgames,newgo,hits,logical
 missing=any(key(w,f,c) not in cache for f in roots for c in (0,1));ec=A.Engine(w,qj) if missing else None;rows=[];refs=[]
 if ec:acks.append(dict(weights=w,prices=ec.prices))
 try:
  for f in roots:
   for c in (0,1):
    logical+=1;k=key(w,f,c)
    if k in cache:g,ref=cache[k];hits+=1
    else:
     g=G.game(ec,eu,w,f,c,gj,cap=d['cap'],nodes=d['nodes'],deadline=t0+1800);newgames+=1;newgo+=len(g['queries']);ref=dict(file='results/dev_aux/task406/games.jsonl',line=newgames);cache[k]=(g,ref)
    rows.append(g);refs.append(ref)
 finally:
  if ec:ec.close()
 mean=sum((Fraction(g['goal']) for g in rows),Fraction())/len(rows)
 return dict(weights=list(w),mean_goal=str(mean),mean_quantity=str(sum(Fraction(g['raw_quantity']) for g in rows)/len(rows)),goals=[g['goal'] for g in rows],sources=refs,true_wins=sum(g['termination']['winner']==g['color'] for g in rows),true_losses=sum(g['termination']['winner'] is not None and g['termination']['winner']!=g['color'] for g in rows))
def prices(logs,base):
 w=list(base)
 for a,z in zip(axes,logs):w[a]=max(32,min(4096,math.floor(math.exp(max(math.log(32),min(math.log(4096),z)))+.5)))
 return w
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 eu=A.Engine(d['fixed_opponent'],qj)
 try:
  for p in d['initial_profiles']:
   w=list(p['weights']);initial=list(w)
   for rd in range(2):
    proposals=[('base',list(w))]
    for a in axes:
     for mode in ['half','double']:
      v=list(w);v[a]=max(32,min(4096,(v[a]+1)//2 if mode=='half' else v[a]*2));proposals.append((str(a)+'-'+mode,v))
    cs=[]
    for label,v in proposals:
     row=batch(v,train);row['label']=label;cs.append(row);print('coordinate',p['name'],rd,label,newgames,round(time.monotonic()-t0),flush=True);progress()
    scores=[Fraction(x['mean_goal']) for x in cs];best=max(range(len(cs)),key=lambda i:scores[i]);rounds.append(dict(family=p['name'],round=rd,start_weights=w,candidates=cs,selected_index=best,strict_gain=str(scores[best]-scores[0])))
    if scores[best]<=scores[0]:break
    w=list(cs[best]['weights'])
   ends.append(dict(method='coordinate',family=p['name'],initial=initial,endpoint=list(w),rounds=rd+1));progress()
  for p in d['initial_profiles']:
   initial=list(p['weights']);w=list(initial);base=batch(w,train)
   for iteration,direction in enumerate(d['directions'][p['name']]):
    start=list(w);plus=list(w);minus=list(w)
    for axis,sign in zip(axes,direction):
     plus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(.25*sign)+.5)))
     minus[axis]=max(32,min(4096,math.floor(w[axis]*math.exp(-.25*sign)+.5)))
    rp=batch(plus,train);rm=batch(minus,train);candidates=[base,rp,rm];scores=[Fraction(row['mean_goal']) for row in candidates];best=max(range(3),key=lambda i:scores[i]);gain=scores[best]-scores[0]
    if gain>0:w=list(candidates[best]['weights']);base=candidates[best]
    else:best=0
    updates.append(dict(family=p['name'],iteration=iteration,direction=direction,start_weights=start,candidates=candidates,selected_index=best,accepted_strict_gain=str(gain),after_weights=list(w),changed_integer_axes=sum(start[axis]!=w[axis] for axis in axes),proposal_changed_axes=[sum(start[axis]!=candidate['weights'][axis] for axis in axes) for candidate in candidates],paired_plus_minus_goal_difference=[str(Fraction(a)-Fraction(b)) for a,b in zip(rp['goals'],rm['goals'])]));progress();print('joint',p['name'],iteration,str(gain),newgames,round(time.monotonic()-t0),flush=True)
   ends.append(dict(method='joint',family=p['name'],initial=initial,endpoint=list(w),iterations=24));progress()
  endpoint_record=dict(frozen_before_development=True,declaration_sha256=hashlib.sha256(declpath.read_bytes()).hexdigest(),endpoints=ends,rounds=rounds,updates=updates,fit_new_games=newgames,fit_new_go=newgo,fit_cache_hits=hits,fit_logical_games=logical,fit_seconds=time.monotonic()-t0)
  (O/'endpoints.json').write_text(json.dumps(endpoint_record,indent=2),encoding='utf-8')
  profiles=[]
  for e in ends:
   for stage,w in [('initial',e['initial']),('endpoint',e['endpoint'])]:
    if not any(x['weights']==w for x in profiles):profiles.append(dict(weights=w,names=[]))
    next(x for x in profiles if x['weights']==w)['names'].append(e['method']+'-'+e['family']+'-'+stage)
  for phase,roots in [('train_endpoint_diagnostic',train),('development',dev)]:
   for p in profiles:
    row=batch(p['weights'],roots);row.update(phase=phase,names=p['names']);diagnostics.append(row);progress();print(phase,p['names'],row['mean_goal'],flush=True)
 finally:eu.close()
(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8');result=dict(seconds=time.monotonic()-t0,new_games=newgames,new_go=newgo,logical_games=logical,cache_hits=hits,diagnostics=diagnostics,endpoints=ends,status='completed');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('COMPLETED',json.dumps({k:v for k,v in result.items() if k not in ['diagnostics','endpoints']}),flush=True)