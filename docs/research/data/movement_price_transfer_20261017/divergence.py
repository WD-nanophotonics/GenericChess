import os
"""Independent mature first-divergence four-objective Core control; no search calls."""
from pathlib import Path
import json,sys,time,hashlib
R=Path.cwd();STOP_ROOT=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R))).resolve();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import apply_action,legal_actions
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from scripts.research_record import record_value
D=R/'.local_agent/movement-transfer-20261017';P=json.loads((D/'divergence-plan.json').read_bytes());models={r['checkpoint_id']:r['checkpoint']for r in json.loads((D/'models.json').read_bytes())['rows']};cc={};visits=0;rows=[];start=time.perf_counter()
def sig(a):return json.dumps(record_value(a),sort_keys=True,separators=(',',':'))
def decode(a):
 d=dict(a);d['to_square']=Square(**d['to_square'])
 if 'from_square'in d:d['from_square']=Square(**d['from_square']);return SemanticBoardMove(**d)
 return SemanticDropMove(**d)
def poll():
 assert time.perf_counter()-start<P['limits']['cap_seconds']and visits<P['limits']['core_visits'],'FROZEN_DIAGNOSTIC_CAP'
 for n in('rollout','advisor','slack'):
  f=json.loads((STOP_ROOT/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('stopped')and not f.get('user_paused'),'EXPLICIT_STOP'
for r in json.loads((D/'divergence-inputs.json').read_bytes())['rows']:
 poll();gs=r['rule']
 if gs not in cc:cc[gs]=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(json.loads((D/f'rule-{gs}.json').read_bytes())))
 c=cc[gs];s=GameSession.replay(c,deserialize_game_record(json.dumps(r['parent_record'])));assert hashlib.sha256(json.dumps(record_value(s.state),sort_keys=True,separators=(',',':')).encode()).hexdigest()==r['left_query']['before_sha256'];assert s.state.position.side_to_move==r['owner'];profiles=[models[r[x+'_query']['checkpoint_id']]for x in('left','right')];n0=visits
 def walk(st,depth,relative):
  global visits
  visits+=1
  if visits%128==0:poll()
  t=st.terminal_status
  if t.is_terminal:return[0 if t.winner is None else(100000000-relative)*(1 if t.winner==0 else-1)]*4
  if depth==0:
   out=[]
   for quantized in(False,True):
    for cp in profiles:
     def weight(v):return round(v*256)if quantized else v*256
     board=sum((1 if pc.owner==0 else-1)*weight(cp['board_weights'].get(pc.current_type_id,0.))for pc in st.position.board if pc);hand=sum((st.position.hands[0].count(t)-st.position.hands[1].count(t))*weight(v)for t,v in cp['hand_weights'].items());out.append(board+hand)
   return out
  vv=[walk(apply_action(st,a,c),depth-1,relative+1)for a in legal_actions(st,c)];fn=max if st.position.side_to_move==0 else min;assert vv;return[fn(v[i]for v in vv)for i in range(4)]
 aa=s.legal_actions();vv=[walk(apply_action(s.state,a,c),1,1)for a in aa];fn=max if r['owner']==0 else min;best=[fn(v[i]for v in vv)for i in range(4)];opts=[{sig(a)for a,v in zip(aa,vv)if abs(v[i]-best[i])<1e-8}for i in range(4)];chosen=[sig(decode(r[k+'_query']['returned_action']))for k in('left','right')];scores=[r[k+'_query']['score']*(1 if r['owner']==0 else-1)for k in('left','right')];quant=[chosen[i]in opts[i+2]and scores[i]==best[i+2]for i in(0,1)];assert all(quant);ownfloat=[chosen[i]in opts[i]for i in(0,1)];regrets=[abs(best[i]-vv[[sig(a)for a in aa].index(chosen[i])][i])for i in(0,1)];cross=[chosen[0]in opts[1],chosen[1]in opts[0]]
 rows.append(dict(rule=gs,foe=r['foe'],comparison=r['comparison'],seed=r['seed'],family=r['family'],owner=r['owner'],absolute_ply=r['absolute_ply'],parent_state_sha256=r['left_query']['before_sha256'],left_slot=r['left_slot'],right_slot=r['right_slot'],own_native_quantized_optimal=quant,own_source_float_optimal=ownfloat,float_regret_native_units=regrets,source_float_optimal_sets_differ=opts[0]!=opts[1],both_chosen_actions_joint_float_ties=all(cross),strict_both_cross_preferences=not any(cross),one_sided_strict=any(cross)and not all(cross),best_values=best,core_visits=visits-n0))
a=dict(status='COMPLETE_MATURE_FIRST_DIVERGENCE_MECHANISM',planned=P['planned_groups'],returned=len(rows),missing=P['planned_groups']-len(rows),all_native_quantized_optimal=all(all(r['own_native_quantized_optimal'])for r in rows),choices_outside_source_float_optsets=sum(not x for r in rows for x in r['own_source_float_optimal']),max_float_regret_native_units=max(x for r in rows for x in r['float_regret_native_units']),joint_chosen_float_ties=sum(r['both_chosen_actions_joint_float_ties']for r in rows),strict_both_cross_preferences=sum(r['strict_both_cross_preferences']for r in rows),one_sided_strict=sum(r['one_sided_strict']for r in rows),different_float_optimal_sets=sum(r['source_float_optimal_sets_differ']for r in rows),core_visits=visits,rows=rows,seconds=time.perf_counter()-start,scope='Firstavailabledivergenceper384declaredcomparison/variant/foe/seedgroups, absentgroupspreserved; exactqueryreferencecountininputs. AllfourCoreD2objectivescomputed; no Nativequery/newfitness/labelselection. Native256isdeclaredapproximation; anyfloatregret limits exactfloatequivalence, notquantizedstudyvalidity. Jointtiesarenotstrictpricepreferences. Notall6669contexts/WDL/all-domainproof.');write_json(D/'divergence-result.json',a);print(json.dumps({k:v for k,v in a.items()if k!='rows'}),flush=True)
