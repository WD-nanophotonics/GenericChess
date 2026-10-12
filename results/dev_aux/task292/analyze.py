import json,time,hashlib
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task292';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task269/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task269/result.json').read_bytes());E=json.loads((R/'results/dev_aux/task269/endpoints.json').read_bytes());start=time.monotonic();train=[z for z in X['calls'] if z['phase']=='train'];assert len(train)==144
rows=[]
for H in (16,32,48):
 for keep in ((0,1),(0,),(1,)):
  means={};signed={};speed={};outcomes={}
  for name in D['profiles']:
   rr=[z for z in train if z['name']==name and z['root'] in keep];assert len(rr)==2*len(keep)
   signs=[];fit=[];tags=[]
   for z in rr:
    f=D['train_roots'][z['root']];b=chess.Board(f['initial_fen'])
    for text in f['history']+z['actions'][:H]:b.push_uci(text)
    oo=b.outcome(claim_draw=False);sgn=0 if oo is None or oo.winner is None else 1 if oo.winner==z['color'] else -1;tag='unknown' if oo is None else 'draw' if oo.winner is None else 'win' if sgn==1 else 'loss';goal=sgn if oo is not None and oo.termination.name=='CHECKMATE' else 0;fitness=Fraction(goal)*(1+Fraction(H-min(H,len(z['actions'])),100*H));signs.append(Fraction(goal));fit.append(fitness);tags.append(tag)
   means[name]=sum(fit)/len(fit);signed[name]=sum(signs)/len(signs);speed[name]=means[name]-signed[name];outcomes[name]={k:tags.count(k) for k in ('win','loss','draw','unknown')}
  for initial,family in D['families'].items():
   best=max(means[name] for name in family);ties=[name for name in family if means[name]==best];chosen=ties[0];signbest=max(signed[name] for name in family);signties=[name for name in family if signed[name]==signbest];selected=E['chosen'][initial]
   rows.append(dict(H=H,keep_training_roots=keep,initial=initial,all9fitness={n:str(means[n]) for n in family},all9signedgoal={n:str(signed[n]) for n in family},all9speedcomponent={n:str(speed[n]) for n in family},all9outcomes={n:outcomes[n] for n in family},selected=chosen,ties=ties,without_speed_selected=signties[0],without_speed_ties=signties,original_H48_selected=selected,original_endpoint_still_selected=selected==chosen,original_endpoint_in_ties=selected in ties))
for row in rows:
 if row['H']==48 and row['keep_training_roots']==(0,1):assert row['selected']==row['original_H48_selected']
out=dict(task_id='292',complete=True,new_games=0,new_model_adopted=False,training_games_reused=144,all_cells=rows,seconds=time.monotonic()-start,source_hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'results/dev_aux/task269/declaration.json',R/'results/dev_aux/task269/result.json',R/'results/dev_aux/task269/endpoints.json']},scope='PosthocH/root/speed diagnostics: mainH48 and originalfitnessfrozen. H16/32 speeduses1percentofH solelydiagnostic, not selection/adoption; unknownnotdraw. RemovingoneTRAINroot leaves2colourgames, cannot establishpopulationstatisticalconfidence.')
(O/'sensitivity.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
for z in rows:print(z['H'],z['keep_training_roots'],z['initial'],z['selected'],len(z['ties']),'sign',z['without_speed_selected'])