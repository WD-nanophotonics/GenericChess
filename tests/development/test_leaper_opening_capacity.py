"""General capacity, unlike parity special case, admits mixed Leap movement."""
from dataclasses import replace
from test_leaper_opening_structure import build
from scripts.leaper_opening_capacity import opening_escape_capacity
from scripts.leaper_opening_structure import structural_opening_witness
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns

def verify_all(c,s,w):
    assert w['status']=='SUFFICIENT_ONE_PLY_REPLY';before=s.to_record()
    for a in s.legal_actions():
        child=type(s).replay(c,before);child.submit(a);assert not child.state.terminal_status.is_terminal
        target=next(x['defender_empty_escape'] for x in w['witnesses'] if x['source']==a.from_square.rank*8+a.from_square.file and x['target']==a.to_square.rank*8+a.to_square.file)
        assert any(x.from_square.rank*8+x.from_square.file==next(i for i,p in enumerate(child.state.position.board) if p is not None and p.owner==1 and c.types_by_id[p.current_type_id].is_anchor) and x.to_square.rank*8+x.to_square.file==target for x in child.legal_actions())

def test_mixed_parity_can_pass_general_capacity_without_loosening_Core_contract():
    c,s=build(mixed=True,far=True);assert structural_opening_witness(s.state,c)['status']=='UNKNOWN';verify_all(c,s,opening_escape_capacity(s.state,c))

def test_general_capacity_rejects_actual_mixed_parity_mate_counterexample():
    c,s=build(mixed=True);assert opening_escape_capacity(s.state,c)['status']=='UNKNOWN'

def test_history_clock_and_support_changes_are_not_geometry_proofs():
    c,s=build();assert opening_escape_capacity(replace(s.state,history=()),c)['status']=='UNKNOWN'
    cc,ss=build(maxply=1);assert opening_escape_capacity(ss.state,cc)['status']=='UNKNOWN'
    bad=replace(c,support=replace(c.support,pass_enabled=True))
    # CompiledSemanticRuleset.pass_enabled explicitly delegates to support
    # (ir.py), so the existing footprint guard ALREADY rejects this mutation.
    assert bad.pass_enabled is True
    assert _plain_leaper_hash_patterns(bad) is None and ordinary_leap_geometry(bad) is None

def test_parity_control_also_passes_general_capacity_actual_Core_reply_check():
    c,s=build();verify_all(c,s,opening_escape_capacity(s.state,c))
