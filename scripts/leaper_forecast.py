"""Evaluate frozen Leaper motion forecasts from CLOSED complete game receipts.

No queries, coefficient fitting, outcome filtering or population significance.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path
from scripts.leaper_design import load,write_record

def ranks(values):
    return [sum(v<x for v in values)+Fraction(sum(v==x for v in values)+1,2) for x in values]

def spearman(x,y):
    if len(x)!=len(y) or len(x)<2:raise ValueError('equal-length paired data required')
    a,b=ranks(x),ranks(y);m=Fraction(len(x)+1,2)
    num=sum((u-m)*(v-m) for u,v in zip(a,b));aa=sum((u-m)**2 for u in a);bb=sum((v-m)**2 for v in b)
    return None if not aa or not bb else float(num)/math.sqrt(float(aa*bb))

def means(slots):
    n=len(slots)
    if not n:raise ValueError('missing planned cells')
    return [sum(Fraction(s['utility'][i]) for s in slots)/n for i in (0,1)]

def analyze(paths,prediction_path):
    predictions=load(prediction_path);runs=[];all_slots=[];seen=set();records=[];registration=[]
    for d in paths:
        r=load(d/'results.json');assert r['status']=='CLOSED'
        reg=load(d/'registration.json');inputs=load(d/'inputs.json');registration.append(reg)
        assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==reg['input_sha256']
        if runs:assert inputs==runs[0]['inputs'],'same full rules/layout required for seed pooling'
        assert len(r['slots'])==reg['planned_games']
        for s in r['slots']:
            cell=(s['world'],s['pair'],s['role'],s['repeat']);assert cell not in seen,'duplicate role/seed cell';seen.add(cell)
            all_slots.append(s)
            if s['status']=='finished':records.append((d,s,load(d/s['receipt'])))
        runs.append({'inputs':inputs,'results':r})
    assert set(s['world'] for s in all_slots)==set(range(len(predictions['features'])))
    rows=[];pairs=registration[0]['pairs'];features=predictions['features']
    for w,feature in enumerate(features):
        assert runs[0]['inputs']['worlds'][w]['masks']==feature['masks']
        members=[s for s in all_slots if s['world']==w]
        per={p:means([s for s in members if s['pair']==p]) for p in pairs}
        ab=per['AB_RNG'];rng=per['RNG_RNG'];fl=per['FLOOR_RNG']
        # Missing/censored utility retains its finite completion interval.
        terms=Counter(s.get('terminal',{}).get('status','missing') for s in members)
        decisive=sum(s['utility'][0]==s['utility'][1] and s['utility'][0]!=0 for s in members)
        unknown=sum(s['utility'][0]!=s['utility'][1] for s in members)
        rows.append({'world':w,'masks':feature['masks'],'degree_sum':feature['degree_sum'],
            'planned':len(members),'unknown':unknown,'terminal_counts':dict(terms),
            'utility_bounds':{p:[str(v) for v in z] for p,z in per.items()},
            'AB_signed_utility_bounds':[str(v) for v in ab],
            'AB_minus_RNG_bounds':[str(ab[0]-rng[1]),str(ab[1]-rng[0])],
            'AB_minus_FLOOR_bounds':[str(ab[0]-fl[1]),str(ab[1]-fl[0])],
            'decisive_fraction_bounds':[str(Fraction(decisive,len(members))),str(Fraction(decisive+unknown,len(members)))]})
    def corr(field):
        bounds=[r[field] for r in rows]
        return None if any(a!=b for a,b in bounds) else spearman([Fraction(str(r['degree_sum'])) for r in rows],[Fraction(z[0]) for z in bounds])
    global_outcomes={p:dict(Counter(str(s['utility']) for s in all_slots if s['pair']==p)) for p in pairs}
    fullrecords=[json.dumps(row['final_record'],sort_keys=True,separators=(',',':')) for _,_,row in records]
    seeds=sorted(set(s['repeat'] for s in all_slots));role_seed=[]
    for rep in seeds:
        for role in (0,1):
            cells=[s for s in all_slots if s['repeat']==rep and s['role']==role]
            vals={p:means([s for s in cells if s['pair']==p]) for p in pairs}
            role_seed.append({'repeat':rep,'role':role,'means':{p:[str(v) for v in z] for p,z in vals.items()},'AB_minus_FLOOR':[str(vals['AB_RNG'][0]-vals['FLOOR_RNG'][1]),str(vals['AB_RNG'][1]-vals['FLOOR_RNG'][0])]})
    return {'status':'CLOSED','runs':[p.as_posix() for p in paths],'predictions_sha256':hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
        'rows':rows,'planned_physical_games':len(all_slots),'finished_games':len(records),'unique_full_records':len(set(fullrecords)),
        'controller_turn_receipts':sum(len(v['queries']) for _,_,v in records),'AB_returns':sum('decision' in q for _,_,v in records for q in v['queries']),
        'H1_raw_AB_RNG_signed_utility_spearman':corr('AB_signed_utility_bounds'),
        'H1_baseline_subtracted_spearman':corr('AB_minus_RNG_bounds'),
        'H1_arithmetic_ambiguity':'Frozen H1 wording did not specify subtracting RNG_RNG baseline. Both raw AB-versus-RNG signed utility and baseline-subtracted versions are reported; neither is silently chosen after results as the unique preregistered arithmetic.','primary_H2_spearman_decisive_fraction':corr('decisive_fraction_bounds'),
        'secondary_AB_minus_FLOOR_spearman':corr('AB_minus_FLOOR_bounds'),'global_outcomes':global_outcomes,'role_seed':role_seed,
        'interpretation':'All planned codes, average tied ranks. Frozen H1 arithmetic is ambiguous; raw AB_RNG and RNG_RNG-subtracted versions are both retained without selecting a favorable one. Undefined correlations are None, not zero. No population pvalue, coefficient fit, unseen-rule holdout, causal inference or independent trajectory claim.'}

def paired_capacity(candidate, baselines):
    """Complete source/rule/seed-matched budget contrast; never refill baselines."""
    c=load(candidate/'registration.json');cr=load(candidate/'results.json');ci=load(candidate/'inputs.json')
    assert cr['status']=='CLOSED'
    controls=('seed','caller_plies','rule_max_ply','repetition_limit','q','forced_check_depth','disk_cache','TT','source_sha256')
    old={}
    for d in baselines:
        b=load(d/'registration.json');br=load(d/'results.json');assert br['status']=='CLOSED'
        assert load(d/'inputs.json')==ci,'capacity contrasts require identical full rules and profiles'
        assert all(c[k]==b[k] for k in controls),'unmatched control'
        for slot in br['slots']:
            if slot['pair']!='AB_RNG':continue
            key=(slot['world'],slot['role'],slot['repeat']);assert key not in old
            old[key]=(d,slot)
    rows=[]
    for slot in cr['slots']:
        assert slot['pair']=='AB_RNG'
        d,base=old[(slot['world'],slot['role'],slot['repeat'])]
        delta=[slot['utility'][0]-base['utility'][1],slot['utility'][1]-base['utility'][0]]
        row={'world':slot['world'],'role':slot['role'],'repeat':slot['repeat'],'candidate_slot':slot['slot'],'baseline_slot':base['slot'],
             'baseline_run':d.as_posix(),'utility_difference_bounds':delta,'first_different_action':None,'full_trajectory_identical':None}
        if slot['status']==base['status']=='finished':
            a=load(candidate/slot['receipt']);b=load(d/base['receipt']);assert a['rng_seeds']==b['rng_seeds'] and a['policy_by_actor']==b['policy_by_actor']
            row['full_trajectory_identical']=a['final_record']==b['final_record']
            for qa,qb in zip(a['queries'],b['queries']):
                assert qa['state_sha256']==qb['state_sha256']
                if qa['action']!=qb['action']:
                    row['first_different_action']={'ply':qa['root_ply'],'actor':qa['actor'],'candidate':qa,'baseline':qb};break
            row['actual_candidate_AB_nodes']=sum(q['decision']['nodes'] for q in a['queries'] if 'decision' in q)
            row['actual_baseline_AB_nodes']=sum(q['decision']['nodes'] for q in b['queries'] if 'decision' in q)
            row['candidate_policy_seconds']=sum(q['seconds'] for q in a['queries'])
            row['baseline_policy_seconds']=sum(q['seconds'] for q in b['queries'])
        rows.append(row)
    n=len(rows);perworld=[]
    for w in range(len(ci['worlds'])):
        group=[r for r in rows if r['world']==w]
        perworld.append({'world':w,'masks':ci['worlds'][w]['masks'],'planned':len(group),'difference_bounds':[str(sum(Fraction(r['utility_difference_bounds'][i]) for r in group)/len(group)) for i in (0,1)]})
    return {'status':'CLOSED','new_candidate_games':n,'reused_baseline_frames':n,'difference_bounds':[str(sum(Fraction(r['utility_difference_bounds'][i]) for r in rows)/n) for i in (0,1)],'per_world':perworld,'rows':rows,
        'scope':'Same complete rules/profile/source and actor seeds; only node budget differs. RNG consumption diverges after changed actions. Finite observed utility, not monotone optimal strength or independent sample CI.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--run',type=Path,action='append',required=True);p.add_argument('--predictions',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=analyze(a.run,a.predictions);write_record(a.output,result);print(json.dumps({k:v for k,v in result.items() if k not in ('rows','role_seed')},indent=2))
