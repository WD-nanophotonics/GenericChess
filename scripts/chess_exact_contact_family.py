"""Separate fully qualified five-mode virtual means; original consumer unchanged."""
import json
from pathlib import Path
from fractions import Fraction as F
from scripts.native_chess_contact_intervals import native_contact_intervals,contact_interval_choice,TERMINAL_UNIT
from scripts.material_interval_choice import certified_ongoing_material_choice
DATA=Path(__file__).resolve().parents[1]/'docs/research/data'

def exact_chess_contact_intervals(duration):
    if duration not in ('geometric_half','linear_mixture'):raise ValueError('separate declared duration required')
    r=json.loads((DATA/'chess_zero_target_correction_20261005.json').read_text())
    if not r['complete'] or not r['source_hashes_unchanged']:raise ValueError('independently qualified complete census required')
    m=(lambda t:F(1,2)**t) if duration=='geometric_half' else (lambda t:F(2,(t+1)*(t+2)))
    means={mode:sum(F(n)*m(int(t)) for t,n in row['histogram'].items())/249984 for mode,row in r['rows'].items()}
    old=native_contact_intervals(duration);maximum=means['Q']
    if set(means)!=set('PNBRQ') or any(not 0<v<=maximum for v in means.values()):raise ValueError('complete common maximum failed')
    result={('board',mode):(value/maximum,value/maximum) for mode,value in means.items()}
    if any(not old[k][0]<=lo==hi<=old[k][1] for k,(lo,hi) in result.items()):raise ValueError('exact mean outside old sound envelope')
    return result

def exact_chess_contact_choice(children,game,*,owner,duration,complete=False):
    if duration=='both':
        results={law:exact_chess_contact_choice(children,game,owner=owner,duration=law,complete=complete) for law in ('geometric_half','linear_mixture')}
        if not all(r['complete'] for r in results.values()):return dict(complete=False,selected=None,by_law=results)
        picks={r['selected'] for r in results.values()}
        return dict(complete=True,selected=next(iter(picks)) if len(picks)==1 and None not in picks else None,by_law=results)
    base=contact_interval_choice(children,game,owner=owner,duration=duration,complete=complete)
    if not base['complete']:return base
    boxes=exact_chess_contact_intervals(duration);boxes[TERMINAL_UNIT]=(F(1),F(1))
    return dict(certified_ongoing_material_choice(base['features'],boxes,owner=owner,complete=True),features=base['features'],duration=duration,
        scope='same Western zero-rights/EP native/current scope; exact virtual means, no WDL substitution')
