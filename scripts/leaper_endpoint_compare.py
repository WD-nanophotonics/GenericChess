"""Frozen equal-full-service threat-order comparison; no refill or defaults.

Qualifier gate controls games. Cold Player/TT per decision in both arms; compiled
RuleSet/session already admitted outside service. Observer setup, constructor,
choose and observer-result aggregation are INSIDE the common caller deadline.
Core gameplay/save/verification overhead is recorded separately, not hidden.
"""
import hashlib,json,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from scripts.leaper_pvs_quality_pilot import make_session,CallerDeadline,provider_metrics,metric_delta
from scripts.leaper_entry_observer import EntryObserver
from scripts.leaper_threat_policy import threat_policy
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json
from tools.local_agent.session import record_work

def stamp():return datetime.now(timezone.utc).isoformat()
def action_key(a):return json.dumps(action_to_dict(a),sort_keys=True,separators=(',',':'))
def admissible(plan):
    flags=read_json(Path('.local_agent/rollout.json'))
    if any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')):return 'scoped_stop'
    if (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<2:return 'whole_deadline'
    return None

def query(c,s,on,qid,out,plan):
    before=s.to_record();begin=stamp();t0=time.perf_counter();cpu=time.process_time();observer=EntryObserver(qid,limit=256);token=CallerDeadline(t0+plan['service_seconds']);p=None
    try:
        with threat_policy(on),observer.installed():
            p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=False,use_aspiration=False),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
            pm=provider_metrics(p);d=p.choose_action(s,SearchLimits(max_depth=64,max_nodes=500000,max_time_seconds=plan['service_seconds'],quiescence_max_depth=4,quiescence_hard_max_depth=8),cancel_token=token)
        observed=observer.result(d);service=time.perf_counter()-t0;cpu=time.process_time()-cpu;end=stamp()
        row={'query_id':qid,'status':'RETURNED','on':on,'record':record_value(before),'root_fingerprint':c.ruleset_fingerprint,'decision':record_value(d),'action':action_to_dict(d.action) if d.action else None,'observer':observed,'started_at':begin,'ended_at':end,'service_seconds':service,'cpu_seconds':cpu,'caller_deadline_observed':token.observed,'timing_eligible':service<=plan['eligible_actual_service_seconds'],'provider_present':pm['present'],'provider_delta':metric_delta(pm,provider_metrics(p)),'freshPlayerTT':True}
        write_record(out/(qid+'.json'),row);record_work(begin,end,'research',str(out/(qid+'.json')))
        assert s.to_record()==before and d.runtime_depth_balanced
        assert d.action is not None and d.action in s.legal_actions()
        pv=type(s).replay(c,before)
        for action in d.principal_variation:pv.submit(action)
        assert pm['present'] and d.native_legality_fallbacks==0 and d.native_legality_operational_failures==0
        assert row['provider_delta']['availability'].get('declines',0)==0
        assert not observed['errors'],'observer errors'
        return row,d
    except BaseException as exc:
        # Save failure without overwriting any already saved successful return.
        write_record(out/(qid+'-failure.json'),{'query_id':qid,'status':'RAISED','type':type(exc).__name__,'message':str(exc),'original_return_preserved':(out/(qid+'.json')).exists(),'started_at':begin,'ended_at':stamp(),'outer_seconds':time.perf_counter()-t0})
        raise

def qualify(inputs,protocol,out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);(out/'returns').mkdir();plan=json.loads(Path(protocol).read_text());raw=Path(inputs).read_bytes();assert hashlib.sha256(raw).hexdigest()==plan['input_sha256'];rows=json.loads(raw)['rows'];tick=time.perf_counter();groups=[];reason=None
    for path,digest in plan['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    try:
        for r in rows:
            c,s=make_session(r);calls=[]
            for i,on in enumerate((False,True,True,False)):
                reason=admissible(plan)
                if reason or time.perf_counter()-tick+2>=plan['qualifiers']['batch_seconds']:raise RuntimeError(reason or 'qualification_batch_cap')
                result,d=query(c,s,on,r['id']+'-'+str(i),out/'returns',plan);calls.append(result)
            eligible=all(x['timing_eligible'] and x['decision']['completed_depth']>=2 and x['decision']['result_source']=='main_iteration' for x in calls)
            activity=False
            for x in calls[1:3]:
                o=x['observer'];attempt=o['retained_root_attempt']
                witness=any(w['root_attempt']==attempt and w['return']=='NORMAL' for w in o['witnesses'])
                activity=activity or bool(o['retained_changed_entries'] and witness)
            keys=[json.dumps(x['action'],sort_keys=True) for x in calls];signal=keys[0]==keys[3] and keys[1]==keys[2] and keys[0]!=keys[1]
            g={'id':r['id'],'family':r['family'],'eligible':eligible,'retained_activity_witness':activity,'stable_action_difference':signal,'calls':[x['query_id'] for x in calls]};groups.append(g);write_record(out/'groups.json',groups);print(g,flush=True)
    except Exception as exc:reason=type(exc).__name__+':'+str(exc)
    eligible=[g for g in groups if g['eligible']];active={g['family'] for g in eligible if g['retained_activity_witness']};signal={g['family'] for g in eligible if g['stable_action_difference']};coverage={g['family'] for g in eligible}
    passed=reason is None and len(groups)==16 and len(eligible)>=12 and len(coverage)==8 and len(active)>=4 and len(signal)>=4
    summary={'status':'PASS_CONDITIONAL_GAMES_GATE' if passed else 'NO_GO_NO_GAMES','reason':reason,'groups':len(groups),'eligible_groups':len(eligible),'families':sorted(coverage),'active_families':sorted(active),'decision_signal_families':sorted(signal),'returns':len(list((out/'returns').glob('*.json'))),'seconds':time.perf_counter()-tick,'games':'NOT_STARTED','scope':'new prospective development endpoint;actual retained ordering and stablechoicechange only,not accuracy/strength'}
    write_record(out/'summary.json',summary);print(json.dumps(summary));return summary
