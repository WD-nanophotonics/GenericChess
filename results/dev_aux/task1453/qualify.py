from pathlib import Path
import json,time,re,importlib.util,chess
R=Path.cwd();O=R/'results/dev_aux/task1458';O.mkdir(exist_ok=False)
def load(file,name):
 s=importlib.util.spec_from_file_location(name,R/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
P=load('results/dev_aux/task166/run.py','P');U=load('results/dev_aux/task1390/runner.py','U');L=load('results/dev_aux/task1453/literal_pawn.py','L')
roots=json.loads((R/'results/dev_aux/task1455/roots.json').read_bytes())['roots'];deadline=time.monotonic()+90;old=new=None;queries=[];perfts=[];probes=[];invalid=[]
w=dict(P=720,N=720,B=720,R=720,Q=1664,K=0)
try:
 old=P.M.start(R/'.local_agent/leaf-rnb-46/fairy-leaf-rnb.exe',3,deadline,P.stop);new=P.M.start(R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',3,deadline,P.stop)
 oldack=U.config5(old,w,O);newack=U.config5(new,w,O)
 for e,cmd in [(old,'devauxleafrnb 1728 720 720'),(new,'devauxleafrnbp 1728 720 720 720')]:e.send(cmd);e.ready()
 def info(lines):
  out=[]
  for line in lines:
   fs=line.split()
   for k in ['time','nps']:
    if k in fs:i=fs.index(k);del fs[i:i+2]
   out.append(' '.join(fs))
  return out
 for root in roots[:8]:
  rows=[]
  for e in [old,new]:
   e.send('ucinewgame');e.ready();move,meta=U.search(e,chess.Board(root['fen8']),1024);rows.append(dict(move=move,metadata=meta));queries.append(dict(root=root,mode='oldnew_P720',row=rows[-1]))
  assert rows[0]['move']==rows[1]['move'] and info(rows[0]['metadata']['uci_info'])==info(rows[1]['metadata']['uci_info'])
 for pawn in [180,360,720,1440]:
  new.send(f'devauxleafrnbp 1728 720 720 {pawn}');raw=new.ready();expected=f'info string DEV_AUX leafRNBP 1728 720 720 {pawn} nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720';assert expected in raw
  for piece,value in [('P',pawn),('N',720),('B',720),('R',1728),('Q',1664)]:
   for color in ['white','black']:
    new.send('position fen 4k3/8/8/8/2'+(piece if color=='white' else piece.lower())+'5/8/8/K7 w - - 0 1');new.send('eval');ev=new.ready();v=float(next(x for x in ev if x.startswith('Final evaluation')).split()[2]);assert abs(v-(1 if color=='white' else -1)*value/208)<.011;probes.append(dict(pawn=pawn,piece=piece,color=color,raw=ev))
  for root in roots[:8]:
   new.send('ucinewgame');new.ready();move,meta=U.search(new,chess.Board(root['fen8']),1024);queries.append(dict(root=root,mode='Pgrid',pawn=pawn,ack=raw,row=dict(move=move,metadata=meta)))
 for cmd in ['devauxleafrnbp 1728 720 720 0','devauxleafrnbp 1728 720 720 1441','devauxleafrnbp 1728 720 720 abc','devauxleafrnbp 1728 720 720','devauxleafrnbp 4097 720 720 720']:
  new.send(cmd);raw=new.ready();assert 'info string DEV_AUX leafRNBP invalid' in raw;new.send('position fen 4k3/8/8/8/2P5/8/8/K7 w - - 0 1');new.send('eval');ev=new.ready();v=float(next(x for x in ev if x.startswith('Final evaluation')).split()[2]);assert abs(v-1440/208)<.011;invalid.append(dict(command=cmd,raw=raw,rollbackP=ev))
 witnesses=[('white_promotion','4k3/P7/8/8/8/8/8/K7 w - - 0 1'),('black_promotion','7k/8/8/8/8/8/7p/3K4 b - - 0 1'),('EP_legal','k7/8/8/3pP3/8/8/8/7K w - d6 0 2'),('EP_pin_illegal','7k/8/8/r4pPK/8/8/8/8 w - f6 0 2'),('capture_promotion','k5r1/7P/8/8/8/8/8/K7 w - - 0 1')]
 for tag,fen in [(str(r['seed']),r['fen8']) for r in roots]+witnesses:
  b=chess.Board(fen);moves=L.literal(b);assert moves==sorted(m.uci() for m in b.legal_moves);new.send('position fen '+fen);new.send('go perft 1');raw=new.until(lambda x:'Nodes searched:' in x,max_lines=200);native=sorted(m.group(1) for l in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][qrbn]?):\s*(\d+)',l.strip())));assert native==moves;perfts.append(dict(tag=tag,fen=fen,moves=moves,raw=raw))
 assert 'e5d6' in next(x['moves'] for x in perfts if x['tag']=='EP_legal');assert 'g5f6' not in next(x['moves'] for x in perfts if x['tag']=='EP_pin_illegal')
finally:
 for e in [old,new]:
  if e:e.close()
pvm=0;prom=0;ep=0
for q in queries:
 b=chess.Board(q['root']['fen8']);assert q['row']['move'] in L.literal(b)
 for line in q['row']['metadata']['uci_info']:
  fs=line.split()
  if 'pv' in fs:
   v=b.copy()
   for u in fs[fs.index('pv')+1:]:
    assert u in L.literal(v);move=chess.Move.from_uci(u);prom+=bool(move.promotion);ep+=v.is_en_passant(move);v.push(move);pvm+=1
out=dict(status='PASS_PAWN_PROMOTION_EP_NATIVE_LITERAL_PRICE_INTERFACE',new_search_go=len(queries),native_perft=len(perfts),literal_PV_moves=pvm,promotionPV=prom,epPV=ep,queries=queries,probes=probes,invalid=invalid,perfts=perfts,oldack=oldack,newack=newack,all_owned_closed=all(e.closed and e.p.poll()==0 for e in [old,new]),scope='32freshinputnativelegal+5explicitpromotionEPwitnesses. 8old/newP720controls exactnon-time/nps info,4Ppriceson8TRAINonly. NoTRAIN/DEVfit or actualWLgames yet. Bothcolorall5pieceeval andinvalidrollbackPverified; commandatomic4fields source reviewed.')
(O/'qualification.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if not isinstance(v,list) and k not in ['oldack','newack']});assert out['all_owned_closed']
