from fractions import Fraction as F
import json
import pytest
from generic_chess.core.actions import BoardMove, PassAction
from generic_chess.core.coordinates import Square
from generic_chess.ai.decision import PlayerDecision
from generic_chess.core.terminal import TerminalResult,TerminalStatus as T
from scripts.research_record import record_value,write_record

def test_pass_action_identity_survives_nested_research_decision_record(tmp_path):
    decision = PlayerDecision(
        action=PassAction(), score=0, principal_variation=(PassAction(),),
        completed_depth=1, selective_depth=1, nodes=1, qnodes=0,
        elapsed_seconds=0.01, tt_probes=0, tt_hits=0, tt_cutoffs=0,
        beta_cutoffs=0, evaluation_profile_cache_hit=False,
        termination_reason='completed_depth',
    )
    encoded = record_value(decision)
    assert encoded['action'] == {'kind': 'pass'}
    assert encoded['principal_variation'] == [{'kind': 'pass'}]
    output = tmp_path / 'pass-decision.json'
    write_record(output, decision)
    assert json.loads(output.read_text()) == encoded
    # Keep pre-existing records for ordinary actions unchanged.
    assert record_value(BoardMove(Square(0, 1), Square(0, 2))) == {
        'from_square': {'file': 0, 'rank': 1},
        'to_square': {'file': 0, 'rank': 2},
        'promotion_target_id': None,
    }

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


def test_numpy_scalar_metadata_preserves_types_and_large_integer(tmp_path):
    import numpy as np
    p = tmp_path / 'evidence.json'
    value = {'root': np.str_('trajectory/16'), 'count': np.int64(2**60 + 7),
             'known': np.bool_(True), 'score': np.float32(1.25)}
    write_record(p, value)
    assert json.loads(p.read_bytes()) == {
        'root': 'trajectory/16', 'count': 2**60 + 7,
        'known': True, 'score': 1.25,
    }
    old = p.read_bytes()
    with pytest.raises(TypeError):
        write_record(p, {'array': np.asarray([1, 2])})
    with pytest.raises(ValueError):
        write_record(p, {'score': np.float32(np.nan)})
    assert p.read_bytes() == old


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


def test_windows_transient_replacement_reuses_exact_closed_record(tmp_path, monkeypatch):
    import scripts.research_record as records
    p = tmp_path / 'evidence.json'
    p.write_text('{"previous":true}\n')
    original = records.os.replace
    calls, delays = [], []
    def replace(temporary, destination):
        calls.append((temporary, temporary.read_bytes()))
        if len(calls) < 3:
            assert json.loads(destination.read_bytes()) == {'previous': True}
            error = PermissionError('transient Windows file sharing')
            error.winerror = 5
            raise error
        original(temporary, destination)
    monkeypatch.setattr(records.os, 'replace', replace)
    monkeypatch.setattr(records.time, 'sleep', delays.append)
    write_record(p, {'next': True})
    assert len(set(calls)) == 1
    assert delays == [0.01, 0.02]
    assert json.loads(p.read_bytes()) == {'next': True}
    assert not list(tmp_path.glob('*.tmp'))


def test_windows_permanent_replacement_is_bounded(tmp_path, monkeypatch):
    import scripts.research_record as records
    p = tmp_path / 'evidence.json'
    old = b'{"previous":true}\n'
    p.write_bytes(old)
    calls = []
    def replace(*args):
        calls.append(args)
        error = PermissionError('persistent Windows file sharing')
        error.winerror = 32
        raise error
    monkeypatch.setattr(records.os, 'replace', replace)
    monkeypatch.setattr(records.time, 'sleep', lambda _: None)
    with pytest.raises(PermissionError, match='persistent'):
        write_record(p, {'next': True})
    assert len(calls) == 3
    assert p.read_bytes() == old
    assert not list(tmp_path.glob('*.tmp'))


def test_saved_game_record_replays_promotion_drop_aux_and_complete_history(tmp_path):
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.core.actions import SemanticDropMove
    from scripts.price_regions_mixed import fixture

    compiled = compile_ruleset_for_execution(fixture())
    session = GameSession(compiled)
    route = (((1, 1), (1, 3), False), ((7, 7), (6, 7), False),
             ((1, 3), (1, 4), False), ((6, 7), (5, 7), False),
             ((0, 0), (1, 1), True), ((5, 7), (4, 7), False))
    for source, target, semantic in route:
        action, = [a for a in session.legal_actions() if hasattr(a, 'from_square')
                   and (a.from_square.file, a.from_square.rank) == source
                   and (a.to_square.file, a.to_square.rank) == target
                   and a.pattern_id.startswith('sem_') == semantic]
        session.submit(action)
    session.submit(next(a for a in session.legal_actions() if isinstance(a, SemanticDropMove)))
    record = session.to_record()
    path = tmp_path / 'replay.json'
    write_record(path, {'input_record': record})
    payload = json.loads(path.read_bytes())['input_record']
    parsed = deserialize_game_record(json.dumps(payload))
    restored = GameSession.replay(compiled, parsed)
    assert parsed == record
    assert restored.state == session.state
    assert restored._search_witnesses == session._search_witnesses
    assert payload['actions'][-1]['kind'] == 'semantic_drop'


@pytest.mark.parametrize('schema', [1, 2, 3])
def test_nested_game_record_keeps_public_schema_and_typed_actions(schema):
    from generic_chess.session.record import GameRecord, DeclarationRecord
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.core.actions import SemanticBoardMove, SemanticDropMove
    actions = (BoardMove(Square(0, 1), Square(0, 2), 'X'),
               SemanticBoardMove('p', 'g', 'X', Square(0, 2), Square(1, 2)),
               SemanticDropMove('drop', 'square', 'P', Square(2, 2)), PassAction())
    declaration = DeclarationRecord('goal', 1, 'WIN', 42) if schema == 2 else None
    record = GameRecord(schema, 'test-rule', actions, None, declaration,
                        'alternate' if schema == 3 else None)
    payload = record_value({'record': record})['record']
    assert deserialize_game_record(json.dumps(payload)) == record
    # An ordinary diagnostic action/PlayerDecision keeps its established shape.
    assert record_value(actions[0])['from_square'] == {'file': 0, 'rank': 1}


def test_invalid_game_record_cannot_replace_existing_evidence(tmp_path):
    from generic_chess.session.record import GameRecord, DeclarationRecord
    from generic_chess.session.session import SessionRecordError
    path = tmp_path / 'evidence.json'
    old = b'{"preserved":true}\n'
    path.write_bytes(old)
    invalid = GameRecord(1, 'test-rule', (), None, DeclarationRecord('goal', 0, 'WIN'))
    with pytest.raises(SessionRecordError, match='schema v1'):
        write_record(path, {'record': invalid})
    assert path.read_bytes() == old
