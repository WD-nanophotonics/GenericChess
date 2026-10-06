"""Verify historical producer bytes without freezing active development.

Only explicitly archived search/quiescence/tuning/record-writer versions are alternatives;
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
        # An additional explicitly archived development version never replaces
        # the original frozen bindings. Match exact expected bytes only.
        extra = root/'docs/archive/development_before_20261006_qfix/qorder_before_sources.json'
        if extra.exists():
            manifest_extra = json.loads(extra.read_text())
            item = manifest_extra['sources'].get(path)
            if item is not None and item['sha256'] == expected:
                with zipfile.ZipFile(root/manifest_extra['archive']) as archive:
                    return hashlib.sha256(archive.read(path)).hexdigest()
        return current  # original caller assertion reports the mismatch
    with zipfile.ZipFile(root/source['archive']) as archive:
        return hashlib.sha256(archive.read(source['member'])).hexdigest()
