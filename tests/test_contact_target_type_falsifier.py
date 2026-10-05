import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_type_guard_falsifier_keeps_target_zero_and_owner_reflection():
    r=json.loads((ROOT/'docs/research/data/contact_target_type_qualified_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==8 and r['enumerated']==14 and r['candidates']==12
    for row in r['rows']:
        assert row['actual']==(not row['guarded'] or row['target_type']=='V')
        assert row['target']==(0 if row['owner']==0 else 8)
    assert all(q['admitted']!=q['guarded'] for q in r['qualification'])
    assert r['public_transitions']==r['source_queries']==0 and r['seconds']<15
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_zero_observation_failures_are_preserved_not_rerun():
    for name in ('contact_target_type_falsifier','contact_target_type_execution'):
        r=json.loads((ROOT/f'docs/research/data/{name}_20261005.json').read_text())
        assert not r['complete'] and r['public_transitions']==r['enumerated']==r['candidates']==0
        for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
