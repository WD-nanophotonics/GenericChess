import json,sys,time,importlib.util,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task259';assert not (O/'result.json').exists()
D=json.loads((R/'results/dev_aux/task258/declaration.json').read_bytes());old=json.loads((R/'results/dev_aux/task236/declaration.json').read_bytes());profiles={'unit':D['unit'],**{k:v for k,v in old['profiles'].items() if k.endswith('-base')}}
for key in 'NBRQ':
 for v in (52,832):w=dict(D['unit']);w[key]=v;profiles[f'{key}-{v}']=w
D2=dict(task_id='259',question='ActualNative fullhistory D2/D3 control on same4capture roots, original3initialprices+unit+all8coordinatecontrasts.',roots=D['roots'],profiles=profiles,depths=[2,3],tt_megabytes=0,root_window_pruning=False,quiescence_max_depth=0,max_time_seconds=3,native_binary_sha256=old['native_binary_sha256'],deadline_seconds=420,scope='96 actualcold Nativequeries with unchangedprice/flags; oraclecontrol nottraining/holdout, samefullhistory. Actualcanonicaltie maydifferfromlexicaloracle, preserveargmax notonlywinner. Compactcodec islosslessrecordonly. Estimated<=90s batch; nohourjob.')
(O/'declaration.json').write_text(json.dumps(D2,indent=2),encoding='utf-8')
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
s=importlib.util.spec_from_file_location('codec',R/'results/dev_aux/task253/codec.py');C=importlib.util.module_from_spec(s);s.loader.exec_module(C)
assert hashlib.sha256((R/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest()==D2['native_binary_sha256'];start=time.monotonic();c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);rows=[];out=dict(complete=False,rows=rows)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',C.encode(out))
try:
 for f in D2['roots']:
  ss=GameSession(c)
  for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
  before=(ss.state,ss.history,ss.result,ss._search_witnesses)
  for name,w in profiles.items():
   for depth in (2,3):
    P.A.guard(start+420,P.stop);e=SemanticSearchEngine(c,n,board_values=w,hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=0);ts=time.monotonic();v=e.search(ss,SearchLimits(max_depth=depth,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=False);assert before==(ss.state,ss.history,ss.result,ss._search_witnesses);rows.append(dict(root=f['id'],profile=name,weights=w,depth=depth,action=uci(v.action),result=record_value(v),wall_seconds=time.monotonic()-ts));save()
  print(f['id'],len(rows),round(time.monotonic()-start,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(rows),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
