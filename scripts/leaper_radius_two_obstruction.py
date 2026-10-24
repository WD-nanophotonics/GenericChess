"""Finite local-pattern qualification for the A6/A22--B27 obstruction.

No graph, fabricated GameState or labels. n5 Core observations are reused.
"""
from pathlib import Path
from dataclasses import replace
from itertools import product
from collections import Counter
from datetime import datetime,timezone
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_parity_scope import escapes,adjacent
from scripts.leaper_joint_cage_witness import rule as five_rule
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions_from_position
from tools.local_agent.common import write_json
from tools.local_agent import session


def edge_representative(x,n):
    if n<5 or not 0<=x<n:
        raise ValueError('radius2 large-board axis only')
    return x if x<2 else 4-(n-1-x) if n-1-x<2 else 2


def carrier(n,mask):
    b=[None]*(n*n)
    cells=(0,1,2,6) if n==3 else (0,1,n*n-1,n*n-2)
    for sq,owner,tid in zip(cells,(0,0,1,1),('K','A','K','B')):
        b[sq]=L.Piece(owner,tid,tid)
    return replace(five_rule(mask),board_size=n,
        initial_position=tuple(tuple(b[n*y:n*y+n])for y in range(n)),
        drop_allowed={t:((False,)*(n*n),)*2 for t in ('A','B')})


def relative_cases(n,mask):
    """A checks target V; all potential mate patterns lie within radius2."""
    aa=set(L.offsets(mask));bb=set(L.offsets(27));rows=[];counts=Counter()
    for v in product(range(n),repeat=2):
        for kd in product(range(-2,3),repeat=2):
            k=(v[0]+kd[0],v[1]+kd[1])
            if not all(0<=z<n for z in k) or adjacent(k,v):continue
            for d in aa:
                a=(v[0]-d[0],v[1]-d[1])
                if not all(0<=z<n for z in a) or a==k:continue
                counts['local_checked_triples']+=1
                free=escapes(k,a,v,aa,n)
                assert free
                if len(free)!=1:continue
                b=free[0]
                if b in (k,a,v):continue
                unsafe=(k[0]-b[0],k[1]-b[1]) in bb
                capture=(a[0]-b[0],a[1]-b[1]) in bb
                cells=[y*n+x for x,y in (k,a,v,b)]
                rows.append(dict(placement=cells,previous_mover_checked=unsafe,
                                 B_can_capture_A=capture))
                counts['sole_escape_B_candidates']+=1
                counts['unsafe_previous_mover' if unsafe else 'safe_B_captureA_defense']+=1
                assert unsafe or capture, 'unresolved local mating cage'
    return rows,dict(counts)


def run(existing,output):
    if output.exists():raise ValueError('NEW output required')
    output.mkdir(parents=True);tick=time.perf_counter()
    started=datetime.now(timezone.utc).isoformat()
    write_json(output/'registration.json',dict(started_at=started,
        source_sha256=L.sha(Path(__file__)),n5_original_sha256=L.sha(existing),cap_seconds=600,
        input_selection='n3/n4 missing board-edge profiles and independent n5 relative-coordinate match'))
    original=L.load(existing);rows=[];raw=[];core=0;mapping=0
    for n in(3,4,5):
        for mask in(6,22):
            if session.stopped() or time.perf_counter()-tick>=600:raise RuntimeError('stop/cap')
            cases,counts=relative_cases(n,mask)
            rule=carrier(n,mask);c=L.compile_rule(rule)
            if n==5:
                old=next(r for r in original['rows']if r['mask']==mask)
                indexed={tuple(r['placement']):r for r in old['cases']}
                assert set(indexed)=={tuple(r['placement'])for r in cases}
                for r in cases:
                    oldrow=indexed[tuple(r['placement'])]
                    assert r['previous_mover_checked']==oldrow['previous_mover_checked']
                    if not r['previous_mover_checked']:
                        assert r['B_can_capture_A']==oldrow['predicted_B_can_capture_A']
            else:
                for r in cases:
                    board=[None]*(n*n)
                    for sq,owner,tid in zip(r['placement'],(0,0,1,1),('K','A','K','B')):
                        board[sq]=L.Piece(owner,tid,tid)
                    p=replace(c.initial_position,board=tuple(board),side_to_move=1)
                    checked0=is_in_check(p,0,c);checked1=is_in_check(p,1,c)
                    assert checked1 and checked0==r['previous_mover_checked']
                    if checked0:continue
                    acts=legal_actions_from_position(p,c)
                    entry=dict(n=n,mask=mask,static_position=L.record_value(p),
                               actions=L.record_value(acts),geometry=r)
                    raw.append(entry);write_json(output/'latest-raw-frontier.json',entry)
                    core+=1
                    assert len(acts)==1
                    z=acts[0];a=r['placement'][1];b=r['placement'][3]
                    assert (z.from_square.file,z.from_square.rank)==(b%n,b//n)
                    assert (z.to_square.file,z.to_square.rank)==(a%n,a//n)
            rows.append(dict(n=n,mask=mask,rule=L.ruleset_to_dict(rule,include_metadata=True),
                             counts=counts,cases=cases))
    # Executed examples of the algebraic projection, NOT its mathematical proof.
    for n in range(5,41):
        for x in range(n):
            mapped=edge_representative(x,n)
            assert all((0<=x+d<n)==(0<=mapped+d<5)for d in range(-2,3))
            mapping+=1
    r=dict(status='PASS',started_at=started,
           ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick,
           rows=rows,new_boundary_Core_frontiers=core,n5_Core_frontiers_reused=56,
           boundary_raw_frontiers=raw,executed_axis_profile_examples=mapping,
           obstruction='For every potential sole-escape B27 blocker cage, either the previous moving King is checked byB27 or B27 can legally captureA. This refutes admissible checkmate.',
           mathematical_extension='All relevant pieces are within radius2 of target; n>=5 axis edge profiles translate to n5. n3/n4 separately checked. Proof text carries the all-n claim, finite tests alone do not.',
           scope='One A6 or A22 white, one B27 black, King8, symmetricLeap, remove, no promotion/drop/other effects; draw endings. Static obstruction, not a root-WDL draw theorem.',
           new_Player_queries=0,new_graph_or_solver_calls=0)
    write_json(output/'results.json',r)
    print(json.dumps({k:v for k,v in r.items()if k not in('rows','boundary_raw_frontiers')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--existing',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.existing,a.output)
