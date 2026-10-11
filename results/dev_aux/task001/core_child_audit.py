"""Fresh Core-only finite child/undo audit using the pinned probe functions."""
import ast,collections,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core import search_runtime as r
from generic_chess.core.semantic_executor import SemanticEngine as E
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.quiescence import noisy_child,enemy_board_count,material_inventory
from scripts.research_record import record_value
T=r.SearchPathRuntime
probe=ROOT/'.local_agent/availability-core-20261011/representation_outcome.py'
timer=ROOT/'.local_agent/availability-core-20261011/physical_outcome.py'
c=SimpleNamespace(iteration=2,qlevel=1)
ns={'Counter':collections.Counter,'c':c,'push':T._push_impl,'pop':T.pop,'classify':noisy_child,'stack':[],'pending':{},'totals':collections.Counter(),'peak':0}
functions=[x for x in ast.parse(probe.read_text()).body if isinstance(x,ast.FunctionDef) and x.name in ('pushed','consume','classified','popped')]
exec(compile(ast.Module(body=functions,type_ignores=[]),str(probe),'exec'),ns)
p=type("Probe",(),{})();p.__dict__=ns
import time
stage_ns={'time':time,'p':p,'calls':[],'outside':collections.Counter()}
node=next(n for n in ast.parse(timer.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='stage')
exec(compile(ast.Module(body=[node],type_ignores=[]),str(timer),'exec'),stage_ns)
targets=[(E,'_transition','transition'),(E,'_trial_child_if_s3_legal','trial'),(E,'in_check','attack'),(E,'has_legal_action','availability'),(T,'legal_actions','runtime_frontier'),(r,'terminal_from_search_runtime','terminal'),(r,'_semantic_component_diff_hash','component_diff'),(r.RuntimeCountsSnapshot,'updated','snapshot'),(r.RuntimeHistoryContext,'append','context')]
originals=[getattr(o,a) for o,a,_ in targets]
def install(measured):
    T._push_impl=ns['pushed'] if measured else ns['push'];T.pop=ns['popped'] if measured else ns['pop']
    for (o,a,name),old in zip(targets,originals):
        fn=stage_ns['stage'](name,old) if measured else old
        setattr(o,a,staticmethod(fn) if a=='append' else fn)
def reset():
    ns.update(stack=[],pending={},totals=collections.Counter(),peak=0)
    stage_ns.update(calls=[],outside=collections.Counter())
def snapshot(rt):
    return (rt.position,rt.ply_count,rt.terminal_status,rt.runtime_hash,tuple(rt.history),rt._snapshot,rt._history_context,tuple(rt.repetition_counts),len(rt._frames))
def matches_action(a,uci):
    def square(s):return chr(ord('a')+s.file)+str(s.rank+1)
    return hasattr(a,'from_square') and square(a.from_square)+square(a.to_square)==uci
compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
session=GameSession(compiled)
for uci in 'e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 d2d3 f8c5'.split():
    choices=[a for a in session.legal_actions() if matches_action(a,uci)]
    assert len(choices)==1,(uci,len(choices));session.submit(choices[0])
root=session.state
report={'scope':'fresh finite Core-only primitive controls, not original four Native-hybrid D2 searches, no timing comparison','rows':[],'aborts':[]}
for measured in (False,True):
    reset();rt=T(root,compiled,history_witnesses=session._search_history_witnesses)
    actions=rt.legal_actions();before=snapshot(rt);side=rt.position.side_to_move;enemies=enemy_board_count(rt.position,side);inventory=material_inventory(rt.position)
    children=[];install(measured)
    try:
        for a in actions:
            rt.push(a)
            assert len(rt._frames)==1
            classified=ns['classified'] if measured else noisy_child
            included=classified(a,rt.state,side,enemies,inventory,lambda:rt.in_check(1-side))
            children.append({'action':record_value(a),'position_key':str(r._full_runtime_hash(rt.position,compiled)),'terminal':record_value(rt.terminal_status),'included':included,'history_length':len(rt.history)})
            rt.pop();assert snapshot(rt)==before
        rt.assert_balanced();assert not ns['stack'] and not ns['pending'] and not stage_ns['calls']
    finally:install(False)
    report['rows'].append({'measured':measured,'children':children,'metrics':[{ 'iteration':i,'qphase':q,'outcome':o,'metric':k,'value':v} for (i,q,o,k),v in sorted(ns['totals'].items())]})
assert report['rows'][0]['children']==report['rows'][1]['children']
# Abort at four progressively later push seams; the exact original public push
# rollback must restore position/history/counts/context even with probe installed.
for target in ('transition','component_diff','snapshot','terminal'):
    reset();rt=T(root,compiled,history_witnesses=session._search_history_witnesses);action=rt.legal_actions()[0];before=snapshot(rt);install(True)
    obj,attr,_=next(x for x in targets if x[2]==target)
    real=getattr(obj,attr)
    def fail(*args,**kwargs):raise RuntimeError('DEV_AUX injected '+target)
    setattr(obj,attr,stage_ns['stage'](target,fail))
    try:
        try:rt.push(action)
        except RuntimeError as exc:assert 'DEV_AUX injected' in str(exc)
        else:raise AssertionError('injection did not execute')
        assert snapshot(rt)==before and not ns['stack'] and not ns['pending'] and not stage_ns['calls']
        report['aborts'].append({'seam':target,'restored':True,'classified_children':sum(v for (i,q,o,k),v in ns['totals'].items() if k=='children'),'outside_recorded':dict(stage_ns['outside'])})
    finally:install(False)
report['source_hashes']={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in (probe,timer)}
report['limitation']='Push-phase measurements of aborted attempts are discarded because no frame gets registered in pending. This is acceptable for the declared completed-D2 scope but cannot establish an all-attempt cost decomposition.'
(Path(__file__).parent/'core_child_audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'fresh_children_each':len(report['rows'][0]['children']),'plain_instrumented_equal':True,'abort_seams':[x['seam'] for x in report['aborts']],'all_restored':True},indent=2))
