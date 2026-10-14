import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,random,time,importlib.util,hashlib,datetime
R=Path.cwd();O=R/'results/dev_aux/task1669';O.mkdir(exist_ok=False);sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);plan=json.loads((R/'results/dev_aux/task1666/plan.json').read_bytes());rows=list(map(json.loads,(R/'results/dev_aux/task1667/choices.jsonl').open()));unit=[x for x in rows if x['price']==[720,720,720]];other=[x for x in rows if x['price']!=[720,720,720]];rng=random.Random(2026682600);selected=[]
for a,b in zip(rng.sample(unit,16),rng.sample(other,16)):selected.extend([a,b])
(O/'plan.json').write_text(json.dumps({'status':'FROZEN_32_ALTERNATING_PRICE_PROTOCOL_REPLAY_BEFORE_QUERIES','source':'task1667actualcold64choices','keys':[[x['price'],x['state']] for x in selected],'seconds_cap':120,'max_go':32,'purpose':'Check sameengine perquery leafprice switching/cachecold semantics, preserveACK/raw andcompare move/PV/score/depth/nodes independentof time/nps, no fitting.'},indent=2));e=None;start=time.monotonic();error=None;out=[]
def non_time(info):
 a=info.split();z=[];i=0
 while i<len(a):
  if a[i] in ['time','nps']:i+=2;continue
  z.append(a[i]);i+=1
 return ' '.join(z)
try:
 e=P.M.start(R/plan['binary'],3,start+120,P.stop);assert hashlib.sha256((R/plan['binary']).read_bytes()).hexdigest()==plan['binary_sha256']
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/plan['variant_ini'])),('UCI_Variant','aux_tiny')]:e.send(f'setoption name {name} value {val}');e.ready()
 for x in selected:
  P.stop();r,n,b=x['price'];e.send(f'devauxleafrnbp {r} {n} {b} 720');ack=e.ready();assert f'info string DEV_AUX leafRNBP {r} {n} {b} 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack
  e.send('ucinewgame');e.ready();e.send('position fen '+x['position']);e.send('go nodes 64');raw=e.until(lambda z:z.startswith('bestmove '));e.ready();assert raw[-1].split()[1]==x['move'];assert list(map(non_time,raw[:-1]))==list(map(non_time,x['uci_info']));out.append({'price':x['price'],'state':x['state'],'ack':ack,'raw':raw,'reference':x,'same_non_time':True})
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 if e is not None:e.close()
(O/'replayed.json').write_text(json.dumps(out,indent=2));z={'status':'PASS_32_SAME_ENGINE_ALTERNATING_LEAF_ACK_COLD_NON_TIME_REPLAY' if error is None and len(out)==32 else 'FAILURE_OR_PARTIAL_PRESERVED','actual_go':len(out),'error':error,'seconds':time.monotonic()-start,'exit_code':None if e is None else e.p.poll(),'scope':'Protocolsemantic audit, notnewgames/human-price validation, runtimeACK rawpreserved.'};(O/'result.json').write_text(json.dumps(z,indent=2));print(z)

