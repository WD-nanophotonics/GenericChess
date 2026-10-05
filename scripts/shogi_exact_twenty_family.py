"""Exact20 virtual means under the same declared laws and old strict leaf scope."""
import json
from pathlib import Path
from fractions import Fraction as F
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.shogi_contact_interval_choice import shogi_contact_choice,TERMINAL_UNIT
from scripts.material_interval_choice import certified_ongoing_material_choice
DATA=Path(__file__).resolve().parents[1]/'docs/research/data'

def exact_twenty_intervals(duration):
    board=exact_board_means(duration);r=json.loads((DATA/'shogi_exact_held_reweight_20261005.json').read_text())
    if not r['complete'] or not r['source_hashes_unchanged']:raise ValueError('complete conditional held census required')
    scale=board['TR'];result={('board',mode):(value/scale,value/scale) for mode,value in board.items()}
    for row in r['rows']:
        value=F(row['means'][duration])/scale;result['hand',row['type']]=(value,value)
    if len(result)!=20 or any(not 0<lo==hi<=1 for lo,hi in result.values()):raise ValueError('complete exact common-scale family failed')
    return result

def exact_twenty_choice(children,game,*,owner,duration,complete=False):
    if duration=='both':
        results={law:exact_twenty_choice(children,game,owner=owner,duration=law,complete=complete) for law in ('geometric_half','linear_mixture')}
        if not all(r['complete'] for r in results.values()):return dict(complete=False,selected=None,by_law=results)
        picks={r['selected'] for r in results.values()}
        return dict(complete=True,selected=next(iter(picks)) if len(picks)==1 and None not in picks else None,by_law=results)
    base=shogi_contact_choice(children,game,owner=owner,duration=duration,complete=complete)
    if not base['complete']:return base
    boxes=exact_twenty_intervals(duration);boxes[TERMINAL_UNIT]=(F(1),F(1))
    return dict(certified_ongoing_material_choice(base['features'],boxes,owner=owner,complete=True),features=base['features'],duration=duration,
        scope='same strict noncheck full-stock Shogi; exact20 virtual means, no game-goal calibration')
