"""All source/blocker configurations, authentic masks, no event/goal queries."""
import pytest
from generic_chess.core.coordinates import index_to_square
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shogi_native_promotion_routes import promotion_prefix,native_contact_route


@pytest.mark.parametrize('mode,zero,bound',[('S',158,6),('N',114866,3),('B',316,8)])
def test_complete_promotion_support_and_actual_masks(mode,zero,bound):
    c=compile_semantic_ruleset(build_standard_shogi_ruleset());shape=c.support.board_shape
    for owner in (0,1):
        none=0;sign=1 if owner==0 else -1
        for s in range(81):
            for b in range(81):
                if s==b:continue
                p=promotion_prefix(mode,s,b,owner)
                if p is None:none+=79;continue
                assert p[0]==s and b not in p and 1<=len(p)-1<=bound
                for a,z in zip(p,p[1:]):
                    dx,dy=(z%9-a%9)*sign,(z//9-a//9)*sign
                    if mode=='N':assert abs(dx)==1 and dy==2
                    elif mode=='S':assert (dx,dy) in ((0,1),(-1,1),(1,1),(-1,-1),(1,-1))
                    else:assert abs(dx)==abs(dy)==1
                pair=(index_to_square(p[-2],shape),index_to_square(p[-1],shape))
                assert pair in c.support.promotion_allowed[mode][owner]
                for t in c.support.type_metadata[mode].promotion_target_ids:
                    assert c.support.empty_mobility[t][owner][p[-1]]
        assert none==zero


def test_one_blocker_knight_branch_and_bishop_backward_detour():
    assert promotion_prefix('N',0,19) is None  # Sole initial jump blocked.
    assert promotion_prefix('N',0,36) is not None  # Future one branch blocked, other works.
    p=promotion_prefix('B',27,37)  # a4 forward exit b5 blocked; b3-c4 bypass.
    assert p[:3]==[27,19,29] and len(p)-1<=8
    assert native_contact_route('B',27,19,37)==[27,19]  # Earlier target absorbs, no fake quiet traversal.


def test_prefix_vacated_squares_remain_available_to_final_gold_route():
    for mode in ('S','N','B'):
        p=native_contact_route(mode,0,1,55)
        assert p[0]==0 and p[-1]==1 and 55 not in p
        assert len(p)-1<=dict(S=22,N=19,B=24)[mode]
