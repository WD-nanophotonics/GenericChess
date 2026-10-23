"""Descriptive paired utilities and target exposure; no fitting or new queries."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from fractions import Fraction
import gzip
import json
from math import tanh
from pathlib import Path

def average(rows):
    return [str(sum((Fraction(r[j]) for r in rows),Fraction())/len(rows)) for j in (0,1)]

def analyze(packet):
    slots=packet['slots']; games={r['slot']:r for r in packet['games']}; paired=defaultdict(dict)
    for s in slots:
        if s['phase']=='eval': paired[s['world'],s['index'],s['role']][s['arm']]=s
    results={}
    divergences=[]
    for arm,base in [('Mobility','Unit'),('TD','Mobility'),('TD','Unit')]:
        rows=[]
        for (w,context,role),arms in paired.items():
            a=arms[arm]; b=arms[base]
            bounds=[a['utility'][0]-b['utility'][1],a['utility'][1]-b['utility'][0]]
            rows.append(dict(world=w,context=context,role=role,bounds=bounds))
            if a['slot'] in games and b['slot'] in games:
                ga,gb=games[a['slot']],games[b['slot']]
                aa=ga['final_record']['actions']; bb=gb['final_record']['actions']
                i=next((i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y),None)
                # Equal complete records may differ only in unrelated metadata;
                # strict action lists/length define the trajectory comparison.
                divergences.append(dict(arm=arm,base=base,world=w,context=context,role=role,
                                        first_divergence_ply=i,identical=aa==bb,
                                        arm_utility=ga['utility'],base_utility=gb['utility'],
                                        arm_slot=a['slot'],base_slot=b['slot']))
        results[arm+'-'+base]=dict(planned_pairs=len(rows),mean_bounds=average([r['bounds'] for r in rows]),
                                  by_role={str(k):average([r['bounds'] for r in rows if r['role']==k]) for k in (0,1)},
                                  by_context={str(k):average([r['bounds'] for r in rows if r['context']==k]) for k in (0,1)},
                                  by_world={str(k):average([r['bounds'] for r in rows if r['world']==k]) for k in packet['config']['world_ids']},
                                  rows=rows)
    outcomes={}
    for phase in ['train','eval']:
        for arm in ['Unit','Mobility','TD']:
            selected=[s for s in slots if s['phase']==phase and s['arm']==arm]
            if not selected: continue
            outcomes[phase+'_'+arm]=dict(planned=len(selected),W=sum(s['utility']==[1,1] for s in selected),D=sum(s['utility']==[0,0] for s in selected),L=sum(s['utility']==[-1,-1] for s in selected),UNKNOWN=sum(s['utility'][0]!=s['utility'][1] for s in selected),mean_bounds=average([s['utility'] for s in selected]))
    exposure=Counter(); depths=Counter(); updates=[]
    for row in games.values():
        if row['phase']=='train':
            u=row['update']; exposure['observed_training_targets']+=u['observed_searches']; exposure['TD_terms']+=u['samples']; exposure['actual_changed_episodes']+=row['before']!=row['after']
            updates.append(dict(slot=row['slot'],world=row['world'],role=row['role'],before=row['before'],after=row['after'],delta=[b-a for a,b in zip(row['before'],row['after'])],**u))
        for q in row['queries']:
            if q['kind']!='candidate': continue
            r=q['receipt']; depths[row['phase']+':D'+str(r['completed_depth'])]+=1
            if row['phase']=='train' and r['complete']:
                if r['pv_terminal']: exposure['terminal_training_PVs']+=1
                else:
                    exposure['nonterminal_training_PVs']+=1
                    grad=[0 if i==0 else x*(1-tanh(r['value']/10.)**2)/10. for i,x in enumerate(r['pv_phi'])]
                    exposure['nonzero_trainable_gradient_PVs']+=any(grad)
                    for i,x in enumerate(r['pv_phi']):
                        exposure['channel_'+str(i)+'_nonzero']+=x!=0
    return dict(outcomes=outcomes,paired=results,divergences=divergences,training_exposure=exposure,depths=depths,updates=sorted(updates,key=lambda r:r['slot']),scope='Finite exposed-rule, policy-conditioned descriptive contrast. Prefix seeds separate train/eval but rules/layouts and source have already been exposed; no IID confidence, minimax-WDL, generic price or population claim.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('packet',type=Path); a=p.parse_args()
    print(json.dumps(analyze(json.loads(gzip.decompress(a.packet.read_bytes()))),ensure_ascii=True))
