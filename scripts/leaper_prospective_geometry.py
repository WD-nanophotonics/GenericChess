"""Prospective finite-board Leap geometry census; never a game solver.

Keys describe labelled movement relations only. Complete RuleSet/history/clock
identities are deliberately outside this analysis; never use keys for TT reuse.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
import gzip
import hashlib
import json
from pathlib import Path
import time

from tools.local_agent.common import write_json

# Matrices in the square's common absolute coordinate system.
D4 = ((1,0,0,1), (0,-1,1,0), (-1,0,0,-1), (0,1,-1,0),
      (-1,0,0,1), (1,0,0,-1), (0,1,1,0), (0,-1,-1,0))


def checked(n, offsets):
    if type(n) is not int or n < 2:
        raise ValueError("square extent must be an integer >=2")
    out = set()
    for v in offsets:
        if len(v) != 2 or any(type(z) is not int for z in v) or tuple(v) == (0,0):
            raise ValueError("nonzero integer Leap required")
        out.add(tuple(v))
    return tuple(sorted(out))


def effective(n, offsets):
    return tuple(v for v in checked(n, offsets) if abs(v[0]) < n and abs(v[1]) < n)


def vector(v, matrix):
    a,b,c,d = matrix
    return (a*v[0]+b*v[1], c*v[0]+d*v[1])


def square(index, n, matrix):
    x,y = index % n,index // n
    a,b,c,d = matrix
    u,v = vector((x,y), matrix)
    return (u + (n-1 if a+b < 0 else 0)) + n*(v + (n-1 if c+d < 0 else 0))


def edges(n, offsets, owner=0):
    if type(owner) is not int or owner not in (0,1):
        raise ValueError("owner0/1 required")
    sign = 1 if owner == 0 else -1
    result = set()
    for x in range(n):
        for y in range(n):
            for dx,dy in effective(n, offsets):
                u,v = x+sign*dx, y+sign*dy
                if 0 <= u < n and 0 <= v < n:
                    result.add((x+n*y, u+n*v))
    return tuple(sorted(result))


def joint_key(n, labelled_offsets):
    """A simultaneous spatial orbit of TYPE-LABELLED empty-board relations.

    Caller labels must remain fixed. No per-type rotation, type permutation,
    setup, history, legality, evaluation, outcome or complete-rule equivalence.
    """
    names = sorted(labelled_offsets)
    normalized = {name:effective(n, labelled_offsets[name]) for name in names}
    return n, min(tuple((name, tuple(sorted(vector(v,m) for v in normalized[name])))
                        for name in names) for m in D4)


def components(adj):
    unseen = set(adj)
    sizes = []
    while unseen:
        seen = {min(unseen)}
        queue = list(seen)
        while queue:
            for v in adj[queue.pop()] - seen:
                seen.add(v)
                queue.append(v)
        unseen -= seen
        sizes.append(len(seen))
    return tuple(sorted(sizes))


def descriptor(n, offsets):
    ee = edges(n, offsets)
    adj = {v:set() for v in range(n*n)}
    rev = {v:set() for v in adj}
    weak = {v:set() for v in adj}
    for a,b in ee:
        adj[a].add(b); rev[b].add(a); weak[a].add(b); weak[b].add(a)
    # For <=36 vertices, independent reachability closure gives exact SCC sizes.
    reaches = {}
    for root in adj:
        seen = {root}; todo = [root]
        while todo:
            for nxt in adj[todo.pop()] - seen:
                seen.add(nxt); todo.append(nxt)
        reaches[root] = seen
    remaining = set(adj); strong = []
    while remaining:
        root = min(remaining)
        part = {v for v in remaining if v in reaches[root] and root in reaches[v]}
        remaining -= part; strong.append(len(part))
    colors = {}
    bipartite = True
    for root in weak:
        if root in colors: continue
        colors[root] = 0; todo = [root]
        while todo:
            current = todo.pop()
            for nxt in weak[current]:
                if nxt not in colors:
                    colors[nxt] = 1-colors[current]; todo.append(nxt)
                elif colors[nxt] == colors[current]:
                    bipartite = False
    return (len(ee),tuple(sorted(Counter((len(adj[v]),len(rev[v])) for v in adj).items())),
            components(weak),tuple(sorted(strong)),bipartite)


def stable(value):
    return json.dumps(value, sort_keys=True,separators=(",",":"))


def census(output, plan_file):
    if output.exists():
        raise ValueError("new output required; do not refill an existing run")
    output.mkdir(parents=True)
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    frozen = plan["frozen_pool"]
    if frozen["board_sizes"] != [4,5,6] or frozen["radius"] != 5 or frozen["atoms_per_type"] != [1,2]:
        raise ValueError("unexpected frozen pool")
    start = datetime.now(timezone.utc).isoformat(); tick = time.perf_counter()
    dirs = tuple((x,y) for x in range(-5,6) for y in range(-5,6) if (x,y)!=(0,0))
    masks = tuple((v,) for v in dirs) + tuple(combinations(dirs,2))
    assert len(dirs)==120 and len(masks)==7260
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    rows = []; summaries = []; incomplete = None
    for n in frozen["board_sizes"]:
        canon = Counter(); finite = Counter(); desc = defaultdict(set); witnesses = {}
        # Expensive descriptors computed once per effective relation, not raw mask.
        details = {}
        board_rows = []
        for raw in masks:
            if time.perf_counter()-tick >= 600:
                incomplete = {"board":n,"raw":raw,"reason":"frozen600s cap"}
                break
            eff = effective(n,raw); key = joint_key(n,{"T":eff})
            if eff not in details: details[eff] = descriptor(n,eff)
            dd = details[eff]
            canon[key] += 1; finite[eff] += 1; desc[dd].add(key)
            if dd not in witnesses: witnesses[dd] = (raw,key)
            if len(desc[dd]) > 1 and dd not in witnesses.get("collisions",{}):
                old,old_key = witnesses[dd]
                if old_key != key:
                    witnesses.setdefault("collisions",{})[dd] = {"first":old,"second":raw,
                        "descriptor":dd,"first_key":old_key,"second_key":key}
            board_rows.append({"raw":raw,"effective":eff,"spatial_key":key,"descriptor":dd})
        rows.append({"n":n,"rows":board_rows})
        u=(2*n-1)**2-1; inactive=120-u
        # No two effective directions give the same nonempty displacement edge:
        # edge displacement recovers its unique direction; hence analytic count.
        expected_finite=(u+u*(u-1)//2 + int(inactive>0))
        expected_empty=inactive + inactive*(inactive-1)//2
        summaries.append({"n":n,"raw_sets_observed":len(board_rows),"effective_relations":len(finite),
            "effective_relations_expected":expected_finite,"spatial_classes":len(canon),
            "empty_raw_sets":finite.get((),0),"empty_raw_sets_expected":expected_empty,
            "raw_per_spatial_class_min":min(canon.values()),
            "raw_per_spatial_class_max":max(canon.values()),
            "descriptor_groups":len(desc),"descriptor_groups_with_distinct_spatial_keys":
                sum(len(x)>1 for x in desc.values()),
            "descriptor_collision_examples":list(witnesses.get("collisions",{}).values())[:3],
            "not_claimed":"same descriptor is NOT same graph; spatial key NOT full RuleSet/WDL",
            "complete":incomplete is None})
        if incomplete: break
    with gzip.GzipFile(filename=str(output/"rows.json.gz"),mode="wb",mtime=0) as f:
        f.write(stable(rows).encode())
    final = {"status":"INCOMPLETE" if incomplete else "CLOSED_GEOMETRY_ONLY",
        "started_at":start,"ended_at":datetime.now(timezone.utc).isoformat(),
        "seconds":time.perf_counter()-tick,"source_sha256":source_hash,
        "plan_sha256":hashlib.sha256(plan_file.read_bytes()).hexdigest(),
        "summary":summaries,"failure":incomplete,"Player":0,"solver":0,"games":0,
        "claim_scope":"prospective abstract direction pool, NOT generated game acceptance, strength or holdout",
        "raw_rows_sha256":hashlib.sha256((output/"rows.json.gz").read_bytes()).hexdigest()}
    write_json(output/"summary.json",final)
    print(stable(final))
    return final


if __name__ == "__main__":
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--plan",type=Path,required=True)
    a=p.parse_args()
    census(a.output,a.plan)
