from pathlib import Path
from fractions import Fraction as F
import json,chess,collections
R=Path.cwd();O=R/'results/dev_aux/task1221';O.mkdir(exist_ok=False)
first=[json.loads(s) for s in (R/'results/dev_aux/task1206/games.jsonl').read_text().splitlines()]
full=[json.loads(s) for s in (R/'results/dev_aux/task1170/games.jsonl').read_text().splitlines()]
fm={(g['profile'],g['root']['seed'],g['opponent']):g for g in first};old={(g['arm'],g['price'],g['root']['seed'],g['color'],g['opponent']):g for g in full};y=lambda g:F((g['label']=='W')-(g['label']=='L'))
out=[]
for profile,arm in [('J_first','J'),('L_first','L')]:
 for opp in ['ALL','unit_search','uniform_random']:
  z=[]
  for g in first:
   if g['profile']!='baseline' or (opp!='ALL' and g['opponent']!=opp):continue
   n=fm[(profile,g['root']['seed'],g['opponent'])];whole=old[(arm,1728,g['root']['seed'],g['color'],g['opponent'])]
   z.append(dict(seed=g['root']['seed'],opponent=g['opponent'],first_action_same=g['forced_first']==n['forced_first'],base_label=g['label'],first_label=n['label'],whole_label=whole['label'],first_delta=str(y(n)-y(g)),total_delta=str(y(whole)-y(g)),continuation_and_cache_delta=str(y(whole)-y(n))))
  mean=lambda k:sum(F(v[k]) for v in z)/len(z)
  assert mean('first_delta')+mean('continuation_and_cache_delta')==mean('total_delta')
  out.append(dict(profile=profile,opponent=opp,N=len(z),first_delta=str(mean('first_delta')),whole_delta=str(mean('total_delta')),continuation_and_cache_delta=str(mean('continuation_and_cache_delta')),rows=z))
(O/'result.json').write_text(json.dumps(dict(status='EXACT_FIRST_MOVE_DECOMPOSITION_ON_EXPOSED16_FAMILIES',rows=out,new_go=0,scope='Commonuniformteacherrootprewarm acrossfirstmoveinterventions. Wholeθ contrast includeslaterpricepolicies AND differentroot-derived TT warmth; notpureintrinsicleafadvantage attribution. FiniteH24 notultimateWDL; no outcomeselection.'),indent=2))
print([{k:v for k,v in x.items() if k!='rows'} for x in out])
O=R/'results/dev_aux/task1222';O.mkdir()
out=[]
for source in [1188,1197]:
 gs=[json.loads(s) for s in (R/f'results/dev_aux/task{source}/games.jsonl').read_text().splitlines()]
 ix={(g['root']['seed'],g['root']['variant'],g['color'],g['opponent']):g for g in gs};seeds=sorted(set(g['root']['seed'] for g in gs))
 for H in [12,24]:
  label=lambda g:g['label'] if len(g['actions'])<=H and g['label']!='C' else 'C'
  y0=lambda g:F((label(g)=='W')-(label(g)=='L'));dr=[];dn=[]
  for seed in seeds:
   for color in [False,True]:
    side='white' if color else 'black'
    for opp in ['unit_search','uniform_random']:
     b=ix[(seed,'none',color,opp)];r=ix[(seed,side+'R',color,opp)];n=ix[(seed,side+'N',color,opp)];dr.append(y0(r)-y0(b));dn.append(y0(n)-y0(b))
  mr=sum(dr)/len(dr);mn=sum(dn)/len(dn)
  out.append(dict(source=source,H=H,families=len(seeds),physical_games_reused=len(gs),counts=dict(collections.Counter(label(g) for g in gs)),deltaR=str(mr),deltaN=str(mn),R_minus_N=str(mr-mn),ratio_residual=str(mr-F(12,5)*mn),point_ratio=str(mr/mn) if mr>0 and mn>0 else None,scope='Cachedprefixfiniteoutcome noH48/newgames/no eventualWDL claim. Posthocdiagnostic notfreshvalidation.'))
(O/'result.json').write_text(json.dumps(dict(status='CACHED_ACTUAL_TERMINATION_TIME_H12_H24_EFFECTS',rows=out,new_go=0),indent=2));print(out)
