import json,time,sys,hashlib,importlib.util,dataclasses
from pathlib import Path
R=Path.cwd();S=R/'.local_agent/pinned/f1ea1d38';sys.path.insert(0,str(S));sys.path.insert(1,str(R));O=R/'results/dev_aux/task295';O.mkdir(exist_ok=False)
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
import generic_chess._native_core as native
old=json.loads((R/'results/dev_aux/task289/declaration.json').read_bytes());D=dict(task_id='295',question='What actualfixedD4 rootcost/completion differsfromD3before consideringanyfullgameextension?',roots=old['roots'],profiles={k:old['profiles'][k] for k in ('semantic','unit')},depth=4,per_call_seconds=8,whole_fuse_seconds=150,tt_megabytes=1,root_window_pruning=True,repetition_limit=5,binary_sha256=old['binary_sha256'],source_commit=old['source_commit'],scope='Eightrootqueriesonly. Changed premise versus failed294 3s gamepilot: D4rootcost measured withone declared8s ceiling, allincomplete outcomes kept/no automaticretry. No48plygamegrowth; estimated<=64s. Outputrecord savedbeforecompletionassert; failed294 discardedpartialtelemetryacknowledged.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');assert Path(native.__file__).resolve().is_relative_to(S.resolve()) and hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()==D['binary_sha256']
def load(name,path):
 sp=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
P=load('p',R/'results/dev_aux/task166/run.py');C=load('codec',R/'results/dev_aux/task253/codec.py');P.stop();start=time.monotonic();c=compile_semantic_ruleset(dataclasses.replace(build_western_chess_ruleset(),repetition_limit=5));n=compile_native_semantic_rules(c);rows=[];out=dict(complete=False,rows=rows)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for i,f in enumerate(D['roots']):
  ss=GameSession(c)
  for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
  before=(ss.state,ss.history,ss.result,ss._search_witnesses)
  for name,w in D['profiles'].items():
   P.A.guard(start+D['whole_fuse_seconds'],P.stop);e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=1);ts=time.monotonic();v=e.search(ss,SearchLimits(max_depth=4,max_nodes=None,max_time_seconds=8,quiescence_max_depth=0),root_window_pruning=True);assert before==(ss.state,ss.history,ss.result,ss._search_witnesses);rows.append(dict(root=i,profile=name,weights=w,action=uci(v.action),result=C.encode(record_value(v)),wall_seconds=time.monotonic()-ts));save();print(i,name,v.completed_depth,v.score,uci(v.action),round(time.monotonic()-ts,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(rows),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise