"""Regress the observed research-consumer contract defects, not product output."""
from types import SimpleNamespace
from scripts.leaper_labelled_quiet_witness import predicate
from scripts.leaper_quiet_root_intervention import root_snapshot


def test_strict_quiet_witness_uses_every_noisy_upper_bound():
 quiet=dict(noisy=False,source_wdl=[0,0])
 assert predicate([quiet,dict(noisy=True,source_wdl=[-1,-1])])[0]
 assert not predicate([quiet,dict(noisy=True,source_wdl=[-1,1])])[0]
 assert not predicate([quiet,dict(noisy=True,source_wdl=[0,0])])[0]
 assert not predicate([quiet])[0]


def test_root_snapshot_evaluates_key_instead_of_storing_bound_method():
 key=['full-history-key-one']
 rt=SimpleNamespace(position='immutable-position',ply_count=0,terminal_status='ongoing',history=('root',),repetition_counts={'root':1},current_key='position-key',search_key=lambda:key[0])
 before=root_snapshot(rt)
 assert before[-1]=='full-history-key-one'
 key[0]='different-history-key'
 assert root_snapshot(rt)!=before
