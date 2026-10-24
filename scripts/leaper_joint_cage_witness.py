"""Finite B-blocker cage criterion for one A6/A22 versus B27 comparison.

Static postmove Positions only, never fabricated history or graph reachability.
"""
from dataclasses import replace
from itertools import permutations
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_parity_scope import xy,adjacent,escapes
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions_from_position
from tools.local_agent.common import write_json
from tools.local_agent import session


def rule(mask):
    n=5
    r=L.definition(mask,27)
    board=[None]*25
    for sq,owner,tid in ((0,0,'K'),(1,0,'A'),(24,1,'K'),(23,1,'B')):
        board[sq]=L.Piece(owner,tid,tid)
    return replace(r,board_size=n,initial_position=tuple(tuple(board[5*y:5*y+5]) for y in range(5)),
                   initial_setup_options=(),drop_allowed={t:((False,)*25,)*2 for t in ('A','B')},
                   max_ply=6,repetition_limit=2)


def position(c,cells):
    board=[None]*25
    for sq,owner,tid in zip(cells,(0,0,1,1),('K','A','K','B')):
        board[sq]=L.Piece(owner,tid,tid)
    return replace(c.initial_position,board=tuple(board),side_to_move=1)


def run(output):
    if output.exists():
        raise ValueError('NEW output required')
    output.mkdir(parents=True)
    tick=time.perf_counter()
    started=datetime.now(timezone.utc).isoformat()
    reg=dict(started_at=started,source_sha256=L.sha(Path(__file__)),
             input_A_masks=[6,22],B_mask=27,n=5,cap_seconds=300,
             stop='All fixed candidates or first mismatch/stop/cap; retain missing UNKNOWN.',
             scope='Static no-history cage positions; no graph/WDL/reachability claim.')
    write_json(output/'registration.json',reg)
    results=[]
    for mask in (6,22):
        rr=rule(mask)
        c=L.compile_rule(rr)
        aa=set(L.offsets(mask));bb=set(L.offsets(27))
        counts=Counter();cases=[]
        for k,a,v in permutations(range(25),3):
            if time.perf_counter()-tick>=300 or session.stopped():
                raise RuntimeError('Frozen cap/stop; incomplete finite census')
            counts['raw_K0_A0_K1_triples']+=1
            if adjacent(xy(k,5),xy(v,5)):
                counts['adjacent_Kings_excluded']+=1
                continue
            if (xy(v,5)[0]-xy(a,5)[0],xy(v,5)[1]-xy(a,5)[1]) not in aa:
                counts['not_checked_by_A']+=1
                continue
            counts['checked_nonadjacent_triples']+=1
            free=escapes(xy(k,5),xy(a,5),xy(v,5),aa,5)
            if not free:
                write_json(output/'unexpected-bare-mate.json',dict(mask=mask,cells=[k,a,v]))
                raise AssertionError('Orthogonally independent A has no bare-K escape')
            if len(free)!=1:
                counts['at_least_two_bare_K_escapes']+=1
                continue
            b=free[0][1]*5+free[0][0]
            if b in (k,a,v):
                counts['sole_escape_is_capture_A']+=1
                continue
            p=position(c,(k,a,v,b))
            row=dict(placement=[k,a,v,b],static_position=L.record_value(p),
                     previous_mover_checked=is_in_check(p,0,c),
                     sole_bare_K_escape=[free[0][0],free[0][1]])
            assert is_in_check(p,1,c)
            counts['only_possible_B_blocker_placements']+=1
            if row['previous_mover_checked']:
                counts['previous_mover_checked_excluded']+=1
                cases.append(row)
                continue
            # Actual raw frontier is retained before a derived prediction check.
            legal=legal_actions_from_position(p,c)
            row['actual_legal_actions']=L.record_value(legal)
            row['predicted_B_can_capture_A']=(xy(a,5)[0]-xy(b,5)[0],xy(a,5)[1]-xy(b,5)[1]) in bb
            cases.append(row)
            write_json(output/'latest-raw-frontier.json',row)
            counts['admissible_postmove_Core_frontiers']+=1
            assert all(p.board[z.from_square.rank*5+z.from_square.file].current_type_id=='B' for z in legal)
            assert bool(legal)==row['predicted_B_can_capture_A']
            if legal:
                assert len(legal)==1 and legal[0].to_square.file==xy(a,5)[0] and legal[0].to_square.rank==xy(a,5)[1]
                counts['unique_B_captures_A_defense']+=1
            else:
                counts['static_checkmates']+=1
        results.append(dict(mask=mask,rule=L.ruleset_to_dict(rr,include_metadata=True),
                            fingerprint=c.ruleset_fingerprint,counts=dict(counts),cases=cases))
        write_json(output/'partial.json',dict(rows=results,status='PARTIAL'))
    r=dict(status='CLOSED',started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),
           seconds=time.perf_counter()-tick,rows=results,new_Player_queries=0,new_graph_or_solver_calls=0,
           scope='Complete static census at n5 for two A masks and fixed B27, not initial-mu capacity or legal reachability; all exclusions explicit.')
    write_json(output/'results.json',r)
    print(json.dumps(dict(status=r['status'],seconds=r['seconds'],counts=[x['counts'] for x in results])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
