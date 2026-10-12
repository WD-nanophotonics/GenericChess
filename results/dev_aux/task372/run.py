import sys,json,time
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
O=R/'results/dev_aux/task372';O.mkdir(exist_ok=True);fixtures=[{'name':'ordinaryfourfold','initial':'4k4/9/9/9/9/9/9/9/4K4 b - 1','cycle':['5i4i','5a4a','4i5i','4a5a']*3,'expected':{'kind':'fourfold_draw','winner':None}},{'name':'perpetualBlackchecker','initial':'4k4/9/4R4/9/9/9/9/9/8K w - 1','cycle':['5a4a','5c4c','4a5a','4c5c']*3,'expected':{'kind':'perpetual_check_loss','winner':1}},{'name':'sourcecuratedmate','initial':'ln1ks1rnl/1+B1sg4/3p2p1b/p1p2p1pp/1P1P5/PpR1p1PPP/2N1PP1S1/4G3L/L1SKG2N1 b GP 65','cycle':['G*7b'],'expected':{'kind':'checkmate','winner':0}}];w=[0]+[90]*7+[0]+[90]*6+[0];rows=[];t0=time.monotonic();e=A.Engine(w)
try:
 for f in fixtures:
  b=A.shogi.Board(f['initial']);keys=[G.key(b)];checks=[b.is_check()];movers=[];history=[]
  for i in range(len(f['cycle'])+1):
   term=G.terminal(b,keys,checks,movers);expect=f['expected'] if i==len(f['cycle']) else None;assert term==expect,(f['name'],i,term,expect);line=e.state(f['initial'],history);state=A.validate_state(line,b,w);e.send('moves');e.send('auxstate');lines=e.until(lambda x:x.startswith('info string auxstate '));ls=[x for x in lines[:-1] if not x.startswith('info ')];assert len(ls)==1;assert set(ls[0].split())==set(m.usi() for m in b.legal_moves)
   rows.append({'fixture':f['name'],'ply':i,'history':list(history),'independent_terminal':term,'diagnostic_repetition_lookback16':state['repetition'],'state':state,'legal_count':len(ls[0].split())})
   if i<len(f['cycle']):
    u=f['cycle'][i];m=A.shogi.Move.from_usi(u);assert m in b.legal_moves;movers.append(b.turn);b.push(m);history.append(u);keys.append(G.key(b));checks.append(b.is_check())
finally:e.close()
(O/'result.json').write_text(json.dumps({'status':'PASS','seconds':time.monotonic()-t0,'fixtures':fixtures,'rows':rows,'scope':'Actual goal usesexactfourfoldfullhistory+continuouschecker loss, not diagnostic defaultlookback16 repetition enum. Engine andPython legalsets agree; curatedSFEN hasunknownpre-SFENhistory andisnotnewindependentreachablecertificate.'},indent=2),encoding='utf-8');print('PASS',len(rows),time.monotonic()-t0)