"""Frozen intrinsic source-only contact qualifier; no PublicGame execution."""
from collections import defaultdict
from dataclasses import asdict
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.ir import geometry_candidates
from scripts.intrinsic_action_events import event_cubes_for_candidate,_is_history_conditional
from scripts.compatible_contact import SourceNode,contact_steps,discounted_contact_interval

PROTOCOL='docs/research/COMPATIBLE_CONTACT_DISCRIMINATOR_PROTOCOL.md'
SHA='ca8fc02d1d699420e310fd1732c4cb3578935150a9beb9b4e3f9b39644360068'


class Limit(Exception):pass


def audit(report):
    start=monotonic()
    if hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest()!=SHA:raise ValueError('frozen protocol drift')

    def check():
        if monotonic()-start>=15:raise Limit('15-second cap')

    def geometry_tick():
        check()
        if report['geometry_candidates']>=5000:raise Limit('5000 geometry candidate cap')
        report['geometry_candidates']+=1

    def materialize_tick():
        check()
        if report['virtual_materializations']>=128:raise Limit('128 virtual materialization cap')
        report['virtual_materializations']+=1

    compiled=compile_semantic_ruleset(build_standard_shogi_ruleset())
    if compiled.support.board_shape.width!=9 or compiled.support.board_shape.height!=9:
        raise ValueError('frozen board shape mismatch')
    report['scope']=dict(task='intrinsic source-only fixed-target preparation',royal_safety=False,
                         official_history=False,opponent_actions=False,full_game_legality=False,
                         target_type='P',source_base='R',gamma='1/2',public_transitions=0,goal_calls=0)

    def provider(node,row):
        if node in row['cache']:return row['cache'][node]
        groups=defaultdict(set);dynamic=set();held=set();aux=set()
        count_before=report['geometry_candidates']
        for pattern in compiled.ir.patterns:
            if node.current not in pattern.type_ids:continue
            if _is_history_conditional(pattern):raise ValueError('history-dependent source pattern unsupported')
            for invariant in pattern.invariants:
                if invariant.kind=='own_anchor_safe':dynamic.add((pattern.name,invariant.kind))
                else:raise ValueError('unexpected intrinsic invariant')
            for effect in pattern.effects:
                if effect.kind in ('set_token','clear_token'):
                    aux.add((pattern.name,effect.kind))
            if aux:raise ValueError('auxiliary source state cannot be composed')
            for gid in pattern.geometry_ids:
                geometry=compiled.ir.geometry[gid]
                if geometry.kind=='drop':held.add(pattern.name);continue
                if geometry.kind not in ('ray','leap'):raise ValueError('unsupported board geometry')
                for destination,path in geometry_candidates(geometry,'0',node.square):
                    geometry_tick()
                    found=event_cubes_for_candidate(compiled,pattern,type_id=node.current,owner=0,
                                                   source=node.square,target=destination,path=path)
                    for key,cubes in found.items():groups[key].update(cubes)
        events={k:tuple(sorted(v)) for k,v in sorted(groups.items())}
        row['tables'].append(dict(node=asdict(node),geometry_candidates=report['geometry_candidates']-count_before,
                                 complete=True,excluded_dynamic=sorted(dynamic),excluded_held=sorted(held),
                                 events=[dict(key=k,cubes=v) for k,v in events.items()]))
        row['cache'][node]=events
        check();return events

    def choices(node,row,*,goal_only=False,chosen=None):
        events=provider(node,row)
        if chosen is not None:
            # A witness query is not presented as complete legal choices.
            events={k:v for k,v in events.items() if k[3]==chosen and k[6]=='R'}
        return contact_steps(node,events,area=81,owner=0,target=59,blockers=row['blockers'],
                             goal_only=goal_only,checkpoint=materialize_tick)

    def pack(step):return dict(event=step.event,node=asdict(step.node),completed=step.completed)

    try:
        for name,blockers in [('clear',{}),('blocked',{58:'own'})]:
            row=dict(name=name,blockers=blockers,tables=[],first_steps=[],second_goal_queries=[],witness=[],
                     excluded_through=0,witness_length=None,complete=False,contact_interval=[F(0),F(1,2)],cache={})
            report['rows'].append(row)
            root=SourceNode('R','R',54)
            first=choices(root,row);row['first_steps']=[pack(s) for s in first.values()]
            captures=[s for s in first.values() if s.completed]
            if captures:
                row['witness']=[pack(captures[0])];row['witness_length']=1
                row['complete']=True;row['distance']=1
                row['contact_interval']=discounted_contact_interval(F(1,2),excluded_through=0,witness_length=1)
                if name!='clear':raise ValueError('blocked depth1 contradicts frozen hypothesis')
                continue
            if not first:raise ValueError('unexpected no-first-motion task')
            row['excluded_through']=1
            for step in first.values():
                goal=choices(step.node,row,goal_only=True)
                row['second_goal_queries'].append(dict(after_first=step.event,node=asdict(step.node),complete=True,
                                                        goal_steps=[pack(s) for s in goal.values()]))
                if goal:raise ValueError('second contact refutes frozen depth2 exclusion')
            row['excluded_through']=2
            # Reuse the complete first native a7-a6 event, not a new first edge.
            initial=[s for s in first.values() if s.node==SourceNode('R','R',45)]
            if len(initial)!=1:raise ValueError('unique native first witness step absent')
            current=initial[0];row['witness'].append(pack(current))
            for destination in (50,59):
                chosen=choices(current.node,row,chosen=destination)
                if len(chosen)!=1:raise ValueError('unique compatible native witness step absent')
                current=next(iter(chosen.values()));row['witness'].append(pack(current))
            if not current.completed:raise ValueError('witness did not remove designated target')
            row['witness_length']=3;row['distance']=3;row['complete']=True
            row['contact_interval']=discounted_contact_interval(F(1,2),excluded_through=2,witness_length=3)
        report['all_controls_complete']=True
    finally:
        for row in report['rows']:
            row['contact_interval']=discounted_contact_interval(F(1,2),excluded_through=row['excluded_through'],
                                                                witness_length=row['witness_length'])
            row.pop('cache',None)
        report['seconds']=monotonic()-start


if __name__=='__main__':
    destination=ROOT/'docs/research/data/compatible_contact_discriminator_20261005.json'
    if destination.exists() or not destination.parent.is_dir():raise ValueError('fresh output preflight prevents rerun')
    paths=[PROTOCOL,'scripts/audit_compatible_contact_discriminator.py','scripts/compatible_contact.py',
           'scripts/intrinsic_action_events.py','scripts/intrinsic_occupancy_cubes.py',
           'scripts/audit_static_semantic_material_prior_v2.py','scripts/audit_static_semantic_material_prior_v2a.py',
           'scripts/audit_static_semantic_material_prior_v2d.py','scripts/public_task_intervals.py',
           'generic_chess/rules/ir.py','generic_chess/rules/compiler.py','generic_chess/rules/standard_shogi.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                geometry_candidates=0,virtual_materializations=0,rows=[],all_controls_complete=False)
    try:audit(report)
    except Exception as error:report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    destination.write_text(json.dumps(report,indent=2,default=str)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','rows')},default=str))
    print(json.dumps([dict(name=r['name'],first_choices=len(r['first_steps']),second_queries=len(r['second_goal_queries']),
                           complete=r['complete'],interval=r['contact_interval'],distance=r.get('distance'),tables=len(r['tables']))
                      for r in report['rows']],default=str))
