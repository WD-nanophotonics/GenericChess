import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load(name):return json.loads((ROOT/'docs/research/data'/name).read_text())

def test_source_control_coverage_and_semantics():
    r=load('threepiece_source_extension_20261006.json')
    assert r['complete'] and r['original_and_working_integrity_after_close']
    assert r['public_transitions']==0 and r['outer_probe_calls']==10
    assert r['enumerated']==170 and r['table_bytes']==51477
    assert {x['mode'] for x in r['rows']}==set('PNBRQ')
    for row in r['rows']:
        assert row['local_terminal']=='ongoing'
        assert len(row['complete_choices'])==len(set(row['complete_choices']))
        if row['mode'] in 'NB':
            assert row['source_terminal']['termination']=='INSUFFICIENT_MATERIAL'
            assert row['wdl_stm']==row['signed_dtm']==0
        else:assert row['wdl_stm']==1 and row['signed_dtm']>0

def test_promotion_all_ties_and_independent_regret():
    r=load('threepiece_promotion_use_v2_20261006.json')
    assert r['complete'] and r['choices_frozen_before_probes']
    assert len(r['children'])==12 and r['outer_probe_calls']==24
    assert r['public_transitions']==24 and r['prior_failed_local_transitions']==12
    assert r['source_pushes']==21 and r['prior_failed_source_pushes']==9
    labels={k:v['source_root_utility'] for k,v in r['children'].items()}
    assert {k for k,v in labels.items() if v==0}=={'b7b8b','b7b8n'}
    optimum=max(labels.values())
    for name,p in r['policies'].items():
        best=max(p['scores'].values())
        assert p['full_ties']==sorted(k for k,v in p['scores'].items() if v==best)
        values=[labels[k] for k in p['full_ties']]
        assert p['regret_interval']==[optimum-max(values),optimum-min(values)]
        assert p['utility_interval']==[min(values),max(values)]
    assert r['policies']['unit']['utility_interval']==[0,1]
    for law in ('geometric_half','linear_mixture'):
        assert r['policies'][law]['full_ties']==['b7b8q']
        assert r['policies'][law]['utility_interval']==[1,1]

def test_original_promotion_failure_is_preserved_before_labels():
    r=load('threepiece_promotion_use_20261006.json')
    assert not r['complete'] and r['outer_probe_calls']==0 and not r['policies']
    assert r['public_transitions']==12 and r['source_pushes']==9
    assert 'stored native origin scope failed' in r['error']

def test_source_record_pins():
    for name in ('threepiece_source_extension_20261006.json','threepiece_promotion_use_20261006.json','threepiece_promotion_use_v2_20261006.json'):
        r=load(name)
        assert r['source_hashes_unchanged']
        for path,pin in r['source_sha256'].items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
