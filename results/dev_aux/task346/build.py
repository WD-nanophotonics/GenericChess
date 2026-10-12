"""Compact exactD3 trees; intern only equal material terminal leaf projections."""
import json,time,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task346';assert not (O/'declaration.json').exists();D0=json.loads((R/'results/dev_aux/task340/declaration.json').read_bytes());EX=json.loads((R/'results/dev_aux/task340/execution.json').read_bytes());D=dict(task_id='346',question='Do learnedendpoint andnewroot conditions retain unit-gridPV gradient counterexamples?',roots=D0['roots'],profiles=EX['profiles'],unique_profiles=EX['unique_profiles'],depth=3,terminal='CHECKMATE/STALEMATE/FIVEFOLD only, signed1e8-ply; noinsufficient/no-progressinternal likepinnedf1ea.',projection='Leafonly intern identicalPNBRQ(rootturn) featurevectors oridenticalterminalvalues. Internalnodes notdeduplicated; completelegalmoveedgepaths retain all threeply trajectories/history. A leaf isfinitevalue only, never reused as a searchstate, TT orlegality object.',cost='8rootfulltree expectationold258235698leaf8.843s, declared300sfuse; no newenginequeries/horizon/learning. Incrementalinfo whether TDLeaf arbitraryPV gradient persists at ALLsixnewfrozenprices beyond oldunitcapturecohort.',source_endpoint_sha256=EX['endpoint_sha256'],scope='All8developmentroots exposed beforethisdiagnostic, no newholdout/adoption. ExactfiniteD3 material derivatives, notmatureselectivecp gradient. Axisderivatives mayexist withoutfullmultidifferentiability; oldfails preserved.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');sp=importlib.util.spec_from_file_location('p346',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);P.stop();start=time.monotonic();total_leaves=0;total_edges=0;results=[]
with (O/'trees.jsonl').open('x',encoding='utf-8') as journal:
 for ri,f in enumerate(D['roots']):
  b=chess.Board(f['initial_fen'])
  for u in f['history']:b.push_uci(u)
  assert b.fen()==f['expected_fen'];actor=b.turn;nodes=[];pool={};leaves=edges=0;paths=hashlib.sha256()
  def terminal():return b.is_checkmate() or b.is_stalemate() or b.is_fivefold_repetition()
  def visit(ply):
   global total_leaves,total_edges
   nonlocal_dummy=None
   if ply==3 or terminal():
    total_leaves+=1
    if total_leaves%2048==0:P.A.guard(start+300,P.stop)
    oo=b.outcome(claim_draw=False) if terminal() else None;leaf={'t':0 if oo.winner is None else (100000000-ply)*(1 if oo.winner==actor else -1)} if oo is not None else {'v':[len(b.pieces(k,actor))-len(b.pieces(k,not actor)) for k in range(1,6)]};key=('t',leaf['t']) if 't'in leaf else ('v',*leaf['v']);paths.update(json.dumps([b.fen(),[m.uci() for m in b.move_stack],leaf],separators=(',',':')).encode()+b'\n')
    if key not in pool:pool[key]=len(nodes);nodes.append(leaf)
    return pool[key]
   children=[]
   for m in sorted(b.legal_moves,key=lambda m:m.uci()):b.push(m);idx=visit(ply+1);b.pop();children.append([m.uci(),idx]);total_edges+=1
   assert children;idx=len(nodes);nodes.append(dict(op='max' if b.turn==actor else 'min',ply=ply,children=children));return idx
  before=total_leaves;before_edges=total_edges;idx=visit(0);row=dict(root=ri,root_index=idx,nodes=nodes,actual_leaf_visits=total_leaves-before,actual_edges=total_edges-before_edges,leaf_projection_nodes=len(pool),path_fen_history_leaf_sha256=paths.hexdigest());journal.write(json.dumps(row,separators=(',',':'))+'\n');journal.flush();results.append({k:v for k,v in row.items() if k!='nodes'});print(ri,row['actual_leaf_visits'],len(nodes),round(time.monotonic()-start,3),flush=True)
(O/'result.json').write_text(json.dumps(dict(complete=True,roots=results,actual_leaves=total_leaves,actual_edges=total_edges,seconds=time.monotonic()-start,trees_sha256=hashlib.sha256((O/'trees.jsonl').read_bytes()).hexdigest()),indent=2),encoding='utf-8')