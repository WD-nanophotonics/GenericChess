"""Compare fixed final models with EXACT old controls on the same EVAL roots."""
import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path

def mean(rows):
    return [str(sum((Fraction(r[j]) for r in rows),Fraction())/len(rows)) for j in (0,1)]

def compare(old,new,old_sha,new_sha):
    a=json.loads(gzip.decompress(old)); b=json.loads(gzip.decompress(new))
    roots=lambda p:{(r['world'],r['index']):r for r in p['inputs']['roots'] if r['phase']=='eval'}
    assert roots(a)==roots(b)
    assert a['config']['candidate']==b['config']['candidate'] and a['config']['opponent']==b['config']['opponent']
    slots={(s['world'],s['index'],s['role'],s['arm']):s for s in a['slots'] if s['phase']=='eval'}
    games={g['slot']:g for g in a['games']}
    newgames={g['slot']:g for g in b['games']}
    rows=[]
    for s in b['slots']:
        if s['phase']!='eval': continue
        key=(s['world'],s['index'],s['role']); root=roots(b)[key[:2]]
        r=dict(world=s['world'],context=s['index'],role=s['role'],root=root['id'],new_slot=s['slot'],TD_utility=s['utility'])
        for arm in ('Unit','Mobility','TD'):
            oldslot=slots[(*key,arm)]; oldgame=games[oldslot['slot']]
            assert oldgame['root']==root['id']
            r[arm+'_old_slot']=oldslot['slot']; r['old_'+arm+'_utility']=oldslot['utility']
            r['TD64_minus_'+arm+'4' if arm=='TD' else 'TD64_minus_'+arm]=[s['utility'][0]-oldslot['utility'][1],s['utility'][1]-oldslot['utility'][0]]
            if s['slot'] in newgames:
                newgame=newgames[s['slot']]
                aa=newgame['final_record']['actions']; bb=oldgame['final_record']['actions']
                r[arm+'_identical_trajectory']=aa==bb
                r[arm+'_first_divergence_ply']=next((i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y),None)
                r['new_candidate_queries']=sum(q['kind']=='candidate' for q in newgame['queries'])
                r['old_'+arm+'_candidate_queries']=sum(q['kind']=='candidate' for q in oldgame['queries'])
        rows.append(r)
    contrasts={}
    for name in ('TD64_minus_Unit','TD64_minus_Mobility','TD64_minus_TD4'):
        contrasts[name]=dict(mean_bounds=mean([r[name] for r in rows]),
                             by_role={str(k):mean([r[name] for r in rows if r['role']==k]) for k in (0,1)},
                             by_context={str(k):mean([r[name] for r in rows if r['context']==k]) for k in (0,1)},
                             by_world={str(k):mean([r[name] for r in rows if r['world']==k]) for k in b['config']['world_ids']})
    utils=[r['TD_utility'] for r in rows]
    return dict(exact_old_control_sha256=old_sha,new_packet_sha256=new_sha,
                new_physical_eval_games=sum(s['phase']=='eval' and s['status']!='not_started' for s in b['slots']),
                reused_free_control_games=32,reused_old_TD4_games=16,
                final_TD64=dict(W=utils.count([1,1]),D=utils.count([0,0]),L=utils.count([-1,-1]),UNKNOWN=sum(u[0]!=u[1] for u in utils)),
                contrasts=contrasts,rows=rows,
                scope='Same exposed EVAL frames; exact old controls are reuse, not new calls or independent samples. TD4 and TD64 use distinct TRAIN seed streams, so their difference is not a pure episode-count causal effect. No checkpoint/hyperparameter selection or new-rule generalization.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('old',type=Path); p.add_argument('new',type=Path); a=p.parse_args()
    x=a.old.read_bytes(); y=a.new.read_bytes()
    print(json.dumps(compare(x,y,hashlib.sha256(x).hexdigest(),hashlib.sha256(y).hexdigest()),ensure_ascii=True))
