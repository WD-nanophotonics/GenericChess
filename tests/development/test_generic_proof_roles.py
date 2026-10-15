"""Wrong learner identity would silently invert defensive WDL and Native budget."""
import pytest
from scripts.generic_proof_roles import candidate_side,row_target,roles,role_order

@pytest.mark.parametrize("turn",[0,1])
def test_candidate_identity_stays_fixed_after_both_moves(turn):
    for role in ("TO_MOVE","OTHER"):
        target=candidate_side(turn,role)
        row={"candidate_role":role,"candidate_side":target}
        assert row_target(row,turn)==target
        assert candidate_side(turn,"OTHER")==1-candidate_side(turn,"TO_MOVE")
        with pytest.raises(ValueError):row_target(dict(row,candidate_side=1-target),turn)

def test_duplicate_or_unknown_roles_rejected_and_order_balanced():
    for r in ([],["OTHER","OTHER"],["DEFEND"]):
        with pytest.raises(ValueError):roles({"candidate_roles":r})
    p={"candidate_roles":["TO_MOVE","OTHER"]}
    assert role_order(p,0,0)==role_order(p,1,1)==("TO_MOVE","OTHER")
    assert role_order(p,0,1)==role_order(p,1,0)==("OTHER","TO_MOVE")
    assert roles({})==("TO_MOVE",)
    assert row_target({},1)==1
