import sys,json,math,collections,time
from pathlib import Path
from fractions import Fraction
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task390';O.mkdir(exist_ok=True);t0=time.monotonic();axes=[2,3,4,5,6,7,9,10,11,12,13,14];MAP={'P':1,'L':2,'N':3,'S':4,'B':5,'R':6,'G':7,'K':8}
def features(sfen):
 board,turn,hand,num=sfen.split();v=[0]*16;types=[0]*16;prom=False
 for x in board:
  if x=='+':prom=True;continue
  if x=='/' or x.isdigit():continue
  pt=MAP[x.upper()]+(8 if prom else 0);prom=False;v[pt]+=1 if x.isupper() else -1;types[pt]+=1
 count=''
 for x in hand:
  if x=='-':continue
  if x.isdigit():count+=x;continue
  n=int(count or '1');count='';pt=MAP[x.upper()];v[pt]+=n if x.isupper() else -n;types[pt]+=n
 return v,types
def main():
 # Fixed zero-update training baseline only, no label-dependent cell/model choice.
 games=[]
 for line in (R/'results/dev_aux/task387/games.jsonl').open(encoding='utf-8'):
  g=json.loads(line)
  if g['weights']==[0]+[90]*7+[0]+[90]*6+[0]:games.append(g)
  if len(games)==8:break
 assert len(games)==8 and len({(g['root']['seed'],g['color']) for g in games})==8
 played=[];pv=[];playedpresence=[0]*16;pvpresence=[0]*16;queries=0;seenstates=set();terminal=0
 for g in games:
  terminal+=g['termination']['kind']!='cap24'
  for s in [g['root']['expected_sfen']]+[a['after_sfen'] for a in g['actions']]:
   v,types=features(s);played.append([v[a] for a in axes]);playedpresence=[x+int(t>0) for x,t in zip(playedpresence,types)];seenstates.add(s)
  for q in g['queries']:
   queries+=1
   # PV states are recorded search returns, not entire searched frontier.
   import cshogi as C
   b=C.Board(q['initial_sfen'])
   for u in q['history']:b.push_usi(u)
   for text in q['lines']:
    if ' pv ' not in text:continue
    p=b.copy()
    for u in text.split(' pv ',1)[1].split():
     m=p.move_from_usi(u);assert p.is_legal(m);p.push(m);v,types=features(p.sfen());pv.append([v[a] for a in axes]);pvpresence=[x+int(t>0) for x,t in zip(pvpresence,types)]
 certificate=dict(quantity_parity='38nonkingactors, ownerdiff even; capture transfers2, drop/promotion0',singlecell_quantity_difference=Fraction(2,19).__str__(),mean_eightcells=Fraction(1,76).__str__(),normalized_mean=Fraction(1,2432).__str__(),spsa_log_step=Fraction(1,12160).__str__(),price90_continuous_movement=90*math.expm1(1/12160),round90_up_threshold=math.log(90.5/90),same_direction_minimalsteps_to_round90=math.ceil(math.log(90.5/90)*12160),singlecell_nonterminal_zero_to_win_log_step=.025,maximum_all_nonterminal_logstep=.025,maximum_uncapped_anygoal_logstep=.4,axis_cap=.25,normalization='rankingunchanged but rawgoalgradient effectivegain .1/32; no scale-invariantoptimizerclaim',scope='algebra not stochasticnoise/calibration/needtoextend24iterations; frozen schedule retained')
 result=dict(baseline_games=8,query_calls=queries,true_terminal_games=terminal,axes=axes,played_states=len(played),unique_played_sfen=len(seenstates),PV_states=len(pv),played_feature_rank=int(np.linalg.matrix_rank(np.asarray(played))),PV_feature_rank=int(np.linalg.matrix_rank(np.asarray(pv))) if pv else 0,played_presence={str(a):playedpresence[a] for a in axes},PV_presence={str(a):pvpresence[a] for a in axes},certificate=certificate,seconds=time.monotonic()-t0,new_go=0,scope='fixed8zeroupdate actualtrainingpaths/PVonly; no allsearchedstatecoverage or formal parameteridentifiability claim, no gainchange/humanlabels')
 (O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
