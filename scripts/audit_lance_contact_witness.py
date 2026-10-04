"""Frozen one-shot deep virtual Lance witness, not a shortest game solver."""
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
    node=SourceNode('L','L',54)
    def time_check():
        if monotonic()-start>=15:raise RuntimeError('15-second cap')
    def materialize():
        time_check()
        if report['materializations']>=128:raise RuntimeError('128 virtual edge cap')
        report['materializations']+=1
    for destination in [63,*range(64,72),62,53,44,35,26,17,8]:
        events=defaultdict(set);excluded=set()
        for pattern in compiled.ir.patterns:
            if node.current not in pattern.type_ids:continue
            if _is_history_conditional(pattern):raise ValueError('history unsupported')
            if any(effect.kind in ('set_token','clear_token') for effect in pattern.effects):
                raise ValueError('auxiliary source effects unsupported')
            for invariant in pattern.invariants:
                if invariant.kind!='own_anchor_safe':raise ValueError('unsupported invariant')
                excluded.add((pattern.name,invariant.kind))
            for gid in pattern.geometry_ids:
                geometry=compiled.ir.geometry[gid]
                if geometry.kind=='drop':continue
                if geometry.kind not in ('ray','leap'):raise ValueError('board geometry unsupported')
                for target,path in geometry_candidates(geometry,'0',node.square):
                    time_check()
                    if report['geometry_candidates']>=5000:raise RuntimeError('5000 geometry cap')
                    report['geometry_candidates']+=1
                    found=event_cubes_for_candidate(compiled,pattern,type_id=node.current,owner=0,
                                                   source=node.square,target=target,path=path)
                    for key,cubes in found.items():events[key].update(cubes)
        chosen={k:tuple(sorted(v)) for k,v in events.items() if k[3]==destination and k[6]=='TL'}
        steps=contact_steps(node,chosen,area=81,owner=0,target=8,blockers={58:'own'},checkpoint=materialize)
        if len(steps)!=1:raise ValueError('unique selected compatible edge absent')
        step=next(iter(steps.values()))
        if step.completed!=(destination==8):raise ValueError('premature or missing removal')
        report['steps'].append(dict(before=asdict(node),event=step.event,cubes=chosen[step.event],
                                   after=asdict(step.node),completed=step.completed,
                                   excluded_dynamic=sorted(excluded),full_choice_set=False))
        node=step.node
    report['complete']=len(report['steps'])==16 and report['steps'][-1]['completed']
    report['seconds']=monotonic()-start


if __name__=='__main__':
    output=ROOT/'docs/research/data/lance_contact_witness_20261005.json'
    if output.exists():raise ValueError('fresh output required; no rerun')
    pins=['docs/research/LANCE_CONTACT_WITNESS_PROTOCOL.md','scripts/audit_lance_contact_witness.py',
          'scripts/compatible_contact.py','scripts/intrinsic_action_events.py',
          'scripts/intrinsic_occupancy_cubes.py','scripts/audit_static_semantic_material_prior_v2.py',
          'scripts/audit_static_semantic_material_prior_v2a.py','scripts/audit_static_semantic_material_prior_v2d.py',
          'scripts/public_task_intervals.py','generic_chess/rules/ir.py',
          'generic_chess/rules/compiler.py','generic_chess/rules/standard_shogi.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
                steps=[],complete=False,materializations=0,geometry_candidates=0,
                scope=dict(task='virtual source-only preparation',public_transitions=0,goal_calls=0,
                           royal_safety=False,opponent_turns=False,minimum_proof='separate analytic argument'))
    try:audit(report)
    except Exception as error:report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                         for p,h in report['source_sha256'].items())
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','steps')}))
