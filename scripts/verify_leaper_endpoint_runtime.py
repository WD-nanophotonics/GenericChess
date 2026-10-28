"""Saved original-data consumer: source bytes, full Core PV, metrics, no Player."""
import hashlib,json,math
from pathlib import Path
from collections import Counter
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.leaper_boolean_cost_pilot import signature
from scripts.research_record import write_record
HASH_FIELDS={'runtime_semantic_local_hash_updates','runtime_position_identity_hash_cached','runtime_semantic_full_diff_fallbacks'}
def sha(b):return hashlib.sha256(b).hexdigest()

def verify(base,out):
    base=Path(base);inputs_raw=(base/'frozen/inputs.json').read_bytes();inputs=json.loads(inputs_raw)['rows'];contexts={r['id']:make_session(r) for r in inputs};reports={};totalpv=0;totalreturns=0
    for name,width,planned in [('royal-cost',4,64),('binding-cost',4,64),('hash-composition',8,128)]:
        folder=base/name
        if not (folder/'summary.json').exists():continue
        frozen=json.loads((folder/'frozen.json').read_text());summary=json.loads((folder/'summary.json').read_text());assert frozen['inputs_sha256']==sha(inputs_raw)
        for p,item in frozen['sources'].items():assert sha(item['text'].encode('utf-8'))==item['sha256'],p
        files=sorted(folder.glob('return-*.json'));assert len(files)==planned and {int(p.stem.split('-')[-1]) for p in files}==set(range(planned));returns=[];pvcount=0;choices=0;groups=[]
        for slot,p in enumerate(files):
            d=json.loads(p.read_text());assert d['slot']==slot and d['status']=='RETURNED';root=inputs[slot//width];c,s=contexts[root['id']];assert d['record_before']==root['record'];assert d['binary_sha256_checked']==frozen['binary']['sha256'];decision=d['decision'];assert decision['runtime_depth_balanced'] and decision['native_legality_fallbacks']==decision['native_legality_operational_failures']==0
            assert all(math.isfinite(d[k]) and d[k]>=0 for k in ('wall_seconds','cpu_seconds','constructor_seconds'))
            selected=action(decision['action'],s);assert selected in s.legal_actions();choices+=1;pv=type(s).replay(c,s.to_record())
            if decision['principal_variation']:assert decision['principal_variation'][0]==decision['action']
            for value in decision['principal_variation']:pv.submit(action(value,pv));pvcount+=1
            if name=='hash-composition':
                a,b=d['arm'];assert bool(decision['runtime_semantic_local_hash_updates'])==a and decision['runtime_position_identity_hash_cached']==b
            elif d['on']:assert d['model_metrics'] is not None
            returns.append(d)
        for start in range(0,planned,width):
            calls=returns[start:start+width];complete=all(r['decision']['completed_depth']==3 and r['decision']['result_source']=='main_iteration' for r in calls)
            if complete:
                sig=[{k:v for k,v in signature(r['decision']).items() if name!='hash-composition' or k not in HASH_FIELDS} for r in calls];assert all(x==sig[0] for x in sig)
            groups.append({'id':inputs[start//width]['id'],'family':inputs[start//width]['family'],'complete':complete,'calls':calls})
        eligible=[g for g in groups if g['complete']];assert len(eligible)==summary['complete_parity_groups']
        if width==4:
            wall_on=sum(x['wall_seconds'] for g in eligible for x in g['calls'] if x['on']);wall_off=sum(x['wall_seconds'] for g in eligible for x in g['calls'] if not x['on']);cpu_on=sum(x['cpu_seconds'] for g in eligible for x in g['calls'] if x['on']);cpu_off=sum(x['cpu_seconds'] for g in eligible for x in g['calls'] if not x['on']);assert wall_on/wall_off==summary['wall_ratio_complete_groups'] and cpu_on/cpu_off==summary['cpu_ratio_complete_groups']
        else:
            totals={arm:{m:sum(x[m+'_seconds'] for g in eligible for x in g['calls'] if ''.join(str(int(z)) for z in x['arm'])==arm) for m in ('wall','cpu')} for arm in ('00','10','11','01')}
            for arm in totals:
                for metric in ('wall','cpu'):assert math.isclose(totals[arm][metric],summary['totals'][arm][metric],rel_tol=1e-14)
            for arm in ('10','11','01'):
                for metric in ('wall','cpu'):assert math.isclose(totals[arm][metric]/totals['00'][metric],summary['ratios_complete_groups'][arm][metric],rel_tol=1e-14)
        reports[name]={'returns':len(returns),'Core_selected_actions':choices,'Core_PVplies':pvcount,'complete_parity_groups':len(eligible),'binary_sha256':frozen['binary']['sha256'],'source_capsule_hashes':'PASS','actual_treatment':'PASS','numeric_reaggregation':'PASS'};totalpv+=pvcount;totalreturns+=len(returns)
    # Original64equalservice results use their own literal record/observer contract.
    folder=base/'qualification';files=sorted((folder/'returns').glob('*.json'));assert len(files)==64;qpv=0;retained_witness=0;truncated=0
    for p in files:
        r=json.loads(p.read_text());rid=r['query_id'].rsplit('-',1)[0];c,s=contexts[rid];assert r['record']==next(x['record'] for x in inputs if x['id']==rid);decision=r['decision'];assert decision['action']==decision['principal_variation'][0] if decision['principal_variation'] else True
        selected=action(decision['action'],s);assert selected in s.legal_actions();pv=type(s).replay(c,s.to_record())
        for v in decision['principal_variation']:pv.submit(action(v,pv));qpv+=1
        observed=r['observer'];assert not observed['errors'];truncated+=observed['dropped']>0;attempt=observed['retained_root_attempt']
        if observed['retained_changed_entries']:
            assert any(w['root_attempt']==attempt and w['return']=='NORMAL' and w['entry']=='AFTER_ORIGINAL_BUDGET_CHECK' for w in observed['witnesses']);retained_witness+=1
    reports['qualification']={'returns':64,'Core_selected_actions':64,'Core_PVplies':qpv,'queries_with_retained_positive_witness':retained_witness,'queries_with_truncated_witness_capture':truncated,'original_loaded_binary_sha256':'NOT_CAPTURED;latercostbinarycannotretroactivelypinoriginalqualification'}
    totalreturns+=64;totalpv+=qpv;result={'status':'PASS_SAVED_DATA_SCOPE','reports':reports,'total_returns':totalreturns,'total_literal_CorePVplies':totalpv,'new_Player_calls':0,'new_solver':0,'limits':'current sharedCore semanticreplay+independentarithmetic;not independenttiming/hardware/Coreimplementation orholdout;truncatedfullcausalgraphsUNKNOWN'};write_record(Path(out),result);print({k:v for k,v in result.items() if k!='reports'});return result


def verify_curve(base,out):
    base=Path(base);data=(base/'service-curve-inputs.json').read_bytes();roots=json.loads(data)['rows'];f=json.loads((base/'service-curve/frozen.json').read_text());assert sha(data)==f['inputs_sha256'];contexts=[make_session(r) for r in roots];pvs=0;counts=Counter();returned=[]
    for p,item in f['sources'].items():assert sha(item['text'].encode())==item['sha256']
    files=sorted((base/'service-curve').glob('return-*.json'));assert len(files)==192
    for i,p in enumerate(files):
        r=json.loads(p.read_text());c,s=contexts[i//12];assert r['slot']==i and r['record_before']==roots[i//12]['record'] and r['on']==(i%4 in (1,2));assert r['binary_sha256_checked']==f['binary']['sha256'];d=r['decision'];assert d['runtime_depth_balanced'] and d['runtime_position_identity_hash_cached'] is False;assert d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
        if r['on'] and d['runtime_pushes']>0:assert d['runtime_semantic_local_hash_updates']>0 and d['runtime_semantic_full_diff_fallbacks']==0
        assert action(d['action'],s) in s.legal_actions();pv=type(s).replay(c,s.to_record())
        for a in d['principal_variation']:pv.submit(action(a,pv));pvs+=1
        counts[d['result_source']]+=1;returned.append(r)
    groups=[]
    for start in range(0,192,4):
        calls=returned[start:start+4];keys=[json.dumps(x['decision']['action'],sort_keys=True) for x in calls];g={'slot':start,'stable_difference':keys[0]==keys[3] and keys[1]==keys[2] and keys[0]!=keys[1],'family':roots[start//12]['family'],'budget':(0.25,1,3)[start%12//4],'timing_eligible':all(x['wall_seconds']<=1.1*(0.25,1,3)[start%12//4] for x in calls)};groups.append(g)
    summary=json.loads((base/'service-curve/summary.json').read_text())
    for budget in (0.25,1,3):assert sorted({g['family'] for g in groups if g['budget']==budget and g['stable_difference'] and g['timing_eligible']})==summary['by_budget'][str(float(budget))]['stable_choice_difference_families']
    result={'status':'PASS','returns':192,'fullhistory_Core_choices':192,'literal_CorePVplies':pvs,'sources':dict(counts),'sources_bytes':'PASS','actual_localhashactivation':'PASS','new_Player':0,'new_games':0,'scope':'retainedbehaviornotaccuracy;independentarithmetic/sharedCore replay,not independenthardware'};write_record(Path(out),result);return result
