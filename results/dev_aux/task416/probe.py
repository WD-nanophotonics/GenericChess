import json,time,sys,hashlib
from pathlib import Path
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task390'));import adapter as A;import run as G;from analyze import features
O=R/'results/dev_aux/task416';O.mkdir(exist_ok=True);old=json.loads((R/'results/dev_aux/task391/declaration.json').read_text(encoding='utf-8'));profiles=json.loads((R/'results/dev_aux/task410/declaration.json').read_text(encoding='utf-8'))['profiles'];cases=[]
for p in profiles:
 for letter in ['P','L','N','S','B','R','G','+P','+L','+N','+S','+B','+R']:
  sf='k8/9/9/9/4'+letter.lower()+'4/4R4/9/9/8K b - 1';cases.append(dict(name='undefended-'+letter,initial_sfen=sf,history=[],moves=['5f5e'],weights=p['weights']))
 cases.append(dict(name='pawn-horse-pawn',initial_sfen=old['local_exchange']['sfen'],history=[],moves=['5f5e','5d5e'],weights=p['weights']))
 cases.append(dict(name='first-rook-promotion',initial_sfen='k8/9/4p4/4R4/9/9/9/9/8K b - 1',history=[],moves=['5d5c+'],weights=p['weights']))
c=old['real_first_undefended_capture'];cases.append(dict(name='actual391proml',initial_sfen=c['initial_sfen'],history=c['history'],moves=[c['move']],weights=c['weights']))
def literal(sf,w):return sum(a*b for a,b in zip(features(sf)[0],w))
for x in cases:
 b=C.Board(x['initial_sfen'])
 for u in x['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 actor=b.turn;base=literal(b.sfen(),x['weights']);x['before_sfen']=b.sfen()
 for u in x['moves']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 x['after_sfen']=b.sfen();x['expected_local_material']=(1 if actor==0 else -1)*(literal(b.sfen(),x['weights'])-base);x['thresholds']=[x['expected_local_material']-1,x['expected_local_material'],x['expected_local_material']+1]
decl=dict(cases=cases,selection='all6fixed26vectors13capturetypes+one2captureexchange+firstownpromotion+391actualfullhistory; thresholds exactlegal-sequence gain-1,=,+1 before ANY auxsee; no all-defense claim',old_executable_sha256=hashlib.sha256((R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe').read_bytes()).hexdigest(),new_executable_sha256=hashlib.sha256((R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe').read_bytes()).hexdigest());(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');rows=[];t0=time.perf_counter()
for arm,exe in [('old',R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe'),('hand',R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe')]:
 A.EXE=exe
 for x in cases:
  G.stop();e=A.Engine(x['weights'])
  try:
   line=e.state(x['initial_sfen'],x['history']);parts=line.split(' ',7);expected=literal(x['before_sfen'],x['weights']);assert int(parts[3])==int(parts[4])==expected
   for threshold in x['thresholds']:
    e.send(f"auxsee {x['moves'][0]} {threshold}");lines=e.until(lambda s:s.startswith('info string auxsee '));v=bool(int(lines[-1].split()[-1]));want=x['expected_local_material']>=threshold
    rows.append(dict(arm=arm,name=x['name'],weights=x['weights'],threshold=threshold,actual=v,local_sequence_predicate=want,lines=lines))
    if arm=='hand':assert v==want,(x,threshold,lines)
  finally:e.close()
out=dict(status='PASS',cases=len(cases),auxsee_calls=len(rows),new_go=0,seconds=time.perf_counter()-t0,old_mismatch_predicates=sum(x['actual']!=x['local_sequence_predicate'] for x in rows if x['arm']=='old'),hand_mismatch_predicates=sum(x['actual']!=x['local_sequence_predicate'] for x in rows if x['arm']=='hand'),rows=rows);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='rows'})
