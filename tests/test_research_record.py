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


def test_reader_keeps_complete_old_record_until_new_record_is_ready(tmp_path,monkeypatch):
    import scripts.research_record as records
    p=tmp_path/'evidence.json';p.write_text('{"previous":true}\n')
    original_replace=records.os.replace
    observed=[]
    def replace(temporary,destination):
        assert temporary.parent==destination.parent
        observed.append(json.loads(destination.read_bytes()))
        assert json.loads(temporary.read_bytes())=={'next':[1,2,3]}
        original_replace(temporary,destination)
    monkeypatch.setattr(records.os,'replace',replace)
    write_record(p,{'next':[1,2,3]})
    assert observed==[{'previous':True}]
    assert p.read_bytes()==(json.dumps({'next':[1,2,3]},indent=2)+'\n').encode('utf-8')
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.parametrize('indent',[2,None])
def test_replacement_failure_preserves_frontier_and_cleans_temporary(tmp_path,monkeypatch,indent):
    import scripts.research_record as records
    p=tmp_path/'evidence.json';old=b'{"previous":true}\n';p.write_bytes(old)
    def fail(*args):
        raise OSError('injected replacement failure')
    monkeypatch.setattr(records.os,'replace',fail)
    with pytest.raises(OSError,match='replacement failure'):
        write_record(p,{'next':True},indent=indent)
    assert p.read_bytes()==old
    assert not list(tmp_path.glob('*.tmp'))


def test_compact_frontier_preserves_values_and_default_format(tmp_path):
    value={'terminal':TerminalResult(T.CHECKMATE,1),'margin':F(2,3),
           'moves':[{1:'first',2:['next',True]}]*4}
    pretty=tmp_path/'pretty.json';compact=tmp_path/'compact.json'
    write_record(pretty,value)
    write_record(compact,value,indent=None)
    assert json.loads(pretty.read_bytes())==json.loads(compact.read_bytes())==record_value(value)
    assert pretty.read_bytes()==(json.dumps(record_value(value),indent=2)+'\n').encode()
    assert len(compact.read_bytes())<len(pretty.read_bytes())
    assert not list(tmp_path.glob('*.tmp'))
