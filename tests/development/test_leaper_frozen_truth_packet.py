"""Corruption guards on finite truth, source history and complete frontiers."""
from copy import deepcopy
from pathlib import Path
import gzip,json
import pytest
from scripts.leaper_frozen_truth_packet import reconstruct,decode
from scripts.verify_leaper_frozen_pair_truth import qualify_graph
from scripts.leaper_frozen_pair_truth import admit_frozen,pair_summary

P=Path('docs/research/data/leaper_frozen_pair_truth_20261024/packet.json.gz')


@pytest.fixture(scope='module')
def packet():
    p=json.loads(gzip.decompress(P.read_bytes()))
    return next(g for g in p['graphs']if g['n']==4 and g['mask']==31)


def test_actual_source_and_complete_integer_frontier_agree(packet):
    r=qualify_graph(reconstruct(packet),core_samples=16)
    assert r['verified']and r['counts']['full_source_records']==8


def test_reordered_or_omitted_graph_vertex_cannot_inherit_a_label(packet):
    p=deepcopy(packet);p['position_codes'].pop()
    with pytest.raises(ValueError,match='closure'):reconstruct(p)


def test_duplicate_physical_vertex_rejected(packet):
    p=deepcopy(packet);p['position_codes'].append(p['position_codes'][0])
    with pytest.raises(ValueError,match='duplicate'):reconstruct(p)


def test_complete_frontier_digest_is_binding(packet):
    p=deepcopy(packet);p['frontier_sha256']='0'*64
    with pytest.raises(ValueError,match='digest'):reconstruct(p)


def test_same_mask_different_clock_does_not_bind_old_truth(packet):
    raw=deepcopy(packet['rule']);raw['max_ply']=6
    with pytest.raises(ValueError,match='complete rule'):admit_frozen(raw,31,4)


def test_root_full_record_sha_cannot_be_fabricated(packet):
    g=reconstruct(packet);g['roots'][0]['state_sha']='0'*64
    with pytest.raises(ValueError,match='full record'):qualify_graph(g,core_samples=0)


def test_clock_action_quality_is_not_a_graph_scalar(packet):
    g=reconstruct(packet);g['roots'][0]['clocks'][0]['actions'][0]=99
    with pytest.raises(ValueError,match='action labels'):qualify_graph(g,core_samples=0)


def test_clock_draw_cannot_be_mislabeled_as_a_structural_deadzone(packet):
    full=json.loads(gzip.decompress(P.read_bytes()));p=next(g for g in full['graphs']if g['n']==4 and g['mask']==5);g=reconstruct(p)
    assert g['roots'][0]['clocks'][0]['WDL']==0 and g['roots'][0]['graph_WDL']==1
    g['roots'][0]['clocks'][0]['draw_category']='no_reachable_mate'
    with pytest.raises(ValueError,match='attribution'):qualify_graph(g,core_samples=0)


def test_sample_mu_rank_is_distinct_from_forced_rank(packet):
    g=reconstruct(packet)
    assert {r['rank']for r in g['roots']}==set(range(8))
    assert any(r['rank']!=r['forced_rank']for r in g['roots'])


@pytest.mark.parametrize('bad',[True,-1,100000000])
def test_invalid_physical_code_rejected(bad):
    with pytest.raises(ValueError,match='code'):decode(bad,4)
