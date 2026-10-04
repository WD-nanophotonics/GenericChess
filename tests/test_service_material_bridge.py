from fractions import Fraction as F
import json
from pathlib import Path

import pytest

from scripts.audit_service_material_bridge import Node, audit, covariance, exact_values, graph, rank, secured_capture, squared_risk


def test_complete_exact_bridge_certificate():
    result = audit()
    recorded = json.loads((Path(__file__).resolve().parents[1] /
                           'docs/research/data/service_material_bridge_20261004.json').read_text())
    for key in recorded:
        if key != 'elapsed_seconds':
            assert result[key] == recorded[key]
    assert result['local_service_labels'] == [1, 1] and result['goal_labels'] == ['1', '-1']
    assert result['unavoidable_goal_risk'] == '1'


def test_unseen_goal_suffix_changes_value_but_not_local_service():
    nodes = graph()
    assert secured_capture(nodes, ('plus', 0)) == secured_capture(nodes, ('minus', 0)) == 1
    labels = exact_values(nodes)
    assert labels['plus', 0] == 1 and labels['minus', 0] == -1
    nodes['minus', 4] = Node(0, (('i', 0),), (), 0)
    assert exact_values(nodes)['minus', 0] == 1
    assert secured_capture(nodes, ('minus', 0)) == 1


def test_empty_reply_cycle_and_deadline_never_qualify():
    with pytest.raises(ValueError, match='empty action'):
        exact_values({'empty': Node(0, (), ())})
    with pytest.raises(ValueError, match='cyclic'):
        exact_values({'loop': Node(0, (), (('pass', None, 'loop'),))})
    with pytest.raises(TimeoutError):
        audit(seconds=-1)


def test_projection_scale_and_nullspace_controls():
    weights = [F(1, 2), F(1, 2)]
    x = [(F(1), F(-1))] * 2
    assert rank(covariance(x, weights)) == 0
    # Arbitrary slopes can be cancelled by the intercept on constant inventory.
    for slopes in ((F(1), F(1)), (F(8), F(-3))):
        intercept = -sum(a*b for a, b in zip(x[0], slopes))
        assert [intercept + sum(a*b for a, b in zip(row, slopes)) for row in x] == [0, 0]
    assert squared_risk([F(1), F(-1)], [F(0), F(0)], weights) == 1
    assert squared_risk([F(5), F(1)], [F(3), F(3)], weights) == 4
