"""Finite independent comparison of full Runtime state/history for signature memo."""
import json,time
from pathlib import Path
from scripts.leaper_signature_memo import SignatureRuntime,BASE,COUNTERS,reset
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.leaper_relative_history_pilot import record_interval
from scripts.research_record import write_record
from tools.local_agent import session

def projection(r):
    return (r.position,r.ply_count,r.terminal_status,r.runtime_hash,r.current_identity,
            r._snapshot,r._history_context,tuple(r.history),r.search_key(),r.legal_actions())

def run(inputs,out):
    out=Path(out);assert not out.exists();out.mkdir(parents=True);rows=json.loads(Path(inputs).read_text())['rows'];reset();result=[];transitions=0;tick=time.perf_counter()
    def bound():
        assert time.perf_counter()-tick<600,"600secondvalidationcap"
        assert transitions+2<=25000,"25000directRuntimepushcap"
        from tools.local_agent.common import read_json
        f=read_json(Path(".local_agent/rollout.json"));assert not any(f.get(k) for k in ("user_paused","stopped","research_stopped","stop_requested")),"userstop"
    for row in rows:
        bound();began=session.now().isoformat();c,s=make_session(row)
        left=BASE.from_state(s.state,c,history_witnesses=s._search_witnesses,use_plain_leaper_local_hash=True)
        right=SignatureRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,use_plain_leaper_local_hash=True)
        assert right._signature_admitted
        checks=0
        for step in range(8):
            before=projection(left);assert before==projection(right)
            for action in left.legal_actions():
                bound()
                with left.pushed(action),right.pushed(action):
                    assert projection(left)==projection(right)
                    checks+=1;transitions+=2
                assert before==projection(left)==projection(right)
            actions=left.legal_actions()
            if not actions or left.terminal_status.is_terminal:break
            action=actions[(3*step)%len(actions)];left.push(action);right.push(action);transitions+=2
            if left.terminal_status.is_terminal:assert projection(left)==projection(right);break
        while left.depth:left.pop();right.pop()
        left.assert_balanced();right.assert_balanced();assert projection(left)==projection(right)
        result.append({'id':row['id'],'children_verified':checks,'status':'PASS','runtimes':COUNTERS['runtimes'],'cache':dict(COUNTERS)})
        write_record(out/'rows.json',result);record_interval(began,session.now().isoformat(),'validation',str(out/'rows.json')+':'+row['id'],out)
    # Abort after each original checkpoint; signature memo inserts NO checkpoint.
    c,s=make_session(rows[0]);prototype=BASE.from_state(s.state,c,history_witnesses=s._search_witnesses)
    actions=list(prototype.legal_actions())[:3];aborts=[]
    for action in actions:
        for stop in range(12):
            bound();pair=[]
            for cls in (BASE,SignatureRuntime):
                r=cls.from_state(s.state,c,history_witnesses=s._search_witnesses,use_plain_leaper_local_hash=True);r.legal_actions();before=projection(r);calls=[0]
                def check():
                    calls[0]+=1
                    if calls[0]==stop+1:raise RuntimeError('checkpoint-stop')
                try:r.push(action,checkpoint=check);status='RETURNED';r.pop()
                except RuntimeError as e:assert str(e)=='checkpoint-stop';status='ABORTED'
                assert projection(r)==before;r.assert_balanced();pair.append((status,calls[0]))
            assert pair[0]==pair[1];aborts.append({'action':str(action),'checkpoint':stop+1,'result':pair[0]})
    summary={'status':'PASS','rows':len(rows),'paired_child_comparisons':sum(r['children_verified'] for r in result),'direct_runtime_transitions':transitions,'abort_controls':len(aborts),'abort_push_attempts':len(aborts)*2,'counts_scope':'explicit Runtime pushes,not internally generated Coretrialtransitions','cache':dict(COUNTERS),'new_Player_calls':0,'limits':'Finite sharedCore equivalence,not all-domainproof or strength. Imported completehistory/typed identity preserved,not quotiented.'}
    write_record(out/'aborts.json',aborts);write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True);return summary
if __name__=='__main__':
    import sys;run(sys.argv[1],sys.argv[2])
