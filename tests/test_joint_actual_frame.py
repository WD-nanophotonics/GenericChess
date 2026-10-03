from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
from random import Random
from types import SimpleNamespace

import pytest

from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_actual_inventory_sampling import rejection_reason, validate_structural
from scripts.audit_joint_actual_frame import ShogiJointSampler, audit, scope
from scripts.audit_secured_exchange_common_context import Budget


@pytest.fixture(scope='module')
def compiled():
    return compile_ruleset_for_execution(build_standard_shogi_ruleset())


def test_joint_full_frames_preserve_inventory_and_determinism(compiled):
    sampler = ShogiJointSampler(compiled, Budget(seconds=10))
    a, b = Random(17), Random(17)
    for _ in range(4):
        first, second = sampler.sample(a), sampler.sample(b)
        assert first == second
        validate_structural(compiled, first, 'shogi')
        assert all(compiled.support.empty_mobility[p.current_type_id][p.owner][s]
                   for s, p in enumerate(first.board) if p)


def test_inventory_and_mobility_drift_fail_closed(compiled):
    position = initial_state(compiled).position
    board = list(position.board)
    board[next(s for s, p in enumerate(board) if p)] = None
    with pytest.raises(ValueError, match='inventory'):
        scope(compiled, replace(position, board=tuple(board)))
    mobility = {k: {owner: tuple(mask) for owner, mask in enumerate(owners)}
                for k, owners in compiled.support.empty_mobility.items()}
    mobility['G'][0] = (False,) + mobility['G'][0][1:]
    altered = SimpleNamespace(board_size=9, support=SimpleNamespace(empty_mobility=mobility))
    with pytest.raises(ValueError, match='unrestricted mobility'):
        scope(altered, position)


def test_full_state_certificate_and_remaining_filters(compiled):
    result = audit()
    recorded = json.loads((Path(__file__).resolve().parents[1] /
                           'docs/research/data/joint_actual_frame_20261004.json').read_text())
    for key in recorded:
        if key != 'elapsed_seconds':
            assert result[key] == recorded[key]
    assert result['complete']
    sampler = ShogiJointSampler(compiled, Budget(seconds=10))
    rng = Random(result['seed'])
    reasons = [rejection_reason(compiled, sampler.sample(rng), 'shogi', sampler.budget)
               for _ in range(result['proposals'])]
    assert Counter(reasons[:-1]) == Counter(result['rejected'])
    assert reasons[-1] is None
    with pytest.raises(ValueError):
        audit(proposal_limit=129)
    with pytest.raises(TimeoutError):
        audit(Budget(seconds=-1))
