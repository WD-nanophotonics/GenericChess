"""Frozen engineering eligibility and exact-byte publication contracts."""
import gzip
import hashlib
import json

import pytest

from scripts import verify_leaper_child_cost as R


def panel():
    return [dict(case_id=f'r{i}', depth=d, repetition=k, eligible=True,
                 off_seconds=1.0, on_seconds=0.94, off_cpu=1.0, on_cpu=0.94, ratio=0.94)
            for i in range(12) for d in (3, 6) for k in range(3)]


def setup(wall=0.0):
    return {'candidate_import_wall_seconds': wall, 'candidate_import_cpu_seconds': 0.0}


def test_missing_D6_still_unknown_even_if_observed_pairs_fast():
    pairs = panel()
    for p in pairs:
        if p['depth'] == 6 and int(p['case_id'][1:]) >= 7:
            p['eligible'] = False
    result = R.acceptance(pairs, [f'r{i}' for i in range(12)], setup())
    assert result['complete_root_triplets'] == {'3': 12, '6': 7}
    assert result['eligible_pairs'] == 57 and result['decision'] == 'UNKNOWN'
    assert result['gates']['at_least_5pct_wall_gain']


def test_candidate_process_setup_is_charged_not_hidden():
    roots = [f'r{i}' for i in range(12)]
    assert R.acceptance(panel(), roots, setup())['decision'] == 'SCOPED_ENGINEERING_GO'
    actual = R.acceptance(panel(), roots, setup(2.0))
    assert actual['decision'] == 'NO_GO'
    assert actual['charged_wall_ratio'] == pytest.approx((72*0.94+2)/72)
    assert not actual['gates']['at_least_5pct_wall_gain']


def test_one_regressing_root_cannot_be_hidden_by_panel_average():
    pairs = panel()
    for p in pairs:
        p.update(on_seconds=0.9, on_cpu=0.9, ratio=0.9)
        if p['case_id'] == 'r0':
            p.update(on_seconds=1.11, on_cpu=1.11, ratio=1.11)
    r = R.acceptance(pairs, [f'r{i}' for i in range(12)], setup())
    assert r['gates']['at_least_5pct_wall_gain']
    assert not r['gates']['no_root_median_over_1_10'] and r['decision'] == 'NO_GO'


def test_manifest_binds_both_archive_and_original_bytes(tmp_path):
    original = b'{"slot_id":"s000","value":1}\r\n'
    archive = gzip.compress(original, mtime=0)
    (tmp_path/'s000.json.gz').write_bytes(archive)
    manifest = {'members': {'s000.json': {
        'original_sha256': hashlib.sha256(original).hexdigest(),
        'gzip_sha256': hashlib.sha256(archive).hexdigest(), 'original_bytes': len(original)}}}
    path = tmp_path/'manifest.json'; path.write_text(json.dumps(manifest), encoding='utf-8')
    assert R.original_bytes(tmp_path/'s000.json') == original
    assert R.verify_public_manifest(path) == 1
    (tmp_path/'s000.json.gz').write_bytes(gzip.compress(original.replace(b'1', b'2'), mtime=0))
    with pytest.raises(AssertionError):
        R.verify_public_manifest(path)
