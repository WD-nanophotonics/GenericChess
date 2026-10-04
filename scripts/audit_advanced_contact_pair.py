"""Frozen one-shot forced-promotion contact discriminator, not game labels."""
from collections import defaultdict
from dataclasses import asdict
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.ir import geometry_candidates
from scripts.intrinsic_action_events import event_cubes_for_candidate,_is_history_conditional
from scripts.compatible_contact import SourceNode,contact_steps


def audit(report):
    start=monotonic();compiled=compile_semantic_ruleset(build_standard_shogi_ruleset())
    def check():
        if monotonic()-start>=15:raise RuntimeError('15-second cap')
    def materialize():
        check()
        if report['materializations']>=128:raise RuntimeError('128 virtual edge cap')
        report['materializations']+=1
    cache={}
    def provider(node):
        if node in cache:return cache[node]
        groups=defaultdict(set);dynamic=set();held=set()
        for pattern in compiled.ir.patterns:
            if node.current not in pattern.type_ids:continue
            board=[]
            for gid in pattern.geometry_ids:
                geometry=compiled.ir.geometry[gid]
                if geometry.kind=='drop':held.add(pattern.name)
                else:board.append(geometry)
            if not board:continue
            if _is_history_conditional(pattern):raise ValueError('board history unsupported')
            if any(effect.kind in ('set_token','clear_token') for effect in pattern.effects):
                raise ValueError('board auxiliary effects unsupported')
            for invariant in pattern.invariants:
                if invariant.kind!='own_anchor_safe':raise ValueError('unknown board invariant')
                dynamic.add((pattern.name,invariant.kind))
            for geometry in board:
                if geometry.kind not in ('ray','leap'):raise ValueError('unsupported board geometry')
                for destination,path in geometry_candidates(geometry,'0',node.square):
                    check()
                    if report['geometry_candidates']>=5000:raise RuntimeError('5000 geometry cap')
                    report['geometry_candidates']+=1
                    found=event_cubes_for_candidate(compiled,pattern,type_id=node.current,owner=0,
                                                   source=node.square,target=destination,path=path)
                    for key,cubes in found.items():groups[key].update(cubes)
        events={k:tuple(sorted(v)) for k,v in sorted(groups.items())}
        report['tables'].append(dict(node=asdict(node),complete=True,excluded_held=sorted(held),
            excluded_dynamic=sorted(dynamic),events=[dict(key=k,cubes=v) for k,v in events.items()]))
        cache[node]=events;return events
    def choices(node,goal_only=False,chosen=None):
        events=provider(node)
        if chosen is not None:events={k:v for k,v in events.items() if k[3]==chosen and k[6]=='TN'}
        return contact_steps(node,events,area=81,owner=0,target=63,blockers={58:'own'},
                             goal_only=goal_only,checkpoint=materialize)
    def pack(s):return dict(event=s.event,node=asdict(s.node),completed=s.completed)
    first=choices(SourceNode('N','N',54))
    report['knight_first']=[pack(s) for s in first.values()]
    if len(first)!=1:raise ValueError('unexpected first Knight choice coverage')
    initial=next(iter(first.values()))
    if initial.completed or initial.node!=SourceNode('N','TN',73):
        raise ValueError('forced first promotion mismatch')
    for step in first.values():
        goal=choices(step.node,goal_only=True)
        report['knight_second_goal'].append(dict(after_first=step.event,complete=True,
                                                 choices=[pack(s) for s in goal.values()]))
        if goal:raise ValueError('distance2 exclusion refuted')
    report['knight_witness']=[pack(initial)];current=initial
    for destination in (64,63):
        chosen=choices(current.node,chosen=destination)
        if len(chosen)!=1:raise ValueError('unique compatible Knight witness step absent')
        current=next(iter(chosen.values()));report['knight_witness'].append(pack(current))
    if not current.completed:raise ValueError('Knight final removal missing')
    pawn=choices(SourceNode('P','P',54))
    report['pawn_first']=[pack(s) for s in pawn.values()]
    if not any(s.completed for s in pawn.values()):raise ValueError('Pawn direct capture absent')
    report['distances']={'N':3,'P':1}
    report['complete']=True;report['seconds']=monotonic()-start


if __name__=='__main__':
    output=ROOT/'docs/research/data/advanced_contact_pair_20261005.json'
    if output.exists():raise ValueError('fresh raw output required; no rerun')
    pins=['docs/research/ADVANCED_CONTACT_PAIR_PROTOCOL.md','scripts/audit_advanced_contact_pair.py',
          'scripts/compatible_contact.py','scripts/intrinsic_action_events.py',
          'scripts/intrinsic_occupancy_cubes.py','scripts/audit_static_semantic_material_prior_v2.py',
          'scripts/audit_static_semantic_material_prior_v2a.py','scripts/audit_static_semantic_material_prior_v2d.py',
          'scripts/public_task_intervals.py','generic_chess/rules/ir.py',
          'generic_chess/rules/compiler.py','generic_chess/rules/standard_shogi.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
                tables=[],knight_first=[],knight_second_goal=[],knight_witness=[],pawn_first=[],
                geometry_candidates=0,materializations=0,complete=False,
                scope=dict(task='virtual source-only preparation',public_transitions=0,goal_calls=0,
                           royal_safety=False,opponent_turns=False,mode_coefficients=False))
    try:audit(report)
    except Exception as error:report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                         for p,h in report['source_sha256'].items())
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','tables',
                   'knight_first','knight_second_goal','knight_witness','pawn_first')}))
