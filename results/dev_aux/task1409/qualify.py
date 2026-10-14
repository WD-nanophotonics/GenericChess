from pathlib import Path
import ast,json,time,re,importlib.util,hashlib,chess
R=Path.cwd();O=R/'results/dev_aux/task1411';O.mkdir(exist_ok=False)
def load(path,name):
 sp=importlib.util.spec_from_file_location(name,R/path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
P=load('results/dev_aux/task166/run.py','p166');U=load('results/dev_aux/task1390/runner.py','runner');L=load('results/dev_aux/task1387/literal_rb.py','lit')
roots=json.loads((R/'results/dev_aux/task1400/roots.json').read_bytes())['roots'];deadline=time.monotonic()+90;old=new=None;queries=[];perfts=[];invalid=[];probes=[]
w=dict(P=1664,N=720,B=720,R=720,Q=1664,K=0)
try:
 old=P.M.start(R/'.local_agent/leaf-rb-45/fairy-leaf-rb.exe',3,deadline,P.stop);new=P.M.start(R/'.local_agent/leaf-rnb-46/fairy-leaf-rnb.exe',3,deadline,P.stop)
 oldack=U.config5(old,w,O);newack=U.config5(new,w,O)
 for e in [old,new]:e.send('devauxleafrb 1728 720');e.ready()
 for root in roots[:8]:
  rows=[]
  for e in [old,new]:
   e.send('ucinewgame');e.ready();move,meta=U.search(e,chess.Board(root['fen8']),4096);rows.append(dict(move=move,metadata=meta));queries.append(dict(root=root,mode='oldnew_RB',row=rows[-1]))
  norm=lambda lines:[' '.join(t for t in line.split() if t) for line in lines if not line.startswith('info string')]
  def stripmeta(lines):
   out=[]
   for line in norm(lines):
    fs=line.split()
    for key in ['time','nps']:
     if key in fs:i=fs.index(key);del fs[i:i+2]
    out.append(' '.join(fs))
   return out
  assert rows[0]['move']==rows[1]['move'] and stripmeta(rows[0]['metadata']['uci_info'])==stripmeta(rows[1]['metadata']['uci_info'])
 for r,n,b in [(864,360,360),(1728,720,720),(3456,1440,1440)]:
  new.send(f'devauxleafrnb {r} {n} {b}');ack=new.ready();expected=f'info string DEV_AUX leafRNB {r} {n} {b} nativeR 720 nativeN 720 nativeB 720 captureR 720 captureN 720 captureB 720';assert expected in ack
  for piece,value in [('R',r),('N',n),('B',b)]:
   for color in ['white','black']:
    fen='4k3/8/8/8/2'+(piece if color=='white' else piece.lower())+'5/8/8/K7 w - - 0 1'
    new.send('position fen '+fen);new.send('eval');raw=new.ready();v=float(next(x for x in raw if x.startswith('Final evaluation')).split()[2]);assert abs(v-(1 if color=='white' else -1)*value/208)<.011;probes.append(dict(scale=n/720,piece=piece,color=color,raw=raw,measured=v))
  for root in roots[:8]:
   new.send('ucinewgame');new.ready();move,meta=U.search(new,chess.Board(root['fen8']),4096);queries.append(dict(root=root,mode='RNB',prices=[r,n,b],ack=ack,row=dict(move=move,metadata=meta)))
 for command in ['devauxleafrnb 0 360 360','devauxleafrnb 864 0 360','devauxleafrnb 864 360 0','devauxleafrnb 4097 720 720','devauxleafrnb 720 1441 720','devauxleafrnb 720 720 4097','devauxleafrnb abc 720 720','devauxleafrnb 720 720']:
  new.send(command);raw=new.ready();assert 'info string DEV_AUX leafRNB invalid' in raw;invalid.append(dict(command=command,raw=raw))
  for piece,value in [('R',3456),('N',1440),('B',1440)]:
   new.send('position fen 4k3/8/8/8/2'+piece+'5/8/8/K7 w - - 0 1');new.send('eval');raw=new.ready();v=float(next(x for x in raw if x.startswith('Final evaluation')).split()[2]);assert abs(v-value/208)<.011;invalid[-1].setdefault('rollback_probes',[]).append(dict(piece=piece,raw=raw))
 for root in roots:
  new.send('position fen '+root['fen8']);new.send('go perft 1');raw=new.until(lambda x:'Nodes searched:' in x,max_lines=200);moves=sorted(m.group(1) for line in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][qrbn]?):\s*(\d+)',line.strip())));assert moves==root['legal']==L.literal(chess.Board(root['fen8']));perfts.append(dict(seed=root['seed'],moves=moves,raw=raw))
finally:
 for e in [old,new]:
  if e:e.close()
pv=0
for q in queries:
 board=chess.Board(q['root']['fen8']);assert q['row']['move'] in L.literal(board)
 for line in q['row']['metadata']['uci_info']:
  fs=line.split()
  if 'pv' in fs:
   b=board.copy()
   for move in fs[fs.index('pv')+1:]:assert move in L.literal(b);b.push_uci(move);pv+=1
assert all(e.closed and e.p.poll()==0 for e in [old,new])
out=dict(status='PASS_RNB_COLD_BINARY_CONTROLS_PRICE_PROBES_INVALID_ATOMIC_ROLLBACK_NATIVE_LEGAL',new_go=len(queries),perft_go=len(perfts),literal_PV_moves=pv,queries=queries,perfts=perfts,invalid=invalid,probes=probes,old_ack=oldack,new_ack=newack,all_owned_closed=True,scope='8TRAINroot32? oldnew16queries+24scaledqueries=40coldsearchgo,32perft, no WL/fit/DEVselection; old/newexactallnontimingUCIinfo.')
(O/'qualification.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if not isinstance(v,list) and k not in ['old_ack','new_ack']})
