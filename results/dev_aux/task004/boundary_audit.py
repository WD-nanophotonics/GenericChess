"""Complete-history max-ply/mate precedence and strong rollback."""
import sys,json,time,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import chess
from scripts import search_backend_comparison as b
from scripts.research_record import record_value
from scripts.reserve_refresh_diagnostic import stopped
from generic_chess.core.search_runtime import SearchPathRuntime as R
from generic_chess.core import search_runtime as rm
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.terminal import TerminalStatus
start=time.monotonic()
compiled=b.compile_ruleset_for_execution(b.build_builtin_ruleset('western_chess'))
core=b.CoreBoard({'game':'chess','setup':'start','moves':''},compiled);other=b.ChessBoard({'setup':'start','moves':''})
state=core.initial;witnesses=[state.position]
prefix='g1f3 g8f6 f3g1 f6g8'.split()*249
for index,label in enumerate(prefix):
    if index%32==0:stopped();assert time.monotonic()-start<120
    assert not state.terminal_status.is_terminal
    action=dict((b.uci(a),a) for a in legal_actions(state,compiled))[label]
    state=apply_action(state,action,compiled);witnesses.append(state.position);other.board.push_uci(label)
assert state.ply_count==996 and not state.terminal_status.is_terminal and len(state.history)==997
base_state=state;base_witnesses=tuple(witnesses);base_board=other.board.copy(stack=True)
def snapshot(runtime):
    return (runtime.position,runtime.ply_count,runtime.terminal_status,runtime.current_identity,runtime.runtime_hash,runtime._snapshot,tuple(runtime.history),runtime._history_context,tuple(runtime.repetition_counts.items()),tuple(runtime._frames))
rows=[]
for name,tail,selected,expected in (
    ('draw','g1f3 g8f6 f3g1','e7e5','max_ply'),
    ('mate','f2f3 e7e5 g2g4','d8h4','checkmate')):
    state=base_state;witnesses=list(base_witnesses);other.board=base_board.copy(stack=True)
    for label in tail.split():
        stopped();assert time.monotonic()-start<120
        action=dict((b.uci(a),a) for a in legal_actions(state,compiled))[label]
        state=apply_action(state,action,compiled);witnesses.append(state.position);other.board.push_uci(label)
    assert state.ply_count==999 and len(state.history)==1000 and not state.terminal_status.is_terminal
    core.initial=state;core.witnesses=tuple(witnesses);core.runtime=R.from_state(state,compiled,history_witnesses=core.witnesses)
    other.root_fen=other.board.fen();other.root_stack=len(other.board.move_stack);other.root_ply=other.root_stack
    assert core.snapshot()==other.snapshot() and core.evaluate()==other.evaluate() and core.terminal(0)==other.terminal(0)
    ca=core.actions();sa=other.actions();assert [x[0] for x in ca]==[x[0] for x in sa];before=snapshot(core.runtime);special_before=other.board.fen();children=[]
    for (label,action),(_,move) in zip(ca,sa):
        stopped();assert time.monotonic()-start<120
        core.push(action);other.push(move)
        try:
            assert core.snapshot()==other.snapshot();assert core.evaluate()==other.evaluate();assert core.terminal(1)==other.terminal(1)
            children.append({'move':label,'terminal':record_value(core.runtime.terminal_status),'score':core.terminal(1),'history_length':len(core.runtime.history)})
        finally:other.pop();core.pop()
        assert snapshot(core.runtime)==before and other.board.fen()==special_before
    chosen=next(x for x in children if x['move']==selected)
    assert chosen['terminal']['status']==expected
    # Post-history-update failure, not a pre-push flag.
    actual=rm.terminal_from_search_runtime
    def fail(runtime,checkpoint=None):raise RuntimeError('DEV_AUX terminal failure after full child history update')
    rm.terminal_from_search_runtime=fail
    try:
        try:core.push(dict(ca)[selected])
        except RuntimeError as exc:assert 'DEV_AUX terminal failure' in str(exc)
        else:raise AssertionError('failure not reached')
        assert snapshot(core.runtime)==before
    finally:rm.terminal_from_search_runtime=actual
    core.push(dict(ca)[selected]);core.pop();assert snapshot(core.runtime)==before
    left=b.minimal_ab(core,1,seconds=10,node_limit=4096,trace=True);right=b.minimal_ab(other,1,seconds=10,node_limit=4096,trace=True)
    for key in ('move','score','reason','work','trace_sha256'):assert left[key]==right[key],(name,key)
    assert snapshot(core.runtime)==before and core.restored() and other.restored()
    rows.append({'case':name,'parent_plies':999,'parent_history':1000,'witnesses':len(witnesses),'legal_children':len(children),'selected_terminal':chosen,'children':children,'strong_restoration':True,'terminal_failure_restoration':True,'core':{k:v for k,v in left.items() if 'seconds' not in k},'specialized':{k:v for k,v in right.items() if 'seconds' not in k}})
report={'complete':True,'scope':'two synthetic fully replayed999ply Chess parents; no timing/native claim','prefix_plies':996,'prefix_sha256':hashlib.sha256(' '.join(prefix).encode()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'scripts/search_backend_comparison.py').read_bytes()).hexdigest(),'rows':rows}
(Path(__file__).parent/'boundary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps([{'case':row['case'],'children':row['legal_children'],'selected':row['selected_terminal'],'best':row['core']['move'],'score':row['core']['score'],'strong_restoration':True} for row in rows],indent=2))
