import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,time,hashlib,datetime,collections,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1693';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task1692/plan.json').read_bytes());start=time.monotonic();deadline=start+plan['seconds_cap']
def mod(n,path):
 sp=importlib.util.spec_from_file_location(n,R/path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
T=mod('T',plan['model']);P=mod('P','results/dev_aux/task166/run.py');P.stop();cache={};queries=0;hits=0;e=None;error=None;TRAIN=[];DEV=[];selected={}
assert hashlib.sha256((R/plan['model']).read_bytes()).hexdigest()==plan['model_sha256'];assert hashlib.sha256((R/plan['binary']).read_bytes()).hexdigest()==plan['binary_sha256'];assert json.loads((R/'results/dev_aux/task1689/result.json').read_bytes())['status'].startswith('PASS')
(O/'start.json').write_text(json.dumps({'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256((R/'results/dev_aux/task1692/plan.json').read_bytes()).hexdigest(),'session_id':json.loads((R/'.local_agent/session.json').read_bytes())['id'],'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'no_restart':True},indent=2));cf=(O/'choices.jsonl').open('w');gf=(O/'games.jsonl').open('w');af=(O/'acks.jsonl').open('w');jf=(O/'go_journal.jsonl').open('w')
def choose(s,price):
 global queries,hits
 P.stop();assert time.monotonic()<deadline and queries<plan['max_go']
 key=price,s
 if key in cache:hits+=1;return cache[key]
 e.send('devauxleafrnbp '+' '.join(map(str,price)));ack=e.ready();expected='info string DEV_AUX leafRNBP '+' '.join(map(str,price))+' nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720';assert expected in ack,(price,ack);af.write(json.dumps({'price':price,'state':s,'ack':ack})+'\n');af.flush()
 e.send('ucinewgame');e.ready();e.send('position fen '+T.fen(s));jf.write(json.dumps({'event':'INTENT','price':price,'state':s})+'\n');jf.flush();e.send('go nodes 64');queries+=1;jf.write(json.dumps({'event':'SENT','price':price,'state':s})+'\n');jf.flush();raw=e.until(lambda l:l.startswith('bestmove '));e.ready();u=raw[-1].split()[1];assert u in dict(T.moves(s));cf.write(json.dumps({'price':price,'state':s,'fen':T.fen(s),'move':u,'command':'go nodes 64','uci_info':raw[:-1]})+'\n');cf.flush();cache[key]=u;return u
BASE=tuple(plan['baseline'])
def evaluate(price,phase):
 cats=collections.Counter();rows=[]
 for f in plan['families']:
  if f['phase']!=phase:continue
  for color,root in enumerate(f['roots']):
   s=tuple(root);c=s[64];path=[];visited={};pay=None;repeat=None
   for ply in range(plan['H']+1):
    P.stop();assert time.monotonic()<deadline;ll=T.moves(s)
    if not ll:pay=(-1 if s[64]==c else 1) if T.attacked(s,T.king(s,s[64]),1-s[64]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE';break
    if T.bare(s):pay=0;cat='BARE_KINGS_DRAW';break
    if s in visited:pay=0;cat='PROVED_POLICY_CYCLE_DRAW';repeat=[visited[s],ply];break
    if ply==plan['H']:cat='UNRESOLVED';break
    visited[s]=ply;pp=price if s[64]==c else BASE;u=choose(s,pp) if len(ll)>1 else ll[0][0];path.append({'state':s,'move':u,'own':s[64]==c});s=dict(ll)[u]
   row={'price':price,'phase':phase,'family':f['family'],'color':color,'root':root,'H':plan['H'],'trajectory':path,'end':s,'category':cat,'payoff':pay,'repeat':repeat,'lower':-1 if pay is None else pay,'upper':1 if pay is None else pay};gf.write(json.dumps(row)+'\n');gf.flush();rows.append(row);cats[cat]+=1
 out={'price':price,'phase':phase,'games':len(rows),'finite_net':sum(x['payoff'] or 0 for x in rows)/len(rows),'lower':sum(x['lower'] for x in rows)/len(rows),'upper':sum(x['upper'] for x in rows)/len(rows),'categories':dict(cats)};print(out,flush=True);return out
try:
 e=P.M.start(R/plan['binary'],3,deadline,P.stop)
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/plan['variant_ini'])),('UCI_Variant','aux_pawn8')]:
  e.send(f'setoption name {name} value {val}');ack=e.ready()
  if name=='UCI_Variant':(O/'variant_ack.json').write_text(json.dumps(ack));assert any(z.startswith('info string variant aux_pawn8 files 8 ranks 8 ') for z in ack)
 selected={'FIXED_ON_TRAIN':tuple(plan['fixed_candidate'])}
 (O/'selection.json').write_text(json.dumps({'selected':selected,'source':plan['selection_source']},indent=2))
 for price in sorted({BASE,tuple(plan['fixed_candidate'])}):DEV.append(evaluate(price,'DEV'))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 for f in (cf,gf,af,jf):f.close()
 if e:e.close()
out={'status':'COMPLETE' if error is None else 'PARTIAL_PRESERVED','error':error,'actual_go':queries,'cache_hits':hits,'seconds':time.monotonic()-start,'exit_code':e.p.poll() if e else None,'selected':selected,'TRAIN':TRAIN,'DEV':DEV,'scope':plan['labels']};(O/'result.json').write_text(json.dumps(out,indent=2));print('FINAL',{k:v for k,v in out.items() if k not in ('TRAIN','DEV')})
