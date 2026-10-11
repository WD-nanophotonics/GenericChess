"""Recheck the recorded full-Native precedent without executing an engine."""
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

REVISION = 'ee48d0a55c7bda3d702f45ce2dc4162cc3bbc0ac'
INDEX = 'docs/research/data/native_conversion_20261010.json'
DIRECTORY = '.local_agent/native-conversion-20261010/'
FIELDS = ('score', 'action', 'principal_variation', 'decision_line',
          'completed_depth', 'nodes', 'qnodes', 'termination_reason', 'used_fallback')

def git_file(path):
    return subprocess.check_output(['git', 'show', REVISION + ':' + path])

def verify():
    index = json.loads(git_file(INDEX))
    archive = git_file(index['archive'])
    assert hashlib.sha256(archive).hexdigest() == index['archive_sha256']
    summary = json.loads(Path(__file__).with_name('full_native_precedent.json').read_bytes())
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name, expected in summary['selected_members'].items():
            raw = z.read(name)
            assert len(raw) == expected['bytes']
            assert hashlib.sha256(raw).hexdigest() == expected['sha256']
        data = json.loads(z.read(DIRECTORY + 'zero-feature-control.json'))
        pairs = 0
        for root in sorted({row['case'] for row in data['search_rows']}):
            rows = [row for row in data['search_rows'] if row['case'] == root]
            assert len(rows) == 4
            for offset in (0, 2):
                first, second = rows[offset:offset + 2]
                assert (first['dynamic'] is None) != (second['dynamic'] is None)
                for field in FIELDS:
                    assert first['result'][field] == second['result'][field], (root, field)
                pairs += 1
        assert pairs == len(summary['verified_pairs']) == 6
        for stem, source in (('full-native', 'full_native_probe'),
                             ('zero-feature-control', 'zero_feature_control')):
            recorded = json.loads(z.read(DIRECTORY + stem + '.json'))
            assert recorded['source_sha256'] == hashlib.sha256(
                z.read(DIRECTORY + source + '.py')).hexdigest()
    return pairs

if __name__ == '__main__':
    print('verified', verify(), 'historical pairs; no engine execution')
