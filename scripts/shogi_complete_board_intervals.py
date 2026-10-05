"""Exact prefix plus proved support bounds; no point prices or goal labels."""
import json
from pathlib import Path
from fractions import Fraction as F
from scripts.shogi_pawn_promotion_support import pawn_support_interval

TOTAL=511920
ZERO=dict(P=72918,L=72918,N=114866,S=158,B=316)
BOUND=dict(P=22,L=17,N=19,S=22,B=24,G=16,R=3,
           TP=16,TL=16,TN=16,TS=16,TB=16,TR=3)
REPORT=Path(__file__).resolve().parents[1]/'docs/research/data/shared_contact_prefix_shogi_20261005.json'


def moment(duration,t):
    if duration=='geometric_half':return F(1,2)**t
    if duration=='linear_mixture':return F(2,(t+1)*(t+2))
    raise ValueError('only the two predeclared duration laws')


def board_intervals(duration,*,third=False):
    """Current-mode raw means; physical origin persists in upstream profiles."""
    moment(duration,1)
    raw=json.loads(REPORT.read_text(encoding='utf-8'))
    if not raw['complete'] or not raw['source_hashes_unchanged']:raise ValueError('incomplete prefix')
    rows={r['profile']['current']:r for r in raw['rows']}
    refinements={}
    if third:
        newer=json.loads((REPORT.parent/'shogi_small_three_prefix_20261005.json').read_text(encoding='utf-8'))
        if not newer['complete'] or not newer['source_hashes_unchanged']:raise ValueError('incomplete third prefix')
        refinements={r['profile']['current']:r for r in newer['rows']}
    if set(rows)!=set(BOUND):raise ValueError('whole mode population required')
    out={}
    for mode,r in rows.items():
        if r['total']!=TOTAL or r['direct']+r['second']+r['remaining']!=TOTAL:
            raise ValueError('lost world mass')
        tail=r['remaining']-ZERO.get(mode,0)
        if tail<0:raise ValueError('zero support overlaps exact prefix')
        exact=r['direct']*moment(duration,1)+r['second']*moment(duration,2)
        cutoff=3
        if mode in refinements:
            n=refinements[mode]
            if (n['direct'],n['second'])!=(r['direct'],r['second']):raise ValueError('prefix disagreement')
            exact+=n['third']*moment(duration,3);tail-=n['third'];cutoff=4
            if tail<0:raise ValueError('third prefix overlaps zero support')
        lo=(exact+tail*moment(duration,BOUND[mode]))/TOTAL
        hi=(exact+tail*moment(duration,cutoff))/TOTAL
        if mode=='P':lo,hi=pawn_support_interval(duration)
        out[mode]=(lo,hi)
    if third:
        for mode in ('TP','TL','TN','TS'):out[mode]=out['G']
    return out


def coupled_gap(duration,larger,smaller):
    """Named same-world simulations only; not arbitrary marginal ordering."""
    differences={('L','P'):19152,('TP','P'):27176,
                 ('TB','B'):22752,('TR','R'):20224}
    if (larger,smaller) not in differences:raise ValueError('no proved simulation')
    return F(differences[larger,smaller],TOTAL)*(moment(duration,1)-moment(duration,2))
