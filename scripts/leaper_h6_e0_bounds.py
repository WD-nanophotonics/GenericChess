"""Finite shared-UNKNOWN score bounds for the frozen initial-mu E0 handoff."""
from fractions import Fraction as F
from pathlib import Path
import json,time
from collections import Counter
from datetime import datetime,timezone
from scripts import leaper_design as L
from scripts.leaper_parity_scope import adjacent,xy,digest
from tools.local_agent.common import write_json

def now():return datetime.now(timezone.utc).isoformat()
def geometry_certificate(n=3):
    rows=[]
    for v in range(n*n):
        for k in range(n*n):
            if adjacent(xy(k,n),xy(v,n)):continue
            vx,vy=xy(v,n);kx,ky=xy(k,n)
            aa=[(vx+dx,vy+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)) if 0<=vx+dx<n and 0<=vy+dy<n and not adjacent((vx+dx,vy+dy),(kx,ky))]
            assert aa
            rows.append({'victim':v,'other_royal':k,'ordinary_global_colour':(vx+vy)%2,'escape':aa[0]})
    return rows

def colour_condition(family,row):
    # Exact generated rule template and literal validated root, not arbitrary DSL.
    rr=L.ruleset_from_dict(family['rule']);ms=family['masks']
    from dataclasses import replace
    from scripts.leaper_h6_e0 import base_rule
    template=base_rule(*ms,row['placement'])
    if L.ruleset_to_dict(replace(rr,initial_position=template.initial_position,initial_setup_options=()),include_metadata=True)!=L.ruleset_to_dict(template,include_metadata=True):return False
    if rr.board_size!=3 or rr.max_ply!=6 or rr.repetition_limit!=2 or rr.repetition_policy!='draw' or rr.stalemate_result!='draw' or rr.capture_disposition!='remove_from_game' or rr.semantic_actions or rr.declarations or rr.automatic_adjudications or rr.repeated_cycle_target_conditions or rr.no_progress_draw:return False
    if any((dx+dy)%2 for m in ms for dx,dy in L.offsets(m)):return False
    if any(t.is_promotable or t.promotion_target_ids for t in rr.piece_types):return False
    if any(any(any(z) for z in masks) for masks in rr.drop_allowed.values()):return False
    k,a,v,b=row['placement'];return sum(xy(a,3))%2==sum(xy(b,3))%2

def contrast(rows,families,model,baseline,conditional):
    nfamily=len(families);lo=hi=F(0);by=[]
    for fam in families:
        rr=[r for r in rows if r['family']==fam['family']];a=b=F(0)
        for r in rr:
            pp=F(str(r['predictions'][model]));qq=F(str(r['predictions'][baseline]));d0=pp*pp-qq*qq;d1=d0-2*(pp-qq)
            if r['literal_oneply_positive']:low=high=d1
            elif conditional and r['proposed_colour_negative']:low=high=d0
            else:low=min(d0,d1);high=max(d0,d1)
            a+=low;b+=high
        a/=len(rr);b/=len(rr);lo+=a/nfamily;hi+=b/nfamily;by.append({'family':fam['family'],'bounds':[str(a),str(b)]})
    return {'lower':str(lo),'upper':str(hi),'float':[float(lo),float(hi)],'family_bounds':by,'unit':'equaldefined-family weight, uniformadmittedinitiallayout withinfamily; SAMEunknown label inbothscores; negativeismodelimprovement','conditional_on_colour_theorem':conditional}

def contrast_family_rate(rows,families,model,baseline,conditional):
    """Score family MEAN predictions against prevalence, not varying root scores."""
    nfamily=len(families);lo=hi=F(0);by=[]
    for fam in families:
        rr=[r for r in rows if r['family']==fam['family']];n=len(rr)
        p=sum(F(str(r['predictions'][model])) for r in rr)/n
        q=sum(F(str(r['predictions'][baseline])) for r in rr)/n
        positive=sum(r['literal_oneply_positive'] for r in rr)
        negative=sum(r['proposed_colour_negative'] for r in rr) if conditional else 0
        rlo=F(positive,n);rhi=F(n-negative,n)
        a=p*p-q*q-2*(p-q)*rlo;b=p*p-q*q-2*(p-q)*rhi
        low=min(a,b);high=max(a,b);lo+=low/nfamily;hi+=high/nfamily
        by.append({'family':fam['family'],'model_rate_prediction':str(p),'baseline_rate_prediction':str(q),'true_rate_bounds':[str(rlo),str(rhi)],'contrast_bounds':[str(low),str(high)]})
    return {'lower':str(lo),'upper':str(hi),'float':[float(lo),float(hi)],'family_bounds':by,'unit':'equaldefined-familymean RATEsquarederror; meanpredictionsbroadcast asconstants overroots. NotoriginalwithinrootconditionalBrier.','conditional_on_colour_theorem':conditional}

def analyze(source,output):
    start=now();tick=time.perf_counter();p=L.load(source);assert p['status']=='CLOSED';families=[f for f in p['families'] if f['status']=='CLOSED'];rows=[];witnesses=[];summary=[];cert=geometry_certificate()
    for f in families:
        c=L.compile_rule(L.ruleset_from_dict(f['rule']));rr=[r for r in p['rows'] if r['family']==f['family']];cnt=Counter()
        for r in rr:
            positive=bool(r['feature_oneply_scoring_child']);negative=colour_condition(f,r)
            assert not (positive and negative)
            cnt['roots']+=1;cnt['literal_oneply_positive']+=int(positive);cnt['proposed_colour_negative']+=int(negative)
            predictions={**r['predictions'],'v2_exposed_colour_plus_oneply':0.0 if negative else r['predictions']['oneply_augmented_cooperative']}
            rows.append({'family':f['family'],'fingerprint':f['fingerprint'],'mu_id':f['mu_id'],'setup_key':r['setup_key'],'state_sha256':r['state_sha256'],'literal_oneply_positive':positive,'proposed_colour_negative':negative,'predictions':predictions})
            if positive:
                ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(r['full_record'])));w=next(z for z in r['actions'] if z['terminal']['winner'] is not None);ss.submit(L.match_action(ss,w['action']));assert ss.result.winner is not None
                witnesses.append({'family':f['family'],'source_state_sha256':r['state_sha256'],'complete_record':L.record_value(ss.to_record()),'final_state_sha256':L.state_sha(ss.state),'terminal':L.record_value(ss.result)})
        cnt['remaining_UNKNOWN']=cnt['roots']-cnt['literal_oneply_positive']-cnt['proposed_colour_negative'];summary.append({'family':f['family'],'masks':f['masks'],**dict(cnt)})
    pairs=[('oneply_augmented_cooperative','geometric_cooperative'),('geometric_cooperative','uninformative_cooperative'),('oneply_augmented_cooperative','same_board_roster_cooperative'),('v2_exposed_colour_plus_oneply','oneply_augmented_cooperative'),('v2_exposed_colour_plus_oneply','uninformative_cooperative'),('v2_exposed_colour_plus_oneply','same_board_roster_cooperative')]
    contrasts={a+'-minus-'+b:{'literal_positives_only':contrast(rows,families,a,b,False),'with_proposed_colour_binding':contrast(rows,families,a,b,True)} for a,b in pairs}
    rate_contrasts={a+'-minus-'+b:{'literal_positives_only':contrast_family_rate(rows,families,a,b,False),'with_proposed_colour_binding':contrast_family_rate(rows,families,a,b,True)} for a,b in pairs}
    prevalence={'lower':str(sum(F(s['literal_oneply_positive'],s['roots']) for s in summary)/len(summary)),'upper':str(sum(F(s['roots']-s['proposed_colour_negative'],s['roots']) for s in summary)/len(summary)),'condition':'upperconditionalonproposedcolourtheorem, beforeindependentAUXtruth. Root-levelmixture, notoneexistentialbitperfamily.'}
    result={'status':'CLOSED_CONDITIONAL_ANALYSIS_NOT_INDEPENDENT_CALIBRATION','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'source_sha256':L.sha(source),'source_code_sha256':L.sha(Path(__file__)),'defined_families':len(families),'unavailable_family_ids':[f['family'] for f in p['families'] if f['status']=='MU_UNAVAILABLE'],'planned12_mean':'UNDEFINED;missingfamilymu hasnosupport, neverimputeorreplace','rows':rows,'oneply_positive_witnesses':witnesses,'colour_geometry_certificate':cert,'summary':summary,'prevalence_bounds':prevalence,'contrasts':contrasts,'rule_prevalence_contrasts':rate_contrasts,'target_distinction':'RootconditionalBriergain does NOT imply familymean-rate MSEgain. Brier=rateMSE+r(1-r) only when SAMEconstant forecast isbroadcast acrossrootmu.','v1_predictions_unchanged':True,'v2_status':'PosthocanalyticdevelopmentusingPUBLICpreviousAUXproofpremise, notblind/test-refit success. Independentmatching H6truth stillpending.','new_Player_calls':0,'new_solver_calls':0};write_json(output,result);print(summary);print(prevalence);print('rootconditional',{k:v['with_proposed_colour_binding']['float'] for k,v in contrasts.items()});print('ruleprevalence',{k:v['with_proposed_colour_binding']['float'] for k,v in rate_contrasts.items()});return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.source,a.output)
