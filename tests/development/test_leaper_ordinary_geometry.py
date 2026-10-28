"""A footprint guard is not a movement-equivalence contract."""
import runpy
from dataclasses import replace
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry
from scripts.leaper_royal_escape import EmptyRoyalEscape
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.ai.alphabeta.ordering import _quiet_geometry_targets
fixture=runpy.run_path('tests/development/test_leaper_threat_ordering.py')['fixture']

def test_capture_only_footprint_counterexample_rejected_by_new_consumer():
    c,s=fixture(enemy=False);bad=replace(c,ir=replace(c.ir,patterns=tuple(p for p in c.ir.patterns if p.target.kind!='target_empty')))
    assert _plain_leaper_hash_patterns(bad) is not None
    assert _quiet_geometry_targets(bad) is not None
    assert ordinary_leap_geometry(bad) is None
    assert EmptyRoyalEscape(bad).witness(s.state.position) is None
    assert not semantic_engine_for(bad).legal_actions(s.state.position)

def test_supported_geometry_and_empty_escape_match_Core():
    c,s=fixture(enemy=False);assert ordinary_leap_geometry(c) is not None
    w=EmptyRoyalEscape(c).witness(s.state.position);assert w is not None
    assert any(a.source==w['source'] and a.target==w['target'] for a in semantic_engine_for(c).legal_actions(s.state.position))

def test_anchor_metadata_support_mismatch_rejected():
    c,s=fixture();bad=replace(c,_legacy_compiled=replace(c._legacy_compiled,piece_types=tuple(replace(t,is_anchor=False) if t.type_id=='K' else t for t in c.piece_types)))
    # types_by_id is separately retained by legacy product: rebuild the declared map too.
    bad=replace(bad,_legacy_compiled=replace(bad._legacy_compiled,types_by_id={t.type_id:t for t in bad.piece_types}))
    assert ordinary_leap_geometry(bad) is None

def test_semantic_support_drop_permission_not_hidden_by_inspection_metadata():
    c,s=fixture();masks=dict(c.support.drop_allowed);tid=next(iter(masks));owners=[list(xs) for xs in masks[tid]];owners[0][0]=True;masks[tid]=tuple(tuple(xs) for xs in owners);bad=replace(c,support=replace(c.support,drop_allowed=masks))
    # Some fields are direct support properties; drop masks retain the legacy
    # inspection forwarding. The research consumer checks actual support too.
    assert ordinary_leap_geometry(bad) is None

def test_semantic_support_promotion_mask_is_outside_ordinary_research_domain():
    c,s=fixture();bad=replace(c,support=replace(c.support,promotion_allowed={'W':(frozenset({(0,1)}),frozenset())}));assert ordinary_leap_geometry(bad) is None
