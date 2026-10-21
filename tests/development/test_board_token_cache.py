"""Exact hash-token type boundaries and cache eviction controls."""
from scripts.board_token_cache import BoardTokenCache
from generic_chess.core import search_runtime as rt
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from scripts.search_backend_comparison import CASES,CoreBoard
import pytest

def test_typed_hash_tokens_do_not_collapse_boolean_and_integer_owners():
 cache=BoardTokenCache(capacity=1);original=rt._component_token
 values=[None,(True,'P','P',False),(1,'P','P',False),(0,'P','Q',True),(0,'P','Q',1)]
 expected=[original(('board',1),value) for value in values]
 assert expected[1]!=expected[2] and expected[3]!=expected[4]
 for _ in range(2):
  assert [cache(('board',1),value) for value in values]==expected
 assert cache(('side',),True)!=cache(('side',),1)
 assert cache(('aux',('x',-1)),True)==original(('aux',('x',-1)),True)
 assert cache(('aux',('x',-1)),1)==original(('aux',('x',-1)),1)
 assert cache.board.cache_info().currsize<=1

@pytest.mark.parametrize('case_id',['chess-ep','chess-promotion','shogi-promotion','shogi-drop'])
def test_full_runtime_hash_and_incremental_child_hash_survive_cache_eviction(case_id):
 case=next(x for x in CASES if x['id']==case_id)
 c=compile_ruleset_for_execution(build_builtin_ruleset('western_chess' if case['game']=='chess' else 'standard_shogi'))
 core=CoreBoard(case,c);runtime=core.runtime;cache=BoardTokenCache(capacity=1);original=rt._component_token
 root=runtime.position;expected=rt._full_runtime_hash(root,c)
 cache.install()
 try:
  assert rt._full_runtime_hash(root,c)==expected
  for action in runtime.legal_actions()[:16]:
   runtime.push(action)
   try:
    observed=runtime.runtime_hash
    rt._component_token=original
    exact=rt._full_runtime_hash(runtime.position,c)
    rt._component_token=cache
    assert observed==exact
   finally:runtime.pop()
  assert runtime.position==root and runtime.runtime_hash==expected
  runtime.assert_balanced()
 finally:cache.restore()
 assert rt._component_token is original


def test_production_tokens_match_original_serialization_after_bounded_eviction():
    # The oracle stays the original JSON/blake2 implementation, not another
    # cached full-hash traversal. Every field and primitive type is retained.
    for value in [None,(True,'P','Q',False),(1,'P','Q',False),(0,'P','Q',True),(0,'P','Q',1)]:
        assert rt._component_token(('board',3),value)==rt._uncached_component_token(('board',3),value)
    for value in [True,1,False,0]:
        assert rt._component_token(('side',),value)==rt._uncached_component_token(('side',),value)
    for value in [True,1,('x',True),('x',1)]:
        assert rt._component_token(('aux',('flag',-1)),value)==rt._uncached_component_token(('aux',('flag',-1)),value)
    first=(0,'P','P',False);expected=rt._uncached_component_token(('board',0),first)
    for index in range(4100):
        value=(index%2,'T'+str(index),'T'+str(index),False)
        assert rt._component_token(('board',index%64),value)==rt._uncached_component_token(('board',index%64),value)
    assert rt._board_component_token.cache_info().currsize<=4096
    assert rt._component_token(('board',0),first)==expected
