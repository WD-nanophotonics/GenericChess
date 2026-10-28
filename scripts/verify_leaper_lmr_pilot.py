"""Independent immutable-return/Core/PV reader; never runs search or games."""
import argparse,gzip,json,math
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime,timezone
from generic_chess.session.session import GameSession
from scripts.leaper_pvs_quality_pilot import make_session,digest
from scripts.leaper_postexchange_source import load,sha,stopped
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.verify_leaper_admitted_extension import submission
from scripts.research_record import record_value,write_record
from scripts.leaper_check_extension_quality import record_interval


def service(q):
    assert q['requested_service_seconds']==1.5
    lim=q['limits'];d=q['decision'];on=q['on']
    assert type(on) is bool and q['policy_owned_TT'] is True
    assert q['policy_id']==('late-quiet-nonPV-oneply/v1' if on else 'existing-PVS/v1')
    assert 0<lim['max_time_seconds']<=1.5 and 0<=q['construction_packing_seconds']
    assert lim['max_time_seconds']+q['construction_packing_seconds']<=1.5+1e-8
    assert lim['max_depth']==64 and lim['max_nodes']==500000
    assert lim['quiescence_max_depth']==4 and lim['quiescence_hard_max_depth']==8
    expected={'use_root_tactical','use_ordered_qsearch_in_check','use_pvs'}
    assert {k for k,v in q['actual_tuning'].items() if k.startswith('use_') and v is True}==expected
    assert not q['actual_tuning']['require_full_pv'] and not q['actual_tuning']['stop_after_root_win']
    assert all(math.isfinite(q[k]) and q[k]>=0 for k in ('service_wall_seconds','cpu_seconds','lmr_classification_seconds'))
    assert q['timing_eligible']==(q['service_wall_seconds']<=1.65)
    assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
    assert q['provider_present'] and q['provider_delta']['availability'].get('declines',0)==0
    assert d['main_check_extensions']==0
    if d['result_source']=='main_iteration':
        assert d['completed_depth']>=1 and d['result_ordinary_qdepth']==(0 if d['completed_depth']==1 else 4)
    counts=q['lmr'];r=counts.get('reductions',0)
    assert all(type(v) is int and v>=0 for v in counts.values())
    assert counts.get('full_depth_researches',0)+counts.get('reduced_fail_low_kept',0)<=r<=counts.get('eligible_dispatch_attempts',0)
    if not on:assert not counts and q['lmr_classification_seconds']==0


def outcome_bounds(games):
    points=0;valid=0;families=defaultdict(list);outcomes=Counter()
    for g in games:
        value=None
        if g['status']=='TERMINAL' and g['timing_eligible']:
            winner=g['Core_terminal']['winner'];value=.5 if winner is None else float(winner==g['on_seat'])
            points+=value;valid+=1;outcomes['DRAW' if winner is None else 'ON_WIN' if value else 'OFF_WIN']+=1
        families[g['family']].append(value)
    positive=sum(len(v)==2 and all(x is not None for x in v) and sum(v)>1 for v in families.values())
    return dict(planned=16,eligible=valid,missing=16-valid,ON_points=points,outcomes=dict(outcomes),positive_families=positive,
                raw_completion_bounds=[points/16,(points+16-valid)/16],
                gate=len(games)==16 and valid==16 and positive>=4 and points>=.55*16)


def verify(plan_path,folder,out,credit_work=False):
    plan=load(plan_path)
    for p,h in plan['files'].items():assert sha(p)==h,p
    assert load(folder/'frozen.json')==plan
    packet_path=Path(plan['input_packet']);rows=json.loads(gzip.decompress(packet_path.read_bytes()))['rows']
    expected=[(r,on) for r in rows for on in ((0,1) if r['family']%2==0 else (1,0))]
    assert len(expected)==16
    identity=dict(plan_sha256=sha(plan_path),input_sha256=sha(packet_path),verifier_source_sha256=sha(__file__))
    verified=[];raw_names=set();missing=[]
    for i,(row,on_seat) in enumerate(expected):
        if stopped():raise RuntimeError('scoped_stop')
        gpath=folder/f'game-{i:02d}.json'
        if not gpath.exists():missing.append(i);continue
        g=load(gpath);assert g['game_id']==i and g['case_id']==row['id'] and g['family']==row['family'] and g['on_seat']==on_seat
        assert g['fingerprint']==row['fingerprint'] and g['initial_record']==row['record']
        cache=out/f'verified-game-{i:02d}.json'
        if cache.exists():
            old=load(cache)
            assert all(old[k]==v for k,v in identity.items()) and old['game_sha256']==sha(gpath)
            for name,h in old['raw_hashes'].items():assert sha(folder/'returns'/name)==h
            assert not raw_names.intersection(old['raw_hashes']);raw_names.update(old['raw_hashes'])
            verified.append(g);continue
        begin=datetime.now(timezone.utc).isoformat();c,s=make_session(row);hashes={};pv_steps=0
        for q in g['queries']:
            name=q['query_id']+'.json';assert name not in raw_names;raw_names.add(name)
            raw_path=folder/'returns'/name;raw=load(raw_path);hashes[name]=sha(raw_path)
            service(raw)
            assert raw['seat']==s.state.position.side_to_move and raw['on']==(raw['seat']==on_seat)
            assert raw['record_before_sha256']==digest(s.to_record())
            d=raw['decision'];pv=GameSession.replay(c,s.to_record())
            for v in d['principal_variation']:pv.submit(action(v,pv));pv_steps+=1
            a=action(d['action'],s);assert a in s.legal_actions();s.submit(a)
            submission(raw,q,digest(s.to_record()))
        if 'final_record' in g:
            assert record_value(s.to_record())==g['final_record']
            assert record_value(s.state.terminal_status)==g['Core_terminal'] and record_value(s.result)==g['Session_result']
            assert (g['status']=='TERMINAL')==s.state.terminal_status.is_terminal
            assert g['timing_eligible']==all(q['timing_eligible'] for q in g['queries'])
        else:assert g['status'] in ('NOT_STARTED','FAILED')
        ended=datetime.now(timezone.utc).isoformat()
        result=dict(**identity,game_id=i,status='PASS',game_sha256=sha(gpath),raw_hashes=hashes,Player_returns=len(g['queries']),Core_transitions=len(g['queries']),PV_steps=pv_steps,root_full_prefix=len(row['record']['actions']),started_at=begin,ended_at=ended,ledger_credit=credit_work,scope='Shared-Core independent literal replay,not a separate WDL engine')
        write_record(cache,result)
        if credit_work:record_interval(begin,ended,'validation',str(cache),out)
        verified.append(g)
    # Active current-game originals are legitimately not assigned to a sealed
    # game yet. Final closure additionally requires no orphans and16slot files.
    orphan_names=sorted({p.name for p in (folder/'returns').glob('*.json')}-raw_names)
    closed=(folder/'summary.json').exists()
    if closed:assert not missing and not orphan_names
    totals=[load(out/f'verified-game-{g["game_id"]:02d}.json') for g in verified]
    result=dict(status='PASS' if closed else 'INCOMPLETE_ACTIVE_PRODUCER',verified_games=len(verified),missing_slot_files=missing,unassigned_originals=orphan_names,
                Player_returns=sum(x['Player_returns'] for x in totals),Core_transitions=sum(x['Core_transitions'] for x in totals),PV_steps=sum(x['PV_steps'] for x in totals),outcome=outcome_bounds(verified),
                limits='Finite exposed development increment over existingPVS only;no desktop-default improvement/unseen strength or formal all-defense mate proof;changed gamehistories forbid matchedspeedup')
    if closed:
        producer=load(folder/'summary.json');assert producer['outcome']['ON_points']==result['outcome']['ON_points'] and producer['outcome']['positive_families']==result['outcome']['positive_families'] and producer['outcome']['exploratory_gate_passed']==result['outcome']['gate']
    write_record(out/'verification.json',result);print({k:v for k,v in result.items() if k!='unassigned_originals'})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--credit-work',action='store_true');a=p.parse_args();a.output.mkdir(exist_ok=True);verify(a.plan,a.folder,a.output,a.credit_work)
