"""Independent exhaustive compact-tree replay and exact directional sensitivity."""
import json,time,hashlib,math,random,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task347';assert not (O/'audit.json').exists();start=time.monotonic();D=json.loads((R/'results/dev_aux/task346/declaration.json').read_bytes());T=[json.loads(l) for l in (R/'results/dev_aux/task346/trees.jsonl').read_bytes().splitlines()];EX=json.loads((R/'results/dev_aux/task340/execution.json').read_bytes());records=[json.loads(l) for l in (R/'results/dev_aux/task340/games.jsonl').read_bytes().splitlines()];sp=importlib.util.spec_from_file_location('codec347',R/'results/dev_aux/task308/codec.py');C=importlib.util.module_from_spec(sp);sp.loader.exec_module(C);sp2=importlib.util.spec_from_file_location('p347',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp2);sp2.loader.exec_module(P);rng=random.Random(2026102446);directions=[]
while len(directions)<32:
 d=[rng.randrange(-1,2) for _ in range(4)]
 if any(d) and d not in directions:directions.append(d)
results=[];replayed_leaves=edges=0
for t in T:
 f=D['roots'][t['root']];b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 assert b.fen()==f['expected_fen'];actor=b.turn;hh=hashlib.sha256();nodes=t['nodes'];visits=0
 def terminal():return b.is_checkmate() or b.is_stalemate() or b.is_fivefold_repetition()
 def replay(ix,ply):
  global replayed_leaves,edges
  z=nodes[ix]
  if 'children'not in z:
   assert ply==3 or terminal();oo=b.outcome(claim_draw=False) if terminal() else None;leaf={'t':0 if oo.winner is None else (100000000-ply)*(1 if oo.winner==actor else -1)} if oo is not None else {'v':[len(b.pieces(k,actor))-len(b.pieces(k,not actor)) for k in range(1,6)]};assert z==leaf;hh.update(json.dumps([b.fen(),[m.uci() for m in b.move_stack],leaf],separators=(',',':')).encode()+b'\n');replayed_leaves+=1
   if replayed_leaves%2048==0:P.A.guard(start+300,P.stop)
   return
  assert not terminal() and ply<3 and z['ply']==ply and z['op']==('max' if b.turn==actor else 'min');actual={m.uci() for m in b.legal_moves};assert len(z['children'])==len(actual) and {u for u,child in z['children']}==actual
  for u,child in z['children']:assert 0<=child<ix;b.push_uci(u);replay(child,ply+1);b.pop();edges+=1
 replay(t['root_index'],0);assert hh.hexdigest()==t['path_fen_history_leaf_sha256']
 def response(w):
  # base and both axis derivatives plus predeclared mixed directional derivatives.
  vals=[];left=[];right=[];mixed=[]
  for z in nodes:
   if 't'in z:vals.append(z['t']);left.append([0]*5);right.append([0]*5);mixed.append([0]*32)
   elif 'v'in z:v=z['v'];vals.append(sum(w[k]*x for k,x in zip('PNBRQ',v)));left.append(v);right.append(v);mixed.append([sum(a*x for a,x in zip(d,v[1:])) for d in directions])
   else:
    op=max if z['op']=='max' else min;counter=min if z['op']=='max' else max;v=op(vals[ch] for u,ch in z['children']);active=[ch for u,ch in z['children'] if vals[ch]==v];vals.append(v);left.append([counter(left[ch][j] for ch in active) for j in range(5)]);right.append([op(right[ch][j] for ch in active) for j in range(5)]);mixed.append([op(mixed[ch][j] for ch in active) for j in range(32)])
  ix=t['root_index'];return vals[ix],left[ix],right[ix],mixed[ix]
 for name in EX['unique_profiles']:
  w=EX['profiles'][name];row=next(z for z in records if z['profile']==name and z['root']==t['root'] and z['color'] is True);rec=row['search_records'][0];assert rec['ply']==0 and rec['player']=='candidate';raw=C.decode(rec['result']);base,lo,hi,mx=response(w);assert raw['score']==base;pvboard=b.copy(stack=True)
  for a in raw['principal_variation']:
   fr=a['from_square'];to=a['to_square'];u=chess.square_name(chess.square(fr['file'],fr['rank']))+chess.square_name(chess.square(to['file'],to['rank']))+(a.get('promotion_target_id')or'').lower();assert chess.Move.from_uci(u) in pvboard.legal_moves;pvboard.push_uci(u)
  tv=pvboard.is_checkmate() or pvboard.is_stalemate() or pvboard.is_fivefold_repetition();gradient=[0]*5 if tv else [len(pvboard.pieces(k,actor))-len(pvboard.pieces(k,not actor)) for k in range(1,6)];actual=[sum(a*x for a,x in zip(d,gradient[1:])) for d in directions];results.append(dict(root=t['root'],profile=name,weights=w,score=base,PV_vector=gradient,left=lo,right=hi,axis_nondifferentiable=sum(a!=b for a,b in zip(lo,hi)),PV_axis_mismatch=sum(g!=a or g!=b for g,a,b in zip(gradient,lo,hi)),mixed_directions=mx,PV_mixed_predictions=actual,mixed_mismatches=sum(a!=b for a,b in zip(mx,actual))))
 print(t['root'],replayed_leaves,len(results),round(time.monotonic()-start,3),flush=True)
out=dict(complete=True,replayed_leaves=replayed_leaves,edges=edges,cases=len(results),axischecks=len(results)*5,mixeddirectionchecks=len(results)*32,directions=directions,axis_nondifferentiable=sum(z['axis_nondifferentiable'] for z in results),PV_axis_mismatches=sum(z['PV_axis_mismatch'] for z in results),PV_mixed_mismatches=sum(z['mixed_mismatches'] for z in results),details=results,seconds=time.monotonic()-start,proof='Forcontinuouslinearleafvalues exactone-sidedderivative propagatesoverBASEACTIVEties: max right=max/minleft, minright=min/maxleft; strictnonactivebranches remaininactivefor sufficientlysmall epsilon. Terminalderivative0; fullfiniteD3tree/mathonly, notclaimedNativefractionalprice orselectivecpgradient. Mixeddirectionlambda>=0 usesmax/minactive similarly. Axisagreementnotfull differentiability.',scope='All48actualNativebasequeries reused/frozen6prices8exposedroots. Fullreplayallpaths verifies pooledleafprojection only; scalarintegerfinite-epsilon secondarycheck348. No universalTD impossibility; literature intentionallyallows arbitrarytie branch approximation butthisdoesnotmakeit a true directional derivative.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('details','directions')},indent=2))