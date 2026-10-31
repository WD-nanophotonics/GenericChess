"""Independent saved-data arithmetic and Core PV replay, never invokes Player."""
import hashlib,json,math,statistics
from pathlib import Path
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.leaper_boolean_cost_pilot import signature
from scripts.research_record import write_record

KERNEL={'runtime_push','runtime_pop','core_terminal','semantic_transition','native_import','action_binding','action_decode','native_legal_frontier','native_check','native_availability'}
TRANSPORT={'native_import','action_decode','action_binding'}
def close(a,b):assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-9),(a,b)
def digest(b):return hashlib.sha256(b).hexdigest()

def verify(base,out):
    base=Path(base);inputs=(base/'inputs.json').read_bytes();roots=json.loads(inputs)['rows'];contexts=[make_session(r) for r in roots];total=0;pvcount=0;reports={}
    for name,width in [('measurement',3),('signature-cost',4)]:
        folder=base/name
        if not (folder/'summary.json').exists():continue
        f=json.loads((folder/'frozen.json').read_text(encoding='utf-8'));s=json.loads((folder/'summary.json').read_text());assert digest(inputs)==f['plan']['inputs_sha256'];assert f['inputs']==json.loads(inputs)
        source_checks=0
        for rel,item in f['sources'].items():
            if name=='measurement':
                raw=(base/'source-originals'/rel).read_bytes();assert digest(raw)==item['sha256'];assert raw.decode('utf-8-sig').replace('\r\n','\n').replace('\r','\n')==item['text']
            else:assert digest(item['text'].encode('utf-8'))==item['sha256']
            source_checks+=1
        files=sorted(folder.glob('return-*.json'));assert len(files)==s['returns'];assert s['NOT_RUN']==list(range(len(files),s['planned']));calls=[];pvs=0
        for i,p in enumerate(files):
            r=json.loads(p.read_text());assert r['slot']==i;ri=(i%48)//3 if name=='measurement' else i//4;c,session=contexts[ri]
            assert r['record_before']==roots[ri]['record'];d=r['decision'];assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
            assert r['binary_sha256']==f['binary']['sha256'];assert d['runtime_semantic_full_diff_fallbacks']==0 and d['runtime_position_identity_hash_cached'] is False
            assert action(d['action'],session) in session.legal_actions();pv=type(session).replay(c,session.to_record())
            if d['principal_variation']:assert d['principal_variation'][0]==d['action']
            for a in d['principal_variation']:pv.submit(action(a,pv));pvs+=1
            if name=='measurement':
                assert r['observed']==(i%3==1)
                if r['observed']:
                    rows=r['observer_rows'];assert rows['runtime_push']['calls']==d['runtime_pushes']+rows['runtime_push']['exceptions']
                    assert all(v['self_ns']>=0 and v['inclusive_ns']>=v['self_ns'] for v in rows.values())
                    part=r['partition'];close(part['all_observed_self_seconds'],sum(v['self_ns'] for v in rows.values())/1e9)
                    close(part['broad_observed_union_seconds'],sum(v['self_ns'] for k,v in rows.items() if k in KERNEL)/1e9)
                    close(part['transport_binding_observed_union_seconds'],sum(v['self_ns'] for k,v in rows.items() if k in TRANSPORT)/1e9)
                    close(part['outside_and_unwrapped_seconds'],r['wall_seconds']-sum(v['self_ns'] for v in rows.values())/1e9)
            else:
                assert r['candidate']==(i%4 in (1,2))
                if r['candidate']:assert r['memo']['runtimes']==1 and r['memo']['hits']>0 and r['memo']['fallbacks']==0 and r['memo']['peak_entries']<=4096
                else:assert all(v==0 for v in r['memo'].values())
            calls.append(r)
        groups=[]
        for start in range(0,len(calls)-width+1,width):
            batch=calls[start:start+width];target=batch[0]['depth'] if name=='measurement' else 4
            ok=all(r['decision']['completed_depth']==target and r['decision']['result_source']=='main_iteration' for r in batch)
            if ok:
                assert all(signature(r['decision'])==signature(batch[0]['decision']) for r in batch)
                assert all(r['Native_delta']==batch[0]['Native_delta'] for r in batch)
            groups.append((target,ok,batch))
        if name=='measurement':
            for depth in (3,5):
                gs=[g for g in groups if g[0]==depth and g[1]];original=s['by_depth'][str(depth)];assert len(gs)==original['eligible_groups']
                if gs:
                    walls=sum(g[2][1]['wall_seconds'] for g in gs)
                    for field,key in [('broad_observed_union_seconds','broad_observed_fraction'),('transport_binding_observed_union_seconds','transport_binding_observed_fraction')]:close(sum(g[2][1]['partition'][field] for g in gs)/walls,original[key])
                    close(statistics.median(g[2][1]['wall_seconds']/((g[2][0]['wall_seconds']+g[2][2]['wall_seconds'])/2) for g in gs),original['median_observer_ratio'])
        else:
            eligible=[g for g in groups if g[1]];assert len(eligible)==s['complete_groups']
            for m in ('wall','cpu'):
                on=sum(g[2][i][m+'_seconds'] for g in eligible for i in (1,2));off=sum(g[2][i][m+'_seconds'] for g in eligible for i in (0,3));close(on,s['totals']['ON_'+m]);close(off,s['totals']['OFF_'+m])
                if off:close(on/off,s['ratios'][m])
            fams={roots[g[2][0]['slot']//4]['family'] for g in eligible}
            gate=len(calls)==64 and s['reason'] is None and len(eligible)>=12 and len(fams)==8 and all(g[2][0]['cpu_seconds']+g[2][3]['cpu_seconds']>0 for g in eligible) and all(s['ratios'][m] is not None and s['ratios'][m]<=.95 for m in ('wall','cpu'))
            assert (s['status']=='PASS_SCOPED_EXACT_COST')==gate
        reports[name]={'returns':len(calls),'Core_PVplies':pvs,'raw_source_bindings':source_checks,'matched_complete_groups':sum(g[1] for g in groups),'status':'PASS'};total+=len(calls);pvcount+=pvs
    result={'status':'PASS_SAVED_SCOPE','returns':total,'literal_CorePVplies':pvcount,'reports':reports,'new_Player_calls':0,'not_independent_timing_or_Core_implementation':True};write_record(Path(out),result);print(json.dumps(result));return result
if __name__=='__main__':
    import sys;verify(sys.argv[1],sys.argv[2])
