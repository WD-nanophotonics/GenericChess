import pytest
from scripts.leaper_observed_path_proofs import shortest_paths,run,verify,apply
from tests.development.test_leaper_saved_suffix_transfer import case
from scripts.leaper_explorer_truth import digest


def test_incomplete_edgebook_proposes_only_finite_paths_and_never_absence():
    edges={'a':[('ab','b'),('ax','x')],'b':[('ba','a'),('bg','g')],'x':[('xx','x')]}
    ds,nxt=shortest_paths(edges,['g'])
    assert ds=={'g':0,'b':1,'a':2}
    assert 'x'not in ds
    assert nxt['a']==('ab','b')and nxt['b']==('bg','g')


def test_actual_target_path_certifies_cooperation_only_and_verifies_directly():
    t,_,s,actions=case();r=t['roots'][0]
    q=dict(input_digest=digest(t),rows=[dict(id=r['id'],fingerprint=r['fingerprint'],witness=actions)],
           caps=dict(proof_seconds=10,proposals=1))
    packet=run(t,q);receipt=verify(t,q,packet)
    assert receipt['counts']==dict(positive_roots=1,literal_edges=2)
    out=apply(t,packet)
    assert out['roots'][0]['cooperative_decisive']is True and 'wdl_bounds'not in out['roots'][0]
    packet['rows'][0]['observation']['terminal_winner']=0
    with pytest.raises(ValueError,match='literal proof'):verify(t,q,packet)


def test_bounded_incomplete_path_is_not_negative_truth():
    t,_,s,actions=case();r=t['roots'][0]
    q=dict(input_digest=digest(t),rows=[dict(id=r['id'],fingerprint=r['fingerprint'],witness=actions[:1])],
           caps=dict(proof_seconds=10,proposals=1))
    packet=run(t,q)
    assert packet['counts']['unknown']==1
    assert apply(t,packet)['roots'][0]['cooperative_decisive']is None
