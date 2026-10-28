"""Actual Core/profile counterexamples, not a proposed product behavior."""
import json
import pytest
from scripts import aux_representation_contract as C
from scripts import aux_representation_history as H
from generic_chess.rules.compiler import compile_ruleset,compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.validation import RuleValidationError
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.session.session import GameSession

@pytest.mark.parametrize("compiler",[compile_ruleset,compile_legacy_ruleset_for_semantic_execution])
def test_globally_dead_promotion_still_changes_default_support_and_score(compiler):
    a,b,_=C.definitions();ca,cb=compiler(a),compiler(b);cfg=EvaluationConfig()
    pa,pb=build_ruleset_profile(ca,cfg),build_ruleset_profile(cb,cfg)
    assert pa.piece_profiles["P"].raw_capability_score==pb.piece_profiles["P"].raw_capability_score
    assert pa.board_value_by_type["P"]==1000 and pb.board_value_by_type["P"]==569
    eb=Evaluator(cb,pb,cfg)
    assert all(not zone for zone in eb._zones.values())
    assert (Evaluator(ca,pa,cfg).evaluate(GameSession(ca).state),eb.evaluate(GameSession(cb).state))==(1002,571)

@pytest.mark.parametrize("semantic",[False,True])
def test_dead_promotion_pair_full_Core_prefixes_and_action_bijection(semantic):
    a,b,_=C.definitions();r=C.paired_legacy(a,b,semantic=semantic)
    assert r["complete_to_depth"] and r["paired_edges"]==12 and r["nodes"]==13
    assert r["repetition_key_bijection_size"]==13
    if semantic:assert any(x!=y for x,y in r["pattern_id_mapping"].items())

def test_extra_setup_cannot_introduce_a_new_inventory():
    *_,bad=C.definitions()
    with pytest.raises(RuleValidationError,match="INITIAL_SETUP_INVENTORY_MISMATCH"):
        compile_ruleset(bad)

def test_identical_mover_label_quotient_does_not_preserve_repetition_adjudication(tmp_path):
    frozen=tmp_path/"frozen.json";observed=tmp_path/"observed.json";H.freeze(frozen)
    r=H.run(frozen,observed)
    for d in r["routes"].values():
        assert d["first_many_to_one_identity"]["ply"]==8
        last=d["trace"][-1]
        assert last["source_status"]["status"]=="repetition"
        assert last["colored_status"]["status"]=="ongoing"
        assert (last["source_current_count"],last["colored_current_count"])==(4,2)
        assert d["all_prefix_raw_values_equal"]
