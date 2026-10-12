import sys,json,time,hashlib,re
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));import adapter as A
O=R/'results/dev_aux/task376';O.mkdir(exist_ok=True);end=json.loads((R/'results/dev_aux/task370/endpoints.json').read_text(encoding='utf-8'));vectors=[]
for rr in end['rounds']:
 for c in rr['candidates']:
  if c['weights'] not in vectors:vectors.append(c['weights'])
(O/'declaration.json').write_text(json.dumps({'vectors':vectors,'scope':'fresh post-fit process reload of ALLuniqueactualproposal prices; tables/options+literalstateprobes. Not fabricated historical fullack fromoriginaltrainingprocesses; originalgo states independently audited375. No newgo/fits.'},indent=2),encoding='utf-8');rows=[];t0=time.monotonic();empty='k8/9/9/9/9/9/9/9/8K b - 1'
for wi,w in enumerate(vectors):
 e=A.Engine(w)
 try:
  prices=[]
  for line in e.prices:
   if not line.startswith('info string auxprice '):continue
   pc,v,signed,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if 9<=pt<=14 else pt;assert v==w[pt] and signed==(1 if pc<16 else -1)*w[pt];assert cap==(0 if pt in (0,8,15) else w[pt]+w[base]);assert prom==(w[base+8]-w[base] if 1<=base<=6 else 0);prices.append(line)
  assert len(prices)==32;e.send('getoption');e.send('auxstate');lines=e.until(lambda x:x.startswith('info string auxstate '));options={}
  for line in lines:
   m=re.match(r'Options\[(.+?)\]\s*=\s*(.*)',line)
   if m:options[m.group(1)]=m.group(2)
  for k,v in {'Threads':'1','USI_Hash':'16','BookFile':'no_book','GenerateAllLegalMoves':'true','EnteringKingRule':'NoEnteringKing','DrawValueBlack':'0','DrawValueWhite':'0','PvInterval':'0','MultiPV':'1','USI_Ponder':'false'}.items():assert options.get(k)==v,(k,options.get(k),v)
  probes=[]
  for pypt in range(1,15):
   if pypt==8:continue
   b=A.shogi.Board(empty);b.set_piece_at(A.shogi.SQUARE_NAMES.index('5e'),A.shogi.Piece(pypt,0));b.turn=1;line=e.state(b.sfen(),[]);state=A.validate_state(line,b,w);assert state['cached']==w[A.MAP[pypt]];probes.append(state)
  rows.append({'weights':w,'prices':prices,'options':options,'probes':probes})
 finally:e.close()
 print(wi+1,len(vectors),flush=True)
(O/'result.json').write_text(json.dumps({'status':'PASS','vectors':len(vectors),'table_entries':len(vectors)*32,'state_probes':len(vectors)*13,'seconds':time.monotonic()-t0,'executable_sha256':hashlib.sha256(A.EXE.read_bytes()).hexdigest(),'rows':rows},indent=2),encoding='utf-8');print('PASS',len(vectors),time.monotonic()-t0)