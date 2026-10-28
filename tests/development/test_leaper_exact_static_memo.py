"""Exact static-memo safety: view lifetime, collision guard, caps and purity."""
import gzip,json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from generic_chess.core.identity import RuntimeHash
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.ai.evaluation.evaluator import Evaluator
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.leaper_exact_static_memo import ExactStaticMemo

@pytest.fixture
def setup():
 p=Path('docs/research/data/leaper_check_extension_20261028/resource/inputs.json.gz')
 c,s=make_session(json.loads(gzip.decompress(p.read_bytes()))['rows'][0]);cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg)
 return c,s,Evaluator(c,profile,cfg)


def test_full_position_guard_survives_forced_hash_collision(setup):
 c,s,base=setup;memo=ExactStaticMemo(c,base);key=RuntimeHash(7,11);rt=SimpleNamespace(runtime_hash=key)
 a=SimpleNamespace(position=s.state.position,_runtime=rt);b=SimpleNamespace(position=replace(a.position,side_to_move=1-a.position.side_to_move),_runtime=rt)
 va=base.evaluate(a);vb=base.evaluate(b)
 assert memo.evaluate(a)==va and memo.evaluate(b)==vb
 assert memo.metrics['misses']==2 and memo.metrics['hash_collision_misses']==1
 assert memo.evaluate(a)==va and memo.metrics['hits']==1 and memo.metrics['raw_evaluator_calls']==2


def test_cache_stores_position_instead_of_mutable_runtime_view(setup):
 c,s,base=setup;rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses);memo=ExactStaticMemo(c,base);parent=rt.position;v=memo.evaluate(rt.state)
 with rt.pushed(s.legal_actions()[0]):assert memo.evaluate(rt.state)==base.evaluate(rt.state)
 rt.assert_balanced();assert rt.position==parent and memo.evaluate(rt.state)==v and memo.metrics['hits']==1
 assert all(type(pos) is type(parent) for bucket in memo.buckets.values() for pos,value in bucket)


def test_capacity_flush_and_nonruntime_bypass(setup):
 c,s,base=setup;memo=ExactStaticMemo(c,base,capacity=1);rt=SimpleNamespace(runtime_hash=RuntimeHash(1,2));a=SimpleNamespace(position=s.state.position,_runtime=rt);b=SimpleNamespace(position=replace(a.position,side_to_move=1-a.position.side_to_move),_runtime=rt)
 memo.evaluate(a);memo.evaluate(b)
 assert memo.entries==memo.metrics['peak_entries']==1 and memo.metrics['flushes']==1
 assert memo.evaluate(s.state)==base.evaluate(s.state) and memo.metrics['bypasses']==1


def test_shadow_detects_an_impure_evaluator_instead_of_silently_reusing(setup,monkeypatch):
 c,s,base=setup;rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses);memo=ExactStaticMemo(c,base,shadow=True);v=memo.evaluate(rt.state)
 monkeypatch.setattr(base,'evaluate',lambda state:v+1)
 with pytest.raises(AssertionError,match='purity'):memo.evaluate(rt.state)
 assert memo.metrics['raw_evaluator_calls']==2


def test_raw_static_reuse_is_history_independent_not_a_terminal_cache(setup):
 c,s,base=setup;rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses);memo=ExactStaticMemo(c,base);v=memo.evaluate(rt.state)
 other=SimpleNamespace(position=rt.position,ply_count=s.state.ply_count+1000,terminal_status='not inspected by static evaluator',_runtime=rt)
 assert memo.evaluate(other)==base.evaluate(other)==v and memo.metrics['hits']==1
 # This test asserts evaluator purity only; real search still adjudicates Core
 # terminal/history before reaching the static cache.
