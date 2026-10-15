"""Accepted raw Native geometry paths retain first matching source semantics.
These deliberately edited numeric payloads test Native's public contract, not
an alternate Core ruleset or a claim that the standard compiler emits duplicates.
"""
import copy
import pytest
from conftest import make_ruleset
from generic_chess.core.pieces import PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules,build_semantic_compile_payload
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native import semantic as sem
from generic_chess.session.session import GameSession

pytestmark=pytest.mark.skipif(not native_available(),reason='Native unavailable')

@pytest.mark.parametrize('entries,expected',[
 ([[0,[3]],[2,[4]],[2,[5]],[4,[6]]],{4}),
 ([[2,[4]],[0,[3]],[2,[5]],[4,[6]]],{4}),
 ([[0,[3]],[1,[4]],[2,[5]],[3,[6]]],{5}),
 ([[0,[3]],[4,[6]]],set()),
])
def test_first_source_geometry_lookup_preserves_checked_actions(entries,expected):
 k=PieceType('K','Anchor',(),is_anchor=True)
 x=PieceType('X','Actor',(LeapAtom((0,1)),))
 rules=make_ruleset(4,[k,x],['...k','....','....','K.X.'],drop_all={'X':(False,)*16})
 session=GameSession(compile_legacy_ruleset_for_semantic_execution(rules))
 nr=compile_native_semantic_rules(session.compiled);payload,_=build_semantic_compile_payload(session.compiled)
 xi=nr.type_ids.index('X');gi=next(i for i,g in enumerate(payload['geometries'])if g['atom_source']is not None and g['atom_source'][0]==xi)
 payload['geometries'][gi]['paths'][0]=copy.deepcopy(entries)
 nr._capsule=nr.backend_module.compile_semantic_rules(payload)
 pos=pack_semantic_search_position(session.compiled,nr,session);before=sem.snapshot(nr,pos)
 actions=sem.guarded_actions(nr,pos)
 assert {sem.unpack_action(a,native_rules=nr)['to']for a in actions}==expected
 for action in actions:
  child=sem.make_checked(nr,pos,action);snapshot=sem.snapshot(nr,child)
  assert snapshot['ply']==1 and snapshot['history_exact'] and snapshot['history_events_exact']
  assert len(snapshot['history'])==2
 assert sem.snapshot(nr,pos)==before
