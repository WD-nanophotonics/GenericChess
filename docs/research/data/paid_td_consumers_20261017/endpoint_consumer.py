import os
"""Actual92 weights/full-record Native serving control; no AUX imports or trainer."""
from pathlib import Path
from copy import copy
from math import tanh
import json,sys,time,hashlib
R=Path.cwd();STOP_ROOT=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R))).resolve();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.core.transition import apply_action,legal_actions
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value
D=R/'.local_agent/paid-td-20261017';P=json.loads((D/'endpoint-plan.json').read_bytes());start=time.perf_counter();rows=[];visits=0;compiled={};kernels={};source=D/'exact/results/dev_aux/task2525'
def poll():
 if time.perf_counter()-start>=P['limits']['global_seconds']or visits>=P['limits']['core_visits']:raise TimeoutError('FROZEN_COMPONENT_CAP')
 for n in ('rollout','advisor','slack'):
  f=json.loads((STOP_ROOT/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('stopped')and not f.get('user_paused'),'EXPLICIT_STOP'
def features(state,channels):
 return [sum((1 if p.owner==0 else -1)for p in state.position.board if p and p.current_type_id==t)if kind=='board'else state.position.hands[0].count(t)-state.position.hands[1].count(t)for kind,t in channels]
def digest(x):return hashlib.sha256(json.dumps(record_value(x),sort_keys=True,separators=(',',':')).encode()).hexdigest()
for item in json.loads((D/'endpoint-inputs.json').read_bytes())['rows']:
 poll();gs=item['rule'];q=item['query'];channels=item['channels'];weights=q['weights']
 if gs not in compiled:
  compiled[gs]=compile_ruleset(ruleset_from_dict(json.loads((source/f'rules-{gs}.json').read_bytes())));kernels[gs]=compile_native_semantic_rules(compiled[gs])
 c=compiled[gs];s=GameSession.replay(c,deserialize_game_record(json.dumps(q['record_before'])));before=(s.state,s.to_record(),s.history,s._search_witnesses);board={t:0. for t in {x[1]for x in channels}|{"K"}};hand=dict(board)
 for (kind,t),w in zip(channels,weights):(board if kind=='board'else hand)[t]=w
 cp=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,evaluation_profile_version='actual92-raw-material-control',board_weights=board,hand_weights=hand,material_scale=256,value_scale=10.,reference_median=1.);clone=LearnableMaterialCheckpoint.from_dict(json.loads(json.dumps(cp.to_dict())));assert clone.board_weights==board and clone.hand_weights==hand
 n0=visits
 def solve(st,depth,relative):
  global visits
  poll();visits+=1;term=st.terminal_status
  if term.is_terminal:
   z=0 if term.winner is None else 1 if term.winner==0 else -1;return (1e6*z,(100000000-relative)*z)
  if depth==0:
   phi=features(st,channels);return(sum(x*w for x,w in zip(phi,weights)),sum(x*round(w*256)for x,w in zip(phi,weights)))
  values=[solve(apply_action(st,a,c),depth-1,relative+1)for a in legal_actions(st,c)];assert values;fn=max if st.position.side_to_move==0 else min;return tuple(fn(v[j]for v in values)for j in (0,1))
 actions=s.legal_actions();values=[solve(apply_action(s.state,a,c),1,1)for a in actions];fn=max if s.state.position.side_to_move==0 else min;best=[fn(v[j]for v in values)for j in (0,1)];floatopts=[a for a,v in zip(actions,values)if abs(v[0]-best[0])<1e-9];quantopts=[a for a,v in zip(actions,values)if v[1]==best[1]];assert abs(best[0]-q['value'])<1e-9
 t=time.perf_counter();e=SemanticSearchEngine(c,kernels[gs],checkpoint=cp,tt_megabytes=0);res=e.search(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),root_window_pruning=False);seconds=time.perf_counter()-t;assert before==(s.state,s.to_record(),s.history,s._search_witnesses)
 assert res.completed_depth==2 and not res.used_fallback and res.action in actions
 actual=res.score*(1 if s.state.position.side_to_move==0 else -1);assert actual==best[1]and res.action in quantopts
 leaf=copy(s)
 for a in res.decision_line:
  if isinstance(a,str):leaf.declare(a)
  else:leaf.submit(a)
 term=leaf.result.status.value!='ongoing';phi=features(leaf.state,channels)
 pred=(0. if leaf.result.winner is None else 1. if leaf.result.winner==0 else -1.)if term else tanh(sum(x*w for x,w in zip(phi,weights))/10.)
 gradient=[0.]*6 if term else[(0. if j==0 and item['method']=='fixed5'else x*(1-pred*pred)/10.)for j,x in enumerate(phi)]
 sourceafter=deserialize_game_record(json.dumps(q['record_after']));same_action=res.action==sourceafter.actions[-1];diff=None
 rows.append(dict(rule=gs,method=item['method'],seed=item['seed'],threshold=None,source_query_sha256=hashlib.sha256(json.dumps(q,sort_keys=True).encode()).hexdigest(),checkpoint=cp.to_dict(),checkpoint_id=cp.checkpoint_id,root_state_sha256=digest(s.state),source_float_best=best[0],native_quantized_best=best[1],native_action=record_value(res.action),native_float_optimal=res.action in floatopts,native_quantized_optimal=True,same_source_action=same_action,source_prediction=tanh(q['value']/10),native_leaf_float_prediction=pred,prediction_abs_difference=abs(pred-tanh(q['value']/10)),gradient_max_abs_difference=diff,source_phi=None,native_phi=phi,source_terminal=None,native_terminal=term,native_leaf_state_sha256=digest(leaf.state),native_decision_line=record_value(res.decision_line),completed_depth=res.completed_depth,native_nodes=res.nodes,core_visits=visits-n0,caller_seconds=seconds,source_record_unchanged=True,native_gradient=gradient,source_gradient_available=False,source_float_regret=abs(best[0]-values[actions.index(res.action)][0]),color=item['color'],foe=item['foe'],family=item['family']))
assert len(rows)==128 and not any(k.startswith('results.dev_aux')for k in sys.modules)
result=dict(status='COMPLETE_ACTUAL92_ENDPOINT_NATIVE_FIDELITY',rows=rows,calls=128,core_visits=visits,all_quantized_optimal=True,outside_float_optimum=sum(not x['native_float_optimal']for x in rows),same_source_action_objects=sum(x['same_source_action']for x in rows),different_gradients=None,max_gradient_difference=None,max_prediction_difference=max(x['prediction_abs_difference']for x in rows),seconds=time.perf_counter()-start,scope='ALL128firstactualendpointEVALcandidateinputs/fullhistory/actualfrozenweights, currentPRIMARYCoreandNative consumer, noAUXimports/trainer/fitness/defaultactivation. Native1e8relative-mate versus source1e6constant checkedseparately; originalsourcefloatoptima criterion retained. OriginalEVALdoesnotrecordPVphi/gradient: referenceabsentNOTzero; Nativeactualleafgradientderivedonly. No identicalonlineTDclaim. Perf_counteraccuratecallerclock; wholeincludesindependentCore.')
write_json(D/'endpoint-result.json',result);print(json.dumps({k:v for k,v in result.items()if k!='rows'}),flush=True)
