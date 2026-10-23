"""Post-hoc target sensitivity on frozen saved PVs, without fitting or search."""
import argparse
from collections import defaultdict
from fractions import Fraction
import gzip
import json
from math import tanh,sqrt
from pathlib import Path

def rank(rows):
    a=[[Fraction(x) for x in r] for r in rows if any(r)]
    rank=0
    for j in range(2):
        pivot=next((i for i in range(rank,len(a)) if a[i][j]),None)
        if pivot is None: continue
        a[rank],a[pivot]=a[pivot],a[rank]
        d=a[rank][j]; a[rank]=[x/d for x in a[rank]]
        for i in range(len(a)):
            if i==rank: continue
            d=a[i][j]; a[i]=[x-d*y for x,y in zip(a[i],a[rank])]
        rank+=1
        if rank==2: break
    return rank

def analyze(p):
    byworld=defaultdict(list); episodes=[]
    for g in p['games']:
        if g['phase']!='train': continue
        receipts=[q['receipt'] for q in g['queries'] if q['kind']=='candidate' and q['receipt']['complete']]
        pairs=[]
        for r in receipts:
            if not r['pv_terminal']:
                byworld[g['world']].append(r['pv_phi'][1:3])
        for weights in (g['before'],g['after']):
            v=[tanh(r['value']/10.) if r['pv_terminal'] else tanh(sum(x*w for x,w in zip(r['pv_phi'],weights))/10.) for r in receipts]
            errors=[b-a for a,b in zip(v,v[1:])]
            if v and g['outcome'] is not None: errors.append(g['outcome']-v[-1])
            pairs.append(sum(e*e/2 for e in errors)/max(1,len(errors)))
            if weights==g['before']:
                nonzero_errors=sum(e!=0 for e in errors)
                incoming_terminal_errors=sum(e!=0 and i+1<len(receipts) and receipts[i+1]['pv_terminal'] for i,e in enumerate(errors))
                last_error=errors[-1] if errors else None
        episodes.append(dict(slot=g['slot'],world=g['world'],role=g['role'],targets=len(receipts),
                             delta_l2=sqrt(sum((a-b)**2 for a,b in zip(g['before'],g['after']))),
                             old_PV_TD_loss_before=pairs[0],old_PV_TD_loss_after=pairs[1],
                             loss_difference=pairs[1]-pairs[0],terminal_final_credit=g['update']['terminal_credit_l1']))
        episodes[-1].update(nonzero_errors=nonzero_errors,incoming_terminal_search_errors=incoming_terminal_errors,last_error=last_error)
    return dict(world_trainable_feature_rank={str(w):rank(rows) for w,rows in byworld.items()},
                episodes=episodes,loss_decreased=sum(e['loss_difference']<0 for e in episodes),
                loss_increased=sum(e['loss_difference']>0 for e in episodes),
                loss_equal=sum(e['loss_difference']==0 for e in episodes),
                scope='Saved frozen leaf-path diagnostic only; new weights could choose other PVs. Rank of observed B/C features is not identifiability of strategic prices. TD semi-gradient need not minimize the recomputed TD-residual objective. No hyperparameter selection or new rollout.')

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__); a.add_argument('packet',type=Path); args=a.parse_args()
    print(json.dumps(analyze(json.loads(gzip.decompress(args.packet.read_bytes()))),ensure_ascii=True))
