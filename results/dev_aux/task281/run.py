import json,time,sys,hashlib,importlib.util
from pathlib import Path
R=Path.cwd();S=R/'.local_agent/pinned/f1ea1d38';sys.path.insert(0,str(S));sys.path.insert(1,str(R));O=R/'results/dev_aux/task281';D0=json.loads((R/'results/dev_aux/task259/declaration.json').read_bytes());B=json.loads((R/'results/dev_aux/task279/build.json').read_bytes());assert B['complete'];D=dict(task_id='281',source_commit=B['source_commit'],binary_sha256=B['binary_sha256'],roots=D0['roots'],profiles={k:v for k,v in D0['profiles'].items() if k=='unit' or k.endswith('-base')},search=dict(depth=3,time_seconds=3,tt_megabytes=1,quiescence_max_depth=0,root_window_pruning=True),deadline_seconds=120,question='Do ownfixedpublicnewRootTrueq0source/binary preserveall16prices/history/finiteD3scores+selectedPVleafs?',scope='16actualcandidatequeries, independent ownrebuild; broadernewsource notisolatedperf ablationvsoldRootFalse. No privateimmediate-win/ordering/default/UI orPRIMARYprocesses; prices/history frozen259, oracle258exacttree.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8')
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
import generic_chess._native_core as native
assert Path(native.__file__).resolve().is_relative_to(S.resolve());assert hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest()==D['binary_sha256']
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();start=time.monotonic();c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);rows=[];out=dict(complete=False,rows=rows,binary_sha256=D['binary_sha256'],source_commit=D['source_commit'])
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for f in D['roots']:
  ss=GameSession(c)
  for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
  before=(ss.state,ss.history,ss.result,ss._search_witnesses)
  for name,w in D['profiles'].items():
   P.A.guard(start+120,P.stop);e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=1);ts=time.monotonic();v=e.search(ss,SearchLimits(max_depth=3,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=True);assert before==(ss.state,ss.history,ss.result,ss._search_witnesses);rows.append(dict(root=f['id'],profile=name,weights=w,action=uci(v.action),result=record_value(v),seconds=time.monotonic()-ts));save();print(f['id'],name,v.completed_depth,v.score,uci(v.action),round(time.monotonic()-ts,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(rows),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
