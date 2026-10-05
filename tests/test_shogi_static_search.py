import hashlib,json
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
import pytest
from scripts.shogi_static_inventory import StaticInventory,quantize,SCALE
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.audit_shogi_static_search import full_reference
from scripts.research_state_replay import read_game_state
from generic_chess.core.position import Hands
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

def test_fixed_rounding_error_and_static_sign_custody():
    for x in (F(0),F(1),F(1,200000),F(3,200000),F(2,7),F(1,3)):
        assert abs(F(quantize(x),SCALE)-x)<=F(1,2*SCALE)
    assert quantize(F(1,200000))==1
    with pytest.raises(ValueError):quantize(F(-1,10))
    raw=json.loads((DATA/'shogi_promotion_use_20261005.json').read_text());state=read_game_state(raw['root'])
    evaluator=StaticInventory({'P':F(1,4),'TP':F(3,4),'R':F(1)})
    assert evaluator.evaluate(state)==-75000
    assert evaluator.evaluate(replace(state,position=replace(state.position,side_to_move=1)))==75000
    bad=replace(state,position=replace(state.position,hands=(Hands((('TP',1),)),Hands())))
    with pytest.raises(ValueError):evaluator.evaluate(bad)

def test_actual_runtime_matches_complete_saved_reference_and_full_ties():
    r=json.loads((DATA/'shogi_static_search_20261006.json').read_text());raw=json.loads((DATA/'shogi_promotion_use_20261005.json').read_text())
    assert r['complete'] and r['runtime_pushes']==r['runtime_pops']==94
    assert r['candidates']==220 and r['returned_actions']==910 and r['public_transitions']==r['source_queries']==0
    means=exact_board_means('geometric_half');weights={t:means[t]/means['TR'] for t in ('P','TP','R')}
    for row in r['searches']:
        e=StaticInventory(weights if row['law']=='geometric_half' else {t:F(1) for t in weights})
        best,ties,values=full_reference(raw,e)
        assert row['reference_score']==row['score']==best and row['ties']==ties
        assert row['selected'] in ties and row['branch_minima']==values
        assert row['statistics']['completed_depth']==2 and row['statistics']['qnodes']==0
        assert row['reason']=='completed_depth' and not row['statistics']['root_scan_used_fallback']
        assert len(row['visited'])==row['statistics']['runtime_pushes']
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
