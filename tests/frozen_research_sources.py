"""Verify historical producer bytes without freezing active development.

Only explicitly archived search/quiescence/tuning versions are alternatives;
unrelated changed sources still fail their original digest assertion.
"""
import hashlib
import json
import zipfile


def source_digest(root, path, expected):
    current = hashlib.sha256((root/path).read_bytes()).hexdigest()
    if current == expected:
        return current
    manifest = root/'docs/archive/development_before_20261006_qfix/sources.json'
    source = json.loads(manifest.read_text())['sources'].get(path)
    if source is None or source['sha256'] != expected:
        return current  # original caller assertion reports the mismatch
    with zipfile.ZipFile(root/source['archive']) as archive:
        return hashlib.sha256(archive.read(source['member'])).hexdigest()
