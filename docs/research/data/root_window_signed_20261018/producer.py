"""Bounded signed checkpoint mode control. Core reference, raw paid receipts first."""
from pathlib import Path
from copy import copy
import json,sys,time,hashlib
from collections import Counter
R=Path.cwd();sys.path.insert(0,str(R))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.transition import apply_action,legal_actions
D=Path(__file__).resolve().parent;P=json.loads((D/'plan.json').read_bytes());I=json.loads((D/'inputs.json').read_bytes());start=time.perf_counter();counts=Counter();refs=[];status='COMPLETE';error=None
assert not(D/'queries.jsonl').exists()
compiled={int(gs):compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(r))for gs,r in I['rules'].items()};native={gs:compile_native_semantic_rules(c)for gs,c in compiled.items()}
def digest(v):return hashlib.sha256(json.dumps(record_value(v),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def poll():
 assert time.perf_counter()-start<P['global_seconds']and counts['core_visits']<P['core_visit_cap'],'FROZEN_COMPONENT_CAP'
 for n in('rollout','advisor','slack'):
  f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not(f.get('stopped')or f.get('user_paused')),'EXPLICIT_STOP'
try:
 with(D/'queries.jsonl').open('x',encoding='utf8')as log:
  for row in I['rows']:
   poll();item=row['item'];idx=row['source_index'];c=compiled[item['rule']];q=item['query'];channels=item['channels'];weights=q['weights'];s=GameSession.replay(c,deserialize_game_record(json.dumps(q['record_before'])));cp=LearnableMaterialCheckpoint.from_dict(row['published_checkpoint']);cp.validate_ruleset(c);assert cp.board_weights['P']<0
   def solve(st,depth,dist):
    poll();counts['core_visits']+=1
    if st.terminal_status.is_terminal:
     w=st.terminal_status.winner;z=0 if w is None else 1 if w==0 else-1;return(1000000*z,(100000000-dist)*z)
    if not depth:
     phi=[sum((1 if pc.owner==0 else-1)for pc in st.position.board if pc and pc.current_type_id==t)if kind=='board'else st.position.hands[0].count(t)-st.position.hands[1].count(t)for kind,t in channels];return(sum(x*w for x,w in zip(phi,weights)),sum(x*round(w*256)for x,w in zip(phi,weights)))
    vv=[solve(apply_action(st,a,c),depth-1,dist+1)for a in legal_actions(st,c)];fn=max if st.position.side_to_move==0 else min;return tuple(fn(v[j]for v in vv)for j in(0,1))
   aa=s.legal_actions();vv=[solve(apply_action(s.state,a,c),1,1)for a in aa];fn=max if s.state.position.side_to_move==0 else min;best=[fn(v[j]for v in vv)for j in(0,1)];opts=[j for j,v in enumerate(vv)if v[1]==best[1]];assert abs(best[0]-q['value'])<1e-9
   refs.append(dict(source_index=idx,checkpoint_id=cp.checkpoint_id,parent_state_sha256=digest(s.state),parent_witness_sha256=digest(s._search_witnesses),actions=record_value(aa),action_values=vv,float_best=best[0],quantized_best=best[1],quantized_optimal_indices=opts));write_json(D/'references.json',dict(rows=refs))
   for mode in P['modes']:
    poll();before=(s.state,s.to_record(),s.history,s._search_witnesses);e=SemanticSearchEngine(c,native[item['rule']],checkpoint=cp,tt_megabytes=0);tick=time.perf_counter();r=e.search(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),root_window_pruning=mode);elapsed=time.perf_counter()-tick;del e
    out=dict(source_index=idx,mode=mode,checkpoint_id=cp.checkpoint_id,parent_state_sha256=digest(s.state),parent_unchanged=before==(s.state,s.to_record(),s.history,s._search_witnesses),action=record_value(r.action),declaration_id=r.declaration_id,decision_line=record_value(r.decision_line),score=r.score,depth=r.completed_depth,nodes=r.nodes,qnodes=r.qnodes,cause=r.termination_reason,fallback=r.used_fallback,kernel_seconds=r.elapsed_seconds,caller_seconds=elapsed,root_window=r.root_window_pruning)
    log.write(json.dumps(out,separators=(',',':'))+'\n');log.flush();counts['queries']+=1;counts['nodes']+=r.nodes;assert out['parent_unchanged']and r.root_window_pruning==mode
    leaf=copy(s)
    for a in r.decision_line:
     if isinstance(a,str):leaf.declare(a)
     else:leaf.submit(a);counts['PV_core_edges']+=1
    if r.completed_depth==2 and not r.used_fallback:
     assert r.action in aa and aa.index(r.action)in opts;assert r.score*(1 if s.state.position.side_to_move==0 else-1)==best[1];counts['completed_D2_correct']+=1
    else:counts['UNRESOLVED']+=1
except BaseException as exc:status='ERROR';error=repr(exc)
write_json(D/'result.json',dict(status=status,error=error,counts=dict(counts),planned=32,returned=counts['queries'],missing=32-counts['queries'],seconds=time.perf_counter()-start,scope='16fixedpublishednegativeP fullinputs, pairedFalse/True, frozenrawsignedcoefficients. FreshcompleteCoreD2integeroptima/fullhistory/PV/parentunchanged. No newgame/training/gradientreference/all-domain orsignedstrengthclaim; originalsourceEVALPV/gradient remainsabsent.'))
print('SIGNED_CLOSED',status,error,dict(counts),time.perf_counter()-start)
