"""Native aligned price driver; complete state, explicit domain/budget identity."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,time,hashlib,datetime,collections,importlib.util
R=Path.cwd()
def mod(n,path):
 sp=importlib.util.spec_from_file_location(n,R/path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
def sha(path):return hashlib.sha256((R/path).read_bytes()).hexdigest()
class Driver:
 def __init__(self,plan,out):
  self.plan=plan;self.O=out;out.mkdir(exist_ok=False);self.T=mod('T53',plan['model']);self.P=mod('STOP53','results/dev_aux/task166/run.py')
  self.start=time.perf_counter();self.deadline=time.monotonic()+plan['seconds_cap'];self.queries=0;self.hits=0;self.cache={};self.current=None;self.e=None;self.rows=[];self.newnodes=0
  for a,b in [('model','model_sha256'),('binary','binary_sha256'),('variant_ini','variant_sha256'),('stockproof','stockproof_sha256')]:assert sha(plan[a])==plan[b],a
  proof=json.loads((R/plan['stockproof']).read_bytes());assert proof['status']=='PROVED_NO_MATE_IN_COMPLETE_CLOSED_SINGLE_N_B_OR_BARE_STOCK' and proof['width']==self.T.W and proof['model_sha256']==plan['model_sha256']
  self.domain=(plan['model_sha256'],plan['binary_sha256'],plan['variant_sha256'],'GLOBAL_ALIGNED')
  self.files={n:(out/f'{n}.jsonl').open('w',encoding='utf-8') for n in ('choices','games','acks','go_journal')}
  (out/'start.json').write_text(json.dumps(dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=json.loads((R/'.local_agent/session.json').read_bytes())['id'],source_sha256=sha('results/dev_aux/task1720/driver.py'),plan=plan),indent=2))
 def log(self,n,x):self.files[n].write(json.dumps(x)+'\n');self.files[n].flush()
 def guard(self):self.P.stop();assert time.monotonic()<self.deadline,'wallcap';assert self.queries<self.plan['max_go'],'gocap'
 def start_engine(self):
  self.guard();self.e=self.P.M.start(R/self.plan['binary'],3,self.deadline,self.P.stop)
  for n,v in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/self.plan['variant_ini']))]:self.e.send(f'setoption name {n} value {v}');self.e.ready()
 def choose(self,s,p,nodes):
  self.guard();p=tuple(p);s=tuple(s);key=self.domain,nodes,p,s
  if key in self.cache:self.hits+=1;return self.cache[key]
  e=self.e;clear=0;va=[];ack=[]
  if self.current!=p:
   vn=self.plan['variant_names'][str(p)];e.send('setoption name UCI_Variant value '+vn);va=e.ready();assert any(z.startswith(f'info string variant {vn} files {self.T.W} ranks {self.T.H} ') for z in va)
   e.send('devauxleafrnbp '+' '.join(map(str,p)));ack=e.ready()
   expected='info string DEV_AUX leafRNBP '+' '.join(map(str,p))+f' nativeP {p[3]} nativeR {p[0]} nativeN {p[1]} nativeB {p[2]} captureP {p[3]} captureR {p[0]} captureN {p[1]} captureB {p[2]}'
   assert expected in ack,(expected,ack);self.current=p;clear=1
  else:e.send('ucinewgame');ack=e.ready();clear=1
  self.log('acks',dict(price=p,state=s,nodes=nodes,variant_ack=va,ack=ack,price_changed=bool(va),explicit_clear_commands=clear,domain=self.domain))
  e.send('position fen '+self.T.fen(s));t=time.perf_counter_ns();meta=dict(price=p,state=s,nodes=nodes,domain=self.domain)
  self.log('go_journal',dict(event='INTENT',**meta));e.send('go nodes '+str(nodes));self.queries+=1;self.log('go_journal',dict(event='SENT',**meta))
  raw=e.until(lambda z:z.startswith('bestmove '));e.ready();elapsed=time.perf_counter_ns()-t;u=raw[-1].split()[1];assert u in dict(self.T.moves(s))
  nn=0
  for row in raw[:-1]:
   a=row.split()
   if 'nodes' in a:nn=max(nn,int(a[a.index('nodes')+1]))
  self.newnodes+=nn;self.log('choices',dict(**meta,fen=self.T.fen(s),move=u,command='go nodes '+str(nodes),uci_info=raw[:-1],reported_nodes=nn,elapsed_ns=elapsed,explicit_clear_commands=clear));self.cache[key]=u;return u
 def stockdraw(self,s):
  pieces=[p.upper() for p in s[:-1] if p not in ('.','K','k')]
  return not pieces or len(pieces)==1 and pieces[0] in ('N','B')
 def game(self,p,f,color,op,phase):
  s=tuple(f['roots'][color]);c=s[-1];path=[];visited={};pay=None;repeat=None
  for ply in range(self.plan['H']+1):
   self.guard();ll=self.T.moves(s)
   if not ll:
    pay=(-1 if s[-1]==c else 1) if self.T.attacked(s,self.T.king(s,s[-1]),1-s[-1]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE';break
   if self.stockdraw(s):pay=0;cat='PROVED_SINGLE_STOCK_DRAW';break
   if s in visited:pay=0;cat='PROVED_POLICY_CYCLE_DRAW';repeat=[visited[s],ply];break
   if ply==self.plan['H']:cat='UNRESOLVED';break
   visited[s]=ply;own=s[-1]==c;pp=p if own else op['price'];n=self.plan['candidate_nodes'] if own else op['nodes']
   u=self.choose(s,pp,n) if len(ll)>1 else ll[0][0];path.append(dict(state=s,move=u,own=own));s=dict(ll)[u]
  row=dict(price=p,phase=phase,family=f['family'],color=color,opponent=op['id'],opponent_price=op['price'],opponent_nodes=op['nodes'],root=f['roots'][color],H=self.plan['H'],trajectory=path,end=s,category=cat,payoff=pay,repeat=repeat,lower=-1 if pay is None else pay,upper=1 if pay is None else pay)
  self.log('games',row);self.rows.append(row);return row
 def evaluate(self,p,phase):
  rows=[self.game(p,f,c,op,phase) for f in self.plan['families'] if f['phase']==phase for c in (0,1) for op in self.plan['opponents']]
  out=dict(price=p,phase=phase,games=len(rows),finite_net=sum(x['payoff'] or 0 for x in rows)/len(rows),lower=sum(x['lower'] for x in rows)/len(rows),upper=sum(x['upper'] for x in rows)/len(rows),categories=dict(collections.Counter(x['category'] for x in rows)))
  print('EVALUATE',out,flush=True);return out
 def close(self):
  for f in self.files.values():f.close()
  if self.e:self.e.close()
def main():
 plan=json.loads((R/sys.argv[1]).read_bytes());d=Driver(plan,R/sys.argv[2]);train=[];dev=[];selected={};error=None
 try:
  d.start_engine()
  for phase in ('TRAIN1','TRAIN2'):
   for p in plan['prices']:train.append(d.evaluate(tuple(p),phase))
  for phase in ('TRAIN1','TRAIN2'):selected[phase]=tuple(min([z for z in train if z['phase']==phase],key=lambda z:(-z['finite_net'],z['price']))['price'])
  pool={tuple(p):sum(z['finite_net'] for z in train if tuple(z['price'])==tuple(p))/2 for p in plan['prices']}
  selected['POOLED']=min(pool,key=lambda p:(-pool[p],p))
  (d.O/'selection.json').write_text(json.dumps(dict(selected=selected,pooled={str(p):v for p,v in pool.items()}),indent=2))
  for p in sorted(set(selected.values())|{tuple(plan['baseline'])}):dev.append(d.evaluate(p,'DEV'))
 except BaseException as ex:error=type(ex).__name__+':'+str(ex)
 finally:d.close()
 out=dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,actual_go=d.queries,cache_hits=d.hits,actual_reported_nodes=d.newnodes,seconds=time.perf_counter()-d.start,exit_code=d.e.p.poll() if d.e else None,TRAIN=train,DEV=dev,selected=selected,actual_games=len(d.rows),source_sha256=sha('results/dev_aux/task1720/driver.py'))
 (d.O/'result.json').write_text(json.dumps(out,indent=2));print('FINAL',{k:v for k,v in out.items() if k not in ('TRAIN','DEV')},flush=True)
if __name__=='__main__':main()

