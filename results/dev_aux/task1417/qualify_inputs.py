from pathlib import Path
import json,ast,time,importlib.util,chess,re
R=Path.cwd();O=R/'results/dev_aux/task1419';O.mkdir()
src=(R/'results/dev_aux/task1390/runner.py').read_text(encoding='utf-8-sig')
exec(compile(ast.Module(body=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='config5'],type_ignores=[]),'nativeconfig','exec'))
sp=importlib.util.spec_from_file_location('P166',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);start=time.monotonic();e=P.M.start(R/'.local_agent/leaf-rnb-46/fairy-leaf-rnb.exe',3,start+60,P.stop);rows=[]
try:
 ack=config5(e,dict(P=1664,N=720,B=720,R=720,Q=1664,K=0),O)
 for root in json.loads((R/'results/dev_aux/task1416/roots.json').read_bytes())['roots']:
  e.send('position fen '+root['fen8']);e.send('go perft 1');raw=e.until(lambda x:'Nodes searched:' in x,max_lines=200);moves=sorted(m.group(1) for l in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][qrbn]?):\s*(\d+)',l.strip())));assert moves==root['legal'];rows.append(dict(seed=root['seed'],raw=raw,moves=moves))
finally:e.close()
(O/'qualification.json').write_text(json.dumps(dict(status='PASS_FIXED_SCALE64_NATIVE_LEGAL_INPUTS',actual_perft_go=len(rows),seconds=time.monotonic()-start,ACK=ack,rows=rows,new_search_go=0,scope='64fresh frozen scalevalidation inputs, nativelegalonly no choices or fitting'),indent=2));print('NEXT_PERFT',len(rows))

