"""Capped actual random-opponent mate-speed pilot, frozen before any scores."""
import json,time,sys,math,os,random,hashlib
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task313'));import run as Q
O=R/'results/dev_aux/task320'
def run_game(e,weights,f,color,seed,limit,deadline,configure,cap=48,journal=None):
 probes,ack=configure(e,weights);b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 assert b.fen()==f.get('expected_fen',f.get('fen'));rng=random.Random(seed);actions=[];searches=[];random_choices=[];ts=time.monotonic()
 for ply in range(cap):
  Q.P.A.guard(deadline,Q.P.stop)
  if b.is_game_over(claim_draw=False):break
  if b.turn==color:
   e.send('ucinewgame');e.ready();m,meta=Q.P.M.M.search(e,b.copy(stack=True),deadline,Q.P.stop,limit=limit);searches.append(dict(ply=ply,record=meta))
   if journal is not None:journal.write(json.dumps(dict(event='query',ply=ply,record=meta),separators=(',',':'))+'\n');journal.flush()
  else:
   legal=sorted(b.legal_moves,key=lambda m:m.uci());ix=rng.randrange(len(legal));m=legal[ix];random_choices.append(dict(ply=ply,index=ix,legal_count=len(legal),move=m.uci()))
  assert m in b.legal_moves;b.push(m);actions.append(m.uci())
 oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if oo is None or oo.winner is None else 1 if oo.winner==color else -1;reward=Fraction(49-len(actions),48) if kind=='CHECKMATE' and sign==1 else Fraction(-1) if kind=='CHECKMATE' and sign==-1 else Fraction(0)
 return dict(weights=weights,color=color,seed=seed,actions=actions,search_records=searches,random_choices=random_choices,final_fen=b.fen(),termination=kind,winner=None if oo is None else oo.winner,finite_mate_sign=sign if kind=='CHECKMATE' else 0,fitness=str(reward),seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack)
def execute():
 O.mkdir(exist_ok=False);Q.P.stop();roots0=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes())['roots'];roots=[z for z in roots0 if z['phase']=='TRAIN'];assert len(roots)==2;prof=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes())['profiles'];D=dict(task_id='320',question='Can actualmate speed vs uniformrandom provide price discrimination before any small learning?',roots=roots,profiles={k:prof[k] for k in ('unit','semantic','s703-base')},random_seeds=[2026102301,2026102302],colors=[True,False],node_limit=1024,cap=48,fitness='Black/Whiteagentwin (49-actualhalfply)/48; agentloss-1; draw/unknown0FINITEgoal, not ultimateWDL.',opponent='UniformALLlegalmoves sortedUCI; randrange once/opponentply. Commonseeds same RNGsequence but legalsets can differ; not identical opponentactions.',cold='Freshprocessperprice; configure/readbackpergame; ucinewgamepereachcandidatego; fullhistoryalways.',binary_sha256=Q.sha(R/'.local_agent/alignment-order/fairy-order-toggle.exe'),initials='3existingprices unit/semantic/oldrandom; nohumanparameters/newseed/rootselection.',games=24,whole_fuse_seconds=600,scope='Changedopponent+truefastmateobjective vs old269unitsearchfitness. Pilotonly, nofit/adoption/deepercap. 2oldTRAINroots, no independence/generalconfidence.')
 Q.write(O/'declaration.json',D);start=time.monotonic();deadline=start+600;env=dict(P=Q.P,O=O,deadline=deadline,math=math);exec(compile((R/'results/dev_aux/task267/configure.py').read_text(),'configure267','exec'),env);configure=env['configure'];rows=[];out=dict(complete=False,calls=rows);e=None
 try:
  with (O/'queries.jsonl').open('x',encoding='utf-8') as journal:
   for name,w in D['profiles'].items():
    e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
    try:
     for ri,f in enumerate(roots):
      for color in D['colors']:
       for seed in D['random_seeds']:
        row=run_game(e,w,f,color,seed,1024,deadline,configure,journal=journal);rows.append(dict(name=name,root=ri,**row));Q.write(O/'result.json',out);journal.flush();os.fsync(journal.fileno())
    finally:e.close();e=None
    print(name,len(rows),[(r['termination'],len(r['actions']),r['fitness']) for r in rows if r['name']==name],flush=True)
  out['complete']=True
 except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));raise
 finally:
  if e:e.close()
  out['seconds']=time.monotonic()-start;Q.write(O/'result.json',out)
if __name__=='__main__':execute()