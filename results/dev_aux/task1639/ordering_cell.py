import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,time,random,collections,importlib.util,hashlib,datetime
R=Path.cwd();O=R/'results/dev_aux/task1664';O.mkdir(exist_ok=False);start=time.monotonic();plan=json.loads((R/'results/dev_aux/task1663/plan.json').read_bytes());deadline=start+600
def module(name,path):
 sp=importlib.util.spec_from_file_location(name,R/path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
T=module('T','results/dev_aux/task1626/rules.py');P=module('P','results/dev_aux/task166/run.py')
states=list(map(tuple,json.loads((R/'results/dev_aux/task1627/states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};value=json.loads((R/'results/dev_aux/task1627/values.json').read_bytes())['value']
cache={};reuse=0;queries=0;e=None;error=None;train=[];dev=[];diagnostics=[];selected=None
for path in sorted((R/'results/dev_aux/task1631').glob('*_choices.jsonl'))+sorted((R/'results/dev_aux/task1634').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1641').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1644').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1652').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1661').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1667').glob('*choices.jsonl')):
 for line in path.open():
  x=json.loads(line);key=tuple(x['price']),tuple(x['state']);assert T.fen(key[1])==x['position'];assert x.get('child') is None or dict(T.moves(key[1]))[x['move']]==tuple(x['child']);cache[key]=x['move']
(O/'start.json').write_text(json.dumps({'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'session_id':json.loads((R/'.local_agent/session.json').read_bytes())['id'],'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds_cap':600,'max_go':50000,'no_restart':True},indent=2))
proof=json.loads((R/'results/dev_aux/task1649/result.json').read_bytes());assert proof['status'].startswith('PASS');safe=set(proof['proved_no_mate_masks']);slots=proof['slots'];cf=(O/'choices.jsonl').open('w');gf=(O/'games.jsonl').open('w')
def choose(s,price):
 global reuse,queries
 P.stop();assert time.monotonic()<deadline and queries<50000
 if (price,s) in cache:reuse+=1;return cache[price,s]
 e.send('ucinewgame');e.ready();e.send('position fen '+T.fen(s))
 with (O/'go_journal.jsonl').open('a') as j:j.write(json.dumps({'event':'SEND_INTENT','price':price,'state':s})+'\n')
 e.send('go nodes 64');queries+=1
 with (O/'go_journal.jsonl').open('a') as j:j.write(json.dumps({'event':'SENT','price':price,'state':s})+'\n')
 raw=e.until(lambda x:x.startswith('bestmove '));move=raw[-1].split()[1];e.ready();assert move in dict(T.moves(s))
 cf.write(json.dumps({'price':price,'state':s,'move':move,'position':T.fen(s),'command':'go nodes 64','uci_info':raw[:-1]})+'\n');cf.flush();cache[price,s]=move;return move
def evaluate(price,phase,families,seeds,H):
 e.send(f'devauxleafrnbp {price[0]} {price[1]} {price[2]} 720');ack=e.ready();assert f'info string DEV_AUX leafRNBP {price[0]} {price[1]} {price[2]} 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack
 (O/('ACK_'+str(price)+'_'+phase+'.json')).write_text(json.dumps(ack));rows=[];cats=collections.Counter()
 for f in families:
  for colorindex,root in enumerate(f['roots']):
   for seed in range(seeds):
    rng=random.Random(2026678600+f['family']*100+seed);s=tuple(root);c=s[8];trajectory=[];payoff=None
    for ply in range(H+1):
     P.stop();assert time.monotonic()<deadline;ll=T.moves(s)
     if not ll:payoff=(-1 if s[8]==c else 1) if T.attacked(s,s[4*s[8]],1-s[8]) else 0;category='PHYSICAL_MATE' if payoff else 'PHYSICAL_STALE';break
     if sum(1<<i for i,k in enumerate(slots) if s[k]!=16) in safe:payoff=0;category='RULE_NO_MATE_DRAW';break
     if ply==H:category='UNRESOLVED';break
     u=rng.random()
     if s[8]==c:move=choose(s,price) if len(ll)>1 else ll[0][0]
     else:move=ll[min(int(u*len(ll)),len(ll)-1)][0]
     trajectory.append({'state':s,'move':move,'uniform':u,'own':s[8]==c});s=dict(ll)[move]
    lo=-1 if payoff is None else payoff;hi=1 if payoff is None else payoff;row={'price':price,'phase':phase,'family':f['family'],'color_index':colorindex,'seed':seed,'H':H,'root':root,'trajectory':trajectory,'end':s,'category':category,'payoff':payoff,'lower':lo,'upper':hi};gf.write(json.dumps(row)+'\n');gf.flush();rows.append(row);cats[category]+=1
 out={'price':price,'phase':phase,'H':H,'games':len(rows),'lower':sum(x['lower'] for x in rows)/len(rows),'upper':sum(x['upper'] for x in rows)/len(rows),'finite_net':sum(x['payoff'] or 0 for x in rows)/len(rows),'categories':dict(cats)};print(out,flush=True);return out
try:
 assert hashlib.sha256((R/plan['binary']).read_bytes()).hexdigest()==plan['binary_sha256'];e=P.M.start(R/plan['binary'],3,deadline,P.stop)
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/plan['variant_ini'])),('UCI_Variant','aux_tiny')]:
  e.send(f'setoption name {name} value {val}');ack=e.ready()
  if name=='UCI_Variant':assert any(z.startswith('info string variant aux_tiny files 4 ranks 4 ') for z in ack)
 for price in map(tuple,plan['profiles']):dev.append(evaluate(price,'ORDERING_CELL',plan['family_subset'],4,48))
 rows=[dict(json.loads(line),reused_game=True,source='task1652') for line in (R/'results/dev_aux/task1652/games.jsonl').open() if json.loads(line)['phase']=='DEV' and json.loads(line)['price']==[1728,720,720] and json.loads(line)['family'] in {f['family'] for f in plan['family_subset']}]
 assert len(rows)==512
 for x in rows:x['phase']='ORDERING_CELL';gf.write(json.dumps(x)+'\n')
 gf.flush();dev.append({'price':(1728,720,720),'phase':'ORDERING_CELL','H':48,'games':512,'lower':sum(x['lower'] for x in rows)/512,'upper':sum(x['upper'] for x in rows)/512,'finite_net':sum(x['payoff'] or 0 for x in rows)/512,'categories':dict(collections.Counter(x['category'] for x in rows)),'reused_game':True})
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 cf.close();gf.close()
 if e is not None:e.close()
out={'status':'COMPLETE' if error is None else 'PARTIAL_PRESERVED','error':error,'actual_go':queries,'cache_hits':reuse,'seconds':time.monotonic()-start,'exit_code':None if e is None else e.p.poll(),'selected':selected,'TRAIN':train,'DEV':dev,'diagnostics':diagnostics,'scope':plan['scope']};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

