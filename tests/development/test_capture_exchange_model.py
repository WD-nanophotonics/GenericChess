"""Material surrogate contracts only;not chess prices or gameWDL."""
from functools import lru_cache
from itertools import product
from scripts.leaper_capture_exchange import material_exchange


def exact(victim,mover,own,enemy):
 @lru_cache(None)
 def continuation(on_target,us,them):
  return max([0]+[on_target-continuation(cost,them,us[:i]+us[i+1:]) for i,cost in enumerate(us)])
 return victim-continuation(mover,tuple(enemy),tuple(own))


def test_greedy_model_against_all_order_material_choices_in_small_complete_domain():
 lists=[()]+[(x,) for x in (0,1,4)]+list(product((0,1,4),repeat=2))
 for v,m in product((0,1,4),repeat=2):
  for own,enemy in product(lists,repeat=2):
   assert material_exchange(v,m,own,enemy)==exact(v,m,own,enemy)


def test_units_scale_and_optional_free_capture():
 assert material_exchange(10,100,[],[])==10
 assert material_exchange(10,100,[],[1])==-90
 for own,enemy in [([1],[9,1]),([3,5],[2]),([],[0])]:
  a=material_exchange(7,4,own,enemy)
  assert material_exchange(21,12,[3*x for x in own],[3*x for x in enemy])==3*a


def test_legal_royal_reply_is_not_ignored_or_given_material_price_zero():
 assert material_exchange(980,1000,[],[],(False,True))==-20
 assert material_exchange(1015,1000,[],[980],(False,True))==15


def test_defended_target_prevents_static_royal_recapture():
 assert material_exchange(980,1000,[50],[],(False,True))==980
 assert material_exchange(980,1000,[],[],(True,True))==980
