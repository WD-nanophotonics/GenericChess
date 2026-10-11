import ast,copy,sys,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core import search_runtime as r
from generic_chess.session.session import GameSession
T=r.SearchPathRuntime;compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));session=GameSession(compiled)
tree=ast.parse((ROOT/'generic_chess/core/search_runtime.py').read_text());cl=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime');node=copy.deepcopy(next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='push'))
removed=0
for n in ast.walk(node):
 if isinstance(n,ast.BoolOp) and isinstance(n.op,ast.And):
  size=len(n.values);n.values=[v for v in n.values if ast.unparse(v)!='rollback_frame.bridge_key is not None'];removed+=size-len(n.values)
assert removed==1
ns=dict(vars(r));exec(compile(ast.Module(body=[node],type_ignores=[]),'candidate','exec'),ns)
def table(rt):return frozenset(collections.Counter((h,e.identity,int(e.count)) for h,b in rt._occurrences.items() for e in b).items())
original=T.push;updated=r.RuntimeCountsSnapshot.updated;rows=[]
try:
 for arm,fn in [('original',original),('candidate',ns['push'])]:
  T.push=fn;rt=T.from_state(session.state,compiled,history_witnesses=session._search_witnesses);action=rt.legal_actions()[0];key=rt.search_key();before=table(rt)
  def fail(*args,**kwargs):raise RuntimeError('DEV_AUX key integrity fault')
  r.RuntimeCountsSnapshot.updated=fail
  try:
   try:rt.push(action)
   except RuntimeError as exc:assert 'DEV_AUX key integrity' in str(exc)
   else:raise AssertionError('fault missing')
  finally:r.RuntimeCountsSnapshot.updated=updated
  row={'arm':arm,'root_key_restored':rt.search_key()==key,'root_actual_counts_restored':table(rt)==before}
  rt.push(action);rebuilt=rt._snapshot_from_occurrences()
  clean=T.from_state(session.state,compiled,history_witnesses=session._search_witnesses);clean.push(action)
  row.update(retry_terminal=rt.terminal_status.status.value,retry_actual_count=rt.occurrence_count(),retry_snapshot_items_match_actual=rt._snapshot.items()==rebuilt.items(),retry_digest_matches_actual=rt._snapshot.digest==rebuilt.digest,retry_search_key_matches_clean=rt.search_key()==clean.search_key())
  rt.pop();clean.pop();row['post_pop_actual_restored']=table(rt)==before
  if arm=='candidate':assert all(row[k] for k in ['root_key_restored','root_actual_counts_restored','retry_snapshot_items_match_actual','retry_digest_matches_actual','retry_search_key_matches_clean','post_pop_actual_restored'])
  rows.append(row)
finally:T.push=original;r.RuntimeCountsSnapshot.updated=updated
out={'complete':True,'scope':'two private consistency controls; no TT wrong-cutoff or live fault inferred','rows':rows}
(Path(__file__).parent/'consistency.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
