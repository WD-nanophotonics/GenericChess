"""Separate full board-distance family plus unchanged censored held law."""
import json
from pathlib import Path
from fractions import Fraction as F
from scripts.shogi_complete_board_intervals import moment,board_intervals
from scripts.shogi_contact_interval_choice import shogi_contact_intervals,shogi_contact_choice,TERMINAL_UNIT
from scripts.material_interval_choice import certified_ongoing_material_choice
DATA=Path(__file__).resolve().parents[1]/'docs/research/data'

def exact_board_means(duration):
    moment(duration,1)
    raw=json.loads((DATA/'shogi_full_contact_distance_20261005.json').read_text())
    qualification=json.loads((DATA/'shogi_coordinate_comparison_20261005.json').read_text())
    if not all(r['complete'] and r['source_hashes_unchanged'] for r in (raw,qualification)):
        raise ValueError('complete independently qualified distance census required')
    means={row['profile']['current']:sum(F(n)*moment(duration,int(t)) for t,n in row['histogram'].items())/row['total'] for row in raw['rows']}
    if len(means)!=13:raise ValueError('all current board modes required')
    for mode,(lo,hi) in board_intervals(duration,third=True).items():
        if not lo<=means[mode]<=hi:raise ValueError('full mean outside old proved bounds')
    return means

def exact_shogi_contact_intervals(duration):
    board=exact_board_means(duration);scale=board['TR'];old=shogi_contact_intervals(duration)
    if scale<=0 or any(not 0<value<=scale for value in board.values()):raise ValueError('exact shared maximum failed')
    for mode,value in board.items():old['board',mode]=(value/scale,value/scale)
    return old

def exact_shogi_contact_choice(children,game,*,owner,duration,complete=False):
    if duration=='both':
        results={law:exact_shogi_contact_choice(children,game,owner=owner,duration=law,complete=complete) for law in ('geometric_half','linear_mixture')}
        if not all(r['complete'] for r in results.values()):return dict(complete=False,selected=None,by_law=results)
        picks={r['selected'] for r in results.values()}
        return dict(complete=True,selected=next(iter(picks)) if len(picks)==1 and None not in picks else None,by_law=results)
    base=shogi_contact_choice(children,game,owner=owner,duration=duration,complete=complete)
    if not base['complete']:return base
    boxes=exact_shogi_contact_intervals(duration);boxes[TERMINAL_UNIT]=(F(1),F(1))
    return dict(certified_ongoing_material_choice(base['features'],boxes,owner=owner,complete=True),features=base['features'],duration=duration,
        scope='same full-stock noncheck Shogi scope; exact virtual board distance means, held intervals unchanged')
