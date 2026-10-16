from pathlib import Path
import hashlib,json,sys
import pytest
from results.dev_aux.task2115.publication_pins import verify_publication_pins

def test_projection_is_explicit_and_never_claims_original_identity(tmp_path):
 f=tmp_path/'bridge.py';f.write_bytes(b'publiccopy');orig=hashlib.sha256(b'privateoriginal').hexdigest();pub=hashlib.sha256(f.read_bytes()).hexdigest();key=str(f).replace('\\','/');manifest=tmp_path/'projection.json';manifest.write_text(json.dumps({'files':{key:{'original_sha256':orig,'published_sha256':pub,'must_not_import':'unused_test_bridge'}}}),encoding='utf-8')
 with pytest.raises(AssertionError):verify_publication_pins({str(f):orig})
 r=verify_publication_pins({str(f):orig},manifest)
 assert not r['full_original_byte_identity']and r['published_unused_privacy_projections']==[key]

def test_loaded_module_or_unexplained_changes_fail(tmp_path,monkeypatch):
 f=tmp_path/'bridge.py';f.write_bytes(b'publiccopy');orig=hashlib.sha256(b'privateoriginal').hexdigest();key=str(f).replace('\\','/');manifest=tmp_path/'projection.json';manifest.write_text(json.dumps({'files':{key:{'original_sha256':orig,'published_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'must_not_import':'unused_test_bridge'}}}),encoding='utf-8')
 monkeypatch.setitem(sys.modules,'unused_test_bridge',object())
 with pytest.raises(AssertionError):verify_publication_pins({str(f):orig},manifest)
 monkeypatch.delitem(sys.modules,'unused_test_bridge');f.write_bytes(b'unexplainedchange')
 with pytest.raises(AssertionError):verify_publication_pins({str(f):orig},manifest)
