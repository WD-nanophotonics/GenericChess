import sys,json,re,time,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task397';O.mkdir(exist_ok=True);t0=time.monotonic();old=[json.loads(x) for x in (R/'results/dev_aux/task369/games.jsonl').read_text(encoding='utf-8').splitlines()];new=[json.loads(x) for x in (R/'results/dev_aux/task396/games.jsonl').read_text(encoding='utf-8').splitlines()];assert len(old)==len(new)==16;calls=0
for a,b in zip(old,new):
 for key in ['weights','root','color','actions','termination','final_sfen','raw_quantity','goal']:assert a[key]==b[key],key
 assert len(a['queries'])==len(b['queries'])
 for x,y in zip(a['queries'],b['queries']):
  for key in ['initial_sfen','history','weights','nodes_limit','cold_isready','state','command','bestmove','player','ply']:assert x[key]==y[key],(key,x[key],y[key])
  def semantic(lines):return [' '.join(re.sub(r'\b(?:time|nps) \d+','',line).split()) for line in lines]
  assert semantic(x['lines'])==semantic(y['lines']),(x['lines'],y['lines']);calls+=1
checked=V.audit(396);r=json.loads((R/'results/dev_aux/task396/result.json').read_text(encoding='utf-8'));gamewall=r['gamewall_sum'];components=r['component_sums'];ranked=sorted([(k,v) for k,v in components.items() if k!='search_outer']+[('controller_validation_and_gamejournal_residual',gamewall-components['search_outer'])],key=lambda kv:-kv[1]);result=dict(status='PASS',same_games=16,same_go=calls,independent_audit=checked,component_gamewall_fractions={k:v/gamewall for k,v in ranked},dominant=ranked[0][0],seconds=time.monotonic()-t0,scope='samecompleteactions/state/score/bound/depth/nodes/PV/hashfull, onlyelapsedtime/NPS excluded; tracedcostnotnoisefreegeneralperformance');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))