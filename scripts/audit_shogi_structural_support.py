"""Metadata-only contract audit; no graph or action construction."""
import hashlib,json,sys
from pathlib import Path
from dataclasses import asdict
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_semantic_ruleset,compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shared_contact_prefix import SharedContactPrefix,Profile
from scripts.sparse_contact_cubes import SparseContactCubes
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/shogi_structural_support_20261006.json'
SOURCES=('scripts/audit_shogi_structural_support.py','docs/research/SHOGI_STRUCTURAL_SUPPORT_PROTOCOL.md','scripts/shared_contact_prefix.py','scripts/physical_profile_event_cubes.py','scripts/sparse_contact_cubes.py','scripts/intrinsic_action_events.py','generic_chess/rules/standard_shogi.py','generic_chess/rules/compiler.py','docs/research/data/shogi_full_contact_distance_20261005.json','docs/research/data/shogi_coordinate_comparison_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed metadata preflight')
    start=monotonic();pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    r=dict(complete=False,patterns=[],profiles=[],source_sha256=pins,canonical_candidates=0,distance_worlds=0,semantic_actions=0,public_transitions=0,source_queries=0)
    try:
        old=json.loads((ROOT/SOURCES[-2]).read_text());ind=json.loads((ROOT/SOURCES[-1]).read_text())
        for report in (old,ind):
            assert report['complete'] and report['source_hashes_unchanged']
            for path,pin in report['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        rules=build_standard_shogi_ruleset();a=compile_semantic_ruleset(rules);b=compile_ruleset_for_execution(rules)
        assert a.ruleset_fingerprint==b.ruleset_fingerprint
        fields=('type_metadata','promotion_allowed','promotion_forced','empty_mobility','board_shape')
        r['compile_equal']={field:record_value(getattr(a.support,field))==record_value(getattr(b.support,field)) for field in fields}
        r['compile_equal']['ir']=record_value(a.ir)==record_value(b.ir);assert all(r['compile_equal'].values())
        pp=tuple(Profile(**row['profile']) for row in old['rows']);assert len(pp)==13
        currents={p.current for p in pp}
        for p in pp:SharedContactPrefix._profile(type('Context',(),{'c':b})(),p)
        for pattern in b.ir.patterns:
            if not currents.intersection(pattern.type_ids):continue
            gs=[b.ir.geometry[g] for g in pattern.geometry_ids]
            if gs and all(g.kind=='drop' for g in gs):continue
            row=dict(name=pattern.name,types=pattern.type_ids,geometry_ids=pattern.geometry_ids)
            r['patterns'].append(row)
            assert len(r['patterns'])<=128 and len(pattern.type_ids)==1
            SharedContactPrefix._pattern(pattern,gs);SparseContactCubes._pattern(pattern,gs)
            assert all(g.atom_source is None or g.atom_source[0]==pattern.type_ids[0] for g in gs)
            assert all(g.owner_relative and g.kind in ('leap','ray') for g in gs)
            row['qualified']=True
            assert monotonic()-start<15
        assert all(any(t in row['types'] for row in r['patterns']) for t in currents)
        r['profiles']=[asdict(p) for p in pp];r['rules_fingerprint']=b.ruleset_fingerprint;r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in pins.items())
    write_record(OUT,r);print(json.dumps(dict(complete=r['complete'],patterns=len(r['patterns']),profiles=len(r['profiles']),seconds=r['seconds'],error=r.get('error'))))
