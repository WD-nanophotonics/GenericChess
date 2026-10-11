"""Audit original root-projection oracle against actual private occurrences."""
import ast,sys,time,json,collections,hashlib
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from scripts import search_backend_comparison as b
from generic_chess.core import search_runtime as r
from generic_chess.core.semantic_executor import SemanticEngine as E
from scripts.reserve_refresh_diagnostic import stopped
T=r.SearchPathRuntime
oldpath=ROOT/'results/dev_aux/task001/core_child_audit.py'
node=next(x for x in ast.parse(oldpath.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='snapshot');oldns={}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(oldpath),'exec'),oldns);old_snapshot=oldns['snapshot']
probe=ROOT/'.local_agent/availability-core-20261011/representation_outcome.py';timer=ROOT/'.local_agent/availability-core-20261011/physical_outcome.py'
c=SimpleNamespace(iteration=2,qlevel=1)
ns={'Counter':collections.Counter,'c':c,'push':T._push_impl,'pop':T.pop,'classify':None,'stack':[],'pending':{},'totals':collections.Counter(),'peak':0}
nodes=[x for x in ast.parse(probe.read_text()).body if isinstance(x,ast.FunctionDef) and x.name in ('pushed','consume','popped')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(probe),'exec'),ns)
p=type('Probe',(),{})();p.__dict__=ns;stage_ns={'time':time,'p':p,'calls':[],'outside':collections.Counter()}
node=next(x for x in ast.parse(timer.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='stage')
exec(compile(ast.Module(body=[node],type_ignores=[]),str(timer),'exec'),stage_ns)
targets=[(E,'_transition','transition'),(r,'_semantic_component_diff_hash','component_diff'),(r.RuntimeCountsSnapshot,'updated','snapshot'),(r,'terminal_from_search_runtime','terminal')]
originals=[getattr(obj,attr) for obj,attr,name in targets]
def table(rt):
    return frozenset((runtime_hash,entry.identity,entry.count) for runtime_hash,bucket in rt._occurrences.items() for entry in bucket)
def naive(rt):
    return old_snapshot(rt)+(frozenset(rt.repetition_counts.items()),)
def strong(rt):
    return naive(rt)+(table(rt),rt.current_identity)
def install(active):
    T._push_impl=ns['pushed'] if active else ns['push'];T.pop=ns['popped'] if active else ns['pop']
    for (obj,attr,name),fn in zip(targets,originals):setattr(obj,attr,stage_ns['stage'](name,fn) if active else fn)
def reset():
    ns.update(stack=[],pending={},totals=collections.Counter(),peak=0)
    stage_ns.update(calls=[],outside=collections.Counter())
start=time.monotonic();compiled=b.compile_ruleset_for_execution(b.build_builtin_ruleset('western_chess'));board=b.CoreBoard(b.CASES[0],compiled)
def fresh():return T.from_state(board.initial,compiled,history_witnesses=board.witnesses)
rt=fresh();rt.legal_actions();before_old=old_snapshot(rt);before_naive=naive(rt);before_strong=strong(rt)
rt._occurrence_add(rt.current_identity,rt.runtime_hash)
sentinel={'original_missed':old_snapshot(rt)==before_old,'naive_values_missed':naive(rt)==before_naive,'actual_table_detected':strong(rt)!=before_strong,'root_actual_count_after':rt.occurrence_count()}
assert all(sentinel[k] for k in ('original_missed','naive_values_missed','actual_table_detected'))
rt._occurrence_remove(rt.current_identity,rt.runtime_hash);assert strong(rt)==before_strong
rows=[]
for measured in (False,True):
    for target in ('transition','component_diff','snapshot','terminal'):
        stopped();assert time.monotonic()-start<60
        reset();rt=fresh();action=rt.legal_actions()[0];old=old_snapshot(rt);nv=naive(rt);st=strong(rt);bt=table(rt);install(measured)
        obj,attr,name=next(x for x in targets if x[2]==target)
        def fail(*args,**kwargs):raise RuntimeError('DEV_AUX declared '+target+' failure')
        setattr(obj,attr,stage_ns['stage'](name,fail) if measured else fail)
        try:
            try:rt.push(action)
            except RuntimeError as exc:assert 'DEV_AUX declared' in str(exc)
            else:raise AssertionError('injection not reached')
            after=table(rt)
            row={'measured':measured,'seam':target,'original_claim_passed':old_snapshot(rt)==old,'naive_values_passed':naive(rt)==nv,'actual_table_restored':after==bt,'strong_restored':strong(rt)==st,'before_entries':len(bt),'after_entries':len(after),'added_entry_counts':[count for h,identity,count in after-bt],'removed_entry_counts':[count for h,identity,count in bt-after],'probe_empty':not ns['stack'] and not ns['pending'] and not stage_ns['calls'],'frames':len(rt._frames),'public_projection_unchanged':rt.repetition_counts==dict(board.initial.repetition_counts)}
            assert row['probe_empty'] and row['frames']==0;rows.append(row)
        finally:install(False)
report={'complete':True,'scope':'strong private-table oracle; source-pinned injected exceptions, not a natural cancellation or live allocation failure frequency claim','original_oracle_sha256':hashlib.sha256(ast.dump(next(x for x in ast.parse(oldpath.read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='snapshot'),include_attributes=False).encode()).hexdigest(),'sentinel':sentinel,'rows':rows}
(Path(__file__).parent/'oracle.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
