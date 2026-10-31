"""Read frozen persistent-controller evidence; no search/controller invocation."""
import json,hashlib,math
from pathlib import Path
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.leaper_boolean_cost_pilot import signature
from generic_chess.session.serialization import deserialize_game_record

def verify_lifecycle(base):
    base=Path(base);folder=base/'lifecycle';f=json.loads((folder/'frozen.json').read_text());s=json.loads((folder/'summary.json').read_text());raw=(base/'inputs.json').read_bytes();roots=json.loads(raw)['rows']
    assert hashlib.sha256(raw).hexdigest()==f['inputs_sha256'] and f['inputs']==json.loads(raw)
    for p,item in f['sources'].items():assert hashlib.sha256(item['text'].encode()).hexdigest()==item['sha256']
    contexts=[make_session(r) for r in roots];calls={};pvcount=0;missing={f'{ri}:{step}:{int(on)}' for ri in range(16) for step in range(4) for on in (False,True)}
    for slot,p in enumerate(sorted(folder.glob('return-*.json'))):
        r=json.loads(p.read_text());assert r['slot']==slot;ri=r['root_index'];step=r['prefix'];on=r['candidate'];key=(ri,step,on);assert key not in calls
        assert r['record_before']==f['paths'][ri]['records'][step]
        c,initial=contexts[ri];session=type(initial).replay(c,deserialize_game_record(json.dumps(r['record_before'])));d=r['decision'];assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0 and r['wall_seconds']<=33
        assert r['binary_sha256']==f['binary']['sha256'] and action(d['action'],session) in session.legal_actions()
        pv=type(session).replay(c,session.to_record())
        for a in d['principal_variation']:pv.submit(action(a,pv));pvcount+=1
        if on:assert r['memo']['runtimes']==1 and r['memo']['fallbacks']==0 and r['memo']['peak_entries']<=4096
        else:assert not any(r['memo'].values())
        calls[key]=r;missing.remove(f'{ri}:{step}:{int(on)}')
    assert len(calls)==s['returns'] and sorted(missing)==s['NOT_RUN']
    eligible=[];paired=0;unpaired=0
    for ri in range(16):
        clean=True
        for step in range(4):
            pair=[calls.get((ri,step,on)) for on in (False,True)]
            if not all(pair):unpaired+=sum(x is not None for x in pair);break
            paired+=1;assert all(r['history_clean_before_pair']==clean for r in pair)
            complete=all(r['decision']['completed_depth']==4 and r['decision']['result_source']=='main_iteration' for r in pair)
            parity=signature(pair[0]['decision'])==signature(pair[1]['decision']) if complete else False
            if clean and complete:assert parity and pair[0]['Native_delta']==pair[1]['Native_delta']
            valid=clean and complete and parity
            if valid and step>0:eligible.append((ri,step,pair))
            clean=bool(valid)
    assert len(eligible)==s['eligible_warm_pairs'];fams=sorted({roots[ri]['family'] for ri,step,pair in eligible});assert fams==s['families']
    for m in ('wall','cpu'):
        for side,index in [('OFF',0),('ON',1)]:
            total=sum(pair[index][m+'_seconds'] for ri,step,pair in eligible);assert math.isclose(total,s['warm_totals'][side+'_'+m],rel_tol=1e-12,abs_tol=1e-9)
        off=s['warm_totals']['OFF_'+m]
        if off:assert math.isclose(s['warm_totals']['ON_'+m]/off,s['warm_ratios'][m],rel_tol=1e-12)
    gate=len(calls)==128 and s['reason'] is None and len(eligible)>=36 and len(fams)==8 and all(pair[0]['cpu_seconds']>0 for ri,step,pair in eligible) and all(v is not None and v<=.95 for v in s['warm_ratios'].values())
    assert (s['status']=='PASS_SCOPED_WARM_TRANSFER')==gate
    constructors=s['constructors'];assert len({(r['root'],r['candidate']) for r in constructors})==len(constructors)
    return {'status':'PASS_SAVED_SCOPE','returns':len(calls),'Core_PVplies':pvcount,'complete_pairs':paired,'unpaired_returns':unpaired,'qualified_warm_pairs':len(eligible),'families':fams,'NOT_RUN':len(missing),'cost_gate_passed':gate,'new_Player':0,'limits':'Partial controller transfer notstrength or a completed fullgate;sharedCore/source/readback,not independenthardware.'}
