"""Cooperative first-repetition reachability on an admitted physical graph.

This is a graph diagnostic, not a replacement for Core, WDL solving, Player
search or full rule admission. It finds a shortest legal suffix whose FIRST
history-based draw is repetition at a selected vertex. Static terminals cannot
be traversed. Other history adjudications are outside scope.
"""
from collections import deque

def min_first_repetition(edges,terminals,root,counts,limit,target,*,witness=False,guard=lambda:None):
    n=len(edges)
    if (len(counts)!=n or type(limit)is not int or limit<2 or
        not 0<=root<n or not 0<=target<n or
        any(type(c)is not int or not 0<=c<limit for c in counts)or counts[root]==0 or root in terminals):
        raise ValueError('ongoing complete-count contract required')
    if any((bool(ee)if i in terminals else not ee)or any(type(j)is not int or not 0<=j<n for j in ee)for i,ee in enumerate(edges)):
        raise ValueError('complete terminal-sink graph required')
    if target in terminals:return None
    required=limit-counts[target];N=2*n+2;source=2*n;sink=source+1;network=[[]for _ in range(N)]
    originals=[]
    def add(u,v,capacity,cost,move=None):
        if capacity<=0:return
        originals.append((u,len(network[u]),capacity,move))
        network[u].append([v,len(network[v]),capacity,cost]);network[v].append([u,len(network[u])-1,0,-cost])
    for i in range(n):
        if i not in terminals and i!=target:add(2*i,2*i+1,limit-counts[i]-1,0)
    for i,ee in enumerate(edges):
        if i in terminals:continue
        for j in ee:
            if j not in terminals:add(2*i+1,2*j,required,1,(i,j))
    if root==target:add(source,2*target+1,required,0)
    else:
        add(source,2*root+1,1,0);add(source,2*target+1,required-1,0)
    add(2*target,sink,required,0)
    sent=0;total=0;INF=10**20
    while sent<required:
        guard()
        distance=[INF]*N;distance[source]=0;previous=[None]*N
        # Integral successive shortest augmentation. Bellman-Ford supports the
        # reverse residual arcs; previous optimal flows have no negative cycle.
        for _ in range(N-1):
            guard()
            changed=False
            for u,aa in enumerate(network):
                if distance[u]==INF:continue
                for k,(v,reverse,capacity,cost)in enumerate(aa):
                    candidate=distance[u]+cost
                    if capacity>0 and candidate<distance[v]:
                        distance[v]=candidate;previous[v]=(u,k);changed=True
            if not changed:break
        if previous[sink]is None:return None
        amount=required-sent;at=sink
        while at!=source:
            u,k=previous[at];amount=min(amount,network[u][k][2]);at=u
        at=sink
        while at!=source:
            u,k=previous[at];v,reverse,capacity,cost=network[u][k];network[u][k][2]-=amount;network[v][reverse][2]+=amount;at=u
        sent+=amount;total+=amount*distance[sink]
    if not witness:return total
    outgoing=[[]for _ in range(N)]
    for u,k,capacity,move in originals:
        used=capacity-network[u][k][2]
        if used:outgoing[u].append([network[u][k][0],used,move])
    paths=[]
    for _ in range(required):
        at=source;moves=[];start=None;visited=set()
        while at!=sink:
            if at in visited:raise ValueError('positive-flow cycle in shortest solution')
            visited.add(at)
            edge=next((e for e in outgoing[at]if e[1]),None)
            if edge is None:raise ValueError('flow decomposition failed')
            to,used,move=edge;edge[1]-=1
            if at==source:start=to//2
            if move is not None:moves.append(move)
            at=to
        paths.append((start,moves))
    if root!=target:paths.sort(key=lambda p:p[0]!=root)
    walk=[root]
    for start,moves in paths:
        if walk[-1]!=start:raise ValueError('flow paths cannot be concatenated')
        for i,j in moves:
            if walk[-1]!=i:raise ValueError('flow movement mismatch')
            walk.append(j)
    if len(walk)-1!=total:raise ValueError('flow move cost mismatch')
    return dict(distance=total,walk=walk,required_target_visits=required)
