"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task1066';O.mkdir(exist_ok=False)
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((R/'results/dev_aux/task1041/plan.json').read_bytes())

import random
BINARY=R/'.local_agent/alignment-order/fairy-order-toggle.exe'
def inside(s):return chess.square_file(s)<5 and chess.square_rank(s)<5
def legal5(b):return sorted(m.uci() for m in b.legal_moves if inside(m.from_square) and inside(m.to_square))
def fen5(b):
 rows=[]
 for rank in range(4,-1,-1):
  text='';empty=0
  for file in range(5):
   pc=b.piece_at(chess.square(file,rank))
   if pc:
    if empty:text+=str(empty);empty=0
    text+=pc.symbol()
   else:empty+=1
  if empty:text+=str(empty)
  rows.append(text)
 return '/'.join(rows)+(' w ' if b.turn else ' b ')+'- - '+str(b.halfmove_clock)+' '+str(b.fullmove_number)
def term5(b):
 legal=legal5(b)
 if not legal:return dict(kind='CHECKMATE' if b.is_check() else 'STALEMATE',winner=not b.turn if b.is_check() else None)
 if len(b.piece_map())==2:return dict(kind='KING_ONLY',winner=None)
 if b.is_repetition(3):return dict(kind='THREEFOLD_AUTO',winner=None)
 if b.halfmove_clock>=100:return dict(kind='FIFTY_MOVE_AUTO',winner=None)
 return None
def config5(e,w,out):
 line=' '.join(k.lower()+':'+str(w[k]) for k in 'PNBRQ');config=out/'variant.ini';config.write_text('[aux_mini:gardner]\npieceValueMg = '+line+'\npieceValueEg = '+line+'\n',encoding='utf-8')
 for name,value in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(config)),('UCI_Variant','aux_mini')]:
  e.send('setoption name '+name+' value '+str(value));reply=e.ready()
  if name=='UCI_Variant':assert any(x.startswith('info string variant aux_mini files 5 ranks 5 ') for x in reply);ack=[x for x in reply if x.startswith('info string DEV_AUX alignment ')];assert len(ack)==1
 f=ack[0].split();assert int(f[4])==e.alignment;assert {int(x.split(':')[0]):list(map(int,x.split(':')[1:])) for x in f[5:]}==({i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')} if e.alignment else {i+1:[a,b] for i,(a,b) in enumerate(zip([126,781,825,1276,2538],[208,854,915,1380,2682]))})
 probes=[]
 for piece in 'NR':
  e.send('position fen 4k/5/2'+piece+'2/5/K4 w - - 0 1');e.send('eval');r=e.ready();v=[x for x in r if x.startswith('Final evaluation')];assert len(v)==1;measured=float(v[0].split()[2]);assert abs(measured-w[piece]/208)<=.011;probes.append(dict(piece=piece,measured=measured,expected=w[piece]/208,raw=r))
 return dict(raw=ack[0],probes=probes,weights=w)




import ast
plan=json.loads((R/'results/dev_aux/task1065/plan.json').read_bytes());binary=R/'.local_agent/leaf-scale41/fairy-leaf-scale.exe';start=time.monotonic();deadline=start+120;rows=[];acks=[];evals=[];treecurves=[];controls=[];error=None
rule=dict(chess=chess)
for file,names in [('task1016/qualify.py',['inside','legal5','fen5','term5']),('task1016/audit_pilot.py',['reachable','attacked','literal'])]:
 tree=ast.parse((R/'results/dev_aux'/file).read_text(encoding='utf-8-sig'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'literal_scope','exec'),rule)
for scale in [None,1,2,4]:
 e=M.start(binary,3,deadline,P.stop)
 try:
  w=dict(P=208,N=90,B=208,R=419,Q=208,K=0);ack=config5(e,w,O);leafack=None
  if scale is not None:
   e.send(f'devauxleafnr {90*scale} {419*scale}');raw=e.ready();leafack=next(x for x in raw if x.startswith('info string DEV_AUX leafR '));assert leafack==f'info string DEV_AUX leafR {419*scale} leafN {90*scale} nativeN 90 captureN 90 nativeR 419 captureR 419'
  acks.append(dict(scale=scale,native=ack,leafack=leafack))
  for case in plan['cases']:
   e.send('ucinewgame');e.ready();b=chess.Board(case['fen8'])
   for u in case['history']:assert u in rule['literal'](b);b.push_uci(u)
   e.send('position fen '+fen5(b.root())+' moves '+' '.join(m.uci() for m in b.move_stack));e.send('go nodes 64');lines=e.until(lambda x:x.startswith('bestmove '));move=lines[-1].split()[1];assert move in rule['literal'](b);e.ready();PVs=[];last=None
   for line in lines[:-1]:
    f=line.split()
    if 'tbhits' in f:assert int(f[f.index('tbhits')+1])==0
    if 'pv' in f:
     p=f[f.index('pv')+1:];bb=b.copy()
     for u in p:assert u in rule['literal'](bb);bb.push_uci(u)
     PVs.append(p)
    if 'score' in f:i=f.index('score');last=dict(kind=f[i+1],value=int(f[i+2]),depth=int(f[f.index('depth')+1]),nodes=int(f[f.index('nodes')+1]))
   rows.append(dict(case=case['id'],scale=scale,move=move,last=last,printed_PVs=PVs,raw=lines))
   if scale is None:continue
   color=b.turn;children=[]
   for first in rule['literal'](b):
    b.push_uci(first);t=term5(b);replies=[None] if t else rule['literal'](b);values=[]
    for second in replies:
     if second:b.push_uci(second)
     t=term5(b);n=len(b.pieces(2,color))-len(b.pieces(2,not color));r=len(b.pieces(4,color))-len(b.pieces(4,not color))
     if t:val=0 if t['winner'] is None else 1000000 if t['winner']==color else -1000000
     else:
      e.send('position fen '+fen5(b.root())+' moves '+' '.join(m.uci() for m in b.move_stack));e.send('eval');raw=e.ready();line=next(x for x in raw if x.startswith('Final evaluation'));actual=float(line.split()[2]);stm_val=(n*90+r*419)*scale*(1 if b.turn==color else -1);assert abs(actual-stm_val/208)<=.011
      evals.append(dict(case=case['id'],scale=scale,first=first,second=second,fen=b.fen(),history=[m.uci() for m in b.move_stack],n=n,r=r,expected_stm=stm_val,actual_cp_pawn=actual,raw=raw));val=(n*90+r*419)*scale
     values.append(val)
     if second:b.pop()
    b.pop();children.append(dict(move=first,value=min(values)))
   best=max(x['value'] for x in children);treecurves.append(dict(case=case['id'],scale=scale,all_best=[x['move'] for x in children if x['value']==best],children=children))
 finally:e.close()
old=json.loads((R/'results/dev_aux/task1057/result.json').read_bytes())
for row in rows:
 if row['scale'] is not None:continue
 prior=next(x for x in old['rows'] if x['case']['id']==row['case'] and x['native']==419 and x['leaf'] is None);assert all(row[k]==prior[k] for k in ['move','last','printed_PVs']);controls.append(dict(case=row['case'],exact_default=True))
for case in plan['cases']:
 curves=[x for x in treecurves if x['case']==case['id']];assert len(set(tuple(x['all_best']) for x in curves))==1
(O/'result.json').write_text(json.dumps(dict(status='PASS_ACTUAL_LEAF_READBACK_AND_FIXEDTREE_SCALE_INVARIANCE',actual_go=len(rows),eval_calls=len(evals),rows=rows,acks=acks,controls=controls,treecurves=treecurves,seconds=time.monotonic()-start),indent=2),encoding='utf-8');(O/'leaf_evals.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in evals),encoding='utf-8');print([(x['case'],x['scale'],x['move'],x['last']) for x in rows]);print('actualevals',len(evals))
