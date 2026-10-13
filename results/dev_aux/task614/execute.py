import json,hashlib,time,sys,os
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task614';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());b=json.loads((R/'results/dev_aux/task612/result.json').read_bytes());q=json.loads((R/'results/dev_aux/task613/result.json').read_bytes());assert q['status']=='PASS_ALL_MODE0_QUALIFICATION';profiles=json.loads((R/'results/dev_aux/task599/result.json').read_bytes())['profiles'];plan=dict(question='Newmatecurriculum price×MAINcapturegainprojection interaction atSAMErequest/stoppingpolicy?',profiles=profiles,roots=d['roots'],modes=[0,1],colors=[0,1],cap=12,nodes=1024,seed_base=d['seed_base'],planned_games=1152,fuse_seconds=600,expected_cost='ALL72roots4actualprices2colors2modes expectedunder1-2min; no newtraining/independentroots oradaptiveextension',executable_sha256=b['executable_sha256'],qualification_sha256=hashlib.sha256((R/'results/dev_aux/task613/result.json').read_bytes()).hexdigest(),goals=['terminal','mixed'],analysis='ForBOTHstarts endpoint-minusinitial withinmode, then I=mode1gain-mode0gain; ALLtrain/development separately andoriginalfamilyomission ALLoffsets/setup/candidatecolors grouped. Both signs informative, neither humanrecovery expectation. Unfinished separatedfromdraw. ALLnodes/depth/time retained, no filtering onpostinterventiondepth ornodecounts.',scope='ExposedNEW596matecurriculum, notold29main+qstudy: onlyMAINcapturefutilityexpression, q/leaf/SEE/order/history/margins unchanged, all4sameactualprices; no source/human pricefitness/opponent/rootselection. Same1024 request/stoppolicy notstrictsameactualnodes; cheappartialrootbiaseddiagnostic not pricelearning/generality proof. All1152newphysicalgames, no prefsourcecache soactualwork transparent.');(O/'declaration.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
# Import justthe counterclass definition, no qualificationproducer execution.
s=(R/'results/dev_aux/task613/qualify.py').read_text(encoding='utf-8');fields=['eligible','old_pruned','new_pruned','rescued_by_new','newly_pruned_by_new','new_gain_larger','new_gain_smaller'];exec(compile(s[s.index('class CounterEngine('):s.index('semq=')],'counteradapteronly','exec'))
A.EXE=R/'.local_agent/yaneura33_capture/yaneura-capture-diag.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==plan['executable_sha256'];start=time.monotonic();deadline=start+600;rows=[];acks=[];go=0
assert not(O/'games.jsonl').exists()
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 for pi,p in enumerate(profiles):
  ee=[]
  for mode in [0,1]:
   os.environ['DEV_AUX_CAPTURE_GAIN_MODE']=str(mode);e=CounterEngine(p['weights'],qj,'warm_game');ee.append(e);acks.append(dict(profile=pi,mode=mode,weights=e.w,prices=e.prices));(O/'price_acks.json').write_text(json.dumps(acks,indent=2),encoding='utf-8')
  try:
   for f in d['roots']:
    for c in [0,1]:
     for mode,e in enumerate(ee):
      G.stop();assert time.monotonic()<deadline;e.begin_game();g=native_game(e,None,e.w,f,c,None,d,deadline);assert all(x['capture_diag']['mode']==mode for x in g['queries']);g.update(mode=mode,profile=pi);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());go+=len(g['queries']);rows.append(dict(profile=pi,mode=mode,root=f['index'],family=f['source_family'],phase=f['phase'],color=c,goal=g['goal'],quantity=g['raw_quantity'],termination=g['termination'],go=len(g['queries']),plies=len(g['actions']),source=dict(file='results/dev_aux/task614/games.jsonl',line=len(rows)+1)))
  finally:
   for e in ee:e.close()
  print('pricepilot',pi,len(rows),go,round(time.monotonic()-start,2),flush=True)
out=dict(status='COMPLETE_ALL_CELLS',actual_games=len(rows),actual_go=go,rows=rows,price_acks=acks,seconds=time.monotonic()-start,scope=plan['scope']);assert len(rows)==1152;(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ['rows','price_acks']}))