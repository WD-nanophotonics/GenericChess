from pathlib import Path
import json,sys,time,os
R=Path.cwd();sys.path[:0]=[str(R),str(R/'tests'),str(R/'tests/product')]
from tools.local_agent.common import STATE,write_json,read_json
from test_repeated_cycle_aux_defaults import fixture,advance
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.session.session import GameSession
from generic_chess.core.transition import legal_actions,apply_action
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value
STOP_ROOT=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R))).resolve();D=Path(os.environ.get('GC_NEUTRALITY_DATA_DIR',str(STATE/'rule-neutrality-20261017'))).resolve();start=time.perf_counter();write_json(D/'aux-plan.json',dict(question='Is missing legacy movement metadata a mapping-only boundary or does it also block explicit checkpoints with complete auxiliary history?',inputs='Existing repeated-cycle sparse/default auxiliary fixture at its actual4-ply imported state; no synthetic history, allstate retained.',limits=dict(seconds=120,native_calls=2,core_visits=10000),decision='Keep clear mapping/default-profile refusal ifmetadata absent; explicit serving may work or honestlyrefuse, neither shrinks genericdomain. Existingkings-onlyfixture is deliberately NOT informative material utility.'))
c,s=fixture();advance(s);assert not hasattr(c,'piece_types')and c._legacy_compiled is None
try:build_ruleset_profile(c,EvaluationConfig());raise AssertionError('must refuse absent legacy descriptor')
except ValueError as exc:refusal=str(exc)
profile,scope=build_semantic_opportunity_profile(c,EvaluationConfig());before=record_value(dict(state=s.state,record=s.to_record(),history=s.history,witnesses=s._search_witnesses));rows=[];visits=0
n=compile_native_semantic_rules(c)
for sign in (1,-1):
 cp=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,evaluation_profile_version='scoped-aux-serving-control',board_weights={'K':0,'R':sign,'TP':sign*2},hand_weights={'K':0,'R':sign*.5,'TP':sign},material_scale=256,value_scale=10,reference_median=1)
 cp.validate_ruleset(c);clone=LearnableMaterialCheckpoint.from_dict(cp.to_dict());assert clone==cp
 def val(st,d,ply):
  global visits
  visits+=1;assert visits<=10000 and time.perf_counter()-start<120
  term=st.terminal_status
  if term.is_terminal:return 0 if term.winner is None else (100000000-ply)*(1 if term.winner==0 else -1)
  if d==0:
   p=st.position;return sum((1 if x.owner==0 else -1)*round(cp.board_weights[x.current_type_id]*256)for x in p.board if x)+sum((1 if o==0 else -1)*k*round(cp.hand_weights[t]*256)for o,h in enumerate(p.hands)for t,k in h.counts)
  vv=[val(apply_action(st,a,c),d-1,ply+1)for a in legal_actions(st,c)];return(max if st.position.side_to_move==0 else min)(vv)
 aa=s.legal_actions();vv=[val(apply_action(s.state,a,c),1,1)for a in aa];best=(max if s.state.position.side_to_move==0 else min)(vv);opts=[a for a,v in zip(aa,vv)if v==best]
 out=SemanticSearchEngine(c,n,checkpoint=cp,tt_megabytes=0).search(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=5,quiescence_max_depth=0),root_window_pruning=False)
 assert out.completed_depth==2 and not out.used_fallback and out.score*(1 if s.state.position.side_to_move==0 else -1)==best and out.action in opts
 assert before==record_value(dict(state=s.state,record=s.to_record(),history=s.history,witnesses=s._search_witnesses))
 fresh=GameSession.replay(c,s.to_record());assert fresh.state==s.state and fresh._search_witnesses==s._search_witnesses
 rows.append(dict(sign=sign,score=out.score,action=record_value(out.action),pv=record_value(out.decision_line),completed_depth=out.completed_depth,nodes=out.nodes,checkpoint=cp.to_dict()))
write_json(D/'aux-result.json',dict(status='PASS_EXPLICIT_SERVING_AND_CLEAR_DEFAULT_BOUNDARY',default_refusal=refusal,complete_input=before,semantic_candidate_scope=scope,rows=rows,core_visits=visits,seconds=time.perf_counter()-start,scope='Actual4-ply sparse/default auxiliary/repeatedcycle state;2rawsignedCP consumer checks,0truncate/defaultmetadata fallback. Kings-only materialcounts allzero: no usefulprice/causalvalueclaim; semanticopportunity candidate excludesstateeffects and is NOTdrop-in rawA mapping.'))
print('AUX_PASS',visits,'Corevisits',round(time.perf_counter()-start,3),'seconds')
