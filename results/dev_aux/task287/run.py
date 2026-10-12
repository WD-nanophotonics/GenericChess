import json,time,sys,copy,hashlib,importlib.util,os
from pathlib import Path
R=Path.cwd();S=R/'.local_agent/pinned/f1ea1d38';sys.path.insert(0,str(S));sys.path.insert(1,str(R))
import chess
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
import generic_chess._native_core as native
O=R/'results/dev_aux/task287';O.mkdir(exist_ok=False)
old=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes());build=json.loads((R/'results/dev_aux/task279/build.json').read_bytes())
D=dict(task_id='287',question='Do four cost-pilot paired games using exact D3 purematerial search expose a feasible semantic/unit comparison without mature selective heuristics?',roots=old['roots'][:2],profiles={k:old['profiles'][k] for k in ('semantic','unit')},cells=[dict(root=i,color=color) for i in range(2) for color in (True,False)],cap=48,depth=3,tt_megabytes=1,root_window_pruning=True,quiescence_max_depth=0,per_call_seconds=3,whole_fuse_seconds=240,source_commit=build['source_commit'],binary_sha256=build['binary_sha256'],scope='Four pilot games on old exposed training roots, not independent holdout; no new seeds/prices/generations/human fitting. Fresh cold engine each player query, full Core/chess history and legal sets. Fixed-depth calls must finish D3; failures retained, no automatic retry. Finite mate-by48 separate from quantity/unknown; backend comparison is overall reference, not equal-work control.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8')
assert Path(native.__file__).resolve().is_relative_to(S.resolve());assert hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()==D['binary_sha256']
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
P=load('p',R/'results/dev_aux/task166/run.py');C=load('codec',R/'results/dev_aux/task253/codec.py');P.stop();start=time.monotonic();deadline=start+D['whole_fuse_seconds'];c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);cache={};rows=[];out=dict(complete=False,calls=rows,source_commit=D['source_commit'],binary_sha256=D['binary_sha256'])
def sig(ss,b):return ss.state,ss.history,ss.result,ss._search_witnesses,b.fen(),tuple(m.uci() for m in b.move_stack)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for i,f in enumerate(D['roots']):
  ss=GameSession(c);b=P.board(f)
  for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
  cache[i]=(ss,b,sig(ss,b))
 with (O/'journal.jsonl').open('xb') as journal:
  for cell in D['cells']:
   ss0,b0,signature=cache[cell['root']];ss=copy.copy(ss0);b=b0.copy(stack=True);actions=[];searches=[];ts=time.monotonic()
   for ply in range(D['cap']):
    P.A.guard(deadline,P.stop)
    if b.is_game_over(claim_draw=False):break
    aa={uci(a):a for a in ss.legal_actions()};assert sorted(aa)==sorted(m.uci() for m in b.legal_moves)
    name='semantic' if b.turn==cell['color'] else 'unit';w=D['profiles'][name]
    e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=1);before=sig(ss,b);vt=time.monotonic();v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=True);raw=record_value(v);assert sig(ss,b)==before
    searches.append(dict(ply=ply,profile=name,weights=w,root_fen=b.fen(),full_history=[m.uci() for m in b.move_stack],result=C.encode(raw),wall_seconds=time.monotonic()-vt))
    assert v.completed_depth==3 and not v.used_fallback,(v.completed_depth,v.termination_reason)
    m=chess.Move.from_uci(uci(v.action));assert m.uci() in aa;ss.submit(aa[m.uci()]);b.push(m);actions.append(m.uci())
   assert sig(ss0,b0)==signature
   outcome=b.outcome(claim_draw=False);tag='unknown' if outcome is None else 'draw' if outcome.winner is None else 'win' if outcome.winner==cell['color'] else 'loss'
   row=dict(**cell,actions=actions,search_records=searches,final_fen=b.fen(),score=P.G.score(b,cell['color'],len(actions),D['cap']),outcome=tag,terminal=record_value(ss.result),wall_seconds=time.monotonic()-ts)
   line=C.canonical(dict(sequence=len(rows),sha256=hashlib.sha256(C.canonical(row)).hexdigest(),record=row))+b'\n';journal.write(line);journal.flush();os.fsync(journal.fileno());rows.append(row);save();print(cell,tag,len(actions),round(time.monotonic()-ts,3),flush=True)
 out['complete']=True;out['actual_games']=len(rows);out['actual_queries']=sum(len(z['search_records']) for z in rows);save();print('COMPLETE',out['actual_games'],out['actual_queries'],out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise