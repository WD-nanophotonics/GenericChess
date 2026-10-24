"""Static mate versus admissible last-move entry, one generated rule boundary."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_corner_capacity_law import rule as five_rule,d4
from scripts.leaper_delayed_capture_witness import snapshot
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions_from_position
from tools.local_agent.common import write_json


def carrier(n,mask,b):
    r=five_rule(mask,b)
    cells=(0,1,8,7)if n==3 else(0,1,15,14)
    board=[None]*(n*n)
    for sq,owner,tid in zip(cells,(0,0,1,1),('K','A','K','B')):
        board[sq]=L.Piece(owner,tid,tid)
    return replace(r,board_size=n,initial_position=tuple(tuple(board[n*y:n*y+n])for y in range(n)),
                   drop_allowed={t:((False,)*(n*n),)*2 for t in('A','B')})


def place(c,cells,n):
    board=[None]*(n*n)
    for sq,owner,tid in zip(cells,(0,0,1,1),('K','A','K','B')):
        board[sq]=L.Piece(owner,tid,tid)
    return replace(c.initial_position,board=tuple(board),side_to_move=1)


def measure(output):
    tick=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
    write_json(output/'registration.json',dict(started_at=started,source_sha256=L.sha(Path(__file__)),
        B_masks=[5,7,21,23],n3_canonical_mate=[2,8,0,3],symmetries=8,n4_A_before=[3,3],n4_A_after=[2,2],cap_seconds=600))
    rows=[];fresh=[]
    for b in(5,7,21,23):
        rr=carrier(3,22,b);c=L.compile_rule(rr)
        for cells in d4([2,8,0,3],3):
            p=place(c,cells,3)
            row=dict(B_mask=b,rule=L.ruleset_to_dict(rr,include_metadata=True),
                     mate_position=L.record_value(p),cells=list(cells),
                     target_checked=is_in_check(p,1,c),previous_mover_checked=is_in_check(p,0,c),
                     defenses=L.record_value(legal_actions_from_position(p,c)),inverse_candidates=[])
            for which,tid,offsets in((0,'K',L.offsets(3)),(1,'A',L.offsets(22))):
                target=cells[which];tx,ty=target%3,target//3
                for dx,dy in offsets:
                    px,py=tx-dx,ty-dy
                    entry=dict(piece=tid,from_square=[px,py],to_square=[tx,ty])
                    if not(0<=px<3 and 0<=py<3):entry['exclusion']='outside_board'
                    elif px+3*py in cells:entry['exclusion']='occupied_predecessor_square'
                    else:
                        board=list(p.board);board[target]=None;board[px+3*py]=L.Piece(0,tid,tid)
                        pre=replace(p,board=tuple(board),side_to_move=0)
                        entry.update(predecessor_position=L.record_value(pre),
                                     enemy_king_already_checked=is_in_check(pre,1,c),
                                     own_king_checked=is_in_check(pre,0,c))
                        entry['exclusion']='enemy_king_checked_before_White_turn'if entry['enemy_king_already_checked']else'UNRESOLVED_ADMISSIBLE'
                    row['inverse_candidates'].append(entry)
            rows.append(row);write_json(output/'latest-raw-incoming.json',row)
        for mask in(6,22):
            rr=carrier(4,mask,b);board=[None]*16
            for sq,owner,tid in((2,0,'K'),(15,0,'A'),(0,1,'K'),(4,1,'B')):
                board[sq]=L.Piece(owner,tid,tid)
            rr=replace(rr,initial_position=tuple(tuple(board[4*y:4*y+4])for y in range(4)))
            c=L.compile_rule(rr);s=L.GameSession(c);initial=snapshot(s)
            raw=next(L.record_value(a)for a in s.legal_actions()if a.actor_type_id=='A'
                     and(a.from_square.file,a.from_square.rank)==(3,3)and(a.to_square.file,a.to_square.rank)==(2,2))
            s.submit(L.match_action(s,raw))
            fresh.append(dict(B_mask=b,mask=mask,rule=L.ruleset_to_dict(rr,include_metadata=True),
                              initial=initial,action=raw,after=snapshot(s)))
    return dict(started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick,
                n3_mate_rows=rows,n4_fresh_rows=fresh,new_Player_queries=0,new_graph_or_solver_calls=0)


def qualify(m):
    assert len(m['n3_mate_rows'])==32
    assert {(r['B_mask'],tuple(r['cells']))for r in m['n3_mate_rows']}=={(b,p)for b in(5,7,21,23)for p in d4([2,8,0,3],3)}, 'complete inverse target motifs required'
    counts={}
    for row in m['n3_mate_rows']:
        expected={(tid,(row['cells'][idx]%3-dx,row['cells'][idx]//3-dy),(row['cells'][idx]%3,row['cells'][idx]//3))for idx,tid,offsets in((0,'K',L.offsets(3)),(1,'A',L.offsets(22)))for dx,dy in offsets}
        actual={(x['piece'],tuple(x['from_square']),tuple(x['to_square']))for x in row['inverse_candidates']}
        assert len(row['inverse_candidates'])==20 and actual==expected, 'complete inverse atom list required'
        for x in row['inverse_candidates']:
            px,py=x['from_square']
            expected_exclusion=('outside_board'if not(0<=px<3 and 0<=py<3)else'occupied_predecessor_square'if py*3+px in row['cells']else'enemy_king_checked_before_White_turn')
            assert x['exclusion']==expected_exclusion, 'inverse exclusion geometry mismatch'
            if expected_exclusion=='enemy_king_checked_before_White_turn':assert x['enemy_king_already_checked']
        assert row['target_checked']and not row['previous_mover_checked']and not row['defenses']
        for x in row['inverse_candidates']:
            assert x['exclusion']!='UNRESOLVED_ADMISSIBLE'
            counts[x['exclusion']]=counts.get(x['exclusion'],0)+1
    assert len(m['n4_fresh_rows'])==8
    for b in(5,7,21,23):
        lo,hi=[next(x for x in m['n4_fresh_rows']if x['B_mask']==b and x['mask']==a)for a in(6,22)]
        assert lo['initial']['state']['position']['board']==hi['initial']['state']['position']['board']
        assert lo['after']['state']['position']['board']==hi['after']['state']['position']['board']
        assert lo['after']['result']['status']=='ongoing'
        assert hi['after']['result']['status']=='checkmate'and hi['after']['result']['winner']==0
    return dict(status='PASS',n3_static_mates=32,n3_admissible_last_move_predecessors=0,
                exclusions=counts,n4_paired_fresh_Win_entries=4,
                conclusion='n3 static possibility is not reachable mating opportunity from compiler-admitted safe roots. n4 has literal fresh entering moves for all four newly positive B masks.',
                theorem_basis='No added/captured-back pieces or type changes exist in this scope. Last White action must move K orA; all inverse sources are occupied/outside or already check the enemy King, impossible at a legal White turn. Fresh compiler rejects checked anchors.',
                limits='No graph closure or independent engine, no arbitrary initial-check relaxation, no exact LOSS/DRAW labels for remaining roots.',
                new_Player_queries=0,new_graph_or_solver_calls=0)



def parity_boundary(output):
    tick=time.perf_counter();started=datetime.now(timezone.utc).isoformat()
    write_json(output/'registration.json',dict(started_at=started,source_sha256=L.sha(Path(__file__)),
        masks=[22,23],B_present=[True,False],n=3,cap_seconds=300,
        scope='Four fixed literal one-action cells only, separate from even-attack corner theorem.'))
    rows=[]
    for present in(True,False):
        for mask in(22,23):
            r=five_rule(mask,5);board=[None]*9
            for sq,owner,tid in((5,0,'K'),(8,0,'A'),(3,1,'K')):
                board[sq]=L.Piece(owner,tid,tid)
            if present:board[0]=L.Piece(1,'B','B')
            r=replace(r,board_size=3,initial_position=tuple(tuple(board[3*y:3*y+3])for y in range(3)),
                      drop_allowed={t:((False,)*9,)*2 for t in('A','B')})
            c=L.compile_rule(r);z=L.GameSession(c);initial=snapshot(z)
            action=next(L.record_value(a)for a in z.legal_actions()if a.actor_type_id=='A'
                and(a.from_square.file,a.from_square.rank)==(2,2)and(a.to_square.file,a.to_square.rank)==(1,1))
            z.submit(L.match_action(z,action))
            rows.append(dict(mask=mask,B_present=present,rule=L.ruleset_to_dict(r,include_metadata=True),
                             initial=initial,shared_action=action,after=snapshot(z)))
            write_json(output/'latest-raw-boundary.json',rows[-1])
    measured=dict(started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),
                  seconds=time.perf_counter()-tick,rows=rows,new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'measurements.json',measured)
    q=qualify_parity_boundary(measured);write_json(output/'qualification.json',q)
    print(json.dumps(q))


def qualify_parity_boundary(m):
    indexed={(r['mask'],r['B_present']):r for r in m['rows']}
    assert len(indexed)==len(m['rows'])==4
    expected={(22,True):'ongoing',(23,True):'checkmate',(22,False):'stalemate',(23,False):'checkmate'}
    for key,row in indexed.items():
        assert row['after']['result']['status']==expected[key]
        if key[0]==23:assert row['after']['result']['winner']==0
        else:assert row['after']['result']['winner']is None
    for present in(True,False):
        lo,hi=[indexed[a,present]for a in(22,23)]
        assert lo['initial']['state']['position']['board']==hi['initial']['state']['position']['board']
        assert lo['after']['state']['position']['board']==hi['after']['state']['position']['board']
        assert lo['initial']['result']['status']==hi['initial']['result']['status']=='ongoing'
    return dict(status='PASS',terminals=[dict(mask=r['mask'],B_present=r['B_present'],status=r['after']['result']['status'])for r in m['rows']],
                checked_king_square=[0,1],noncorner_mate=True,
                implication='Adding only Wazir breaks the even-offset corner lemma. Old joint static capacity was already positive on n3, yet this common fresh entry is born. B survival separates ongoing from stalemate under oldA22.',
                scope='Four literal complete fresh records. Does not extend the A6/A22 corner law toA23 or assert new generic WDL labels.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--parity-boundary',action='store_true');a=p.parse_args()
    if a.output.exists():raise ValueError('NEW output required')
    a.output.mkdir(parents=True)
    if a.parity_boundary:
        parity_boundary(a.output)
        return
    m=measure(a.output);write_json(a.output/'measurements.json',m)
    q=qualify(m);write_json(a.output/'qualification.json',q);print(json.dumps(q))


if __name__=='__main__':main()
