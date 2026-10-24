"""Cheap sufficient first-current-repetition certificate, no Core changes."""
from collections import deque

def repeated_single_cycle(edges,terminals,root,counts,limit):
    if (len(counts)!=len(edges)or limit<2 or root in terminals or
        not 0<=root<len(edges)or any(not 0<=c<limit for c in counts)or counts[root]==0):
        raise ValueError('ongoing count contract required')
    repeats=limit-counts[root]
    allowed={i for i in range(len(edges))if i not in terminals and(i==root or limit-counts[i]-1>=repeats)}
    todo=deque();parent={root:None};end=None
    for j in edges[root]:
        if j==root:return dict(distance=repeats,cycle=[root,root],walk=[root]*(repeats+1),repeats=repeats)
        if j in allowed and j not in parent:parent[j]=root;todo.append(j)
    while todo and end is None:
        i=todo.popleft()
        for j in edges[i]:
            if j==root:end=i;break
            if j in allowed and j not in parent:parent[j]=i;todo.append(j)
    if end is None:return None  # UNKNOWN, not a no-cycle/no-repetition proof.
    back=[end]
    while back[-1]!=root:back.append(parent[back[-1]])
    path=list(reversed(back))+[root];walk=[root]+path[1:]*repeats
    return dict(distance=(len(path)-1)*repeats,cycle=path,walk=walk,repeats=repeats)
