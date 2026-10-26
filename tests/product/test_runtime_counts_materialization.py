"""Exact persistent repetition-map reconstruction, including collision guards."""
from dataclasses import replace
from generic_chess.core.search_runtime import RuntimeCountsSnapshot

def reference_items(snapshot):
    values={}
    if snapshot.parent is None:values.update(dict(snapshot.root_items))
    else:
        values.update(dict(reference_items(snapshot.parent)))
        if snapshot.key is not None:
            if snapshot.count:values[snapshot.key]=snapshot.count
            else:values.pop(snapshot.key,None)
    from generic_chess.core.search_runtime import _identity_sort_key
    return tuple(sorted(values.items(),key=lambda item:_identity_sort_key(item[0])))

def test_multilevel_updates_deletions_and_reinsertions():
    root=RuntimeCountsSnapshot.from_counts({'a':1,'b':2})
    cur=root
    for key,count in [('a',3),('b',0),('c',1),('a',0),('b',4),('a',2)]:
        cur=cur.updated(key,count)
        assert cur.items()==reference_items(cur)
    assert dict(cur.items())=={'a':2,'b':4,'c':1}
    assert root.items()==(('a',1),('b',2))

def test_persistent_siblings_do_not_mutate_each_other():
    root=RuntimeCountsSnapshot.from_counts({'a':1});left=root.updated('a',2);right=root.updated('b',1)
    assert left.items()==(('a',2),)
    assert right.items()==(('a',1),('b',1))
    assert root.items()==(('a',1),)

def test_equal_maps_different_update_order_keep_exact_equality():
    root=RuntimeCountsSnapshot.from_counts({'a':1})
    x=root.updated('b',2).updated('c',3);y=root.updated('c',3).updated('b',2)
    assert x.digest==y.digest and x==y and hash(x)==hash(y)

def test_matching_digest_cannot_hide_different_exact_count_or_key():
    x=RuntimeCountsSnapshot.from_counts({'a':1});y=RuntimeCountsSnapshot.from_counts({'a':2});z=RuntimeCountsSnapshot.from_counts({'b':1})
    assert x!=replace(y,digest=x.digest)
    assert x!=replace(z,digest=x.digest)

def test_realistic_long_branch_matches_reference_without_parent_resorting():
    root=RuntimeCountsSnapshot.from_counts({str(i):1 for i in range(16)});cur=root
    for i in range(128):cur=cur.updated(str(i%32),i%4)
    assert cur.items()==reference_items(cur)
    assert root.items()==reference_items(root)

def test_none_key_nonroot_snapshot_retains_parent_map():
    root=RuntimeCountsSnapshot.from_counts({'a':1});cur=RuntimeCountsSnapshot(root,None,0,0,root.digest)
    assert cur.items()==root.items() and cur==root
