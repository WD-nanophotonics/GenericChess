"""Same-parent mask reweighting plus signed deadline moments, not game premiums."""
from fractions import Fraction as F
import json
from pathlib import Path
from scripts.shogi_complete_board_intervals import moment,BOUND,ZERO,TOTAL,board_intervals
DATA=Path(__file__).resolve().parents[1]/'docs/research/data'


def board_hand_gap(duration,*,normalized=False):
    moment(duration,1)
    raw=json.loads((DATA/'shared_contact_prefix_shogi_20261005.json').read_text())
    newer=json.loads((DATA/'shogi_small_three_prefix_20261005.json').read_text())
    if not all(r['complete'] and r['source_hashes_unchanged'] for r in (raw,newer)):raise ValueError('complete frozen prefixes required')
    rows={r['profile']['current']:r for r in raw['rows']}
    third={r['profile']['current']:r['third'] for r in newer['rows']}
    out={}
    for mode in 'PLNSGBR':
        ratio=(F(6,7)*F(79,70)+F(1,7)*F(79,63)) if mode=='P' else F(79,70 if mode=='L' else 61 if mode=='N' else 79)
        difference=lambda t:moment(duration,t)-ratio*moment(duration,t+1)
        row=rows[mode];masses={1:row['direct'],2:row['second']}
        if mode in third:masses[3]=third[mode]
        tail=TOTAL-ZERO.get(mode,0)-sum(masses.values());cutoff=max(masses)+1
        if tail<0:raise ValueError('lost/overlapping support mass')
        # Native R's remainder is exactly distance3, not an unresolved tail.
        candidates=(3,) if mode=='R' else range(cutoff,BOUND[mode]+1)
        minimum=min(difference(t) for t in candidates)
        lower=(sum(n*difference(t) for t,n in masses.items())+tail*minimum)/TOTAL
        if lower<=0:raise ValueError('declared native board/hand certificate fails')
        out[mode]=dict(lower=lower,mask_ratio_bound=ratio,tail_coefficient=minimum,
                       exact_masses=masses,reachable_tail=tail)
    if normalized:
        maximum=board_intervals(duration,third=True)['TR']
        if maximum[0]!=maximum[1] or maximum[0]<=0:raise ValueError('exact common scale required')
        out={k:dict(v,lower=v['lower']/maximum[0]) for k,v in out.items()}
    return out
