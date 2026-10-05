"""Replay saved state/effect evidence without repeating observed transitions."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/research/data'

def test_frozen_failed_and_bound_reports():
    failed=json.loads((DATA/'chess_pawn_aux_route_20261005.json').read_text())
    good=json.loads((DATA/'chess_pawn_aux_route_bound_20261005.json').read_text())
    assert not failed['complete'] and failed['enumerated']==failed['virtual_materializations']==0
    assert 'CompiledAuxSlot' in failed['error']
    assert good['complete'] and good['virtual_materializations']==10 and good['enumerated']==112
    assert good['seconds']+failed['seconds']<15
    for report in (failed,good):
        for name,pin in report['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin

def test_aux_lifecycle_and_origin_in_both_owner_paths():
    good=json.loads((DATA/'chess_pawn_aux_route_bound_20261005.json').read_text())
    for owner in (0,1):
        rows=[r for r in good['rows'] if r['owner']==owner]
        assert len(rows)==5
        for i,row in enumerate(rows):
            after=row['after'];tokens={tuple(k):v for k,v in after['aux_state']}
            assert tokens[2,-1]==([3,5 if owner else 2] if i==0 else None)
            assert all(v==0 for k,v in tokens.items() if k!=(2,-1))
            piece=after['board'][row['selected']['target']]
            assert piece['base_type_id']=='P' and piece['owner']==owner
            assert piece['current_type_id']==('Q' if i==4 else 'P')
            assert after['side_to_move']==1-owner
            assert not any('en_passant' in str(a) and a['source']==row['selected']['source'] for a in row['actions'])

def test_refined_pawn_interval_retains_double_mass():
    from fractions import Fraction as F
    from scripts.native_chess_contact_intervals import native_contact_intervals
    for law,m in (('geometric_half',lambda t:F(1,2)**t),('linear_mixture',lambda t:F(2,(t+1)*(t+2)))):
        q=(87696*m(1)+162048*m(2)+240*m(3))/249984
        upper=(6076*m(1)+(5124+840+2808+2450+3304+1586)*m(2)+170844*m(3))/249984
        assert native_contact_intervals(law)['board','P'][1]==upper/q
