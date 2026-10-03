from collections import Counter
from fractions import Fraction
from itertools import combinations, product
import hashlib
import json
from pathlib import Path
from random import Random

import pytest

from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.audit_physical_placement_sampling import (
    audit, paired_choices, sample_frame, substituted, rejection_reason, support_masses,
)
from scripts.audit_secured_exchange_common_context import Budget


def test_small_board_paired_images_equal_independent_physical_enumeration():
    # Exhaust the conditional population independently of the production sampler.
    cells = set(range(9)) - {4}; expected = set()
    for own in combinations(sorted(cells), 2):
        if any(s // 3 == 2 or s % 3 == 1 for s in own) or len({s % 3 for s in own}) != 2:
            continue
        for enemy in combinations(sorted(cells - set(own)), 3):
            if any(s // 3 == 0 for s in enemy) or len({s % 3 for s in enemy}) != 3:
                continue
            expected.add((own, enemy))
    images = []
    for choices in product(*paired_choices(3, (1, 1))):
        own = tuple(sorted(row * 3 + file for file, (row, _) in enumerate(choices) if row is not None))
        enemy = tuple(sorted(row * 3 + file for file, (_, row) in enumerate(choices)))
        images.append((own, enemy))
    assert len(images) == len(set(images)) == 9
    assert set(images) == expected


def test_greedy_uniform_own_row_is_not_uniform_joint_physical_pairs():
    pairs = paired_choices(3, (1, 1))[0]
    assert pairs == ((0, 1), (0, 2), (1, 2))
    assert Fraction(sum(own == 0 for own, _ in pairs), len(pairs)) == Fraction(2, 3)
    greedy = {pair: Fraction(1, 2) / sum(own == pair[0] for own, _ in pairs) for pair in pairs}
    assert set(greedy.values()) == {Fraction(1, 4), Fraction(1, 2)}
    assert sum(greedy.values()) == 1


@pytest.fixture(scope='module')
def result():
    return audit()


def test_first_full_inventory_roots_have_complete_evidence_without_nonzero_claim(result):
    assert result['complete'] and len(result['roots']) == 12
    assert result['materialized_transitions'] == sum(1 + action['reply_count']
        for row in result['roots'] for action in row['actions'])
    assert result['materialized_transitions'] == 1642
    assert all(row['success'] == 0 for row in result['roots'])
    assert result['games']['chess']['proposals'] == 2
    assert result['games']['shogi']['proposals'] == 7
    assert len(result['games']['shogi']['common_screen_family']) == 13


def test_direct_proposals_preserve_physical_inventory_and_pawn_conditions():
    chess, _ = standard_engine()
    shogi = compile_ruleset_for_execution(build_standard_shogi_ruleset())
    for game, compiled in [('chess', chess), ('shogi', shogi)]:
        original = initial_state(compiled).position
        frame = sample_frame(compiled, game, Random(20261003))
        assert Counter((p.owner, p.base_type_id) for p in original.board if p) == Counter(
            (p.owner, p.base_type_id) for p in frame.board if p)
        assert frame.board[3 * compiled.board_size + 3].current_type_id == 'P'
        if game == 'shogi':
            for owner in (0, 1):
                files = [i % 9 for i, p in enumerate(frame.board) if p and p.owner == owner and p.current_type_id == 'P']
                assert len(files) == 9 and len(set(files)) == 9
                assert all((i // 9 != (8 if owner == 0 else 0)) for i, p in enumerate(frame.board)
                           if p and p.owner == owner and p.current_type_id == 'P')
            promoted = substituted(frame, 'TR', compiled).board[30]
            assert promoted.base_type_id == 'R' and promoted.current_type_id == 'TR' and promoted.promoted
        else:
            assert all(0 < i // 8 < 7 for i, p in enumerate(frame.board) if p and p.current_type_id == 'P')


def test_structural_mass_is_an_exact_bound_not_full_legality_probability():
    masses = support_masses()
    assert masses['chess'] == Fraction(775661821, 126038941455)
    assert masses['shogi'] == Fraction(41052847357053, 129853494624428432000)
    assert 3_000_000 < 1 / masses['shogi'] < 3_200_000


def test_proposal_limit_preserves_incomplete_status_instead_of_zero_vector():
    result = audit(proposal_limit=0)
    assert not result['complete'] and result['roots'] == []
    assert 'no common frame' in result['incomplete_reason']
    assert 'observed_task_scores' not in result['games']['chess']


def test_transition_cap_aborts_before_any_complete_vector():
    with pytest.raises(RuntimeError, match='no complete vector'):
        audit(Budget(transitions_limit=1))


def test_frozen_physical_evidence_and_source_hash_reproduce(result):
    root = Path(__file__).resolve().parents[1]
    recorded = json.loads((root / 'docs/research/data/physical_placement_sampling_20261003.json').read_text())
    assert recorded['program_sha256'] == hashlib.sha256(
        (root / 'scripts/audit_physical_placement_sampling.py').read_bytes()).hexdigest()
    for field in ('protocol_sha256', 'program_sha256', 'seed', 'complete', 'support_masses',
                  'games', 'roots', 'materialized_transitions'):
        assert result[field] == recorded[field]


def test_zero_diagnosis_replays_actual_background_countercaptures():
    from scripts.diagnose_physical_exchange_zero import diagnose
    root = Path(__file__).resolve().parents[1]
    evidence = json.loads((root / 'docs/research/data/physical_placement_sampling_20261003.json').read_text())
    result = diagnose(evidence)
    recorded = json.loads((root / 'docs/research/data/physical_exchange_zero_diagnosis_20261003.json').read_text())
    assert result['program_sha256'] == recorded['program_sha256'] == hashlib.sha256(
        (root / 'scripts/diagnose_physical_exchange_zero.py').read_bytes()).hexdigest()
    assert result['input_content_sha256'] == recorded['input_content_sha256']
    assert result['counts'] == {'no_immediate_custody_gain': 30,
                                'other_token_countercapture': 13, 'focal_recapture': 3}
    assert result['replayed_transitions'] == 62
    assert all(w['first_refutation']['custody_delta'] <= 0 for w in result['gain_action_witnesses'])
