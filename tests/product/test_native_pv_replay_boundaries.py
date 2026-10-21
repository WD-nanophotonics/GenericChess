"""Observed caller replay boundary: real history terminals and declaration tails."""
from dataclasses import replace
import pytest
from conftest import make_ruleset
from generic_chess.core.pieces import PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.native import native_available, SemanticSearchEngine
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native import semantic as sem
from generic_chess.ai.limits import SearchLimits
from test_native_terminal_declaration_priority import position

pytestmark=pytest.mark.skipif(not native_available(),reason='Native unavailable')
DECL=1<<63


def repeated_root():
    king=PieceType('K','K',(),is_anchor=True)
    f=PieceType('F','F',(LeapAtom((0,1)),LeapAtom((0,-1))))
    g=PieceType('G','G',(LeapAtom((0,1)),LeapAtom((0,-1))))
    z=PieceType('Z','Z',())
    zero=(False,)*16
    rules=make_ruleset(4,[king,f,g,z],['Z..k','...g','F...','K..z'],
                       drop_all={'F':zero,'G':zero,'Z':zero})
    s=GameSession(compile_legacy_ruleset_for_semantic_execution(rules))
    for _ in range(11):
        actions=s.legal_actions();assert len(actions)==1;s.submit(actions[0])
    return s


def engine_and_raw(s):
    nr=compile_native_semantic_rules(s.compiled)
    e=SemanticSearchEngine(s.compiled,nr,tt_megabytes=0)
    pos=pack_semantic_search_position(s.compiled,nr,s)
    raw=dict(e._backend.semantic_engine_search(e._capsule,pos,1,100,None,None,None,False,False))
    return e,nr,pos,raw


def deliver(e,s,raw):
    backend=e._backend
    class InjectedResult:
        def __getattr__(self,name):return getattr(backend,name)
        def semantic_engine_search(self,*args):return raw
    e._backend=InjectedResult()
    return e.search(s,SearchLimits(max_depth=2,max_time_seconds=2))


@pytest.mark.parametrize('suffix',['board','declaration'])
def test_pv_rejects_continuation_after_actual_repetition(suffix):
    s=repeated_root();e,nr,pos,raw=engine_and_raw(s)
    first=pack_semantic_action(nr,s.state.position,s.legal_actions()[0])
    child=apply_action(s.state,s.legal_actions()[0],s.compiled)
    assert child.terminal_status.status.value=='repetition'
    cp=sem.make_checked(nr,pos,first)
    following=sem.transient_legal_actions(nr,cp)[0] if suffix=='board' else DECL
    raw['principal_variation']=(first,following);raw['best_action']=first
    with pytest.raises((ValueError,RuntimeError),match='terminal|terminal state|declaration'):
        deliver(e,s,raw)


@pytest.mark.parametrize('extra',[0,1<<8,1<<40])
def test_pv_rejects_move_after_declaration_and_noncanonical_tag(extra):
    s=position(declaring_owner=0);e,nr,pos,raw=engine_and_raw(s)
    code=pack_semantic_action(nr,s.state.position,s.legal_actions()[0])
    raw['principal_variation']=(DECL|extra,code) if not extra else (DECL|extra,)
    with pytest.raises(ValueError,match='declaration'):
        deliver(e,s,raw)


@pytest.mark.parametrize('field',['actor_current','base','pattern','geometry'])
def test_pv_rejects_changed_raw_action_identity(field):
    s=position();e,nr,pos,raw=engine_and_raw(s)
    code=pack_semantic_action(nr,s.state.position,s.legal_actions()[0]);fields=sem.unpack_action(code,native_rules=nr)
    fields[field]=(fields[field]+1) if field in ('pattern','geometry') else (fields[field]+1)%len(nr.type_ids)
    raw['principal_variation']=(sem.pack_action(fields,native_rules=nr),)
    with pytest.raises((ValueError,RuntimeError)):
        deliver(e,s,raw)


def test_real_terminal_leaf_and_declaration_are_still_delivered():
    for s in (position(),position(declaring_owner=0),repeated_root()):
        nr=compile_native_semantic_rules(s.compiled);e=SemanticSearchEngine(s.compiled,nr,tt_megabytes=1)
        for _ in range(2):
            r=e.search(s,SearchLimits(max_depth=2,max_time_seconds=3))
            state=s.state
            for action in r.principal_variation:state=apply_action(state,action,s.compiled)
            assert state.terminal_status.is_terminal or r.declaration_id=='win'
