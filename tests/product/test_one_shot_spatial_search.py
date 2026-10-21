"""Regression for one-shot search rejecting the complete owner spatial axis."""
import pytest
from generic_chess.native import native_available
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import semantic_iterative_search, snapshot
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
pytestmark=pytest.mark.skipif(not native_available(),reason='native extension unavailable')

@pytest.mark.parametrize('mapping',[False,True])
def test_one_shot_spatial_owner_axes_reach_nonzero_search(mapping):
    compiled=compile_semantic_ruleset(build_western_chess_ruleset())
    native=compile_native_semantic_rules(compiled);session=GameSession(compiled)
    packed=pack_semantic_search_position(compiled,native,session);before=snapshot(native,packed)
    rows={f'{owner}:{tid}':[0]*9 for owner in (0,1) for tid in native.type_ids}
    rows['0:P'][0]=17;rows['0:P'][8]=-17
    rows['1:Q'][7]=11;rows['1:Q'][1]=-11
    vector=tuple(v for owner in (0,1) for tid in native.type_ids for v in rows[f'{owner}:{tid}'])
    values=rows if mapping else vector;zero={tid:0 for tid in native.type_ids}
    baseline=semantic_iterative_search(native,packed,1,board_values=zero,hand_values=zero)
    actual=semantic_iterative_search(native,packed,1,board_values=zero,hand_values=zero,spatial_occupancy_values=values)
    expected=SemanticSearchEngine(compiled,native,board_values=zero,hand_values=zero,spatial_occupancy_values=vector,evaluator_scale=1,tt_megabytes=0).search(session,SearchLimits(max_depth=1,quiescence_max_depth=0))
    assert actual['completed_depth']==expected.completed_depth==1
    assert actual['score']==expected.score and actual['score']!=baseline['score']
    assert actual['principal_variation'] and expected.action in session.legal_actions()
    assert actual['evaluator_config_hash'] != baseline['evaluator_config_hash']
    assert snapshot(native,packed)==before
    with pytest.raises(ValueError,match=r'2 \* type_count \* 9'):
        semantic_iterative_search(native,packed,1,spatial_occupancy_values=vector[:len(vector)//2])