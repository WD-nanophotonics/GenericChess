from pathlib import Path
import json,collections
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1090';O.mkdir(exist_ok=False)
a=[json.loads(x) for x in (R/'results/dev_aux/task1081/games.jsonl').read_text().splitlines()];b=[json.loads(x) for x in (R/'results/dev_aux/task1087/games.jsonl').read_text().splitlines()];ix={g['game']:g for g in a};rows=[]
for g in b:
 old=ix[g['game']];assert g['actions'][:len(old['actions'])]==old['actions'];assert g['queries'][:len(old['queries'])]==old['queries']
 if old['label']!='C':assert old['label']==g['label'] and old['actions']==g['actions']
for h,gg in [(16,a),(24,b)]:
 for p in [64,90,671]:
  xx=[g for g in gg if g['price']==p];cc=collections.Counter(g['label'] for g in xx);by={opp:str(F(sum((g['label']=='W')-(g['label']=='L') for g in xx if g['opponent']==opp),64)) for opp in ['unit_search','uniform_random']};rows.append(dict(H=h,price=p,N=128,counts=dict(cc),mixed_J=str(F(cc['W']-cc['L'],128)),opponent_J=by))
result=dict(status='PASS_ALL384_EXACT_ACTION_AND_FULL_QUERY_PREFIXES',rows=rows,transitions={p:dict(collections.Counter(ix[g['game']]['label']+'->'+g['label'] for g in b if g['price']==p)) for p in [64,90,671]},comparison='H16mixed64=671=25/128 versus90=23/128; H24 mixed64=13/64<90=31/128<671=1/4. Lowpricedlocallearneradvantageflipswithdeadline. No refit; noteventualWDL.',scope='Developmentexposeddeadlinecontrast, finiteactualW-L,C!=draw. Exactqueryprefix meanspolicyunchanged,onlycapdiffers.',new_go=0)
(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(rows)
