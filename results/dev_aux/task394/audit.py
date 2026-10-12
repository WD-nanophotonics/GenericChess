import json,sys,time,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task394';O.mkdir(exist_ok=True);t0=time.monotonic();unit=[0]+[90]*7+[0]+[90]*6+[0];gs=[]
for line,text in enumerate((R/'results/dev_aux/task387/games.jsonl').open(encoding='utf-8'),1):
 g=json.loads(text)
 if g['weights']==unit:gs.append((line,g))
 if len(gs)==8:break
assert len(gs)==8;rows=[]
def fields(q):return {k:q[k] for k in ['initial_sfen','history','weights','nodes_limit','state','command','lines','bestmove']}
for seed in sorted({g['root']['seed'] for _,g in gs}):
 pair=[(line,g) for line,g in gs if g['root']['seed']==seed];a=next((line,g) for line,g in pair if g['color']==0);b=next((line,g) for line,g in pair if g['color']==1);assert a[1]['root']==b[1]['root'];assert a[1]['actions']==b[1]['actions'];assert a[1]['termination']==b[1]['termination'] and a[1]['final_sfen']==b[1]['final_sfen'];assert a[1]['raw_quantity']==-b[1]['raw_quantity'] and Fraction(a[1]['goal'])==-Fraction(b[1]['goal']);qa=[fields(q) for q in a[1]['queries']];qb=[fields(q) for q in b[1]['queries']]
 # Engine info embeds measuredtime/NPS, not deterministic semantic output. Retain counters/score/PV without comparingtime.
 def semantic(q):
  r={k:v for k,v in q.items() if k!='lines'};r['lines']=[l for l in q['lines'] if l.startswith('bestmove ')];return r
 assert [semantic(q) for q in qa]==[semantic(q) for q in qb]
 rows.append(dict(seed=seed,lines=[a[0],b[0]],plies=len(a[1]['actions']),goals=[a[1]['goal'],b[1]['goal']],termination=a[1]['termination'],same_actual_action_history=True,same_query_position_prices_state_bestmove=True,scope='measuredinfo time/NPS notclaimedidentical, no machineexclusivity'))
result=dict(status='PASS',rootpairs=4,games=8,queries=sum(len(g['queries']) for _,g in gs),mean_goal=str(sum(Fraction(g['goal']) for _,g in gs)/8),rows=rows,seconds=time.monotonic()-t0,new_go=0,scope='fixedzeroupdatecontrol actualcolourantisymmetry/fullhistory; rules±32 not noise purelybecausemagnitude. Nomodelreselection orabsenceofallstochasticity proof');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))