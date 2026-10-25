"""Qualification refuses missing horizons and mismatched frozen identities."""
import hashlib,json,gzip
from pathlib import Path
import pytest
from scripts.verify_leaper_branch_allocation import assess

def fixture(d):
    inp=dict(root=dict(actor=1),actions=[{'move':0},{'move':1}],children=[dict(actor=0,state_sha256='a'),dict(actor=0,state_sha256='b')])
    slots=[dict(phase='clock',branch=i,limits=dict(max_depth=10))for i in range(2)]
    rows=[]
    for i in range(2):
        depth=10 if i==0 else 9
        rows.append(dict(slot=slots[i],child_state_sha256=inp['children'][i]['state_sha256'],decision=dict(completed_depth=depth,score=-100-i,nodes=7,qnodes=9,termination_reason='completed_depth'if i==0 else'time_limit'),iterations=[dict(depth=depth,score=-100-i)],seconds=2.))
    data={'inputs.json':inp,'labels.json':dict(labelled_actions=[dict(action=a,truth=dict(value=v))for a,v in zip(inp['actions'],[0,-1])]),'plan.json':dict(slots=slots,source_sha256='source'),'receipt.json':dict(status='CLOSED',attempted=2,queries=2,source_sha256='source')}
    for n,x in data.items():(d/n).write_bytes(json.dumps(x).encode())
    plan=data['plan.json'];plan['inputs_sha256']=hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest();(d/'plan.json').write_bytes(json.dumps(plan).encode())
    (d/'queries.jsonl').write_bytes(('\n'.join(json.dumps(x)for x in rows)+'\n').encode())
    (d/'qualification.jsonl').write_bytes(('\n'.join(json.dumps(dict(slot=x,pv_steps=1))for x in slots)+'\n').encode())

def test_incomplete_requested_horizon_never_ranks_partial_winner(tmp_path):
    fixture(tmp_path);r=assess(tmp_path);phase=r['phases']['clock'];assert not phase['all_complete'];assert phase['best_branches']==[];assert phase['rows'][1]['score_root']is None

def test_wrong_frozen_state_is_rejected(tmp_path):
    fixture(tmp_path);p=tmp_path/'queries.jsonl';s=p.read_text().replace('"child_state_sha256": "a"','"child_state_sha256": "other"');p.write_bytes(s.encode())
    with pytest.raises(AssertionError):assess(tmp_path)

def test_lossless_gzip_only_packet_accepted_and_input_tamper_rejected(tmp_path):
    fixture(tmp_path)
    for p in list(tmp_path.iterdir()):
        raw=p.read_bytes();Path(str(p)+'.gz').write_bytes(gzip.compress(raw));p.unlink()
    assert assess(tmp_path)['queries']==2
    p=tmp_path/'inputs.json.gz';d=json.loads(gzip.decompress(p.read_bytes()));d['root']['actor']=0;p.write_bytes(gzip.compress(json.dumps(d).encode()))
    with pytest.raises(AssertionError):assess(tmp_path)
