import gzip,json
from pathlib import Path
import pytest
import generic_chess.native as native
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.research_record import record_value

@pytest.fixture(scope='module')
def module():
 import os
 from scripts.leaper_transient_import_pilot import load_private_native
 private=os.environ.get('GENERIC_CHESS_TRANSIENT_TEST_BINARY')
 if private:load_private_native(private)
 m=native._module()
 if not hasattr(m,'semantic_pack_transient_position'):pytest.skip('prototypeNative build required')
 return m

@pytest.fixture(scope='module')
def roots():
 return json.loads(gzip.decompress(Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz').read_bytes()))['rows']


def test_full_roots_children_readonly_parity_and_input_immutability(module,roots):
 checks=0
 for row in roots:
  c,s=make_session(row);old=NativeSemanticLegalityProvider.try_create(c);new=NativeSemanticLegalityProvider.try_create(c,transient_imports=True)
  assert old and new and not old.transient_imports and new.transient_imports
  rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses)
  def verify():
   nonlocal checks
   pos=rt.position
   for side in (0,1):
    assert old.in_check(pos,side)==new.in_check(pos,side)
   assert old.has_legal_action(pos)==new.has_legal_action(pos)
   assert [x[0] for x in old(pos,rt.ply_count)]==[x[0] for x in new(pos,rt.ply_count)]
   checks+=1
  before=s.to_record();verify()
  for a in rt.legal_actions():
   with rt.pushed(a):verify()
  rt.assert_balanced();assert s.to_record()==before
 assert checks>100


def test_transient_capsules_cannot_gain_persistent_authority(module,roots):
 c,s=make_session(roots[0]);p=NativeSemanticLegalityProvider.try_create(c)
 payload=p._state_only_payload(s.state.position,0)
 temporary=module.semantic_pack_transient_position(p.native_rules.capsule,payload)
 assert isinstance(module.semantic_in_check(p.native_rules.capsule,temporary,0),bool)
 for name in ['semantic_position_key','semantic_position_snapshot','semantic_terminal','semantic_material_summary']:
  with pytest.raises(ValueError):getattr(module,name)(p.native_rules.capsule,temporary)
 with pytest.raises(ValueError):module.semantic_probe_search(p.native_rules.capsule,temporary,1)
 with pytest.raises(ValueError):module.semantic_make_checked(p.native_rules.capsule,temporary,0)
 for key in ('history','history_events'):
  with pytest.raises(ValueError,match='cannot carry history'):module.semantic_pack_transient_position(p.native_rules.capsule,dict(payload,**{key:[]}))


def test_malformed_representation_still_rejected(module,roots):
 from copy import deepcopy
 c,s=make_session(roots[0]);p=NativeSemanticLegalityProvider.try_create(c);payload=p._state_only_payload(s.state.position,0)
 for field,value in [('side',3),('ply',-1),('board',[]),('hands',[])]:
  bad=deepcopy(payload);bad[field]=value
  with pytest.raises(Exception):module.semantic_pack_transient_position(p.native_rules.capsule,bad)
  with pytest.raises(Exception):module.semantic_pack_position(p.native_rules.capsule,bad)


def test_declared_nonplain_rule_falls_back_and_default_stays_off(module,roots):
 from dataclasses import replace
 c,s=make_session(roots[0]);altered=replace(c,support=replace(c.support,pass_enabled=True))
 # Native compiler explicitly rejects pass (compiler.py build contract), so
 # that rule must decline the entire provider rather than invent Native support.
 from generic_chess.native.compiler import compile_native_semantic_rules,NativeUnsupportedRuleError
 with pytest.raises(NativeUnsupportedRuleError,match='pass'):
  compile_native_semantic_rules(altered)
 assert NativeSemanticLegalityProvider.try_create(altered,transient_imports=True) is None
 # A supported Native mixed geometry still uses the original import route.
 from rule_semantics_ir_fixtures import STRESS_GROUPS
 from generic_chess.rules.compiler import compile_semantic_ruleset
 ray=compile_semantic_ruleset(STRESS_GROUPS['cannon']())
 p=NativeSemanticLegalityProvider.try_create(ray,transient_imports=True)
 assert p is not None and not p.transient_imports
 baseline=AlphaBetaPlayer(c,use_disk_cache=False)
 assert not baseline.native_legality_provider.transient_imports


def test_complete_search_and_immediate_cancel_preserve_history_tt_work(module,roots):
 from scripts.leaper_boolean_cost_pilot import signature
 c,s=make_session(roots[0]);before=s.to_record();answers=[]
 for on in (False,True):
  player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True,use_native_transient_imports=on)
  assert player.native_legality_provider.transient_imports==on
  d=player.choose_action(s,SearchLimits(max_depth=3,max_nodes=100000,max_time_seconds=3,quiescence_max_depth=4,quiescence_hard_max_depth=8))
  assert d.completed_depth==3 and d.runtime_depth_balanced and s.to_record()==before
  answers.append(signature(record_value(d)))
 assert answers[0]==answers[1]
 class Cancel:
  def is_cancelled(self):return True
 canceled=[]
 for on in (False,True):
  player=AlphaBetaPlayer(c,use_disk_cache=False,use_native_transient_imports=on)
  d=player.choose_action(s,SearchLimits(max_depth=6,max_nodes=10000,max_time_seconds=3),cancel_token=Cancel())
  assert s.to_record()==before and d.runtime_depth_balanced
  canceled.append(signature(record_value(d)))
 assert canceled[0]==canceled[1]


def test_transient_capsule_copies_input_and_rejects_rule_mismatch(module,roots):
 c,s=make_session(roots[0]);provider=NativeSemanticLegalityProvider.try_create(c)
 payload=provider._state_only_payload(s.state.position,0)
 capsule=module.semantic_pack_transient_position(provider.native_rules.capsule,payload)
 before=module.semantic_transient_legal_actions(provider.native_rules.capsule,capsule)
 payload['board'].clear();payload['hands'].clear()
 assert module.semantic_transient_legal_actions(provider.native_rules.capsule,capsule)==before
 other,_=make_session(roots[2]);q=NativeSemanticLegalityProvider.try_create(other)
 assert other.ruleset_fingerprint!=c.ruleset_fingerprint
 with pytest.raises(ValueError):module.semantic_in_check(q.native_rules.capsule,capsule,0)
 with pytest.raises(ValueError):module.semantic_has_legal_action(q.native_rules.capsule,capsule)
 with pytest.raises(ValueError):module.semantic_transient_legal_actions(q.native_rules.capsule,capsule)


def test_older_native_api_keeps_original_import_path(module,roots):
 c,s=make_session(roots[0]);p=NativeSemanticLegalityProvider.try_create(c)
 class OldAPI:
  def __getattr__(self,name):
   if name=='semantic_pack_transient_position':raise AttributeError(name)
   return getattr(module,name)
 p.native_rules._backend_module=OldAPI()
 q=NativeSemanticLegalityProvider(c,p.engine,p.native_rules,transient_imports=True)
 assert not q.transient_imports
 assert q.in_check(s.state.position,0)==p.in_check(s.state.position,0)
