"""Apply Dot diagnostics to existing pilot; no reselection or new games."""
import json,collections,random,time
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task323';O.mkdir(exist_ok=True);assert not (O/'audit.json').exists();D=json.loads((R/'results/dev_aux/task320/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task320/result.json').read_bytes());start=time.monotonic();blocks=[]
for ri in range(2):
 for color in D['colors']:
  for seed in D['random_seeds']:
   zz=[next(z for z in X['calls'] if (z['name'],z['root'],z['color'],z['seed'])==(name,ri,color,seed)) for name in D['profiles']];blocks.append(dict(root=ri,color=color,seed=seed,profiles={z['name']:dict(fitness=z['fitness'],sign=z['finite_mate_sign'],termination=z['termination'],halfplies=len(z['actions'])) for z in zz}))
loo=[]
for axis,values in [('root',range(2)),('color',D['colors']),('seed',D['random_seeds'])]:
 for omitted in values:
  bb=[b for b in blocks if b[axis]!=omitted];values={name:dict(speed=str(sum(F(b['profiles'][name]['fitness']) for b in bb)/len(bb)),net_sign=str(F(sum(b['profiles'][name]['sign'] for b in bb),len(bb)))) for name in D['profiles']};loo.append(dict(axis=axis,omitted=omitted,means=values,semantic_minus_unit_speed=str(F(values['semantic']['speed'])-F(values['unit']['speed'])),semantic_minus_unit_sign=str(F(values['semantic']['net_sign'])-F(values['unit']['net_sign']))))
div=[]
for block in blocks:
 ri,color,seed=block['root'],block['color'],block['seed'];base=next(z for z in X['calls'] if (z['name'],z['root'],z['color'],z['seed'])==('unit',ri,color,seed))
 for name in ('semantic','s703-base'):
  other=next(z for z in X['calls'] if (z['name'],z['root'],z['color'],z['seed'])==(name,ri,color,seed));first=next((i for i,(a,b) in enumerate(zip(base['actions'],other['actions'])) if a!=b),None);following=[]
  if first is not None:
   for z in (base,other):
    upcoming=next((r for r in z['random_choices'] if r['ply']>first),None);following.append(dict(profile=z['name'],first_different_action=z['actions'][first],first_following_random=upcoming))
  div.append(dict(root=ri,color=color,seed=seed,other=name,first_divergent_ply=first,following=following))
allmean={name:dict(speed=str(sum(F(b['profiles'][name]['fitness']) for b in blocks)/8),net_sign=str(F(sum(b['profiles'][name]['sign'] for b in blocks),8))) for name in D['profiles']};out=dict(complete=True,new_games=0,blocks=blocks,all_means=allmean,delete_groups=loo,divergences=div,delete_groups_speed_reversal_semantic_vs_unit=sum(F(z['semantic_minus_unit_speed'])>0 for z in loo),speed_only_direction='Unit faster overall .53646vssemantic.40625, but net7/8vs8/8; fasterconditionalmate andwinningmore aredifferent. Losseszero; unknownseparate. RandomRNG same seed doesnotfixopponentactions afterdivergence.',seconds=time.monotonic()-start,decision='Conditionalrandommatepilot, NOTgeneralpricelearning signal. Frozen322 specificallytestsactualhalf/double coordinate neighbors and64cells eachprice, stopswhenno strictimprovement; nofuturegenerationgrowth/humantuning. Keep outcome+speeddecomposition/rootdependence. Dot consulted beforefirstmultiroundresults, advice isdesignreviewnotexecutionofnewquerydata.',consult_reply_ts='1791816009.893229');(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('blocks','delete_groups','divergences')},indent=2))