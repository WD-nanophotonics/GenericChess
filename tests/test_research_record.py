from fractions import Fraction as F
import json
import pytest
from generic_chess.core.terminal import TerminalResult,TerminalStatus as T
from scripts.research_record import record_value,write_record

def test_exact_terminal_dataclass_and_rational_record(tmp_path):
    p=tmp_path/'evidence.json'
    write_record(p,{'terminal':TerminalResult(T.CHECKMATE,1),'margin':F(2,3),'tuple_key':{('board','P'):1}})
    x=json.loads(p.read_text())
    assert x['terminal']=={'status':'checkmate','winner':1}
    assert x['margin']=='2/3' and x['tuple_key']=={"('board', 'P')":1}

def test_encoding_failure_never_truncates_existing_evidence(tmp_path):
    p=tmp_path/'evidence.json';p.write_text('old')
    with pytest.raises(TypeError):write_record(p,{'unsupported':object()})
    assert p.read_text()=='old'
    with pytest.raises(ValueError,match='collision'):record_value({1:'a','1':'b'})
