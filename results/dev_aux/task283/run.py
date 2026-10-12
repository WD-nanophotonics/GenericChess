import json,time,sys,hashlib,importlib.util
from pathlib import Path
R=Path.cwd();S=R/'.local_agent/pinned/f1ea1d38';sys.path.insert(0,str(S));sys.path.insert(1,str(R));O=R/'results/dev_aux/task283';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists()
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
import generic_chess._native_core as native
assert Path(native.__file__).resolve().is_relative_to(S.resolve()) and hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()==D['binary_sha256'];s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
s=importlib.util.spec_from_file_location('codec',R/'results/dev_aux/task253/codec.py');C=importlib.util.module_from_spec(s);s.loader.exec_module(C);P.stop();start=time.monotonic();c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);rows=[];out=dict(complete=False,rows=rows)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for f in D['roots']:
  ss=GameSession(c)
  for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
  before=(ss.state,ss.history,ss.result,ss._search_witnesses)
  for name,w in D['profiles'].items():
   cell=len(rows)//4;order=D['arms'][cell%4:]+D['arms'][:cell%4]
   for arm in order:
    P.A.guard(start+300,P.stop);e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=arm['tt']);ts=time.monotonic();v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=arm['root']);assert before==(ss.state,ss.history,ss.result,ss._search_witnesses);rows.append(dict(root=f['id'],profile=name,weights=w,arm=arm,action=uci(v.action),result=C.encode(record_value(v)),seconds=time.monotonic()-ts));save()
   print(f['id'],name,len(rows),round(time.monotonic()-start,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(rows),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
