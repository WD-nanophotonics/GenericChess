"""Six complete Core D2 objectives; diagnostic channels, never a deployed recipe."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import json,sys,time,os
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import apply_action,legal_actions
D=R/'.local_agent/nearest-rule-transfer-20261017';STOP=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R)));p=json.loads((D/'coupling-plan.json').read_bytes());inputs=json.loads((D/'coupling-inputs.json').read_bytes());cc={};rows=[];visits=0;started=time.perf_counter()
def poll():
 assert time.perf_counter()-started<p['limits']['seconds'] and visits<p['limits']['visits'],'FROZEN_COUPLING_CAP'
 for n in ('rollout','advisor','slack'):
  z=json.loads((STOP/'.local_agent'/(n+'.json')).read_bytes());assert not z.get('user_paused') and not z.get('stopped'),'EXPLICIT_STOP'
def sig(a):return json.dumps(record_value(a),sort_keys=True,separators=(',',':'))
for item in inputs['rows']:
 poll();gs=item['rule'];target=item['target']
 if gs not in cc:cc[gs]=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(inputs['rules'][str(gs)]))
 c=cc[gs];s=GameSession.replay(c,deserialize_game_record(json.dumps(item['record'])));before=(s.state,s.to_record(),s.history,s._search_witnesses);hybrid=deepcopy(item['mapped']);hybrid['board_weights'][target]=item['direct']['board_weights'][target];hybrid['hand_weights']['P']=item['direct']['hand_weights']['P'];profiles=[item['direct'],item['mapped'],hybrid];n0=visits
 def context(st):
  return [dict(owner=o,current_target=sum(pc is not None and pc.owner==o and pc.current_type_id==target for pc in st.position.board),baseP_current_target=sum(pc is not None and pc.owner==o and pc.base_type_id=='P' and pc.current_type_id==target for pc in st.position.board),baseTarget_current_target=sum(pc is not None and pc.owner==o and pc.base_type_id==target and pc.current_type_id==target for pc in st.position.board),hand_baseP=st.position.hands[o].count('P')) for o in (0,1)]
 def leaf(st,relative):
  t=st.terminal_status
  if t.is_terminal:return [0 if t.winner is None else (100000000-relative)*(1 if t.winner==0 else -1)]*6
  vals=[]
  for quant in (False,True):
   for cp in profiles:
    def w(v):return round(v*256) if quant else v*256
    vals.append(sum((1 if pc.owner==0 else -1)*w(cp['board_weights'].get(pc.current_type_id,0))for pc in st.position.board if pc)+sum((st.position.hands[0].count(t)-st.position.hands[1].count(t))*w(v)for t,v in cp['hand_weights'].items()))
  return vals
 def walk(st,depth,relative):
  global visits
  visits+=1
  if visits%64==0:poll()
  if st.terminal_status.is_terminal or depth==0:return leaf(st,relative),[dict(line=[],context=context(st),terminal=record_value(st.terminal_status))for _ in range(6)]
  actions=sorted(legal_actions(st,c),key=repr);assert actions;vv=[];tr=[]
  for a in actions:
   v,t=walk(apply_action(st,a,c),depth-1,relative+1);vv.append(v);tr.append([dict(x,line=[record_value(a)]+x['line'])for x in t])
  fn=max if st.position.side_to_move==0 else min;best=[fn(v[j]for v in vv)for j in range(6)];ix=[next(i for i,v in enumerate(vv)if abs(v[j]-best[j])<1e-8)for j in range(6)];return best,[tr[ix[j]][j]for j in range(6)]
 actions=sorted(s.legal_actions(),key=repr);vv=[];tr=[]
 for a in actions:
  v,t=walk(apply_action(s.state,a,c),1,1);vv.append(v);tr.append([dict(x,line=[record_value(a)]+x['line'])for x in t])
 fn=max if s.state.position.side_to_move==0 else min;best=[fn(v[j]for v in vv)for j in range(6)];opts=[{sig(a)for a,v in zip(actions,vv)if abs(v[j]-best[j])<1e-8}for j in range(6)];chosen=[next(i for i,v in enumerate(vv)if abs(v[j]-best[j])<1e-8)for j in range(6)];trace=[tr[chosen[j]][j]for j in range(6)];disjoint=not(opts[0]&opts[1]);integer_disjoint=not(opts[3]&opts[4]);restored=bool(opts[0]&opts[2]) and bool(opts[3]&opts[5]);initialcontext=context(s.state);channelchanges=any(t['context']!=initialcontext for t in trace)
 rows.append(dict(rule=gs,target=target,all_P_targets=item['all_P_targets'],seed=item['seed'],source_slot=item['source_slot'],absolute_ply=item['absolute_ply'],root_record=item['record'],root_context=initialcontext,best_values=best,optimal_action_sets=[sorted(x)for x in opts],representative_complete_minimax_lines=trace,float_direct_mapped_disjoint=disjoint,integer_direct_mapped_disjoint=integer_disjoint,hybrid_recovers_some_direct_both_units=restored,local_channel_witness=disjoint and integer_disjoint and restored and channelchanges,observed_relevant_context_change=channelchanges,core_visits=visits-n0,hybrid_weights=hybrid));assert before==(s.state,s.to_record(),s.history,s._search_witnesses)
q=dict(status='COMPLETE_BOUNDED_LOCAL_CHANNEL_DIAGNOSTIC',rows=rows,roots=inputs['actual_roots'],calls=len(rows),planned_roots=inputs['planned_roots'],missing_roots=inputs['missing_roots'],local_witnesses=sum(r['local_channel_witness']for r in rows),float_disjoint=sum(r['float_direct_mapped_disjoint']for r in rows),integer_disjoint=sum(r['integer_direct_mapped_disjoint']for r in rows),core_visits=visits,seconds=time.perf_counter()-started,scope='Exact SIX CoreD2 minimax objectives on16fixedUnittrajectorystates/all4TDseeds, noNativequery/newgame/TRAIN/default. Jointtwochannel intervention targetsFIRSTactualPpromotiontarget+handbaseP; PtargetsnotuniformX. Existingtargetpieces andalternativepromotiontargets remain confounds; localdecision witness NOTutility/promotiononly/causalfitness proof. Lackwitnessnotlackdeeperinteraction. Fullhistory retained.')
write_json(D/'coupling-result.json',q);print(json.dumps({k:v for k,v in q.items()if k!='rows'}),flush=True)
