"""Separate tightened Pawn family; preserves the frozen old interval consumer."""
import json
from pathlib import Path
from fractions import Fraction as F
from scripts.native_chess_contact_intervals import native_contact_intervals,contact_interval_choice,TERMINAL_UNIT
from scripts.material_interval_choice import certified_ongoing_material_choice
REPORT=Path(__file__).resolve().parents[1]/'docs/research/data/chess_pawn_third_prefix_20261005.json'

def third_native_contact_intervals(duration):
    if duration not in ('geometric_half','linear_mixture'):raise ValueError('use separate declared duration')
    r=json.loads(REPORT.read_text())
    if not r['complete'] or not r['source_hashes_unchanged']:raise ValueError('complete third-prefix qualification required')
    m=(lambda t:F(1,2)**t) if duration=='geometric_half' else (lambda t:F(2,(t+1)*(t+2)))
    maximum=(87696*m(1)+162048*m(2)+240*m(3))/249984
    lo,hi=map(F,r['raw_bounds'][duration]);boxes=native_contact_intervals(duration)
    oldlo,oldhi=boxes['board','P']
    if not oldlo<=lo/maximum<=hi/maximum<=oldhi:raise ValueError('new Pawn bounds not nested')
    boxes['board','P']=(lo/maximum,hi/maximum);return boxes

def third_contact_choice(children,game,*,owner,duration,complete=False):
    if duration=='both':
        by_law={law:third_contact_choice(children,game,owner=owner,duration=law,complete=complete) for law in ('geometric_half','linear_mixture')}
        if not all(x['complete'] for x in by_law.values()):return dict(complete=False,selected=None,by_law=by_law)
        picks={x['selected'] for x in by_law.values()}
        return dict(complete=True,selected=next(iter(picks)) if len(picks)==1 and None not in picks else None,by_law=by_law)
    base=contact_interval_choice(children,game,owner=owner,duration=duration,complete=complete)
    if not base['complete']:return base
    boxes=third_native_contact_intervals(duration);boxes[TERMINAL_UNIT]=(F(1),F(1))
    return dict(certified_ongoing_material_choice(base['features'],boxes,owner=owner,complete=True),
                features=base['features'],duration=duration,scope='same Western zero-rights/EP envelope; tightened third-prefix Pawn family')
