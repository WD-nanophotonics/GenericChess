"""Truth/cost matching must bind actual full states and retain missing scope."""
from pathlib import Path
import json,gzip
import pytest
from scripts.leaper_frozen_cost_truth import analyze

P=Path('docs/research/data/leaper_frozen_pair_truth_20261024/packet.json.gz')
B=Path('docs/research/data/leaper_forward_width_20261024/screen-evidence.json.gz')


def test_retained_cost_returns_outside_truth_domain_stay_unlabelled():
    r=analyze(P,B)
    assert r['matched_returns']==864 and r['unmatched_returns']==288
    assert sum(s['inferior']for s in r['summary'])==0
    assert r['paired']==dict(roots=432,different_actions=0,different_action_WDL=0)
    assert all('chosen_action_WDL'not in x for x in r['unmatched'])


def test_same_rule_name_with_edited_full_state_is_not_truth_binding(tmp_path):
    packet=json.loads(gzip.decompress(P.read_bytes()));g=next(g for g in packet['graphs']if g['n']==4 and g['mask']==10);g['roots'][0]['state_sha']='0'*64
    path=tmp_path/'edited.json.gz';path.write_bytes(gzip.compress(json.dumps(packet).encode(),mtime=0))
    with pytest.raises(ValueError,match='fullrule/mu/history'):analyze(path,B)
