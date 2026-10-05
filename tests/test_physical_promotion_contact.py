import hashlib,json
from pathlib import Path
from dataclasses import replace
import pytest
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from generic_chess.core.pieces import Piece
from scripts.promotion_mobility_micro import build
from scripts.physical_promotion_contact_cubes import PhysicalPromotionContactCubes,ContactUnsupported
from scripts.promotable_contact_cubes import PromotableContactCubes
from scripts.shared_contact_prefix import Profile
from scripts.audit_promotion_mobility_completion import rejection_rules
ROOT=Path(__file__).resolve().parents[1]
P=Profile('opaque_initial','opaque_initial');Q=Profile('opaque_initial','opaque_changed',True)
def test_alive_gate_catches_old_semantic_counterexample_and_retains_promoted_motion():
    c=compile_ruleset_for_execution(build());old=PromotableContactCubes(c,(P,Q));new=PhysicalPromotionContactCubes(c,(P,Q))
    assert (3,Q) in old.quiet[P,0] and (3,Q) not in new.quiet[P,0]
    assert (3,P) in new.quiet[P,0] and not new.quiet[P,3] and 6 not in new.capture[P,3]
    assert new.quiet[Q,4]==old.quiet[Q,4] and new.capture[Q,4]==old.capture[Q,4]
    board=[None]*9;board[0]=Piece(0,P.base,P.current);board[1]=Piece(1,'target','target');board[8]=Piece(0,'blocker','blocker')
    actions=semantic_engine_for(c).legal_actions(replace(initial_state(c).position,board=tuple(board),side_to_move=0))
    assert [(a.target,a.promotion_target_id) for a in actions]==[(3,None)]
def test_live_optional_and_forced_results_are_distinct_profiles():
    k=PhysicalPromotionContactCubes(compile_ruleset_for_execution(build(live=True)),(P,Q))
    assert {(d,p) for d,p in k.quiet[P,0]}=={(3,P),(3,Q)}
    assert {(d,p) for d,p in k.quiet[P,3]}=={(6,Q)} and 6 in k.capture[P,3]
@pytest.mark.parametrize('flag',['none','guard'])
def test_unsupported_whole_mode_rejected(flag):
    with pytest.raises(ContactUnsupported):PhysicalPromotionContactCubes(compile_ruleset_for_execution(build(live=True,**{flag:True})),(P,Q))
def test_promoted_current_fixture_compiles_then_constructor_rejects():
    c=compile_ruleset_for_execution(rejection_rules())
    with pytest.raises(ContactUnsupported,match='promoted-current'):PhysicalPromotionContactCubes(c,(P,Q))
def test_worldwise_population_and_chain_pins():
    data=ROOT/'docs/research/data'
    r=json.loads((data/'promotion_mobility_gate_20261005.json').read_text());s=json.loads((data/'promotion_completion_record_20261005.json').read_text())
    assert not r['complete'] and 'PROMOTION_MASK' in r['error']
    assert s['complete'] and s['control_compiled'] and s['new_worlds']==s['new_enumerated']==0
    assert s['qualified_worlds']==4032 and s['charged_candidates']==144 and s['charged_enumerated']==27 and s['cumulative_seconds']<15
    assert r['new_worlds']==3528 and len(r['controls'])==16
    for row in r['rows']:
        assert row['ordered_cube_sha256']==row['ordered_coordinate_sha256'] and row['first_mismatch'] is None
        assert sum(row['census']['histogram'].values())+row['census']['unreachable']==504
    assert all(x['actual']==x['expected'] for x in r['controls'])
    for record in (r,s):
        for path,pin in record['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
