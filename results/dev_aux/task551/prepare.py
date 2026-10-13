import sys,json,time,random,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task551'
for n in [360,364]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G
policy=dict(seeds=[2026104210,2026104211],prefix=40,unavailable='Recordfirstterminalbefore40, no replacement/reseed; allnegativeconditions retained',frozen_before_generation=time.time(),scope='Fresh physicalcontroller pairedcost, not old532 continuation/refit/holdout')
(O/'input_policy.json').write_text(json.dumps(policy,indent=2),encoding='utf-8');roots=[];unavailable=[]
for i,s in enumerate(policy['seeds']):
 b=A.shogi.Board();f=dict(index=i,seed=s,phase='train',initial_sfen=b.sfen(),history=[]);rng=random.Random(s)
 for ply in range(40):
  if not sorted(m.usi() for m in b.legal_moves):break
  k,checks,movers=G.full_root(dict(initial_sfen=f['initial_sfen'],history=f['history']))[1:];term=G.terminal(b,k,checks,movers)
  if term:unavailable.append(dict(seed=s,ply=ply,terminal=term));break
  u=rng.choice(sorted(m.usi() for m in b.legal_moves));b.push_usi(u);f['history'].append(u)
 if len(f['history'])==40:f['expected_sfen']=b.sfen();roots.append(f)
 else:assert any(x['seed']==s for x in unavailable)
profiles=json.loads((R/'results/dev_aux/task529/declaration.json').read_bytes())['initial_profiles']
d=dict(question='Does native physicalrule controller reduce warm callercost while ALL actualnon-time search output and paths stay identical?',roots=roots,unavailable=unavailable,profiles=profiles,opponents=['unit','random'],colors=[0,1],budgets=[1024,8192],cap=24,seed_base=2026104292,policy='warm_game',executable_sha256='c69d96c10244b65da124d66c653449bc701680f4e3da05ec48b3979ef950d2e2',controllers=['python_rules','native_rules'],order='caseparitycounterbalanced',fuse=600,expected_cost='1-3minutes64actualshortgames includingfull queryvalidation/journals; nofit/workers/fees; singlepanel notsplitlongrun',qualification='ALL non-time queries/node/depth/PV/actionmetadata/goal/fullhist/reset identical per matchedpair; independentPythonreplay nativepaths; freshnegativecases retain without rerun',known_scope='standardShogi NoEnteringKing; warmwithinGAME only; no generatedrule generality/productdefault change; ordinaryconcurrency limits timing')
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(len(roots),len(unavailable))
