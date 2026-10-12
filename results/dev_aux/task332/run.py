"""Frozen endpoints against fixed unit SEARCH; no further training."""
import json,time,sys,math,os,importlib.util
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();sp=importlib.util.spec_from_file_location('G332',R/'results/dev_aux/task320/run.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G);Q=G.Q;O=R/'results/dev_aux/task332'
def execute():
 O.mkdir(exist_ok=False);Q.P.stop();E=json.loads((R/'results/dev_aux/task322/endpoints.json').read_bytes());assert E['complete'];D0=json.loads((R/'results/dev_aux/task322/declaration.json').read_bytes());old=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes());roots=old['roots'][2:];profiles={**{f'initial-{k}':w for k,w in D0['initials'].items()},**{f'endpoint-{k}':v['weights'] for k,v in E['endpoints'].items()}};unique={};aliases={}
 for name,w in profiles.items():
  kk=tuple(w[k] for k in 'PNBRQK')
  if kk not in unique:unique[kk]=name
  aliases[name]=unique[kk]
 unit={k:208 for k in 'PNBRQ'};unit['K']=0
 D=dict(task_id='332',source_task='331 PREPARED only',question='Do all frozen randommate endpoints transfer against fixed unit SEARCH?',roots=roots,profiles=profiles,unique_profiles=list(unique.values()),aliases=aliases,opponent_weights=unit,colors=[True,False],node_limit=1024,cap=48,games=20,whole_fuse_seconds=600,estimated_seconds=30,endpoint_sha256=Q.sha(R/'results/dev_aux/task322/endpoints.json'),binary_sha256=Q.sha(R/'.local_agent/alignment-order/fairy-order-toggle.exe'),fitness='true finite CHECKMATE win (49-ply)/48; loss -1; other 0. Quantity counts all nonking actors separately, no price labels.',scope='Old development roots exposed; no new holdout, selection, generations, human fitting or unmodified Stockfish claim. Fresh candidate process per distinct price; opponent process only ever unit. Cold TT each go/full initial FEN+history, both players readbacks per game. Thread1/Hash16/NNUEfalse/noTB/materialmode3.')
 Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+600;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task272/configure.py').read_text(encoding='utf-8'),'configure272','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,calls=rows);eu=None
 try:
  eu=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
  with (O/'queries.jsonl').open('x',encoding='utf-8') as journal:
   for name in unique.values():
    w=profiles[name];ec=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
    try:
     for ri,f in enumerate(roots):
      for color in D['colors']:
       probes,ack=configure(ec,w);up,ua=configure(eu,unit);b=Q.P.board(f);actions=[];queries=[];ts=time.monotonic();journal.write(json.dumps(dict(event='game_start',profile=name,root=ri,color=color,weights=w),separators=(',',':'))+'\n');journal.flush()
       for ply in range(48):
        Q.P.A.guard(deadline,Q.P.stop)
        if b.is_game_over(claim_draw=False):break
        player='candidate' if b.turn==color else 'unit';e=ec if player=='candidate' else eu;e.send('ucinewgame');e.ready();m,meta=Q.P.M.M.search(e,b.copy(stack=True),deadline,Q.P.stop,limit=1024);q=dict(ply=ply,player=player,record=meta);queries.append(q);journal.write(json.dumps(dict(event='query',**q),separators=(',',':'))+'\n');journal.flush();assert m in b.legal_moves;b.push(m);actions.append(m.uci())
       oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if kind!='CHECKMATE' else 1 if oo.winner==color else -1;reward=Fraction(49-len(actions),48) if sign==1 else Fraction(-1) if sign==-1 else Fraction(0);count=lambda c:sum(len(b.pieces(k,c)) for k in range(1,6));row=dict(profile=name,root=ri,weights=w,color=color,actions=actions,search_records=queries,final_fen=b.fen(),termination=kind,winner=None if oo is None else oo.winner,finite_mate_sign=sign,fitness=str(reward),quantity_difference=count(color)-count(not color),seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack,opponent_leaf_probes=up,opponent_table_ack=ua);rows.append(row);Q.write(O/'result.json',out);journal.flush();os.fsync(journal.fileno())
    finally:ec.close()
    print(name,len(rows),round(time.monotonic()-start,3),flush=True)
  out['complete']=True
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
 finally:
  if eu:eu.close()
  out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)
if __name__=='__main__':execute()