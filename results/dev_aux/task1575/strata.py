from pathlib import Path
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task1577';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1538';s=json.loads((G/'states.json').read_bytes());original=json.loads((G/'values.json').read_bytes())['value'];plan=json.loads((G/'study.json').read_bytes());values={(phase,p,c):json.loads((R/f'results/dev_aux/task{tid}/B64_R{p}_C{c}.json').read_bytes())['value'] for phase,tid in [('A',1555),('B',1568)] for p in [720,1728] for c in [0,1]};groups={}
for f in plan['families']:
 for i in f['state_ids']:
  c=s[i][6];kind='R' if s[i][3*c+1]!=12 else 'N';key=f'{kind}:oracle{original[i]}';g=groups.setdefault(key,{'roots':0,'A_base':collections.Counter(),'A_high':collections.Counter(),'B_base':collections.Counter(),'B_high':collections.Counter(),'A_gain_sum':0,'B_gain_sum':0});g['roots']+=1
  for phase in ['A','B']:
   a=values[phase,720,c][i];b=values[phase,1728,c][i];g[phase+'_base'][a]+=1;g[phase+'_high'][b]+=1;g[phase+'_gain_sum']+=b-a
assert sum(g['A_gain_sum'] for g in groups.values())==12 and sum(g['B_gain_sum'] for g in groups.values())==9
(O/'result.json').write_text(json.dumps({'status':'EXPOSED64_POLICY_STOCK_STRATA','groups':groups,'scope':'Descriptive partition ofsameold128families/256roots; no newindependentvalidation, pricefit orcausalclaim. Positive-net doesnotmeanmorewins.'},indent=2));print(groups)
