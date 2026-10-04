"""One-shot path-length metadata inspection; creates no candidate events."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


def inspect(report):
    start=monotonic();compiled=compile_semantic_ruleset(build_standard_shogi_ruleset())
    for tid,metadata in compiled.support.type_metadata.items():
        if metadata.is_anchor:continue
        for owner in ('0','1'):
            predicted=0;unique={};held=set()
            for pattern in compiled.ir.patterns:
                if tid not in pattern.type_ids:continue
                for gid in pattern.geometry_ids:
                    if monotonic()-start>=15:raise RuntimeError('15-second metadata cap')
                    g=compiled.ir.geometry[gid]
                    if g.kind=='drop':held.add(pattern.name);continue
                    if g.kind not in ('ray','leap'):raise ValueError('unsupported geometry cost')
                    count=sum((1 if path else 0) if g.kind=='leap' else
                              max(0,len(path)-max(0,(g.min_steps or 1)-1))
                              for path in g.paths.get(owner,{}).values())
                    predicted+=count;unique[gid]=count
            report['modes'].append(dict(current_type=tid,owner=int(owner),
                prospective_pattern_candidate_tests=predicted,
                unique_geometry_id_input_candidates=sum(unique.values()),excluded_held=sorted(held)))
    report['complete_metadata']=True;report['seconds']=monotonic()-start


if __name__=='__main__':
    output=ROOT/'docs/research/data/contact_geometry_cost_preflight_20261005.json'
    if output.exists():raise ValueError('fresh metadata output required')
    pins=['docs/research/CONTACT_CONSTRUCTION_PREFLIGHT.md','scripts/inspect_contact_geometry_cost.py',
          'generic_chess/rules/compiler.py','generic_chess/rules/ir.py','generic_chess/rules/standard_shogi.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
                modes=[],complete_metadata=False,scope=dict(new_geometry_candidates=0,
                new_events=0,new_materializations=0,public_transitions=0,goal_calls=0))
    try:inspect(report)
    except Exception as error:report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                         for p,h in report['source_sha256'].items())
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=report['complete_metadata'],seconds=report.get('seconds'),
        mode_owner_rows=len(report['modes']),
        predicted_owner0=sum(m['prospective_pattern_candidate_tests'] for m in report['modes'] if m['owner']==0),
        predicted_R_TR_owner0=sum(m['prospective_pattern_candidate_tests'] for m in report['modes']
                                 if m['owner']==0 and m['current_type'] in ('R','TR')),
        source_hashes_unchanged=report['source_hashes_unchanged'],error=report.get('error'))))
