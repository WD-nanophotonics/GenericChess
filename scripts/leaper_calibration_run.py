"""Run one NEW registered Leaper calibration with its declared empirical gate.

Preserve the stock sampled-maximum forecast. This does not extend a cap, resume
an old run, impute missing games, or provide a worst-case coverage guarantee.
"""
import argparse
from pathlib import Path
from datetime import datetime, timezone
from scripts import leaper_design as L


def execute(d):
    assert not (d/'results.json').exists() and not (d/'preflight.json').exists()
    r=L.load(d/'registration.json')
    assert r['whole_cap_seconds']<7200 and r['expected_seconds']<7200
    assert 0<r['empirical_loop_forecast_seconds']<r['whole_cap_seconds']
    w={'started_at':datetime.now(timezone.utc).isoformat(),'activity':'research'}
    L.write_record(d/'execution-start.json',w)
    try:
        L.preflight(d)
        pf=L.load(d/'preflight.json');L.write_record(d/'preflight-maximum-call-original.json',pf)
        forecast=r['empirical_loop_forecast_seconds']+r['preparation_seconds']+pf['seconds']
        gate=not pf['missing'] and forecast<r['whole_cap_seconds'] and max(x['seconds']for x in pf['rows'])<5
        pf.update(cost_gate_passed=gate,empirical_whole_game_forecast_seconds=forecast,gate_method=r['cost_basis'])
        L.write_record(d/'preflight.json',pf)
        if not gate:raise ValueError('Frozen empirical gate failed; zero fitness. No cap extension.')
        L.run(d);w['returncode']=0
    finally:
        w['ended_at']=datetime.now(timezone.utc).isoformat();L.write_record(d/'actual-execution-window.json',w)
    print('WINDOW_CLOSED',w,flush=True)


def materialize(packet, group, output):
    """Copy input DATA to a NEW zero-query replication, never execute sources."""
    import gzip, json, copy, hashlib, time
    assert not output.exists(), 'new replication only; never modify frozen originals'
    tick=time.perf_counter();blob=packet.read_bytes();data=json.loads(gzip.decompress(blob))
    source=data['runs'][group];files=source['files'];original=files['registration.json']
    assert original['source_sha256']==L.sha(Path(L.__file__)), 'pin the recorded library source before replication'
    inputs=files['inputs.json']
    for w in inputs['worlds']:
        if w['status']!='ready':continue
        c=L.compile_rule(L.ruleset_from_dict(w['rule']))
        s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['initial_record'])))
        assert L.record_value(s.state)==w['initial_state']
    output.mkdir(parents=True)
    L.write_record(output/'replication-original-registration.json',original)
    L.write_record(output/'inputs.json',inputs)
    if 'preflight-inputs.json'in files:L.write_record(output/'preflight-inputs.json',files['preflight-inputs.json'])
    reg=copy.deepcopy(original)
    reg.update(frozen_at=datetime.now(timezone.utc).isoformat(),
        input_sha256=L.sha(output/'inputs.json'),preparer_sha256=L.sha(Path(__file__)),
        preparation_seconds=time.perf_counter()-tick,
        replication_provenance={'packet_sha256':hashlib.sha256(blob).hexdigest(),
            'group':group,'original_registered_input_sha256':original['input_sha256'],
            'original_preparer_sha256':original['preparer_sha256'],
            'original_file_sha256':source['original_file_sha256'],
            'reason':'New zero-query replication. Input JSON values and logical controls preserved; reencoded byte hash, actual new preparation time/source and freeze timestamp are new. Original registration retained, not rewritten. Original cost forecast remains an OLD planning estimate; execute makes NEW preflight calls.'})
    assert L.load(output/'inputs.json')==inputs
    L.write_record(output/'registration.json',reg)
    print({'materialized':str(output),'worlds':len(inputs['worlds']),'Player_calls':0,'fitness':0},flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--materialize-from-packet',type=Path);p.add_argument('--group');a=p.parse_args()
    if a.materialize_from_packet:
        if not a.group:p.error('materialization requires --group')
        materialize(a.materialize_from_packet,a.group,a.output)
    else:execute(a.output)
if __name__=='__main__':main()
