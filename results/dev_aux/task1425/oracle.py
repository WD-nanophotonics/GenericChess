from pathlib import Path
import json,chess,importlib.util,time
R=Path.cwd();O=R/'results/dev_aux/task1424';O.mkdir(exist_ok=False)
roots=json.loads((R/'results/dev_aux/task1416/roots.json').read_bytes())['roots'][:16];D=json.loads((R/'results/dev_aux/task1415/study.json').read_bytes());rows=[];nodes=0;start=time.monotonic();deadline=start+180
def term(b):
 ll=sorted(m.uci() for m in b.legal_moves)
 if not ll:return dict(kind='CHECKMATE' if b.is_check() else 'STALEMATE',winner=not b.turn if b.is_check() else None)
 if b.is_insufficient_material():return dict(kind='INSUFFICIENT',winner=None)
 if b.is_repetition(3):return dict(kind='THREEFOLD_AUTO',winner=None)
 if b.halfmove_clock>=100:return dict(kind='FIFTY_AUTO',winner=None)
 return None
for root in roots:
 b=chess.Board(root['fen8']);side=b.turn;tree={}
 for u in sorted(m.uci() for m in b.legal_moves):
  b.push_uci(u);t=term(b);replylist=[None] if t else sorted(m.uci() for m in b.legal_moves);leafs=[]
  for v in replylist:
   assert time.monotonic()<deadline
   if v:b.push_uci(v)
   t=term(b);coef={p:len(b.pieces(typ,side))-len(b.pieces(typ,not side)) for p,typ in [('R',4),('N',2),('B',3)]}
   leafs.append(dict(reply=v,fen=b.fen(),termination=t,coefficients=coef,ply=1+bool(v)));nodes+=1
   if v:b.pop()
  tree[u]=leafs;b.pop()
 profiles={}
 for name,pr in D['profiles'].items():
  values={}
  for u,ls in tree.items():
   vv=[]
   for x in ls:
    t=x['termination']
    val=(0 if t['winner'] is None else (1 if t['winner']==side else -1)*(32000-x['ply'])) if t else sum(x['coefficients'][p]*pr['leaf'+p] for p in 'RNB')
    vv.append(val)
   values[u]=min(vv)
  mx=max(values.values());profiles[name]=dict(value=mx,opt=sorted(u for u,v in values.items() if v==mx),action_values=values)
 for role in ['V','U']:assert profiles[role+'_Shalf']['opt']==profiles[role+'_Sone']['opt']==profiles[role+'_Stwo']['opt']
 rows.append(dict(root=root,tree=tree,profiles=profiles))
out=dict(status='COMPLETE_D2_SCALE_ARGMAX_INVARIANT_FIRST16',roots=16,frontier_nodes=nodes,seconds=time.monotonic()-start,rows=rows,new_go=0,scope='Complete2ply exactmaterial with terminalauthority andfixed32000mate. All3positiveintegerproportionalunits preserveoptset withinroles. NotlongtermWDL/matureuniformdepthproof; tree/no heuristic/check extensions/PVS/TT.')
(O/'certificate.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='rows'})
