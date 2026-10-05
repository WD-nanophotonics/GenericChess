"""One-shot compiled metadata qualification, without per-square event generation."""
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shogi_direct_mode_bounds import LEAPS,RAYS,direct_and_zero,partial_raw_interval

OUT=ROOT/'docs/research/data/shogi_direct_modes_20261005.json'
SOURCES=('scripts/audit_shogi_direct_modes.py','scripts/shogi_direct_mode_bounds.py',
         'generic_chess/rules/compiler.py','generic_chess/rules/standard_shogi.py',
         'docs/research/SHOGI_DIRECT_MODE_BOUND_DESIGN.md')


def digest(p):
    return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()


if __name__=='__main__':
    if OUT.exists():
        raise FileExistsError('frozen qualification never rerun')
    start=monotonic()
    report=dict(complete=False,checked_patterns=0,modes={},public_transitions=0,
                goal_queries=0,geometry_candidates=0,event_materializations=0,
                source_sha256={p:digest(p) for p in SOURCES})
    try:
        c=compile_semantic_ruleset(build_standard_shogi_ruleset())
        for tid in LEAPS:
            shapes={kind:set() for kind in ('empty','target_enemy')};names=[]
            for p in c.ir.patterns:
                if tid not in p.type_ids:
                    continue
                geometries=[c.ir.geometry[g] for g in p.geometry_ids]
                if all(g.kind=='drop' for g in geometries):
                    continue
                if monotonic()-start>=15 or report['checked_patterns']>=128:
                    raise ValueError('15sec/128 metadata pattern cap')
                report['checked_patterns']+=1
                if p.target.kind not in shapes or p.guards or p.slot_guards or p.square_zone_guards or p.postconditions:
                    raise ValueError('unsupported state/history/postcondition')
                if any(i.kind!='own_anchor_safe' for i in p.invariants):
                    raise ValueError('unsupported dynamic invariant')
                effects=tuple(e.kind for e in p.effects)
                if effects != (('move',) if p.target.kind=='empty' else ('remove','move')):
                    raise ValueError('unsupported physical effect')
                if p.target.kind=='target_enemy' and (p.effects[0].disposition!='capture_to_hand' or
                    p.effects[0].piece_owner!='opponent' or p.effects[0].square_ref.kind!='target'):
                    raise ValueError('unqualified target custody')
                if p.promotion_mode!='inherit_compiled_masks':
                    raise ValueError('unqualified promotion contract')
                for g in geometries:
                    if not g.owner_relative or g.kind not in ('ray','leap'):
                        raise ValueError('unqualified geometry')
                    expected_path=('path_clear',) if g.kind=='ray' else ()
                    if tuple(x.kind for x in p.path)!=expected_path:
                        raise ValueError('unqualified blocker path')
                    shapes[p.target.kind].add((g.kind,tuple(g.offset if g.kind=='leap' else g.direction)))
                names.append(p.name)
            expected={('leap',x) for x in LEAPS[tid]}|{('ray',x) for x in RAYS.get(tid,())}
            if any(s!=expected for s in shapes.values()):
                raise ValueError('missing/extra physical geometry')
            direct,zero=direct_and_zero(tid)
            report['modes'][tid]=dict(direct=direct,proved_zero=zero,remaining=511920-direct-zero,
                qualified_patterns=names,excluded_dynamic='own_anchor_safe',
                raw_intervals={m:[str(x) for x in partial_raw_interval(tid,m)] for m in ('geometric_half','linear_mixture')})
        report['complete']=len(report['modes'])==11
    except Exception as e:
        report['error']=f'{type(e).__name__}: {e}'
    report['seconds']=monotonic()-start
    report['source_hashes_unchanged']=all(digest(p)==h for p,h in report['source_sha256'].items())
    OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('modes','source_sha256')}))
