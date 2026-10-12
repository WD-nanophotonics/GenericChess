from pathlib import Path
from fractions import Fraction
import json,sys,time,hashlib
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task422';O.mkdir(exist_ok=True);t0=time.perf_counter();audit=V.audit(421);a=json.loads((R/'results/dev_aux/task411/result.json').read_text(encoding='utf-8'))['rows'];b=json.loads((R/'results/dev_aux/task421/result.json').read_text(encoding='utf-8'))['rows'];ag=[json.loads(x) for x in (R/'results/dev_aux/task411/games.jsonl').read_text(encoding='utf-8').splitlines()];bg=[json.loads(x) for x in (R/'results/dev_aux/task421/games.jsonl').read_text(encoding='utf-8').splitlines()];rows=[];changed=0;firstmoves=0;termchanges=0
for x,y,g,h in zip(a,b,ag,bg):
 assert (x['weights'],x['root_index'],x['color'])==(y['weights'],y['root_index'],y['color']);same=[z['move'] for z in g['actions']]==[z['move'] for z in h['actions']];changed+=not same;firstmoves+=g['actions'][0]['move']!=h['actions'][0]['move'];termchanges+=g['termination']!=h['termination'];rows.append(dict(names=x['names'],weights=x['weights'],root=x['root_index'],color=x['color'],old_goal=x['goal'],new_goal=y['goal'],gain=str(Fraction(y['goal'])-Fraction(x['goal'])),same_action_trajectory=same,old_termination=x['termination'],new_termination=y['termination']))
groups=[]
for w in {tuple(x['weights']) for x in rows}:
 rs=[x for x in rows if tuple(x['weights'])==w];groups.append(dict(weights=list(w),names=rs[0]['names'],mean_delta=str(sum(Fraction(x['gain']) for x in rs)/8),paired_deltas=[x['gain'] for x in rs]))
out=dict(status='PASS',audit=audit,changed_action_trajectories=changed,changed_first_moves=firstmoves,changed_terminations=termchanges,groups=groups,rows=rows,seconds=time.perf_counter()-t0,scope='exposed411same24ply control; newcandidateSEEonly, oldunitopponent; actualchoice changes not gains by themselves, no fitted/default/optimaldefence claim');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='rows'})
