import hashlib,json
from pathlib import Path
from dataclasses import replace
import pytest
from scripts.audit_physical_profile_dispatch import build,profiles
from scripts.physical_profile_event_cubes import PhysicalProfileEventCubes,ContactUnsupported
from generic_chess.rules.compiler import compile_ruleset_for_execution
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

def test_same_current_distinct_flag_and_none_dispatch():
    p=profiles();k=PhysicalProfileEventCubes(compile_ruleset_for_execution(build()),p)
    assert {(d,q) for d,q in k.quiet[p[1],3] if d==6}=={(6,p[1])}
    assert {(d,q) for d,q in k.quiet[p[2],3] if d==6}=={(6,p[3])}
    n=PhysicalProfileEventCubes(compile_ruleset_for_execution(build(none=True)),p)
    assert {(d,q) for d,q in n.quiet[p[2],3] if d==6}=={(6,p[2])}
    assert k.closure==set(p) and all(q in k.closure for qs in k.quiet.values() for d,q in qs)

def test_explicit_whole_mode_and_invalid_origin_rejected():
    rules=build();action=rules.semantic_actions[0]
    bad=replace(rules,semantic_actions=(replace(action,promotion_mode='explicit',explicit_promotion_type='opaque_changed'),)+rules.semantic_actions[1:])
    with pytest.raises(ContactUnsupported):PhysicalProfileEventCubes(compile_ruleset_for_execution(bad),profiles())

def test_full_population_controls_rename_and_retained_zero_world_failure():
    failed=json.loads((DATA/'physical_profile_dispatch_20261006.json').read_text());r=json.loads((DATA/'physical_profile_qualified_20261006.json').read_text())
    assert failed['worlds']==failed['enumerated']==0 and failed['candidates']==40 and not failed['complete']
    assert r['complete'] and r['worlds']==8064 and len(r['rows'])==16 and len(r['controls'])==80
    assert r['charged_candidates']==240 and r['enumerated']==184 and r['cumulative_seconds']<15
    assert all(row['cube_sha256']==row['coordinate_sha256'] and row['first_mismatch'] is None for row in r['rows'])
    assert all(row['actual']==row['coordinate'] for row in r['controls'])
    assert r['renamed']==[row['census'] for row in r['rows'][:4]]
    for row in r['rows']:assert sum(row['census']['histogram'].values())+row['census']['unreachable']==504
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
