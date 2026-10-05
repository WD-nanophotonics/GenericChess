"""One-shot selected held contact paths; explicitly virtual, not public legality."""
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
from scripts.intrinsic_action_events import (collect_intrinsic_held_drop_events,
                                            event_cubes_for_candidate,_is_history_conditional)
from scripts.compatible_contact import SourceNode,contact_steps


def audit(report):
    started=monotonic()
    compiled=compile_semantic_ruleset(build_standard_shogi_ruleset())
    cache={}
    def check():
        if monotonic()-started>=15:
            raise RuntimeError('15-second cap')
    def materialize():
        check()
        if report['materializations']>=128:
            raise RuntimeError('128 virtual edge cap')
        report['materializations']+=1
    drops={}
    for tid in ('B','R'):
        check()
        table=collect_intrinsic_held_drop_events(compiled,tid,max_targets=1000)
        if not table['coarse_coverage_complete'] or table['excluded_state_constraints']:
            raise ValueError('unqualified held effect/mask/constraint')
        if table['full_legality_modeled'] or table['target_count']!=162:
            raise ValueError('wrong drop scope or mask coverage')
        if table['excluded_dynamic']!=((f'legacy_{tid}_drop','own_anchor_safe'),):
            raise ValueError('unexpected held dynamic exclusion')
        report['drop_tables'][tid]={k:v for k,v in table.items() if k!='events'}
        report['drop_tables'][tid]['events']=[dict(key=k,cubes=v) for k,v in table['events'].items()]
        drops[tid]=table['events']
    def board_events(node,owner):
        key=(node.current,node.square,owner)
        if key in cache:
            return cache[key]
        groups=defaultdict(set);held=set();dynamic=set()
        for pattern in compiled.ir.patterns:
            if node.current not in pattern.type_ids:
                continue
            board=[]
            for gid in pattern.geometry_ids:
                geometry=compiled.ir.geometry[gid]
                if geometry.kind=='drop':
                    held.add(pattern.name)
                else:
                    board.append(geometry)
            if not board:
                continue
            if _is_history_conditional(pattern) or pattern.postconditions:
                raise ValueError('unsupported board history/postconditions')
            if any(e.kind in ('set_token','clear_token') for e in pattern.effects):
                raise ValueError('unsupported auxiliary effects')
            for inv in pattern.invariants:
                if inv.kind!='own_anchor_safe':
                    raise ValueError('unsupported dynamic invariant')
                dynamic.add((pattern.name,inv.kind))
            for geometry in board:
                if geometry.kind not in ('ray','leap'):
                    raise ValueError('unsupported board geometry')
                for target,path in geometry_candidates(geometry,str(owner),node.square):
                    check()
                    if report['geometry_candidates']>=5000:
                        raise RuntimeError('5000 per-pattern candidate cap')
                    report['geometry_candidates']+=1
                    for event,cubes in event_cubes_for_candidate(compiled,pattern,
                            type_id=node.current,owner=owner,source=node.square,target=target,path=path).items():
                        groups[event].update(cubes)
        events={k:tuple(sorted(v)) for k,v in sorted(groups.items())}
        report['board_tables'].append(dict(node=asdict(node),owner=owner,
            complete_intrinsic_board=True,excluded_held=sorted(held),excluded_dynamic=sorted(dynamic),
            excluded_history=[],excluded_auxiliary_effects=[],
            events=[dict(key=k,cubes=v) for k,v in events.items()]))
        cache[key]=events
        return events
    cases=[('B',0,10,61,1),('B',8,16,55,7),
           ('B',72,64,63,73),('B',80,70,71,79),('R',0,10,1,None)]
    for owner in (0,1):
        reflect=lambda x:x if owner==0 or x is None else 80-x
        for tid,d,b,q,r in cases:
            d,b,q,r=map(reflect,(d,b,q,r))
            row=dict(owner=owner,base=tid,target=d,blocker=b,drop=q,quiet=r,steps=[],complete=False)
            report['routes'].append(row)
            event=(owner,tid,'hand',q,'empty',(),tid)
            if event not in drops[tid] or q in (d,b):
                raise ValueError('drop not compatible with held occupancy/mask')
            materialize()
            node=SourceNode(tid,tid,q)
            row['steps'].append(dict(event=event,cubes=drops[tid][event],node=asdict(node),completed=False))
            for destination,current in ([(r,'TB'),(d,'TB')] if tid=='B' else [(d,'R')]):
                full=board_events(node,owner)
                selected={k:v for k,v in full.items() if k[3]==destination and k[6]==current}
                found=contact_steps(node,selected,area=81,owner=owner,target=d,
                                    blockers={b:'own'},checkpoint=materialize)
                if len(found)!=1:
                    raise ValueError('selected compatible board witness absent/nonunique')
                step=next(iter(found.values()))
                if step.completed!=(destination==d) or step.node.base!=tid:
                    raise ValueError('completion or base identity drift')
                row['steps'].append(dict(event=step.event,cubes=selected[step.event],
                                         node=asdict(step.node),completed=step.completed))
                node=step.node
            row['complete']=row['steps'][-1]['completed']
    report['complete']=all(r['complete'] for r in report['routes']) and len(report['routes'])==10
    report['seconds']=monotonic()-started


if __name__=='__main__':
    output=ROOT/'docs/research/data/held_contact_compiled_20261005.json'
    if output.exists():
        raise ValueError('fresh output required; completed audit never rerun')
    pins=['docs/research/HELD_CONTACT_COMPILED_PROTOCOL.md','scripts/audit_held_contact_compiled.py',
          'scripts/compatible_contact.py','scripts/intrinsic_action_events.py',
          'scripts/intrinsic_occupancy_cubes.py','scripts/audit_static_semantic_material_prior_v2.py',
          'scripts/audit_static_semantic_material_prior_v2a.py','scripts/audit_static_semantic_material_prior_v2d.py',
          'generic_chess/rules/compiler.py','generic_chess/rules/ir.py','generic_chess/rules/standard_shogi.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
                drop_tables={},board_tables=[],routes=[],geometry_candidates=0,materializations=0,
                complete=False,scope=dict(n=1,virtual=True,public_transitions=0,goal_calls=0,
                    royal_safety=False,opponent_turns=False,full_inventory=False))
    try:
        audit(report)
    except Exception as error:
        report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                        for p,h in report['source_sha256'].items())
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','drop_tables','board_tables','routes')}))
