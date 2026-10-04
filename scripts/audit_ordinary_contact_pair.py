"""One-shot ordinary-source reversal witness; no official game search."""
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
    start=monotonic();compiled=compile_semantic_ruleset(build_standard_shogi_ruleset());cache={}
    def check():
        if monotonic()-start>=15:raise RuntimeError('15-second cap')
    def materialize():
        check()
        if report['materializations']>=128:raise RuntimeError('128 virtual edge cap')
        report['materializations']+=1
    def provider(node):
        if node in cache:return cache[node]
        groups=defaultdict(set);held=set();dynamic=set()
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
                if invariant.kind!='own_anchor_safe':raise ValueError('unknown invariant')
                dynamic.add((pattern.name,invariant.kind))
            for geometry in board:
                if geometry.kind not in ('ray','leap'):raise ValueError('unsupported geometry')
                for target,path in geometry_candidates(geometry,'0',node.square):
                    check()
                    if report['geometry_candidates']>=5000:raise RuntimeError('5000 geometry cap')
                    report['geometry_candidates']+=1
                    for key,cubes in event_cubes_for_candidate(compiled,pattern,type_id=node.current,
                               owner=0,source=node.square,target=target,path=path).items():groups[key].update(cubes)
        events={k:tuple(sorted(v)) for k,v in sorted(groups.items())}
        report['tables'].append(dict(node=asdict(node),complete=True,excluded_held=sorted(held),
            excluded_dynamic=sorted(dynamic),events=[dict(key=k,cubes=v) for k,v in events.items()]))
        cache[node]=events;return events
    def choices(node,chosen=None,new_type=None):
        events=provider(node)
        if chosen is not None:events={k:v for k,v in events.items() if k[3]==chosen and k[6]==new_type}
        return contact_steps(node,events,area=81,owner=0,target=19,blockers={58:'own'},checkpoint=materialize)
    def pack(s):return dict(event=s.event,node=asdict(s.node),completed=s.completed)
    knight=choices(SourceNode('N','N',0));report['knight_first']=[pack(s) for s in knight.values()]
    if not any(s.completed for s in knight.values()):raise ValueError('Knight direct removal missing')
    first=choices(SourceNode('P','P',0));report['pawn_first']=[pack(s) for s in first.values()]
    if len(first)!=1:raise ValueError('unexpected first Pawn choice coverage')
    current=next(iter(first.values()))
    if current.node!=SourceNode('P','P',9) or current.completed:raise ValueError('Pawn first step mismatch')
    report['pawn_witness']=[pack(current)]
    for destination in (18,27,36,45,54,55,46,37,28,19):
        kind='P' if destination in (18,27,36,45) else 'TP'
        selected=choices(current.node,chosen=destination,new_type=kind)
        if len(selected)!=1:raise ValueError('unique selected Pawn witness absent')
        current=next(iter(selected.values()))
        if current.completed!=(destination==19):raise ValueError('wrong physical completion')
        report['pawn_witness'].append(pack(current))
    report['complete']=len(report['pawn_witness'])==11 and current.completed
    report['distances']={'N_empirical':1,'P_upper_empirical':11,'P_minimum_separate_analytic':11}
    report['seconds']=monotonic()-start


if __name__=='__main__':
    output=ROOT/'docs/research/data/ordinary_contact_pair_20261005.json'
    if output.exists():raise ValueError('fresh raw output required; no rerun')
    pins=['docs/research/ORDINARY_CONTACT_PAIR_PROTOCOL.md','scripts/audit_ordinary_contact_pair.py',
          'scripts/compatible_contact.py','scripts/intrinsic_action_events.py',
          'scripts/intrinsic_occupancy_cubes.py','scripts/audit_static_semantic_material_prior_v2.py',
          'scripts/audit_static_semantic_material_prior_v2a.py','scripts/audit_static_semantic_material_prior_v2d.py',
          'scripts/public_task_intervals.py','generic_chess/rules/ir.py',
          'generic_chess/rules/compiler.py','generic_chess/rules/standard_shogi.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
                tables=[],knight_first=[],pawn_first=[],pawn_witness=[],complete=False,
                geometry_candidates=0,materializations=0,
                scope=dict(task='virtual source-only preparation',public_transitions=0,goal_calls=0,
                           royal_safety=False,opponent_turns=False,empirical_shortest_path_search=False))
    try:audit(report)
    except Exception as error:report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                         for p,h in report['source_sha256'].items())
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','tables',
                                                              'knight_first','pawn_first','pawn_witness')}))
