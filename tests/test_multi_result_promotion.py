import hashlib,json
from pathlib import Path
from scripts.audit_multi_result_promotion import build,PROFILES
from scripts.physical_promotion_contact_cubes import PhysicalPromotionContactCubes
from generic_chess.rules.compiler import compile_ruleset_for_execution
ROOT=Path(__file__).resolve().parents[1]
def test_any_alive_forced_result_and_distinct_quiet_profiles():
    dead=PhysicalPromotionContactCubes(compile_ruleset_for_execution(build(False)),PROFILES)
    live=PhysicalPromotionContactCubes(compile_ruleset_for_execution(build(True)),PROFILES)
    a,b,c=PROFILES
    assert set(dead.quiet[a,0])=={(3,a),(3,c)} and set(dead.quiet[a,3])=={(6,c)}
    assert 6 in dead.capture[a,3] and (3,b) not in dead.quiet[a,0]
    assert set(live.quiet[a,0])=={(3,a),(3,b),(3,c)} and set(live.quiet[a,3])=={(6,b),(6,c)}
    assert dead.quiet[b,4]==live.quiet[b,4] and dead.quiet[c,4]==live.quiet[c,4]
def test_new_complete_multiple_result_population_and_actual_lists():
    r=json.loads((ROOT/'docs/research/data/multi_result_promotion_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==12 and len(r['controls'])==20 and r['worlds']==6048
    assert r['charged_candidates']==304 and r['charged_enumerated']==81 and r['cumulative_seconds']<15
    for row in r['rows']:
        assert row['first_mismatch'] is None and row['cube_sha256']==row['coordinate_sha256']
        assert sum(row['census']['histogram'].values())+row['census']['unreachable']==504
    assert all(x['actual']==x['coordinate'] for x in r['controls'])
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
