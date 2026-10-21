"""Research-only bounded memoization of exact board/side hash tokens."""
from functools import lru_cache
from generic_chess.core import search_runtime as rt
class BoardTokenCache:
 def __init__(self,capacity=4096):
  self.original=rt._component_token;self.calls=0;self.fallbacks=0
  @lru_cache(maxsize=capacity,typed=True)
  def board(index,owner,base,current,promoted):
   return self.original(('board',index),(owner,base,current,promoted))
  @lru_cache(maxsize=capacity,typed=True)
  def empty(index):return self.original(('board',index),None)
  @lru_cache(maxsize=4,typed=True)
  def side(value):return self.original(('side',),value)
  self.board,self.empty,self.side=board,empty,side
 def __call__(self,address,value):
  self.calls+=1
  if type(address) is tuple and len(address)==2 and address[0]=='board' and type(address[1]) is int:
   if value is None:return self.empty(address[1])
   if type(value) is tuple and len(value)==4 and type(value[0]) in (int,bool) and type(value[1]) is str and type(value[2]) is str and type(value[3]) is bool:
    return self.board(address[1],*value)
  if address==('side',) and type(value) in (int,bool):return self.side(value)
  self.fallbacks+=1;return self.original(address,value)
 def install(self):rt._component_token=self
 def restore(self):rt._component_token=self.original
 def counts(self):
  return dict(calls=self.calls,fallbacks=self.fallbacks,board=self.board.cache_info()._asdict(),empty=self.empty.cache_info()._asdict(),side=self.side.cache_info()._asdict())
