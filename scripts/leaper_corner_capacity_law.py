"""Exact corner-template conditional mate law; no full game solver."""
from pathlib import Path
from dataclasses import replace
from itertools import product
import argparse,json,time
from datetime import datetime,timezone
from scripts import leaper_design as L
from scripts.leaper_joint_cage_witness import rule as joint_rule,position
from scripts.leaper_delayed_capture_witness import snapshot,child_frontier
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions_from_position
from tools.local_agent.common import write_json


def templates(mask):
    checks=[(1,1),(2,0),(0,2)]+([(2,2)]if mask==22 else [])
    return [[ky*5+kx,ay*5+ax,0,5]for kx,ky in((2,0),(2,1))
            for ax,ay in checks if(kx,ky)!=(ax,ay)]


def prediction(mask,b):
    if mask==6:return sum(bool(b&x)for x in(1,4,8))<=1
    if mask==22:return not(b&8)or(not(b&1)and not(b&4))
    raise ValueError('only registered A6/A22')


def rule(mask,b):
    r=joint_rule(mask)
    return replace(r,piece_types=tuple(replace(t,movement_atoms=tuple(L.LeapAtom(x)for x in L.offsets(b)))
                   if t.type_id=='B'else t for t in r.piece_types))


def d4(cells,n=5):
    out=[]
    for reflected in(False,True):
        for r in range(4):
            case=[]
            for sq in cells:
                x,y=sq%n,sq//n
                if reflected:x=n-1-x
                for _ in range(r):x,y=n-1-y,x
                case.append(y*n+x)
            out.append(tuple(case))
    return out


def measure(existing,output):
    tick=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
    write_json(output/'registration.json',dict(started_at=started,source_sha256=L.sha(Path(__file__)),
        n5_source_sha256=L.sha(existing),masks=[6,22],B_masks=list(range(1,32)),
        exact_oriented_templates=[5,7],cap_seconds=600))
    old=L.load(existing);rows=[];new_core=0;reused=0
    for mask in(6,22):
        templates0=templates(mask)
        oldrow=next(r for r in old['rows']if r['mask']==mask)
        oldcases={tuple(r['placement']):r for r in oldrow['cases']}
        assert set(oldcases)=={q for p in templates0 for q in d4(p)}
        for b in range(1,32):
            if time.perf_counter()-tick>=600:raise RuntimeError('frozen cap')
            rr=rule(mask,b);c=L.compile_rule(rr);cases=[]
            for cells in templates0:
                p=position(c,cells)
                entry=dict(placement=cells,static_position=L.record_value(p),
                           previous_mover_checked=is_in_check(p,0,c),target_checked=is_in_check(p,1,c))
                if not entry['previous_mover_checked']:
                    if b==27:
                        acts=oldcases[tuple(cells)]['actual_legal_actions'];reused+=1
                        entry['actions']=acts;entry['source']='Reused original n5 Core frontier'
                    else:
                        acts=legal_actions_from_position(p,c);new_core+=1
                        entry['actions']=L.record_value(acts);entry['source']='NEW static Core frontier'
                cases.append(entry)
                write_json(output/'latest-raw-frontier.json',entry)
            rows.append(dict(mask=mask,B_mask=b,rule=L.ruleset_to_dict(rr,include_metadata=True),
                             cases=cases,predicted_static_capacity=bool(prediction(mask,b))))
    witnesses=[]
    for mask in(6,22):
        rr=rule(mask,5)
        board=[None]*25
        for sq,owner,tid in((2,0,'K'),(14,0,'A'),(0,1,'K'),(5,1,'B')):
            board[sq]=L.Piece(owner,tid,tid)
        rr=replace(rr,initial_position=tuple(tuple(board[5*y:5*y+5])for y in range(5)))
        c=L.compile_rule(rr);s=L.GameSession(c)
        # General helper is intentionally n3-specific, so match the ACTUAL n5 action.
        raw=next(L.record_value(a)for a in s.legal_actions()
                 if a.actor_type_id=='A'and(a.from_square.file,a.from_square.rank)==(4,2)
                 and(a.to_square.file,a.to_square.rank)==(2,2))
        initial=snapshot(s);s.submit(L.match_action(s,raw));after=snapshot(s)
        defenses=[]
        for a in s.legal_actions():
            z=L.GameSession.replay(c,s.to_record());z.submit(a)
            defenses.append(dict(action=L.record_value(a),node=snapshot(z)))
        witnesses.append(dict(mask=mask,B_mask=5,rule=L.ruleset_to_dict(rr,include_metadata=True),
                              initial=initial,shared_action=raw,after=after,defenses=defenses))
    return dict(started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),
                seconds=time.perf_counter()-tick,rows=rows,fresh_witnesses=witnesses,
                new_static_Core_frontiers=new_core,reused_static_Core_frontiers=reused,
                new_Player_queries=0,new_graph_or_solver_calls=0)


def qualify(m):
    laws={6:[],22:[]};by={}
    for row in m['rows']:
        mask,b=row['mask'],row['B_mask'];by[mask,b]=row
        assert len(row['cases'])==(5 if mask==6 else 7)
        for c in row['cases']:assert c['target_checked']
        mates=[c for c in row['cases']if not c['previous_mover_checked']and not c['actions']]
        actual=bool(mates)
        assert actual==row['predicted_static_capacity']==bool(prediction(mask,b))
        if actual:laws[mask].append(b)
    a,b=m['fresh_witnesses']
    assert a['initial']['state']['position']['board']==b['initial']['state']['position']['board']
    assert a['after']['state']['position']['board']==b['after']['state']['position']['board']
    assert a['after']['result']['status']=='ongoing'and a['after']['legal_actions']
    assert b['after']['result']['status']=='checkmate'and b['after']['result']['winner']==0
    # Physical shared action, semantic pattern IDs may differ across rules.
    for key in('actor_type_id','from_square','to_square','promotion_target_id'):
        assert a['shared_action'][key]==b['shared_action'][key]
    third={}
    for mask in(6,22):
        # Nonempty B remains guaranteed by the fixed Ferz bit2.
        values={bits:int(by[mask,2+bits[0]+4*bits[1]+8*bits[2]]['predicted_static_capacity'])
                for bits in product((0,1),repeat=3)}
        third[mask]=sum((-1)**(3-sum(bits))*v for bits,v in values.items())
    return dict(status='PASS',positive_B_masks=laws,
                added_static_capacity_B_masks=sorted(set(laws[22])-set(laws[6])),
                third_finite_difference_W_D_N_with_F_fixed=third,
                new_static_Core_frontiers=m['new_static_Core_frontiers'],
                reused_static_Core_frontiers=m['reused_static_Core_frontiers'],
                shared_fresh_action_terminals=['ongoing','checkmate'],new_winner=0,
                old_exact_root_and_action_WDL='UNKNOWN within {-1,0} under the proved no-white-mate scope; not independently solved',
                scope='Corner static-capacity law and literal fresh action only. Numeric cubic degree is NOT a linear-threshold classification impossibility or a price/training gate.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--existing',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    m=measure(a.existing,a.output);write_json(a.output/'measurements.json',m)
    q=qualify(m);write_json(a.output/'qualification.json',q);print(json.dumps(q))


if __name__=='__main__':main()
