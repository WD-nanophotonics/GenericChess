"""Frozen root-feature E0 versus complete-policy Leaper interactions.

Uses retained full histories and existing bounded research producers, never an
oracle or game-selection filter. Predictions are uncalibrated hypotheses.
"""
from __future__ import annotations
import argparse, json, time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from scripts import leaper_design as L


def freeze_predictions(d):
    assert not(d/'e0-predictions.json').exists()
    r=L.load(d/'registration.json');ws=L.load(d/'inputs.json')['worlds'];pf=L.load(d/'preflight.json')
    assert pf['status']=='CLOSED' and not pf['missing']
    assert not(d/'results.json').exists(), 'predict before fitness'
    lookup={(x['world'],x['policy']):x for x in pf['rows']};rows=[]
    for w in ws:
        terminal=w['initial_terminal']['status']!='ongoing';actions={}
        if not terminal:
            for p in ('S3','S4','U3','U4'):
                x=lookup[(w['world'],p)];actions[p]=x['decision']['action']
            gap3=actions['S3']!=actions['U3'];gap4=actions['S4']!=actions['U4']
            feature=gap3!=gap4 or actions['S3']!=actions['S4'] or actions['U3']!=actions['U4']
        else:feature=False
        rows.append({'world':w['world'],'code_world':w['code_world'],'placement_index':w['placement_index'],'prefix_index':w['prefix_index'],'terminal_at_start':terminal,'root_actions':actions,'positive_feature':feature,'probability_any_role_nonzero_interaction':0 if terminal else r.get('calibrated_probability_by_feature',{}).get(str(feature),.75 if feature else .25),'zero_information_baseline_probability':0 if terminal else r.get('calibrated_constant_probability',.5)})
    out={'frozen_at':datetime.now(timezone.utc).isoformat(),'input_sha256':L.sha(d/'inputs.json'),'registration_sha256':L.sha(d/'registration.json'),'preflight_sha256':L.sha(d/'preflight.json'),'producer_source_sha256':L.sha(Path(__file__)),'rows':rows,'truth_scope':r['E0_prediction_rule'],'new_fitness_at_freeze':0}
    L.write_record(d/'e0-predictions.json',out);return out


def interaction_bounds(cells):
    # I=(U4-S4)-(U3-S3); no missing-as-draw or adaptive denominator.
    coeff={'U4':1,'S4':-1,'U3':-1,'S3':1}
    return [sum(a*cells[p][0 if a>0 else 1] for p,a in coeff.items()),sum(a*cells[p][1 if a>0 else 0] for p,a in coeff.items())]


def full_rule_code(world):
    """Read all ordinary movement orbits; legacy masks may truncate C."""
    rule=L.ruleset_from_dict(world['rule']);code=[]
    for t in rule.piece_types:
        if t.is_anchor:continue
        actual={a.offset for a in t.movement_atoms}
        candidates=[mask for mask in range(1,32) if set(L.offsets(mask))==actual]
        if len(candidates)!=1:raise ValueError('E0 code strata require exact plain symmetric Leaper masks')
        code.append(candidates[0])
    if 'code' in world and list(world['code'])!=code:raise ValueError('full code metadata disagrees with actual rule')
    return tuple(code)


def brier_gain_bounds(probability, baseline, label=None):
    """Baseline score minus predictor score, retaining both possible labels."""
    if not(0<=probability<=1 and 0<=baseline<=1) or label not in (None,0,1):raise ValueError('binary probability and label required')
    ys=(0,1) if label is None else (label,)
    values=[(baseline-y)**2-(probability-y)**2 for y in ys]
    return [min(values),max(values)]


def analyze(d):
    tick=time.perf_counter();r=L.load(d/'registration.json');res=L.load(d/'results.json');pred=L.load(d/'e0-predictions.json');ws=L.load(d/'inputs.json')['worlds']
    assert res['status']=='CLOSED' and pred['input_sha256']==L.sha(d/'inputs.json') and pred['registration_sha256']==L.sha(d/'registration.json')
    lookup={(x['world'],x['role'],x['pair'].split('_vs_')[0]):x for x in res['slots']};roles=[];worlds=[];depth=Counter();nodes=qnodes=returns=0;under=[];literal=set()
    for slot in res['slots']:
        if slot['status']!='finished':continue
        g=L.load(d/slot['receipt']);literal.add(json.dumps([ws[slot['world']]['rule'],g['final_record']],sort_keys=True,separators=(',',':')))
        for q in g['queries']:
            dec=q.get('decision')
            if not dec:continue
            returns+=1;nodes+=dec['nodes'];qnodes+=dec['qnodes'];depth[(q['policy'],dec['completed_depth'],q['requested_depth'])]+=1
            if dec['completed_depth']<q['requested_depth'] and dec['completed_depth']!=0:under.append({'slot':slot['slot'],'ply':q['root_ply'],'policy':q['policy'],'requested':q['requested_depth'],'completed':dec['completed_depth']})
    for w,p in zip(ws,pred['rows'],strict=True):
        rr=[]
        for role in (0,1):
            cells={k:lookup[(w['world'],role,k)]['utility'] for k in ('S3','S4','U3','U4')};b=interaction_bounds(cells)
            z={'world':w['world'],'code_world':w['code_world'],'placement_index':w['placement_index'],'prefix_index':w['prefix_index'],'role':role,'cells':cells,'delta3':[cells['U3'][0]-cells['S3'][1],cells['U3'][1]-cells['S3'][0]],'delta4':[cells['U4'][0]-cells['S4'][1],cells['U4'][1]-cells['S4'][0]],'interaction':b,'complete':all(v[0]==v[1] for v in cells.values())};roles.append(z);rr.append(z)
        witness=any(z['interaction'][0]>0 or z['interaction'][1]<0 for z in rr)
        label=1 if witness else 0 if all(z['interaction']==[0,0] for z in rr) else None
        prob=p['probability_any_role_nonzero_interaction'];base=p['zero_information_baseline_probability']
        worlds.append({**p,'label_any_role_nonzero_interaction':label,'brier':None if label is None else (prob-label)**2,'baseline_brier':None if label is None else (base-label)**2,'classification':'UNKNOWN' if label is None else ('TP' if p['positive_feature'] else 'FN') if label else ('FP' if p['positive_feature'] else 'TN'),'all_four_cells_complete_both_roles':all(z['complete'] for z in rr)})
    known=[w for w in worlds if w['label_any_role_nonzero_interaction'] is not None];ongoing=[w for w in known if not w['terminal_at_start']]
    summaries=[]
    for name,selected in [('all',roles),('excluding_old_positive_rule',[z for z in roles if full_rule_code(ws[z['world']])!=(23,28,31)])]+[(f'role{a}',[z for z in roles if z['role']==a]) for a in (0,1)]+[(f'layout{a}',[z for z in roles if z['placement_index']==a]) for a in (0,1)]:
        summaries.append({'stratum':name,'planned_role_histories':len(selected),'complete':sum(z['complete'] for z in selected),'delta3_mean_bounds':[sum(z['delta3'][i] for z in selected)/len(selected) for i in (0,1)],'delta4_mean_bounds':[sum(z['delta4'][i] for z in selected)/len(selected) for i in (0,1)],'interaction_mean_bounds':[sum(z['interaction'][i] for z in selected)/len(selected) for i in (0,1)],'nonzero_complete_interactions':sum(z['complete'] and z['interaction']!=[0,0] for z in selected)})
    out={'status':'CLOSED','world_predictions':worlds,'role_interactions':roles,'summary':summaries,'classification_counts':dict(Counter(w['classification'] for w in worlds)),'known_labels':len(known),'planned_histories':len(worlds),'brier_sum':sum(w['brier'] for w in known),'baseline_brier_sum':sum(w['baseline_brier'] for w in known),'ongoing_brier_sum':sum(w['brier'] for w in ongoing),'ongoing_baseline_brier_sum':sum(w['baseline_brier'] for w in ongoing),'new_game_Player_returns':returns,'nodes':nodes,'qnodes':qnodes,'undercompleted_nonzero_depth':under,'depth_counts':[{'policy':k[0],'completed':k[1],'requested':k[2],'calls':v} for k,v in sorted(depth.items())],'physical_deployments':sum(x['status']=='finished' for x in res['slots']),'terminal_prefix_deployments':sum(ws[x['world']]['initial_terminal']['status']!='ongoing' and x['status']=='finished' for x in res['slots']),'literal_game_records':len(literal),'seconds':time.perf_counter()-tick,'scope':'Finite layer2 complete-policy utility labels, exposed six-rule family. No gameWDL/structuraldeadzone truth, unseenrulegeneralization, IID/calibration estimate, resource equality or coordinate adoption. Baseline and predictor frozen prefitness; allslots attempted independent of rootactions. D0 immediate-win claims require actual Core replay qualification.'}
    gains=[brier_gain_bounds(w['probability_any_role_nonzero_interaction'],w['zero_information_baseline_probability'],w['label_any_role_nonzero_interaction']) for w in worlds]
    out['all_planned_Brier_gain_mean_bounds']=[sum(v[i] for v in gains)/len(worlds) for i in (0,1)]
    out['feature_table_interpretation']='classification_counts refer to the original positive_feature, NOT calibratedprobability>=.5; E1 assessed withproperBrier.'
    out['practical_mean_gain_threshold']=.02 if 'calibration'in r else None
    out['retaining_feature_criterion_passed']=out['all_planned_Brier_gain_mean_bounds'][0]>=.02 if 'calibration'in r else None
    out['original_E0_Brier_sum_known']=sum(((0 if w['terminal_at_start'] else .75 if w['positive_feature'] else .25)-w['label_any_role_nonzero_interaction'])**2 for w in known)
    out['untrained_half_baseline_Brier_sum_known']=sum(((0 if w['terminal_at_start'] else .5)-w['label_any_role_nonzero_interaction'])**2 for w in known)
    L.write_record(d/'e0-analysis.json',out);print({k:out[k] for k in ('classification_counts','known_labels','brier_sum','baseline_brier_sum','new_game_Player_returns','physical_deployments','terminal_prefix_deployments','seconds')},flush=True);return out


def execute(d):
    """Preflight, freeze forecasts, execute once under the original cost cap."""
    r=L.load(d/'registration.json')
    assert not(d/'preflight.json').exists() and not(d/'results.json').exists()
    assert r['expected_seconds']<7200 and r['logical_cap_seconds']<7200
    w={'started_at':datetime.now(timezone.utc).isoformat(),'activity':'research'}
    L.write_record(d/'execution-start.json',w)
    try:
        L.preflight(d);pf=L.load(d/'preflight.json')
        L.write_record(d/'preflight-maximum-call-original.json',pf)
        forecast=r['empirical_loop_forecast_seconds']+r['preparation_seconds']+pf['seconds']
        assert not pf['missing'] and forecast<r['whole_cap_seconds'] and max(x['seconds'] for x in pf['rows'])<5
        pf.update(cost_gate_passed=True,empirical_whole_game_forecast_seconds=forecast,gate_method=r['cost_basis'])
        L.write_record(d/'preflight.json',pf)
        f=freeze_predictions(d);print('PREDICTIONS_FROZEN',len(f['rows']),flush=True)
        L.run(d);w['returncode']=0
    finally:
        w['ended_at']=datetime.now(timezone.utc).isoformat()
        L.write_record(d/'actual-execution-window.json',w);print('WINDOW_CLOSED',w,flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=('freeze','analyze','execute'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();{'freeze':freeze_predictions,'analyze':analyze,'execute':execute}[a.command](a.output)
if __name__=='__main__':main()
