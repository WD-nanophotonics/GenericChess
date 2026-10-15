"""Research certificate JSON transport; decoding is NOT proof verification.

Only public GameRecord replay reconstructs roots; no pickle/eval or arbitrary
GameState import. The independent session verifier/cursor must still validate
all edges and terminal results after decoding. Exact state repr hash is a
source-version-bound provenance check, not a portable game identity standard.
"""
import hashlib,json
from dataclasses import fields
from generic_chess.session.record import GameRecord
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionResult,SessionStatus
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from scripts.generic_win_proof import _same_state
from scripts.generic_session_win_proof import SessionChoice,SessionProofNode,SessionWinCertificate


def _canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def _state_sha(state):return hashlib.sha256(repr(state).encode('utf-8')).hexdigest()
def _fields(value,expected):
    if type(value) is not dict or set(value)!=set(expected):raise ValueError('unexpected certificate JSON fields')
def _limit(value,name):
    if type(value) is not int or value<0:raise ValueError(name+' must be a nonnegative integer')


def export_session_certificate(session,certificate,*,max_nodes=65536):
    _limit(max_nodes,'max_nodes');count=0
    if (not isinstance(certificate,SessionWinCertificate)
        or certificate.ruleset_fingerprint!=session.compiled.ruleset_fingerprint
        or not _same_state(certificate.root_record,session.to_record())
        or not _same_state(certificate.root_state,session.state)):
        raise ValueError('certificate/session root binding mismatch')
    def node(tree,depth):
        nonlocal count
        count+=1
        if count>max_nodes or depth>128:raise ValueError('certificate export size/depth limit')
        if not isinstance(tree,SessionProofNode):raise ValueError('invalid certificate node')
        terminal=None
        if tree.terminal is not None:
            terminal={f.name:getattr(tree.terminal,f.name) for f in fields(SessionResult)}
            terminal['status']=tree.terminal.status.value
        edges=[]
        for choice,child in tree.edges:
            if choice.kind=='ACTION' and choice.action is not None and choice.declaration_id is None:
                record=GameRecord(1,session.compiled.ruleset_fingerprint,(choice.action,),None)
                raw={'kind':'ACTION','action':json.loads(serialize_game_record(record))['actions'][0]}
            elif choice.kind=='DECLARATION' and choice.action is None and isinstance(choice.declaration_id,str):
                raw={'kind':'DECLARATION','declaration_id':choice.declaration_id}
            else:raise ValueError('invalid typed choice')
            edges.append({'choice':raw,'child':node(child,depth+1)})
        return {'rank':tree.rank,'terminal':terminal,'edges':edges}
    result={'schema_version':1,'ruleset_fingerprint':certificate.ruleset_fingerprint,'target':certificate.target,
            'root_record':json.loads(serialize_game_record(certificate.root_record)),
            'root_state_repr_sha256':_state_sha(certificate.root_state),'tree':node(certificate.tree,0)}
    _canonical(result)
    return result


def decode_session_certificate(compiled,data,*,max_nodes=65536,max_record_actions=4096):
    """Return (actual replayed session, UNVERIFIED certificate); caller verifies."""
    _limit(max_nodes,'max_nodes');_limit(max_record_actions,'max_record_actions');count=0
    _fields(data,['schema_version','ruleset_fingerprint','target','root_record','root_state_repr_sha256','tree'])
    if type(data['schema_version']) is not int or data['schema_version']!=1:raise ValueError('unsupported certificate JSON version')
    if type(data['target']) is not int or data['target'] not in (0,1):raise ValueError('invalid target')
    if data['ruleset_fingerprint']!=compiled.ruleset_fingerprint:raise ValueError('rules fingerprint mismatch')
    raw_record=data['root_record']
    if type(raw_record) is not dict or type(raw_record.get('actions')) is not list or len(raw_record['actions'])>max_record_actions:raise ValueError('root record action limit/type')
    record=deserialize_game_record(_canonical(raw_record))
    if _canonical(json.loads(serialize_game_record(record)))!=_canonical(raw_record):raise ValueError('noncanonical root record')
    session=GameSession.replay(compiled,record)
    if data['root_state_repr_sha256']!=_state_sha(session.state):raise ValueError('replayed root state mismatch')
    def node(raw,depth):
        nonlocal count
        count+=1
        if count>max_nodes or depth>128:raise ValueError('certificate decode size/depth limit')
        _fields(raw,['rank','terminal','edges'])
        if type(raw['rank']) is not int or not 0<=raw['rank']<=128 or type(raw['edges']) is not list:raise ValueError('invalid node rank/edges')
        terminal=None
        if raw['terminal'] is not None:
            terminal_data=raw['terminal'];_fields(terminal_data,[f.name for f in fields(SessionResult)])
            for name in ['winner','resigned_by','declared_by','declaration_score']:
                if terminal_data[name] is not None and type(terminal_data[name]) is not int:raise ValueError('invalid terminal scalar')
            for name in ['declaration_id','declaration_outcome']:
                if terminal_data[name] is not None and type(terminal_data[name]) is not str:raise ValueError('invalid terminal string')
            terminal=SessionResult(**{**terminal_data,'status':SessionStatus(terminal_data['status'])})
        edges=[]
        for edge in raw['edges']:
            _fields(edge,['choice','child']);choice=edge['choice']
            if type(choice) is not dict:raise ValueError('invalid choice object')
            if choice.get('kind')=='ACTION':
                _fields(choice,['kind','action'])
                record=deserialize_game_record(_canonical({'schema_version':1,'ruleset_fingerprint':compiled.ruleset_fingerprint,'actions':[choice['action']],'resigned_by':None}))
                normalized=json.loads(serialize_game_record(record))['actions'][0]
                if _canonical(normalized)!=_canonical(choice['action']):raise ValueError('noncanonical action')
                typed=SessionChoice('ACTION',action=record.actions[0])
            elif choice.get('kind')=='DECLARATION':
                _fields(choice,['kind','declaration_id'])
                if type(choice['declaration_id']) is not str or not choice['declaration_id']:raise ValueError('invalid declaration ID')
                typed=SessionChoice('DECLARATION',declaration_id=choice['declaration_id'])
            else:raise ValueError('unknown session choice kind')
            edges.append((typed,node(edge['child'],depth+1)))
        return SessionProofNode(raw['rank'],tuple(edges),terminal)
    certificate=SessionWinCertificate(compiled.ruleset_fingerprint,record,session.state,data['target'],node(data['tree'],0))
    return session,certificate
