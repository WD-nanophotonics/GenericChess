"""A protected tempo shuttle gives a NOT-WIN certificate, not exact DRAW."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_safe_support import rule
from scripts.leaper_delayed_capture_witness import snapshot,replay
from scripts.leaper_rule_coordinates import physical_action
from tools.local_agent.common import write_json


def apply(c,node,key):
    z=replay(c,node['record']);raw=next(a for a in node['legal_actions']if physical_action(a,4)==tuple(key))
    z.submit(L.match_action(z,raw));return snapshot(z)


def measure(plan,data,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter();deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=plan['resources']['absolute_analysis_validation_cap_seconds'])
    parent=load(data/'entry-square.json.gz');row=next(r for r in parent['rows']if r['mask']==22)
    rr=rule(4,22,5,[6,15,4,0]);reg=dict(plan=plan,rule=L.ruleset_to_dict(rr,include_metadata=True),source_sha256=L.sha(Path(__file__)),parent_sha256=L.sha(data/'entry-square.json.gz'),deadline=deadline.isoformat())
    write_json(output/'registration.json',reg);c=L.compile_rule(rr)
    trace=[next(x['node']for x in row['children']if x['action_key']==plan['literal_control'][0])]
    for k in plan['literal_control'][1:]:
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original tempo-policy deadline')
        trace.append(apply(c,trace[-1],k));write_json(output/'latest-target.json',trace[-1])
    m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,trace=trace,new_Core_child_applications=5,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);return reg,m


def load(path):
    from scripts.verify_leaper_delayed_capture import load as impl
    return impl(path)


def qualify(reg,m,data):
    rr=rule(4,22,5,[6,15,4,0]);assert reg['rule']==L.ruleset_to_dict(rr,include_metadata=True), 'exact parity/tempo scope required'
    c=L.compile_rule(rr);p=reg['plan']['policy']
    assert p==dict(entry_after_any_White_first_move=['B',0,1,None],BlackKing_fixed_square=4,B_shuttle_squares=[1,9],B_shuttle_move='Dabbaba b1-b3 andback',White_A_checkerboard_parity=0,BlackKing_and_shuttle_parity=1)
    assert all((dx+dy)%2==0 for dx,dy in L.offsets(22))
    assert (0,2)in L.offsets(5)and(0,-2)in L.offsets(5)and(1,0)in L.offsets(5)
    king=4;targets=(1,9)
    assert all((t%4+t//4)%2==1 and max(abs(t%4-king%4),abs(t//4-king//4))==1 for t in targets)
    assert (king%4+king//4)%2==1
    parent=load(data/'entry-square.json.gz');assert L.sha(data/'entry-square.json.gz')==reg['parent_sha256']
    row=next(r for r in parent['rows']if r['mask']==22);assert row['root']==snapshot(L.GameSession(c))
    keys=[physical_action(a,4)for a in row['root']['legal_actions']]
    assert len(row['children'])==len(keys)==8 and {tuple(x['action_key'])for x in row['children']}==set(keys)
    entry_checked=0
    for child in row['children']:
        node=child['node'];assert node==snapshot(replay(c,node['record']))
        assert node==apply(c,row['root'],child['action_key'])
        assert node['result']['status']=='ongoing'and node['state']['position']['side_to_move']==1
        assert ('B',0,1,None)in {physical_action(a,4)for a in node['legal_actions']}, 'uniform entry policy missing'
        board=node['state']['position']['board'];a=next(i for i,x in enumerate(board)if x and x['current_type_id']=='A')
        assert (a%4+a//4)%2==0 and board[king]['owner']==1 and board[king]['current_type_id']=='K'
        entry_checked+=1
    trace=m['trace'];assert len(trace)==6
    expected_first=next(x['node']for x in row['children']if x['action_key']==reg['plan']['literal_control'][0])
    assert trace[0]==expected_first
    for i,key in enumerate(reg['plan']['literal_control'][1:]):assert trace[i+1]==apply(c,trace[i],key)
    assert trace[-1]['state']['ply_count']==6
    assert trace[-1]['result']['status']=='repetition'and trace[-1]['result']['winner']is None
    assert m['new_Core_child_applications']==5 and m['ended_at']<=reg['deadline']
    return dict(status='PASS',all_white_first_entries_checked=entry_checked,certificate='NOT_WHITE_WIN',exact_White_WDL='UNKNOWN within {-1,0}; cooperative drawtrace does not prove White lowerbound',literal_trace_result='repetitionDRAWply6',new_Core_child_applications=5,
        induction='WhiteA remains even, BlackKing/shuttle targetsodd. WhiteA cannot attack them; WhiteKing cannot capture or occupy King-protectedb1/b3. Target empty, Dabbabashuttle always legal while BlackKing cannot be checked. Under exactdrawending/nootherwin rules White cannot forceWIN. FirstBentry is legal afterall8Whitechoices.',
        scope='Current matchedA22/B5n4root anddeclaredplainparity/protection argument. Not allrootsDRAW, learnedpriceconservation or a competing wholegraph solver. Five explicit newtargetmoves plus retainedallfirstfrontiers; all replayvalidationcostseparate.',new_Player_queries=0,new_graph_or_solver_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    try:
        reg,m=measure(json.loads(a.plan.read_text(encoding='utf-8-sig')),a.data,a.output);q=qualify(reg,m,a.data);write_json(a.output/'qualification.json',q);print(json.dumps(q))
    except Exception as exc:write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc)));raise


if __name__=='__main__':main()
