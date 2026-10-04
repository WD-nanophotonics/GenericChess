from fractions import Fraction as F


def test_direct_h2_tower_and_variance_on_independent_full_state_branches():
    # Abstract exact public first-cycle branches. Unlike a mode refresh, each
    # retains its actual conditional second reward law and earned first reward.
    branches = ((F(1, 4), 1, (F(1, 3), F(2, 3))),
                (F(1, 2), 0, (F(1), F(0))),
                (F(1, 4), 0, (F(1, 2), F(1, 2))))
    direct = sum(p*(r1+p_second_one) for p, r1, (_, p_second_one) in branches)
    full = sum(p*q*(r1+r2) for p, r1, second in branches for r2, q in enumerate(second))
    assert direct == full == F(13, 24)
    var_direct = sum(p*(r1+second[1]-direct)**2 for p, r1, second in branches)
    var_full = sum(p*q*(r1+r2-full)**2 for p, r1, second in branches for r2, q in enumerate(second))
    conditional_variance = sum(p*second[1]*(1-second[1]) for p, _, second in branches)
    assert var_full == var_direct+conditional_variance
    assert conditional_variance == F(17, 144) and var_direct <= var_full
    # Endpoint reward is earned already; stopping does not undo the capture.
    endpoint_branch = (F(1), 1, (F(1), F(0)))
    p, r1, second = endpoint_branch
    assert p*(r1+second[1]) == 1
