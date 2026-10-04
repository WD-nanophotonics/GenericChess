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


def test_held_two_cycle_bound_matches_hidden_label_first_action_enumeration():
    for hand_count in range(1, 7):
        for actions in range(1, 8):
            for drops in range(actions+1):
                # Independent physical-label enumeration: tag is label0,
                # uniformly drawn for each legal first drop; all such board
                # tags get maximal next service1. Other first choices get0.
                total = sum(F(int(action < drops and label == 0), actions*hand_count)
                            for action in range(actions) for label in range(hand_count))
                assert total == F(drops, actions*hand_count)
                assert total <= F(1, hand_count)


def test_drop_conditioning_preserves_hidden_label_service_and_reduces_variance():
    # Explicit labelled worlds, rather than an importance-sampler implementation.
    # Different drops have different successor service and enemy capture risks.
    drop_services = ((0, 1, 1), (0, 0, 1), (1, 1, 1))
    for hand_count in range(1, 6):
        for quiet_choices in range(5):
            actions = len(drop_services)+quiet_choices
            worlds = [F(int(label == 0)*service)
                      for outcomes in drop_services for service in outcomes
                      for label in range(hand_count)]
            # Integrating anonymous labels first yields fractional public trace.
            integrated = [F(service, hand_count)
                          for outcomes in drop_services for service in outcomes]
            assert sum(worlds, F(0))/len(worlds) == sum(integrated, F(0))/len(integrated)
            p = F(len(drop_services), actions)
            original = integrated+[F(0)]*(quiet_choices*3)
            conditioned = [p*value for value in integrated]
            mean = sum(original, F(0))/len(original)
            assert mean == sum(conditioned, F(0))/len(conditioned)
            variance = lambda xs: sum((x-mean)**2 for x in xs)/len(xs)
            second_moment = sum(x*x for x in integrated)/len(integrated)
            assert variance(original)-variance(conditioned) == p*(1-p)*second_moment
            assert all(0 <= x <= p/hand_count for x in conditioned)
            if quiet_choices:
                assert sum(integrated)/len(integrated) > mean  # omitting p biases it


def test_exact_first_reward_is_not_a_universal_total_variance_improvement():
    # Negative covariance: two equally likely first choices give total service1
    # deterministically. Separately integrating R1 destroys that cancellation.
    first_reward = (F(1), F(0))
    next_service = (F(0), F(1))
    original = [a+b for a, b in zip(first_reward, next_service)]
    integrated_first = sum(first_reward)/2
    separated = [integrated_first+b for b in next_service]
    assert original == [F(1), F(1)]
    assert sum(separated)/2 == 1
    assert sum((x-1)**2 for x in original)/2 == 0
    assert sum((x-1)**2 for x in separated)/2 == F(1, 4)
