from types import SimpleNamespace
import pytest
from scripts import leaper_design as L
from scripts.leaper_eval_cache_feasibility import replay_cost,frozen_profile
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.evaluator import Evaluator

@pytest.fixture
def inputs():
 c=L.compile_rule(L.definition(1,8));s=L.GameSession(c);p=AlphaBetaPlayer(c,use_disk_cache=False);a=s.state.position;s.submit(s.legal_actions()[0]);b=s.state.position;e=Evaluator(c,frozen_profile(p._profile),p._config);positions=[a,b];seq=[0,0,1,0];requests=[dict(id=i,raw=e.evaluate(SimpleNamespace(position=positions[i])))for i in seq];return p,e,positions,requests

def test_actual_raw_evaluator_replay_and_finite_eviction(inputs):
 p,e,pos,req=inputs;raw=replay_cost(e,pos,req,1,False);cached=replay_cost(e,pos,req,1,True)
 assert raw['computed']==4 and raw['peak_entries']==0 and raw['hits']==0
 assert cached['computed']==3 and cached['hits']==1 and cached['evictions']==2 and cached['peak_entries']==1

def test_profile_maps_are_copied_and_immutable(inputs):
 p,e,pos,req=inputs;before=e._profile.board_value_by_type['A'];p._profile.board_value_by_type['A']+=7
 assert e._profile.board_value_by_type['A']==before
 with pytest.raises(TypeError):e._profile.board_value_by_type['A']=before+1

def test_raw_integer_corruption_is_not_hidden_by_clipping(inputs):
 p,e,pos,req=inputs;req[0]['raw']+=1
 with pytest.raises(AssertionError,match='raw integer'):replay_cost(e,pos,req,1,True)
