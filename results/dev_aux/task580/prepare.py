import json,math,time,hashlib,ast
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task580';p=R/'results/dev_aux/task574/declaration.json';old=json.loads(p.read_bytes());axes=[2,3,4,5,6,7,9,10,11,12,13,14];w=[0]+[90]*7+[0]+[90]*6+[0];profiles=[dict(name='unit_base',axis=None,sign=0,weights=w)]
for a in axes:
 for sign in [-1,1]:
  v=list(w);v[a]=math.floor(v[a]*math.exp(.25*sign)+.5);profiles.append(dict(name=f'axis{a}_{sign:+}',axis=a,sign=sign,weights=v))
d=dict(question='Does ALLsingle-axis stencil expose localgoalfeedback hiddenbyjointdirections?',root_pool_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),roots=old['roots'],profiles=profiles,axes=axes,opponents=['unit','random'],fixed_opponent=w,colors=[0,1],cap=12,nodes=1024,seed_base=2026104592,policy='warm_game',executable_sha256=old['executable_sha256'],frozen_before_queries=time.time(),fuse=600,logical_games=1000,expected_cost='25prices*2opps*10families*2colors actual12ply=1000maxgames, expected1-3minutes/600singlefuse, nofit/workers/fees',goals='Physicalmixed: WIN/LOSS+/-32/DRAW0/cap12quantitydiff19; derivepureterminalfromsameactualgames; ALLminus/base/plus cellandmeanresponses, no humanlabels inreward/opponent/selector.',scope='Postpopulationexposed574pool localdiagnostic, notnewholdout/learning/causalhumanpriceidentifiability. All12axes symmetric aroundgenericunitanchor fixedP90K0, no chosenhumanwrongaxis/oldepoch extension. Existingcontroller12/warm/exe unchanged.')
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(len(profiles),d['logical_games'])
