"""One fresh virtual event check, independent of prefix blocker-set arithmetic."""
from collections import defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.ir import geometry_candidates
from scripts.intrinsic_action_events import event_cubes_for_candidate
from scripts.compatible_contact import SourceNode,contact_steps

OUT=ROOT/'docs/research/data/shared_prefix_events_20261005.json'
SOURCES=('scripts/audit_shared_prefix_events.py','docs/research/SHARED_PREFIX_EVENT_QUALIFICATION_PROTOCOL.md',
         'scripts/intrinsic_action_events.py','scripts/compatible_contact.py',
         'generic_chess/rules/compiler.py','generic_chess/rules/ir.py','generic_chess/rules/standard_shogi.py')


def run(report):
    start=monotonic();c=compile_semantic_ruleset(build_standard_shogi_ruleset());cache={}
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec including compilation')
    def materialize():
        check()
        if report['materializations']>=128:raise ValueError('128 virtual materialization cap')
        report['materializations']+=1
    def table(node,owner):
        key=(node.current,node.square,owner)
        if key in cache:return cache[key]
        groups=defaultdict(set);excluded=set()
        for p in c.ir.patterns:
            if node.current not in p.type_ids:continue
            if p.guards or p.slot_guards or p.square_zone_guards or p.postconditions:
                raise ValueError('unsupported board guard')
            for gid in p.geometry_ids:
                g=c.ir.geometry[gid]
                if g.kind=='drop':excluded.add(p.name);continue
                if g.kind not in ('ray','leap') or any(i.kind!='own_anchor_safe' for i in p.invariants):
                    raise ValueError('unqualified geometry/invariant')
                for d,path in geometry_candidates(g,str(owner),node.square):
                    check();report['geometry_candidates']+=1
                    if report['geometry_candidates']>5000:raise ValueError('5000 candidate cap')
                    for e,cubes in event_cubes_for_candidate(c,p,type_id=node.current,owner=owner,
                                                           source=node.square,target=d,path=path).items():
                        groups[e].update(cubes)
        events={e:tuple(sorted(cubes)) for e,cubes in groups.items()}
        report['tables'].append(dict(node=asdict(node),owner=owner,excluded_held=sorted(excluded),
            excluded_dynamic='own_anchor_safe',complete=True,events=[dict(event=e,cubes=v) for e,v in events.items()]))
        cache[key]=events;return events
    for owner in (0,1):
        rotate=lambda x:x if owner==0 else 80-x
        s,d,b=map(rotate,(54,65,0));node=SourceNode('S','S',s)
        row=dict(kind='Silver2',owner=owner,target=d,blocker=b,first=[],removals=[],complete=False)
        report['rows'].append(row)
        first=contact_steps(node,table(node,owner),area=81,owner=owner,target=d,blockers={b:'own'},checkpoint=materialize)
        if any(v.completed for v in first.values()):raise ValueError('unexpected Silver direct contact')
        for e,step in first.items():
            row['first'].append(dict(event=e,node=asdict(step.node)))
            final=contact_steps(step.node,table(step.node,owner),area=81,owner=owner,target=d,blockers={b:'own'},
                                goal_only=True,checkpoint=materialize)
            for tail,last in final.items():
                if not last.completed or last.node.base!='S':raise ValueError('source custody/completion drift')
                row['removals'].append(dict(first=e,last=tail,node=asdict(last.node)))
        row['complete']=bool(row['removals'])
        s,d,b,u=map(rotate,(10,9,55,11));node=SourceNode('R','R',s)
        first=contact_steps(node,table(node,owner),area=81,owner=owner,target=d,blockers={b:'own'},checkpoint=materialize)
        step=next(v for v in first.values() if not v.completed and v.node.square==u and v.node.current=='R')
        selected={e:v for e,v in table(step.node,owner).items() if e[3]==d and e[4]=='enemy'}
        tails=contact_steps(step.node,selected,area=81,owner=owner,target=d,blockers={b:'own'},goal_only=True,checkpoint=materialize)
        if len(tails)!=1 or not next(iter(tails.values())).completed:raise ValueError('vacated source ray blocked')
        row=dict(kind='RookVacating',owner=owner,target=d,blocker=b,source=s,intermediate=u,
                 first=step.event,last=next(iter(tails)),complete=True)
        report['rows'].append(row)
    report['complete']=len(report['rows'])==4 and all(r['complete'] for r in report['rows'])
    report['seconds']=monotonic()-start


if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen virtual qualification never rerun')
    report=dict(complete=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
                materializations=0,geometry_candidates=0,public_transitions=0,goal_queries=0,tables=[],rows=[])
    try:run(report)
    except Exception as e:report['error']=f'{type(e).__name__}: {e}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('tables','source_sha256')}))
