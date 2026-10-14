from pathlib import Path
import json,ast,importlib.util,time,chess
R=Path.cwd();O=R/'results/dev_aux/task1388';O.mkdir()
sp=importlib.util.spec_from_file_location('P166',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
s=(R/'results/dev_aux/task1368/runner.py').read_text(encoding='utf-8-sig')
exec(compile(ast.Module(body=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name in ['config5','inside','legal5','search']],type_ignores=[]),'helpers','exec'))
d=json.loads((R/'results/dev_aux/task1386/roots.json').read_bytes());start=time.monotonic();deadline=start+90;rows=[];perfts=[];probes=[];bad=[];error=None;engines=[]
w=dict(P=1664,N=720,B=720,R=720,Q=1664,K=0)
def probe(e,pt,expected):
 e.send('position fen 4k3/8/8/8/2'+pt+'5/8/8/K7 w - - 0 1');e.send('eval');raw=e.ready();v=float(next(l for l in raw if l.startswith('Final evaluation')).split()[2]);assert abs(v-expected/208)<=.011;return dict(piece=pt,expected=expected,measured=v,raw=raw)
old=R/'.local_agent/leaf-4096-43/fairy-leaf-4096.exe';new=R/'.local_agent/leaf-rb-45/fairy-leaf-rb.exe'
try:
 for binary in [old,new]:
  e=P.M.start(binary,3,deadline,P.stop);engines.append(e)
  try:
   native=config5(e,w,O);probes.append(dict(binary=binary.name,native=native,Bnative=probe(e,'B',720)))
   if binary==new:
    import re
    for root in d['roots']:
     e.send('position fen '+root['fen8']);e.send('go perft 1');raw=e.until(lambda x:'Nodes searched:' in x,max_lines=200);moves=sorted(m.group(1) for x in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][qrbn]?):\s*(\d+)',x.strip())));assert moves==root['legal'];perfts.append(dict(seed=root['seed'],moves=moves,raw=raw))
   profiles=[[720,720],[1728,720]] if binary==old else [[720,720],[1728,720],[1728,360],[1728,1440],[4096,4096]]
   for leafR,leafB in profiles:
    e.send('devauxleafr '+str(leafR) if binary==old else f'devauxleafrb {leafR} {leafB}');raw=e.ready()
    wanted=f'info string DEV_AUX leafR {leafR} nativeR 720 captureR 720' if binary==old else f'info string DEV_AUX leafRB {leafR} {leafB} nativeR 720 nativeB 720 captureR 720 captureB 720'
    assert wanted in raw;probes.append(dict(binary=binary.name,R=leafR,B=leafB,ACK=raw,Rprobe=probe(e,'R',leafR),Bprobe=probe(e,'B',leafB)))
    if binary==new:
     for command in ['devauxleafrb 0 720','devauxleafrb 720 0','devauxleafrb 4097 720','devauxleafrb 720 4097','devauxleafrb abc 720']:
      e.send(command);r=e.ready();assert 'info string DEV_AUX leafRB invalid' in r;bad.append(dict(command=command,raw=r,R=probe(e,'R',leafR),B=probe(e,'B',leafB)))
    for root in d['roots'][:16]:
     e.send('ucinewgame');e.ready();b=chess.Board(root['fen8']);move,meta=search(e,b,4096);rows.append(dict(binary=binary.name,R=leafR,B=leafB,root=root,move=move,metadata=meta))
  finally:e.close()
except BaseException as ex:error=type(ex).__name__+': '+str(ex)
out=dict(status='COMPLETE' if error is None else 'FAILED',error=error,seconds=time.monotonic()-start,actual_go=len(rows),actual_perft=len(perfts),rows=rows,perfts=perfts,probes=probes,invalid=bad,closed_all=all(e.closed and e.p.poll() is not None for e in engines),scope='No Btraining/games; DEV roots nativelegal only; candidatequeries only first16TRAIN. R/Noldcommand retained,newatomicR/B actualleaf/nativeACK, invalidpreservesboth.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out['status'],len(rows),len(perfts),out['seconds'],error);assert error is None and len(rows)==112 and len(perfts)==32
