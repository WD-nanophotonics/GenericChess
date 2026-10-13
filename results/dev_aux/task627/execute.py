import json,hashlib,time,sys,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task627';O.mkdir(exist_ok=True);old=json.loads((R/'results/dev_aux/task618/declaration.json').read_bytes());profiles=json.loads((R/'results/dev_aux/task624/declaration.json').read_bytes())['profiles'];seeds=list(range(2026105010,2026105018));plan=dict(question='DoALLold+fastlearnedprices transfer toNEWindependentfamilymatecurriculum withbalancedinitial-generatorpolicy?',independent_seeds=seeds,generator_profiles=old['initial_profiles'],generator_colors=[0,1],setup_cap=48,offsets=[2,4,8,12],probe_profiles=profiles,probe_colors=[0,1],probe_cap=12,nodes=1024,setup_seed_base=2026105092,probe_seed_base=2026105192,executable_sha256=old['executable_sha256'],fuse_seconds=600,expected_cost='32newsetupgamesmax48plies+ALLeligibleoffsets×ALL6prices×bothcolors max1536probe shortgames; expectedunder2min, no resampling/extraepochs',eligibility='ALLactualCHECKMATE setups includeALL2/4/8/12offsets ifavailable; ALLnomate/draw/loss retained, no replacement. Bothgeneratorprices/setupcolors/offsets share originalseedfamily, notextraindependentsamples.',freeze='Allroots+unavailable frozen BEFOREany6priceprobe. Allprices alreadyfixed619oldnewendpoints, no next-fit/selector orreferenceuse.',scope='NEWindependentfamilies vs596train/dev but deliberatelyterminal-enriched conditionalcurriculum, twoarbitraryinitial-generatorpolicies weighted equally; not natural-game distribution/unexposedentiremethod discovery orhumanpricevalidation. No sourceprices/learnedendpoint-selectedroots; ALLnegativecases andallcandidatecolors retained. No product/default/UI/state changes.');(O/'declaration.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');start=time.monotonic();deadline=start+600
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==plan['executable_sha256'];roots=[];missing=[];setup=[];acks=[];P=R/'results/dev_aux/task628';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists()
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for pi,p in enumerate(plan['generator_profiles']):
  e=ControlledEngine(p['weights'],qj,'warm_game');acks.append(dict(generator=pi,weights=e.w,prices=e.prices));(P/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8')
  try:
   for fi,seed in enumerate(seeds):
    for c in [0,1]:
     G.stop();assert time.monotonic()<deadline;b=A.shogi.Board();f=dict(index=fi,seed=seed,phase='balanced_setup',initial_sfen=b.sfen(),history=[],expected_sfen=b.sfen());e.begin_game();g=native_game(e,None,e.w,f,c,None,dict(cap=48,nodes=1024,seed_base=plan['setup_seed_base']),deadline);g.update(generator=pi,stage='setup',cap=48);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());line=len(setup)+1;setup.append(dict(generator=pi,family=seed,color=c,termination=g['termination'],plies=len(g['actions']),go=len(g['queries']),source=dict(file='results/dev_aux/task628/games.jsonl',line=line)))
     if g['termination']['kind']!='checkmate':missing.append(dict(generator=pi,family=seed,color=c,reason='no_mate_within48',termination=g['termination']));continue
     for offset in plan['offsets']:
      n=len(g['actions'])-offset
      if n<0:missing.append(dict(generator=pi,family=seed,color=c,offset=offset,reason='mate_before_offset'));continue
      h=[a['move'] for a in g['actions'][:n]];sf=g['actions'][n-1]['after_sfen'] if n else f['initial_sfen'];root=dict(index=len(roots),seed=seed,phase='independent_balanced_probe',initial_sfen=f['initial_sfen'],history=h,expected_sfen=sf,source_family=seed,generator=pi,setup_color=c,offset=offset,setup_source=dict(file='results/dev_aux/task628/games.jsonl',line=line));pb,k,ch,mo=G.full_root(root);assert G.terminal(pb,k,ch,mo) is None;roots.append(root)
  finally:e.close()
(P/'result.json').write_text(json.dumps(dict(status='ALL_SETUP_COMPLETE',actual_games=32,actual_go=sum(x['go'] for x in setup),rows=setup,price_acks=acks,seconds=time.monotonic()-start),indent=2),encoding='utf-8');freeze=dict(before_any_probe=True,roots=roots,unavailable=missing,eligible_families=len({f['seed'] for f in roots}),setup_mates=sum(x['termination']['kind']=='checkmate' for x in setup),declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest());(O/'roots_frozen.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8');print('balancedroots',len(roots),freeze['eligible_families'],freeze['setup_mates'],len(missing),round(time.monotonic()-start,2),flush=True)
P=R/'results/dev_aux/task629';P.mkdir(exist_ok=True);assert not(P/'games.jsonl').exists();rows=[];acks=[];go=0
with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
 for pi,p in enumerate(plan['probe_profiles']):
  if not roots:break
  e=ControlledEngine(p['weights'],qj,'warm_game');acks.append(dict(profile=pi,weights=e.w,prices=e.prices));(P/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8')
  try:
   for f in roots:
    for c in [0,1]:
     G.stop();assert time.monotonic()<deadline;e.begin_game();g=native_game(e,None,e.w,f,c,None,dict(cap=12,nodes=1024,seed_base=plan['probe_seed_base']),deadline);g.update(profile=pi,stage='probe',cap=12);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());go+=len(g['queries']);rows.append(dict(profile=pi,root=f['index'],family=f['seed'],generator=f['generator'],color=c,goal=g['goal'],termination=g['termination'],plies=len(g['actions']),go=len(g['queries']),source=dict(file='results/dev_aux/task629/games.jsonl',line=len(rows)+1)))
  finally:e.close()
  print('balancedprice',pi,len(rows),go,round(time.monotonic()-start,2),flush=True)
if not roots:(P/'price_acks.json').write_text('[]',encoding='utf-8')
(P/'result.json').write_text(json.dumps(dict(status='ALL_PROBES_COMPLETE' if roots else 'NO_ELIGIBLE_MATE_ROOTS',actual_games=len(rows),actual_go=go,rows=rows,price_acks=acks,setup_games=32,setup_go=sum(x['go'] for x in setup),eligible_roots=len(roots),eligible_families=freeze['eligible_families'],seconds=time.monotonic()-start,scope=plan['scope']),indent=2),encoding='utf-8');print('BALANCED_COMPLETE',len(rows),go,round(time.monotonic()-start,3),flush=True)