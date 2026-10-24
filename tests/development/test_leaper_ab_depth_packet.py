import gzip,hashlib,json
from pathlib import Path
import pytest
from scripts.verify_leaper_ab_depth_packet import read
from scripts.verify_leaper_ab_deeper_targets import paired_bounds


def packet(tmp_path):
    data=tmp_path/'data';data.mkdir()
    payload={'documents_utf8':{'case/input.json':'{"actual":"record"}\n'},'source_capsules_utf8':{'trap.py':'raise AssertionError("capsule executed")\n'}}
    digest=lambda b:hashlib.sha256(b).hexdigest()
    raw=json.dumps(payload).encode();compressed=gzip.compress(raw)
    manifest=dict(packet_sha256=digest(compressed),decoded_sha256=digest(raw),producer_bindings={},external_files={})
    for group,items in payload.items():manifest[group]={n:dict(bytes=len(t.encode()),sha256=digest(t.encode()))for n,t in items.items()}
    (data/'evidence.json.gz').write_bytes(compressed);(data/'manifest.json').write_text(json.dumps(manifest))
    return data,manifest


def test_data_capsule_is_not_executed_or_materialized_as_source(tmp_path):
    data,_=packet(tmp_path);out=tmp_path/'replay';_,p=read(data,out)
    assert (out/'case/input.json').read_text()=='{"actual":"record"}\n'
    assert not (out/'trap.py').exists()and'trap.py'in p['source_capsules_utf8']


def test_corrupt_bytes_rejected_before_any_document_write(tmp_path):
    data,_=packet(tmp_path);p=data/'evidence.json.gz';p.write_bytes(p.read_bytes()+b'broken')
    out=tmp_path/'replay'
    with pytest.raises(AssertionError):read(data,out)
    assert not out.exists()


def test_injected_escape_document_rejected(tmp_path):
    data,manifest=packet(tmp_path);raw=json.loads(gzip.decompress((data/'evidence.json.gz').read_bytes()))
    raw['documents_utf8']['../outside.py']=raw['documents_utf8'].pop('case/input.json')
    manifest['documents_utf8']['../outside.py']=manifest['documents_utf8'].pop('case/input.json')
    body=json.dumps(raw).encode();compressed=gzip.compress(body)
    manifest.update(packet_sha256=hashlib.sha256(compressed).hexdigest(),decoded_sha256=hashlib.sha256(body).hexdigest())
    (data/'evidence.json.gz').write_bytes(compressed);(data/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(AssertionError):read(data,tmp_path/'replay')
    assert not (tmp_path/'outside.py').exists()


def test_wholly_unstarted_pairs_keep_full_denominator_and_unknown_bounds():
    slots=[dict(phase='eval',group='contact',root=i,role=0,arm=a)for i in range(2)for a in('Unit','D4','D6')]
    r=paired_bounds(slots,{('contact',0,0):{'Unit':dict(utility=0,final_record={})}})
    assert len(r)==4
    assert all(x['difference']is None for x in r)
    assert [(x['lower'],x['upper'])for x in r]==[(-1,1),(-1,1),(-2,2),(-2,2)]
