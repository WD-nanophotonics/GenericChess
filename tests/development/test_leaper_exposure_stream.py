import gzip,json
import pytest
from scripts.leaper_exposure_stream import scan

def test_stream_capture_is_data_and_escaped_literal_is_not_claimed_complete(tmp_path):
    pieces=[{'is_anchor':False,'movement_atoms':[{'kind':'leap','offset':[1,0]}]}];p=tmp_path/'x.json.gz';p.write_bytes(gzip.compress(json.dumps({'actual':{'piece_types':pieces},'quoted':json.dumps({'piece_types':pieces})}).encode()));r=scan(p);assert len(r['arrays'])==1;assert 'not covered' in r['limitations']

def test_stream_refuses_incomplete_piece_list_and_size_overrun(tmp_path):
    p=tmp_path/'bad.json.gz';p.write_bytes(gzip.compress(b'{"piece_types":[{'))
    with pytest.raises(json.JSONDecodeError):scan(p)
    p.write_bytes(gzip.compress(b' '*1000))
    with pytest.raises(ValueError,match='cap'):scan(p,cap=10)
