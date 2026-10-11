"""Predeclared private-table candidate bridge/nested/collision cells."""
import ast,copy,sys,json,time
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tests/product')]
from generic_chess.core import search_runtime as r
from generic_chess.core.transition import apply_action
from test_native_history import _cycle_ruleset,_session_at_ply
from scripts.reserve_refresh_diagnostic import stopped
T=r.SearchPathRuntime
tree=ast.parse((ROOT/'generic_chess/core/search_runtime.py').read_text())
cl=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime')
node=copy.deepcopy(next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='push'));removed=0
for n in ast.walk(node):
 if isinstance(n,ast.BoolOp) and isinstance(n.op,ast.And):
  before=len(n.values);n.values=[v for v in n.values if ast.unparse(v)!='rollback_frame.bridge_key is not None'];removed+=before-len(n.values)
assert removed==1
ns=dict(vars(r));exec(compile(ast.Module(body=[node],type_ignores=[]),'private_candidate','exec'),ns)
original=T.push;candidate=ns['push'];updated=r.RuntimeCountsSnapshot.updated;terminal=r.terminal_from_search_runtime
compiled=_cycle_ruleset();session=_session_at_ply(compiled,3);root=session.state;start=time.monotonic()
def actual_table(rt):return frozenset((h,e.identity,e.count) for h,bucket in rt._occurrences.items() for e in bucket)
def snapshot(rt):
 return (rt.position,rt.ply_count,rt.terminal_status,rt.current_identity,rt.runtime_hash,rt._snapshot,tuple(rt.history),rt._history_context,actual_table(rt),frozenset(rt._opaque_imported_keys),frozenset(rt._history_aliases.items()),len(rt._frames),rt._legal_cache,tuple(rt._bindings.items()))
rows=[]
try:
 for arm,fn in [('original',original),('candidate',candidate)]:
  T.push=fn
  for context in ['complete','opaque','nested','nested_collision']:
   for seam in ['snapshot','terminal']:
    stopped();assert time.monotonic()-start<60
    kwargs={}
    state=root;public=root
    if context=='complete':kwargs['history_witnesses']=session._search_witnesses
    else:state=replace(root,history=())
    if context=='nested_collision':kwargs['hash_override']=r.RuntimeHash(0,0)
    rt=T.from_state(state,compiled,**kwargs)
    nested=context.startswith('nested')
    if nested:
     a=rt.legal_actions()[0];rt.push(a);public=apply_action(public,a,compiled)
    action=rt.legal_actions()[0];expected=apply_action(public,action,compiled);before=snapshot(rt)
    observed={}
    def fail(*args,**kwargs):
     frame=rt._frames[-1];observed.update(bridge=frame.bridge_key is not None,child_added=frame.child_occurrence_added,history_length=len(rt.history))
     raise RuntimeError('DEV_AUX declared lifecycle fault')
    if seam=='snapshot':r.RuntimeCountsSnapshot.updated=fail
    else:r.terminal_from_search_runtime=fail
    try:
     try:rt.push(action)
     except RuntimeError as exc:assert 'DEV_AUX declared' in str(exc)
     else:raise AssertionError('fault not reached')
    finally:r.RuntimeCountsSnapshot.updated=updated;r.terminal_from_search_runtime=terminal
    restored=snapshot(rt)==before;after_fault=actual_table(rt)
    rt.push(action);child_equal=rt.position==expected.position and rt.terminal_status==expected.terminal_status;rt.pop()
    row={'arm':arm,'context':context,'seam':seam,'fault':observed,'restored_after_fault':restored,'private_entry_count_before':len(before[8]),'private_entry_count_after':len(after_fault),'ordinary_child_matches_public':child_equal,'restored_after_retry_pop':snapshot(rt)==before}
    if arm=='candidate':assert restored and child_equal and row['restored_after_retry_pop']
    rows.append(row)
    if nested:rt.pop()
    rt.assert_balanced()
finally:T.push=original;r.RuntimeCountsSnapshot.updated=updated;r.terminal_from_search_runtime=terminal
report={'complete':True,'scope':'16 declared private candidate lifecycle cells; forced collision and opaque/nested contexts; no generic-domain or deployment proof','rows':rows}
(Path(__file__).parent/'lifecycle.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
