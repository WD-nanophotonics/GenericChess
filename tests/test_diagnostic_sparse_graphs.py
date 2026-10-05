"""Frozen aggregate proof checks, without rerunning BFS census."""
import hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_all_sparse_classes_account_for_every_world():
    r=json.loads((ROOT/'docs/research/data/diagnostic_sparse_graphs_20261006.json').read_text())
    assert r['complete'] and r['saved_full_match'] and r['source_hashes_unchanged']
    assert r['classes']==523<=1000 and r['expanded_nodes']==2713<=3297<5000 and r['seconds']<15
    assert len(r['rows'])==45 and all(row['complete'] for row in r['rows'])
    total=Counter({0:45*89*88})
    for row in r['rows']:
        assert sum(case['multiplicity'] for case in row['cases'])==89
        assert len({case['blocker'] for case in row['cases']})==len(row['cases'])
        for case in row['cases']:
            assert sum(case['histogram'].values())==88
            for tau,count in case['histogram'].items():total[int(tau)]+=case['multiplicity']*count
    assert dict(total)=={0:685706,1:7308,2:7540,3:3100,4:1218,5:8}
    assert sum(total.values())==704880
    assert r['full_aggregate']['A']==dict(histogram={'1':1408,'2':1396},unreachable=702076,total=704880)
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_component_eye_parity_and_graph_bound_are_explicit():
    r=json.loads((ROOT/'docs/research/data/diagnostic_sparse_graphs_20261006.json').read_text())
    assert sorted((len(c['vertices']),c['edges']) for c in r['components'])==[(4,3),(4,3),(5,4),(5,4),(6,6),(6,6),(7,8),(8,8)]
    for c in r['components']:
        parity={(s%9%2,s//9%2) for s in c['vertices']}
        assert len(parity)==1
        f,p=next(iter(parity))
        assert all((s%9%2,s//9%2)==(1-f,1-p) for s in c['eyes'])
        assert not set(c['vertices'])&set(c['eyes'])
        assert len(c['eyes'])==c['edges']
    bound=sum(len(c['vertices'])**2*(len(c['vertices'])+c['edges']) for c in r['components'])
    assert bound==3297
