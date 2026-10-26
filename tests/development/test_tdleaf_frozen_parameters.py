"""Receipt-only controls for fixed-unit/scale semantics; no search or training."""
import pytest
from generic_chess.learning.incremental import MATE, Model, Receipt, TDLeafEpisode


def receipt(value=2., phi=(0., 1.), terminal=False, complete=True):
    return Receipt(None, value, phi, terminal, (), 0, complete, 0, 0., 'synthetic')


@pytest.mark.parametrize('scale', [1e-200, 10., 1e6, 1e12, 1e200])
@pytest.mark.parametrize('outcome', [-1, 0, 1])
def test_literal_terminal_does_not_depend_on_material_scale(scale, outcome, monkeypatch):
    model = Model([1., 2.], scale=scale)
    episode = TDLeafEpisode()
    def forbidden(*args):
        raise AssertionError('literal terminal must not evaluate material or update parameters')
    monkeypatch.setattr(model, 'gradient', forbidden)
    monkeypatch.setattr(model, 'apply', forbidden)
    episode.observe(model, receipt(MATE * outcome, None, True))
    assert episode.rows == [(float(outcome), (0., 0.))]
    assert model.weights == [1., 2.]


@pytest.mark.parametrize('field,value', [('scale', 20.), ('fixed', 1)])
@pytest.mark.parametrize('boundary', ['observe', 'finish'])
def test_all_prediction_parameters_remain_frozen(field, value, boundary, monkeypatch):
    model = Model([1., 2.]); episode = TDLeafEpisode()
    episode.observe(model, receipt())
    original_rows = episode.rows[:]
    setattr(model, field, value)
    def forbidden(*args):
        raise AssertionError('changed model must be rejected before any update')
    monkeypatch.setattr(model, 'apply', forbidden)
    with pytest.raises(ValueError, match='changed'):
        episode.observe(model, receipt()) if boundary == 'observe' else episode.finish(model, None)
    assert episode.rows == original_rows
    assert model.weights == [1., 2.]


@pytest.mark.parametrize('value,phi', [(1., None), (-2., None), (float('nan'), None),
    (float('inf'), None), (MATE, (0., 1.))])
def test_inconsistent_terminal_receipt_fails_without_partial_observation(value, phi):
    model = Model([1., 2.]); episode = TDLeafEpisode()
    with pytest.raises(ValueError):
        episode.observe(model, receipt(value, phi, True))
    assert episode.rows == [] and episode.snapshot is None
    assert model.weights == [1., 2.]


def test_incomplete_receipt_does_not_freeze_model_or_add_target():
    model = Model([1., 2.]); episode = TDLeafEpisode()
    episode.observe(model, receipt(None, None, False, False))
    assert episode.rows == [] and episode.snapshot is None
    model.scale = 20.
    episode.observe(model, receipt())
    assert len(episode.rows) == 1


def test_frozen_equivalent_copy_is_accepted_without_object_identity():
    model = Model([1., 2.], fixed=0, scale=20.)
    copy = Model([1., 2.], fixed=0, scale=20.)
    episode = TDLeafEpisode()
    episode.observe(model, receipt()); episode.observe(copy, receipt())
    assert len(episode.rows) == 2
    assert episode.rows[0] == episode.rows[1]


def test_positive_unit_gauge_does_not_bypass_raw_score_admission():
    # Same mathematical bounded prediction, but changed raw units cross the
    # actual Model safety guard. This is an admission counterexample, no update.
    old = Model([1., 1e-8], scale=10.)
    assert old.prediction((1., 0.)) > 0
    changed_unit = Model([1., 1e8], scale=1e9)
    with pytest.raises(ValueError, match='terminal safety margin'):
        changed_unit.prediction((0., 1.))


def test_weights_only_constructor_is_not_a_scale_preserving_clone():
    from generic_chess.learning.incremental import unchanged_model
    old = Model([1., 2.], scale=20.)
    historical_fixed_scale_constructor = unchanged_model(old.weights)
    assert historical_fixed_scale_constructor.scale == 10.
    assert old.prediction((0., 1.)) != historical_fixed_scale_constructor.prediction((0., 1.))
    # Existing historical callers intentionally use fixed scale10; this helper
    # is not a self-describing cross-unit checkpoint loader or generic clone.


def test_channel_permutation_requires_declared_physical_unit_identity():
    old = Model([1., 2., 3., 4.], fixed=0, scale=10.)
    # Pure B<->C renaming retains physical A as fixed unit; exact permutation.
    renamed = Model([1., 3., 2., 4.], fixed=0, scale=10.)
    assert old.prediction((2., -1., 3., 0.)) == renamed.prediction((2., 3., -1., 0.))
    assert old.gradient((2., -1., 3., 0.))[0] == 0
    assert renamed.gradient((2., 3., -1., 0.))[0] == 0



@pytest.mark.parametrize('scale', [10., 1e6, 1e12])
@pytest.mark.parametrize('terminal_value', [-1, 0, 1])
def test_independent_terminal_arithmetic_matches_library_without_applying_update(scale, terminal_value, monkeypatch):
    from scripts.verify_leaper_ab_learning import td_sum
    before = [1., 2.]
    records = [dict(value=2., pv_phi=(0., 1.), pv_terminal=False),
               dict(value=MATE * terminal_value, pv_phi=None, pv_terminal=True)]
    expected_after, expected_stats = td_sum(before, records, None, scale=scale)
    model = Model(before, scale=scale); episode = TDLeafEpisode()
    for r in records:
        episode.observe(model, receipt(r['value'], r['pv_phi'], r['pv_terminal']))
    captured = []
    monkeypatch.setattr(model, 'apply', lambda delta: captured.append(delta))
    actual_stats = episode.finish(model, None)
    assert len(captured) == 1
    assert [v + d for v, d in zip(before, captured[0])] == pytest.approx(expected_after, abs=1e-15)
    assert actual_stats == expected_stats
    assert model.weights == before  # Independent arithmetic only; no fit.
