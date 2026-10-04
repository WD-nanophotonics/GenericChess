"""Independent finite graph checks of the proposed reuse contract, not games."""
from collections import deque
from itertools import product


def bfs_contact(edges, terminals, start):
    queue=deque([(start,0)]);seen={start}
    while queue:
        node,cost=queue.popleft()
        if node in terminals:return cost+1
        for a,b in edges:
            if a==node and b not in seen:
                seen.add(b);queue.append((b,cost+1))
    return None


def test_all_three_state_nested_graphs_with_prefix_contact_contract():
    pairs=[(a,b) for a in range(3) for b in range(3) if a!=b]
    checked=0
    # absent from both, relaxed-only, or present in both: all nested edge pairs.
    for assignment in product(range(3),repeat=len(pairs)):
        actual={p for p,x in zip(pairs,assignment) if x==2}
        relaxed={p for p,x in zip(pairs,assignment) if x}
        for mask in range(8):
            terminals={n for n in range(3) if mask&(1<<n)}
            if any(a not in terminals for a,b in relaxed-actual):continue
            for start in range(3):
                assert bfs_contact(actual,terminals,start)==bfs_contact(relaxed,terminals,start)
                checked+=1
    assert checked>1000


def test_removed_edge_without_prefix_contact_can_underestimate():
    actual={(0,2),(2,3),(3,1)};relaxed=actual|{(0,1)}
    assert bfs_contact(actual,{1},0)==4
    assert bfs_contact(relaxed,{1},0)==2
    # Source0 cannot contact; the invalid0->1 edge has no absorbing substitute.
    assert 0 not in {1}


def test_lost_actual_edge_can_overestimate_or_invent_unreachability():
    assert bfs_contact({(0,1)},{1},0)==2
    assert bfs_contact(set(),{1},0) is None


def test_failed_sufficient_contract_does_not_imply_wrong_distance():
    actual={(0,2),(2,1)};relaxed=actual|{(0,3)}
    assert bfs_contact(actual,{1},0)==bfs_contact(relaxed,{1},0)==3
