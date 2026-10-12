import json,time,sys,hashlib,importlib.util
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task247';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists()
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.movegen import legal_actions
from generic_chess.session.result import session_result_from_terminal
from scripts.chess_development import root_from_fen
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();assert hashlib.sha256((R/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest()==D['native_binary_sha256'];start=time.monotonic();c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);rows=[];out=dict(complete=False,rows=rows,native_binary_sha256=D['native_binary_sha256'],scope=D['scope'])
def save():out['seconds']=time.monotonic()-start;(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
try:
 for f in D['roots']:
  state=root_from_fen(f['fen'],c);ss=SimpleNamespace(compiled=c,state=state,_search_witnesses=(state.position,),result=session_result_from_terminal(state.terminal_status),legal_actions=lambda:legal_actions(state,c));before=record_value(state)
  for profile,w in D['profiles'].items():
   for depth in D['depths']:
    P.A.guard(start+90,P.stop);e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=0);t=time.monotonic();v=e.search(ss,SearchLimits(max_depth=depth,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=False);assert record_value(state)==before;rows.append(dict(root=f['name'],fen=f['fen'],profile=profile,weights=w,depth=depth,decision=record_value(v),action=uci(v.action),seconds=time.monotonic()-t));save();print(len(rows),f['name'],profile,uci(v.action),v.completed_depth,flush=True)
 out['complete']=True;save()
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
