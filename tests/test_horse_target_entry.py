import hashlib
import json
from pathlib import Path
import pytest
from scripts.horse_target_entry import incoming_sources, blockers_eliminating_all_entries

ROOT = Path(__file__).resolve().parents[1]


def test_saved_complete_entry_lemma_and_original_cumulative_caps():
    r = json.loads((ROOT/'docs/research/data/horse_target_entry_20261006.json').read_text())
    assert r['complete'] and r['source_hashes_unchanged']
    for path, digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
    assert r['offset_checks'] == 720 and r['intersections'] == 508
    assert r['cumulative_terms'] == 4960 and r['cumulative_forward_nodes'] == 1579
    assert r['entry_zero_worlds'] == 352 and not r['full_reachability_complement_proved']
    assert {row['target']: row['all_entry_blockers'] for row in r['rows'] if row['all_entry_blockers']} == {0: [10], 8: [16], 81: [73], 89: [79]}


def test_arrival_geometry_and_inward_corner_legs():
    assert incoming_sources(0) == [(11, 10), (19, 10)]
    assert blockers_eliminating_all_entries(0) == [10]
    assert blockers_eliminating_all_entries(40) == []
    for target in (0, 1, 40, 89):
        for source, leg in incoming_sources(target):
            dx = target % 9-source % 9; dy = target//9-source//9
            assert sorted((abs(dx), abs(dy))) == [1, 2]
            expected = source+(1 if dx > 0 else -1) if abs(dx) == 2 else source+9*(1 if dy > 0 else -1)
            assert expected == leg and leg not in (source, target)


@pytest.mark.parametrize('target,width,height', [(True,9,10), (-1,9,10), (90,9,10), (0,2,10), (0,9,False)])
def test_invalid_coordinate_domain_rejected(target, width, height):
    with pytest.raises(ValueError): incoming_sources(target, width, height)
