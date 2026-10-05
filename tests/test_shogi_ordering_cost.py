import hashlib,json
from pathlib import Path
from fractions import Fraction as F
import pytest
from generic_chess.core.pieces import Piece
from scripts.shogi_ordering_inventory import OrderingInventory
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

def test_capture_hint_preserves_current_board_and_base_hand():
    e=OrderingInventory({'P':F(1,4),'TP':F(3,4),'R':F(1)})
    assert e.capture_order_value(Piece(0,'R','R'),Piece(1,'P','TP',True))==75000
    assert e.capture_order_value(Piece(0,'K','K'),Piece(1,'R','R'))==200000
    with pytest.raises(ValueError):e.capture_order_value(Piece(0,'P','P'),Piece(1,'K','K'))

def test_full_result_and_accounted_cost_without_control_rerun():
    old=json.loads((DATA/'shogi_static_search_20261006.json').read_text())['searches'][0]
    r=json.loads((DATA/'shogi_ordering_qualified_20261006.json').read_text());row=r['searches'][0]
    failed=json.loads((DATA/'shogi_ordering_cost_20261006.json').read_text())
    assert failed['runtime_pushes']==failed['candidates']==failed['returned_actions']==0 and not failed['complete']
    assert r['complete'] and len(r['searches'])==1 and row['score']==old['score'] and row['ties']==old['ties'] and row['selected'] in old['ties']
    assert row['statistics']['nodes']==27 and row['statistics']['ordering_calls']==7
    assert r['runtime_pushes']==r['runtime_pops']==25 and r['paired_pushes']==74 and r['conservative_enumeration_charge']==1431
    assert r['cumulative_seconds']<15 and r['public_transitions']==r['source_queries']==0
    assert row['reason']=='completed_depth' and row['statistics']['qnodes']==0 and not row['statistics']['root_scan_used_fallback']
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
