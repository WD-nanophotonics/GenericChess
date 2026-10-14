from pathlib import Path
import sys,json,sysconfig,importlib.util,hashlib
ROOT=Path.cwd();sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tests/product')]
from test_completed_root_win import prepared,proves_root_h3
from generic_chess.ai.alphabeta import search as sm
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as Provider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value,write_record
from types import SimpleNamespace
b=ROOT/'.local_agent/root-transfer-20261014';binary=b/('payload-v2/_payload_probe_v2'+sysconfig.get_config_var('EXT_SUFFIX'));spec=importlib.util.spec_from_file_location('_payload_probe_v2',binary);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
old_payload=Provider._state_only_payload;old_check=sm._Budget.check;rows=[]
def c_payload(self,pos,ply):return mod.payload(pos,self.type_map,len(self.type_ids),ply)
try:
 for arm in ('Python','privateC_V2'):
  Provider._state_only_payload=old_payload if arm=='Python' else c_payload
  s=prepared();before=s.state,s.to_record(),s._search_witnesses;token=CancellationToken()
  def cancel(self,stats,*,force=False):
   if stats.nodes+stats.qnodes>=99:token.cancel()
   return old_check(self,stats,force=force)
  sm._Budget.check=cancel
  p=AlphaBetaPlayer(s.compiled,use_disk_cache=False,use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
  d=p.choose_action(s,SearchLimits(max_depth=2,max_time_seconds=5,quiescence_max_depth=2),cancel_token=token)
  assert d.termination_reason=='cancelled' and d.result_source=='completed_root_win' and d.completed_depth==1 and d.score==999999997 and proves_root_h3(s,d.action)
  assert before==(s.state,s.to_record(),s._search_witnesses) and d.runtime_depth_balanced and d.native_legality_calls>0
  rows.append(dict(arm=arm,decision=record_value(d),history_unchanged=True,h3=True))
  sm._Budget.check=old_check
 # Required malformed payload and postquery cancellation stay explicit errors,
 # never a false boolean or a stale input handoff.
 errors=[]
 for arm in ('Python','privateC_V2'):
  Provider._state_only_payload=old_payload if arm=='Python' else c_payload;s=prepared();p=Provider.try_create(s.compiled,strict=True);assert p is not None
  board=list(s.state.position.board);idx=next(i for i,x in enumerate(board) if x is not None);piece=board[idx]
  board[idx]=SimpleNamespace(owner=7,base_type_id=piece.base_type_id,current_type_id=piece.current_type_id,promoted=piece.promoted)
  pos=SimpleNamespace(board=tuple(board),hands=s.state.position.hands,side_to_move=s.state.position.side_to_move,aux_state=s.state.position.aux_state,ruleset_fingerprint=s.compiled.ruleset_fingerprint)
  try:p.in_check(pos,0);raise AssertionError('invalid owner accepted')
  except ValueError as e:assert str(e)=='Native legality payload has an invalid owner';invalid=str(e)
  assert p._metrics_local.check_handoff is None
  polls=[0]
  def poll():
   polls[0]+=1
   if polls[0]==2:raise RuntimeError('actual postquery cancellation')
  try:p.in_check(s.state.position,0,checkpoint=poll);raise AssertionError('required cancellation swallowed')
  except RuntimeError as e:assert str(e)=='actual postquery cancellation'
  assert p._metrics_local.check_handoff is None
  assert isinstance(p.has_legal_action(s.state.position),bool) and p.availability_metrics['imports']==1
  errors.append(dict(arm=arm,invalid_owner_error=invalid,postquery_polls=polls[0],pending_handoff_empty=True,retry_fresh_imports=1))
finally:Provider._state_only_payload=old_payload;sm._Budget.check=old_check
write_record(ROOT/'docs/archive/root_transfer_20261014/payload_stop_supplement.json',dict(searches=rows,primitive_errors=errors,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((b/'payload-v2/payload_probe.c').read_bytes()).hexdigest(),scope='Late2 actual NativeAll cancellation searches plus required-error/read-only input retry controls. Separate supplement; original74member ZIP immutable. No claim of cancellation inside a bounded C payload call or production integration.'))
print('2 actual cancelled NativeAll searches retain full proof/history; both malformed/postquery errors explicit and retries fresh.')

