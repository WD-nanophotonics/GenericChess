"""One preregistered common-root orbit square with independent local geometry.

Only one ply and its literal Black defense frontiers. No whole-game solver,
search controller, TT, trainer or default is modified.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_safe_support import rule,orbit
from scripts.leaper_delayed_capture_witness import snapshot,replay
from scripts.leaper_rule_coordinates import physical_action
from tools.local_agent.common import write_json


def board_value(node):
    return tuple(None if p is None else(p['owner'],p['current_type_id'])for p in node['state']['position']['board'])


def attacked(board,owner,target,a_mask):
    for sq,p in enumerate(board):
        if p is None or p[0]!=owner:continue
        mask=3 if p[1]=='K'else(a_mask if p[1]=='A'else 5)
        if orbit(target%4-sq%4,target//4-sq//4)&mask:return True
    return False


def literal_actions(board,side,a_mask):
    moves=[]
    for sq,p in enumerate(board):
        if p is None or p[0]!=side:continue
        tid=p[1];mask=3 if tid=='K'else(a_mask if tid=='A'else 5)
        for dx,dy in L.offsets(mask):
            x,y=sq%4+dx,sq//4+dy
            if not(0<=x<4 and 0<=y<4):continue
            target=4*y+x;other=board[target]
            if other is not None and(other[0]==side or other[1]=='K'):continue
            after=list(board);after[target]=p;after[sq]=None
            king=next(i for i,z in enumerate(after)if z==(side,'K'))
            if not attacked(after,1-side,king,a_mask):moves.append((tid,sq,target,None))
    return sorted(moves,key=str)


def measure(plan,output):
    start=datetime.now(timezone.utc);tick=time.perf_counter()
    deadline=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=plan['resources']['absolute_analysis_validation_cap_seconds'])
    def gate():
        if datetime.now(timezone.utc)>=deadline:raise RuntimeError('original entry-square inclusive deadline')
    gate();mu=plan['mu'];rules={a:rule(4,a,5,mu['placement'])for a in mu['complete_rule_masks']}
    reg=dict(plan=plan,source_sha256=L.sha(Path(__file__)),complete_rules={str(a):L.ruleset_to_dict(r,include_metadata=True)for a,r in rules.items()},deadline=deadline.isoformat())
    write_json(output/'registration.json',reg)
    rows=[];calls=0
    for mask,rr in rules.items():
        gate();c=L.compile_rule(rr);z=L.GameSession(c);root=snapshot(z);children=[]
        for raw in root['legal_actions']:
            gate();child=replay(c,root['record']);child.submit(L.match_action(child,raw));node=snapshot(child);calls+=1
            if calls>plan['resources']['new_Core_child_limit']:raise RuntimeError('frozen literal child count limit')
            item=dict(action_key=list(physical_action(raw,4)),node=node);children.append(item)
            write_json(output/'latest-return.json',item)
        rows.append(dict(mask=mask,root=root,children=children));write_json(output/'partial.json',dict(rows=rows))
    gate();m=dict(started_at=start.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),producer_seconds_before_final_write=time.perf_counter()-tick,rows=rows,new_Core_child_applications=calls,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',m);return reg,m


def qualify(reg,m):
    plan=reg['plan'];assert plan['mu']['placement']==[6,15,4,0]
    assert [r['mask']for r in m['rows']]==[22,23,30,31]
    counts=[];branches=[];unique=0
    for row in m['rows']:
        mask=row['mask'];rr=rule(4,mask,5,[6,15,4,0]);assert reg['complete_rules'][str(mask)]==L.ruleset_to_dict(rr,include_metadata=True), 'complete square scope mismatch'
        c=L.compile_rule(rr);root=row['root'];assert root==snapshot(L.GameSession(c))and root['result']['status']=='ongoing'
        assert root['check']==[False,False]
        geometric=literal_actions(board_value(root),0,mask)
        actual=sorted((physical_action(a,4)for a in root['legal_actions']),key=str)
        assert geometric==actual, 'independent root geometry mismatch'
        assert len(row['children'])==len(actual) and {tuple(x['action_key'])for x in row['children']}==set(actual), 'complete White first frontier required'
        mates=[]
        for child in row['children']:
            k=tuple(child['action_key']);node=child['node'];z=replay(c,root['record'])
            raw=next(a for a in root['legal_actions']if physical_action(a,4)==k);z.submit(L.match_action(z,raw));assert node==snapshot(z)
            board=board_value(node);defenses=literal_actions(board,1,mask)
            assert sorted((physical_action(a,4)for a in node['legal_actions']),key=str)==defenses, 'independent complete defense mismatch'
            bk=next(i for i,p in enumerate(board)if p==(1,'K'))
            check=attacked(board,0,bk,mask)
            mate=check and not defenses
            assert mate==(node['result']['status']=='checkmate')
            if mate:
                assert node['result']['winner']==0 and k[0]=='A';mates.append(k[2])
            unique+=1
        assert sorted(mates)==plan['predictions']['immediate_mating_A_destinations'][str(mask)]
        assert len(actual)==plan['predictions']['root_branch_counts'][str(mask)]
        for destination in plan['predictions']['shared_A22_actions_destinations']:
            assert ('A',15,destination,None)in actual
        counts.append(len(mates));branches.append(len(actual))
    assert m['new_Core_child_applications']==unique==38, 'planned explicit child counter mismatch'
    assert counts==[0,1,2,5]and branches==[8,10,9,11]
    assert counts[3]-counts[1]-counts[2]+counts[0]==2
    assert int(bool(counts[3]))-int(bool(counts[1]))-int(bool(counts[2]))+int(bool(counts[0]))==-1
    assert m['ended_at']<=reg['deadline']
    return dict(status='PASS',common_input='NEW exposed n4 singletonmu, not a substitute value for undefined n3matched effect',masks=[22,23,30,31],root_branches=branches,immediate_mating_action_counts=counts,
        root_branch_polynomial='8+2W+N',immediate_mating_action_count_polynomial='W+2N+2WN',immediate_mate_indicator_polynomial='W+N-WN',
        full_root_WDL=['UNKNOWN','WIN','WIN','WIN'],new_Core_child_applications=m['new_Core_child_applications'],independent_geometric_child_frontiers=unique,
        scope='Finite exact two-orbit square/common freshroot/alloneplydefenses. Incomparable23/30bothWIN butsharedmatingactions differ; old/new ongoing continuationvalues UNKNOWN. One common board, no population strength or linearlearner impossibility. New-action absence is not an old legal record.',new_Player_queries=0,new_graph_or_solver_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    try:
        reg,m=measure(json.loads(a.plan.read_text(encoding='utf-8-sig')),a.output);q=qualify(reg,m);write_json(a.output/'qualification.json',q);print(json.dumps(q))
    except Exception as exc:write_json(a.output/'failure.json',dict(type=type(exc).__name__,message=str(exc)));raise


if __name__=='__main__':main()
