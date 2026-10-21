"""Optional generator preference uses actual first-action wins, not short walks."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation import filters
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.serialization import deserialize_ruleset


def compiled(name, max_ply=None):
    source = Path(__file__).resolve().parents[1] / 'fixtures' / f'generated_opening_{name}.json'
    rule = deserialize_ruleset(source.read_text())
    return compile_ruleset(replace(rule, max_ply=max_ply) if max_ply is not None else rule)


def check(c, enabled):
    cfg = GeneratorConfig(seed=0, board_size=4,
                          require_no_opening_win_in_one=enabled)
    return {f.name: f for f in filters.run_soft_filters(
        cfg, c, {p.type_id: p for p in c.piece_types})}


def test_disabled_preference_preserves_report_and_does_no_trial_transitions(monkeypatch):
    def forbidden(*args):
        raise AssertionError('disabled preference must not evaluate children')
    monkeypatch.setattr(filters, 'apply_action', forbidden)
    result = check(compiled('141401'), False)
    assert 'opening_has_no_win_in_one' not in result
    assert all(f.passed for f in result.values())


@pytest.mark.parametrize('max_ply', (None, 1))
def test_rejects_actual_mate_in_one_even_with_other_ongoing_choices(max_ply):
    # Frozen actual generated rule has six legal first actions and a mating one.
    # Mate also keeps priority over max_ply; it is not misclassified as a draw.
    result = check(compiled('141401', max_ply), True)
    assert not result['opening_has_no_win_in_one'].passed
    assert 'winning first action' in result['opening_has_no_win_in_one'].detail


@pytest.mark.parametrize('max_ply', (None, 1))
def test_keeps_no_opening_win_despite_a_later_short_mate_or_draw(max_ply):
    # An exposed chosen walk ended at ply5, but no initial action wins.
    # At max1 these nonwinning children draw and must still pass.
    assert check(compiled('141402', max_ply), True)['opening_has_no_win_in_one'].passed
