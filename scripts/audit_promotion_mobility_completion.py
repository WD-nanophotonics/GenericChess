"""Zero-observation rejection envelope and checked reuse of completed populations."""
from dataclasses import replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import PieceType
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.promotion_mobility_micro import build
from scripts.physical_promotion_contact_cubes import PhysicalPromotionContactCubes,ContactUnsupported
from scripts.shared_contact_prefix import Profile
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/promotion_mobility_completion_20261005.json'
SOURCES=('scripts/audit_promotion_mobility_completion.py','docs/research/PROMOTION_MOBILITY_REJECTION_SCOPE.md','docs/research/data/promotion_mobility_gate_20261005.json','docs/research/data/promotable_cube_qualified_20261005.json','scripts/physical_promotion_contact_cubes.py','scripts/promotion_mobility_micro.py')
def rejection_rules():
    rules=build(live=True,promoted_promotable=True)
    types=tuple(replace(p,promotion_target_ids=('opaque_last',)) if p.type_id=='opaque_changed' else p for p in rules.piece_types)+(PieceType('opaque_last','opaque_last',()),)
    allowed=dict(rules.promotion_allowed,opaque_changed=(frozenset(),frozenset()))
    forced=dict(rules.promotion_forced,opaque_changed=(frozenset(),frozenset()))
    drops=dict(rules.drop_allowed,opaque_last=((False,)*9,)*2)
    return replace(rules,piece_types=types,promotion_allowed=allowed,promotion_forced=forced,drop_allowed=drops)
def qualify_saved(record,original):
    assert not record['complete'] and record['error'].startswith('RuleValidationError:')
    assert record['source_hashes_unchanged'] and record['new_worlds']==3528
    assert record['canonical_candidates']==144 and record['enumerated']==27
    assert len(record['rows'])==8 and len(record['controls'])==16
    assert record['public_transitions']==record['source_queries']==0
    for row in record['rows']:
        assert row['worlds']==504 and row['first_mismatch'] is None
        assert row['ordered_cube_sha256']==row['ordered_coordinate_sha256']
        assert row['census']['worlds']==504
    assert sum(bool(x['reused']) for x in record['rows'])==1
    assert record['rows'][1]['census']==original['rows'][1]['census']
    assert record['rows'][1]['ordered_cube_sha256']==original['rows'][1]['ordered_cube_sha256']
    assert all(c['actual']==c['expected'] for c in record['controls'])
    assert all(record['renamed_census'][str(i==1)]==record['rows'][4+i]['census'] for i in (0,1))
    for path,digest in record['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    return True
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('no completion rerun')
    start=monotonic();r=dict(complete=False,new_worlds=0,new_canonical_candidates=0,new_enumerated=0,public_transitions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        old=json.loads((ROOT/SOURCES[2]).read_text());original=json.loads((ROOT/SOURCES[3]).read_text())
        r['saved_populations_qualified']=qualify_saved(old,original)
        compiled=compile_ruleset_for_execution(rejection_rules());r['control_compiled']=True
        try:PhysicalPromotionContactCubes(compiled,(Profile('opaque_initial','opaque_initial'),Profile('opaque_initial','opaque_changed',True)))
        except ContactUnsupported as error:r['promoted_current_rejection']=str(error)
        r['rejections']=dict(old['rejections'],promoted_promotable=r.get('promoted_current_rejection'))
        r['charged_candidates']=old['canonical_candidates'];r['charged_enumerated']=old['enumerated'];r['qualified_worlds']=4032
        r['complete']=r['saved_populations_qualified'] and bool(r.get('promoted_current_rejection')) and len(r['rejections'])==3
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.141
    if r['cumulative_seconds']>=15:r['complete']=False;r['error']='cumulative15sec cap'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps(r))
