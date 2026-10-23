"""Scoped cooperative path witnesses for existing two-Fers inputs, not WDL.

The integer candidate graph has no history oracle. Only a literal full-record
Core replay can certify the returned positive path; failure remains UNKNOWN.
"""
from __future__ import annotations
import argparse, json, time
from collections import deque, Counter
from datetime import datetime, timezone
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import physical_action
from tools.local_agent.common import write_json
from tools.local_agent import session


def now(): return datetime.now(timezone.utc).isoformat()

def neighbours(k, actors, v, side, n=5):
    """Plain King8+twoFers vs bareKing, distinct occupied cells only."""
    near=lambda a,b:max(abs(a%n-b%n),abs(a//n-b//n))<=1
    attacks=lambda a,b:abs(a%n-b%n)==abs(a//n-b//n)==1
    out=[]
    sources=[('K',k,L.offsets(3))]+[('A',a,L.offsets(2)) for a in actors] if side==0 else [('K',v,L.offsets(3))]
    for tid,src,offsets in sources:
        for dx,dy in offsets:
            x,y=src%n+dx,src//n+dy
            if not (0<=x<n and 0<=y<n): continue
            dst=n*y+x
            if side==0:
                if dst in (k,v)+actors: continue
                kk=dst if tid=='K' else k
                aa=tuple(sorted(dst if a==src and tid=='A' else a for a in actors))
                if near(kk,v):continue
                vv=v
            else:
                if dst==k or near(k,dst):continue
                aa=tuple(a for a in actors if a!=dst);kk=k;vv=dst
                if any(attacks(a,dst) for a in aa):continue
            out.append(((tid,src,dst,None),(kk,aa,vv,1-side)))
    return sorted(out)


def physical(state):
    board=state.position.board
    k=next(i for i,p in enumerate(board) if p is not None and p.owner==0 and p.current_type_id=='K')
    v=next(i for i,p in enumerate(board) if p is not None and p.owner==1 and p.current_type_id=='K')
    actors=tuple(i for i,p in enumerate(board) if p is not None and p.owner==0 and p.current_type_id=='A')
    return k,actors,v,state.position.side_to_move


def replay(world,path):
    assert L.compute_fingerprint(L.ruleset_from_dict(world['rule']))=='1988f7df02e58e0d48855e44a576e23b32e90ae5a0353c105615a1f33e946df1', 'this witness reader accepts only its frozen full RuleSet'
    c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(world['roots'][0]['record'])))
    root=L.record_value(s.to_record());rows=[]
    for index,action in enumerate(path):
        before=physical(s.state); legal=s.legal_actions();mapped={physical_action(L.record_value(a),5):a for a in legal}
        expected=dict(neighbours(*before));assert len(mapped)==len(legal) and set(mapped)==set(expected)
        assert action in mapped and not s.state.terminal_status.is_terminal
        s.submit(mapped[action]);assert physical(s.state)==expected[action]
        rows.append(dict(index=index,action=L.record_value(mapped[action]),full_state=L.record_value(s.state),state_sha256=L.state_sha(s.state),legal_frontier=[list(a) for a in mapped],full_record=L.record_value(s.to_record())))
    assert s.result.winner==0 and s.result.status.value=='checkmate'
    restored=L.GameSession.replay(c,s.to_record());assert restored.state==s.state
    return dict(initial_record=root,final_record=L.record_value(s.to_record()),final_state=L.record_value(s.state),terminal=L.record_value(s.result),rows=rows,plies=len(path),status='PASS',scope='Literal full Core histories and every path frontier, shared Core not independent engine; positive cooperative witness only, no forced-WIN or optimality claim.')


def run(inputs,output,cap=900,state_cap=400000):
    assert not output.exists();start=now();tick=time.perf_counter();world=L.load(inputs)['worlds'][1]
    c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(world['roots'][0]['record'])))
    assert s.state.ply_count==0 and L.compute_fingerprint(L.ruleset_from_dict(world['rule']))=='1988f7df02e58e0d48855e44a576e23b32e90ae5a0353c105615a1f33e946df1'
    root=physical(s.state);assert root==(0,(1,6),24,0)
    plan=dict(started_at=start,input_sha256=L.sha(inputs),source_sha256=L.sha(Path(__file__)),seconds_cap=cap,state_cap=state_cap,depth_cap=64,method='BFS candidate paths, pruning loss of either A; only positive literal Core replay accepted; no negative label on exhaustion.',scope='Existing exact mixed-color setup; plain remove/King8/Fers/no extras, not a general history solver.')
    write_json(output.with_suffix('.plan.json'),plan)
    queue=deque([root]);parents={root:None};depth={root:0};expanded=0;edges=0;goal=None;stop=None
    while queue:
        if session.stopped():stop='user_stop';break
        if time.perf_counter()-tick>=cap or len(parents)>=state_cap:stop='budget';break
        pos=queue.popleft();d=depth[pos];actions=neighbours(*pos);expanded+=1
        k,aa,v,side=pos
        if not actions:
            if side==1 and any(abs(a%5-v%5)==abs(a//5-v//5)==1 for a in aa):goal=pos;stop='candidate_mate';break
            continue
        if d==64:continue
        for a,child in actions:
            edges+=1
            if len(child[1])!=2 or child in parents:continue
            parents[child]=(pos,a);depth[child]=d+1;queue.append(child)
        if expanded%5000==0:print('COOP',expanded,len(parents),d,round(time.perf_counter()-tick,2),flush=True)
    path=[]
    if goal is not None:
        node=goal
        while parents[node] is not None:
            node,action=parents[node];path.append(action)
        path.reverse()
    raw=dict(status='CANDIDATE' if goal else 'UNKNOWN',started_at=start,ended_at=now(),seconds=time.perf_counter()-tick,expanded=expanded,discovered=len(parents),edges=edges,stop=stop or 'exhausted',path=[list(a) for a in path],plan=plan,goal=goal)
    write_json(output,raw)
    if goal is not None:
        qualified=replay(world,path);write_json(output.with_suffix('.replay.json'),qualified)
        raw.update(status='COOPERATIVE_TRUE',qualification=output.with_suffix('.replay.json').name,forced_WIN='UNKNOWN');write_json(output,raw)
    print(json.dumps({k:v for k,v in raw.items() if k not in ('path','plan')}),flush=True)
    return raw

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();run(args.input,args.output)
