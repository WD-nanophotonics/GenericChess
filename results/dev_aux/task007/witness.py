"""Declared observable repetition witness; private AST candidate, product unchanged."""
import ast,sys,json,copy,hashlib
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from scripts import search_backend_comparison as b
from generic_chess.core import search_runtime as r
from generic_chess.core.transition import apply_action
from scripts.reserve_refresh_diagnostic import stopped
T=r.SearchPathRuntime
source=ROOT/'generic_chess/core/search_runtime.py'
tree=ast.parse(source.read_text())
cl=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime')
original_node=next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='push')
node=copy.deepcopy(original_node);removed=[]
for n in ast.walk(node):
 if isinstance(n,ast.BoolOp) and isinstance(n.op,ast.And):
  keep=[]
  for value in n.values:
   if ast.unparse(value)=='rollback_frame.bridge_key is not None':removed.append(ast.unparse(value))
   else:keep.append(value)
  n.values=keep
assert len(removed)==1
ns=dict(vars(r));exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
candidate=ns['push'];original=T.push;updated=r.RuntimeCountsSnapshot.updated
compiled=b.compile_ruleset_for_execution(replace(b.build_builtin_ruleset('western_chess'),repetition_limit=2))
from generic_chess.session.session import GameSession
from types import SimpleNamespace
session=GameSession(compiled);board=SimpleNamespace(initial=session.state,witnesses=session._search_witnesses)
def table(rt):return frozenset((h,e.identity,e.count) for h,bucket in rt._occurrences.items() for e in bucket)
rows=[]
try:
 for label,fn in [('original',original),('candidate',candidate)]:
  stopped();T.push=fn
  rt=T.from_state(board.initial,compiled,history_witnesses=board.witnesses)
  action=rt.legal_actions()[0];expected=apply_action(board.initial,action,compiled);before=table(rt)
  def fail(*args,**kwargs):raise MemoryError('DEV_AUX declared snapshot allocation failure')
  r.RuntimeCountsSnapshot.updated=fail
  try:
   try:rt.push(action)
   except MemoryError as exc:assert 'DEV_AUX declared' in str(exc)
   else:raise AssertionError('fault not reached')
  finally:r.RuntimeCountsSnapshot.updated=updated
  restored=table(rt)==before
  rt.push(action)
  row={'arm':label,'action':b.uci(action),'private_restored_after_fault':restored,'retry_count':rt.occurrence_count(),'runtime_terminal':rt.terminal_status.status.value,'public_terminal':expected.terminal_status.status.value,'retry_board_equal':rt.position==expected.position,'retry_history_length':len(rt.history),'public_history_length':len(expected.history)}
  rt.pop();row['private_restored_after_retry_pop']=table(rt)==before
  normal=T.from_state(board.initial,compiled,history_witnesses=board.witnesses);before_normal=table(normal)
  normal.push(action);row['normal_terminal']=normal.terminal_status.status.value;normal.pop();row['normal_private_restored']=table(normal)==before_normal
  assert row['normal_private_restored'] and row['normal_terminal']==row['public_terminal']
  if label=='candidate':assert restored and row['private_restored_after_retry_pop'] and row['runtime_terminal']==row['public_terminal']
  else:assert not restored and row['runtime_terminal']=='repetition' and row['public_terminal']=='ongoing'
  rows.append(row)
finally:T.push=original;r.RuntimeCountsSnapshot.updated=updated
report={'complete':True,'product_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'candidate_only_removed':removed,'scope':'one declared snapshot MemoryError, supported repetition_limit2; no natural failure-frequency or production deployment claim','rows':rows}
(Path(__file__).parent/'witness.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
