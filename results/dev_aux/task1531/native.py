from pathlib import Path
import json,importlib.util,time,re,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1534';O.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
ini='[aux_tiny:chess]\nmaxFile = 3\nmaxRank = 4\ncastling = false\nnMoveRule = 0\nnFoldRule = 0\npieceValueMg = p:720 n:720 b:720 r:720 q:1664\npieceValueEg = p:720 n:720 b:720 r:720 q:1664\nstartFen = k2/3/3/2K w - - 0 1\n'
(O/'variant.ini').write_text(ini);start=time.monotonic();e=P.M.start(R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',3,start+180,P.stop);rows=[];error=None
states=list(map(tuple,json.loads((R/'results/dev_aux/task1532/states.json').read_bytes())));edgefile=(R/'results/dev_aux/task1532/edges.jsonl').open()
try:
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(O/'variant.ini')),('UCI_Variant','aux_tiny')]:
  e.send(f'setoption name {name} value {val}');ack=e.ready()
  if name=='UCI_Variant':(O/'variant_ack.json').write_text(json.dumps(ack));assert any(l.startswith('info string variant aux_tiny files 3 ranks 4 ') for l in ack)
 with (O/'native_perft.jsonl').open('w',encoding='utf8') as f:
  import random
  chosen=set(random.Random(2026670001).sample(range(len(states)),1024))
  for line in edgefile:
   row=json.loads(line);i=row['id']
   if i not in chosen:continue
   s=states[i];e.send('position fen '+T.fen(s));e.send('go perft 1');raw=e.until(lambda l:'Nodes searched:' in l,max_lines=200);moves=sorted(m.group(1) for l in raw if (m:=re.fullmatch(r'([a-c][1-4][a-c][1-4]):\s*(\d+)',l.strip())));assert moves==[u for u,j in row['moves']],(i,T.fen(s),moves,row['moves']);f.write(json.dumps({'id':i,'fen':T.fen(s),'raw':raw,'moves':moves})+'\n');rows.append(i)
   if i%5000==0:print('NATIVE',i,flush=True)
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:edgefile.close();e.close()
out={'status':'PASS_ALL_NATIVE_3X4_LEGAL' if error is None else 'PARTIAL_OR_FAILURE_PRESERVED','error':error,'actual_perft':len(rows),'seconds':time.monotonic()-start,'exit_code':e.p.poll(),'binary_sha256':hashlib.sha256((R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe').read_bytes()).hexdigest(),'scope':'1024 price-blind graph states native moves equal independent3x4 graph; actual perft, no training/search WDL interpretation. Native nFold/nMove disabled to match infinite-cycle draw graph.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
