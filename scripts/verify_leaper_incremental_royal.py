"""Finite semantic consumer for incremental provider; no Player/solver."""
import json,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from scripts.leaper_incremental_royal import IncrementalRoyalProvider
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.research_record import write_record,record_value
from tools.local_agent.session import record_work

def stamp():return datetime.now(timezone.utc).isoformat()
def signature(runtime):return (runtime.position,runtime.ply_count,runtime.terminal_status,tuple(runtime.history),dict(runtime.repetition_counts),runtime.search_key(),runtime.runtime_hash)

def run(input_path,out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);rows=json.loads(Path(input_path).read_text())['rows'];results=[];allcoverage=Counter();tick=time.perf_counter();total=0
    for row in rows:
        begin=stamp();c,s=make_session(row);native=NativeSemanticLegalityProvider.try_create(c);assert native is not None;m=IncrementalRoyalProvider(c,native);assert m.admitted
        rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=native,check_provider=m.in_check,availability_provider=m.has_legal_action);coverage=Counter();checks=0;walk=[]
        def verify():
            nonlocal checks,total
            pos=rt.position
            for owner in (0,1):
                value=m.in_check(pos,owner);truth=m.engine.in_check(pos,owner);assert value==truth,'check mismatch';coverage['in_check_true' if truth else 'in_check_false']+=1
            available=m.has_legal_action(pos);truth=m.engine.has_legal_action(pos);assert available==truth,'availability mismatch';coverage['available_true' if truth else 'available_false']+=1
            data=m._matching(pos)
            if data is not None:
                independent={(o,t):sum(1<<i for i,p in enumerate(pos.board) if p is not None and p.owner==o and p.current_type_id==t) for o in (0,1) for t in c.types_by_id};assert data.boards==independent;assert data.occupied==sum(1<<i for i,p in enumerate(pos.board) if p is not None)
                coverage['literal_mask_equal']+=1
            checks+=1;total+=1
        with m.installed():
            for step in range(8):
                if rt.terminal_status.is_terminal:break
                verify();actions=rt.legal_actions();before=signature(rt)
                for action in actions:
                    if total>=20000 or time.perf_counter()-tick>=240:raise RuntimeError('frozenfinitevalidationcap')
                    before_count=sum(p is not None for p in rt.position.board);side=rt.position.side_to_move
                    with rt.pushed(action):
                        verify();coverage['move_owner'+str(side)]+=1;coverage['capture' if sum(p is not None for p in rt.position.board)<before_count else 'quiet']+=1;coverage['terminal_child' if rt.terminal_status.is_terminal else 'ongoing_child']+=1
                    assert signature(rt)==before,'full runtime/TT/history/undo mismatch'
                if not actions:break
                action=actions[(3*step)%len(actions)];walk.append(record_value(action));rt.push(action)
            while rt._frames:rt.pop()
            rt.assert_balanced();assert not m.undo
        d={'id':row['id'],'status':'PASS','verified_states':checks,'coverage':dict(coverage),'metrics':m.metrics,'walk':walk,'root_record':record_value(s.to_record()),'typedIR':c.ir.to_dict(),'scope':'actualNativefrontiers/Coretruth+fullruntimeguard;finite16roots8deterministicwalksteps,notallstateproof'};write_record(out/(row['id']+'.json'),d);results.append({k:d[k] for k in ['id','status','verified_states','coverage','metrics']});allcoverage.update(coverage);end=stamp();record_work(begin,end,'validation',str(out/(row['id']+'.json')));print(row['id'],checks,m.metrics['guard_misses'],flush=True)
    summary={'status':'PASS','roots':results,'total_verified_states':total,'coverage':dict(allcoverage),'seconds':time.perf_counter()-tick,'Player_calls':0,'games':0};write_record(out/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='roots'}));return summary
