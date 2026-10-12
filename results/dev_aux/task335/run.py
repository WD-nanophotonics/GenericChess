"""Quantity-capped mature search pilot; algorithmic roots, no human labels."""
import json,time,sys,math,os,importlib.util,random,hashlib
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();sp=importlib.util.spec_from_file_location('G335',R/'results/dev_aux/task320/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task335'
def root(seed,phase,index):
 b=chess.Board();rng=random.Random(seed);history=[]
 for _ in range(20):
  assert not b.is_game_over(claim_draw=False),'predeclared root terminal: preserve failure, no replacement';legal=sorted(b.legal_moves,key=lambda m:m.uci());m=legal[rng.randrange(len(legal))];b.push(m);history.append(m.uci())
 assert not b.is_game_over(claim_draw=False)
 return dict(seed=seed,phase=phase,index=index,initial_fen=chess.STARTING_FEN,history=history,expected_fen=b.fen())
def run_game(ec,eu,w,unit,f,color,deadline,configure,journal,cap=24,limit=1024):
 probes,ack=configure(ec,w);up,ua=configure(eu,unit);b=Q.P.board(f);actions=[];queries=[];ts=time.monotonic()
 for ply in range(cap):
  Q.P.A.guard(deadline,Q.P.stop)
  if b.is_game_over(claim_draw=False):break
  player='candidate' if b.turn==color else 'unit';e=ec if player=='candidate' else eu;e.send('ucinewgame');e.ready();m,meta=Q.P.M.M.search(e,b.copy(stack=True),deadline,Q.P.stop,limit=limit);q=dict(ply=ply,player=player,record=meta);queries.append(q);journal.write(json.dumps(dict(event='query',**q),separators=(',',':'))+'\n');journal.flush();assert m in b.legal_moves;b.push(m);actions.append(m.uci())
 oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if kind!='CHECKMATE' else 1 if oo.winner==color else -1;cnt=lambda c:sum(len(b.pieces(k,c)) for k in range(1,6));quantity=cnt(color)-cnt(not color);goal=F(sign*32) if sign else F(quantity,15)
 return dict(weights=w,color=color,actions=actions,search_records=queries,final_fen=b.fen(),termination=kind,winner=None if oo is None else oo.winner,finite_mate_sign=sign,fitness=str(goal),quantity_difference=quantity,seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack,opponent_leaf_probes=up,opponent_table_ack=ua)
def execute():
 O.mkdir(exist_ok=False);Q.P.stop();old=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes());initials={k:old['profiles'][k] for k in ('unit','semantic','s703-base')};train=[root(2026102400+i,'train',i) for i in range(8)];dev=[root(2026102480+i,'development',i) for i in range(8)];D=dict(task_id='335',question='Can cheap capped quantity reward discriminate mature material policies over algorithmic roots?',train_roots=train,development_roots=dev,root_algorithm='Standardinitialboard; sortedUCI uniformlegal randrange seed; exactly20halfply, failclosed ifterminal, no outcome/price/human screening or replacement.',initials=initials,unit=initials['unit'],colors=[True,False],node_limit=1024,cap=24,goal='CHECKMATE candidate ±32; otherwise unweighted nonking actor count difference/15, including ordinary draws. Mate/sign/rawquantity reported separately, not finalWDL.',games=48,whole_fuse_seconds=600,binary_sha256=Q.sha(R/'.local_agent/alignment-order/fairy-order-toggle.exe'),scope='Changed goal+root distribution versus322randommate/old269mate-search. Fresh same-code/same-node bothplayers, mode3 fixedselectivity and candidate leaf/SEE/order prices. 16 deterministiccells/price, no statisticalconfidence; development outcomes not consulted in pilot/learning.')
 Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+600;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(encoding='utf-8'),'configure272','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,calls=rows);eu=None
 try:
  eu=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
  with (O/'queries.jsonl').open('x',encoding='utf-8') as journal:
   for name,w in initials.items():
    ec=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
    try:
     for ri,f in enumerate(train):
      for color in D['colors']:
       journal.write(json.dumps(dict(event='game_start',name=name,root=ri,color=color,weights=w),separators=(',',':'))+'\n');journal.flush();row=dict(name=name,root=ri,**run_game(ec,eu,w,D['unit'],f,color,deadline,configure,journal));rows.append(row)
    finally:ec.close()
    Q.write(O/'result.json',out);print(name,len(rows),str(sum(F(z['fitness']) for z in rows if z['name']==name)/16),round(time.monotonic()-start,3),flush=True)
  out['complete']=True
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
 finally:
  if eu:eu.close()
  out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)
if __name__=='__main__':execute()