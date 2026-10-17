"""One bounded rule-aware mapping feasibility probe, no games/training."""
from pathlib import Path
from copy import copy
import json,sys,time,hashlib,os
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.transition import apply_action,legal_actions
from generic_chess.core.actions import SemanticBoardMove,SemanticDropMove
from generic_chess.core.coordinates import Square
from scripts.research_record import record_value
STOP_ROOT=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R))).resolve();D=R/'.local_agent/movement-transfer-20261017';F=R/'.local_agent/rule-aware-map-20261017';F.mkdir(exist_ok=True);started=time.perf_counter();plan=json.loads((D/'plan.json').read_bytes());inventory=json.loads((D/'next-rule-aware-mapping-inventory.json').read_bytes())['rows'];want={(r['rule'],r['label']):r for r in inventory};slots=json.loads((D/'slots.json').read_bytes())['slots'];selected={}
for line in (D/'queries.jsonl').open():
 q=json.loads(line);rid,f,label,owner,foe=slots[q['slot']]
 if (rid,label)not in want or q['actor']!=owner or (rid,label)in selected:continue
 selected[rid,label]=dict(rule=rid,label=label,owner=owner,family=f,foe=foe,query=q,mapping=want[rid,label])
assert len(selected)==96
records={}
for line in (D/'games.jsonl').open():
 g=json.loads(line)
 if any(r['query']['slot']==g['slot']for r in selected.values()):records[g['slot']]=g['record']
roots={(r['rule'],r['family']):r for r in json.loads((D/'roots.json').read_bytes())['rows']}
for r in selected.values():
 record=dict(records[r['query']['slot']]);record['actions']=record['actions'][:roots[r['rule'],r['family']]['prefix_completed']+r['query']['relative_ply']];r['parent_record']=record
write_json(F/'feasibility-inputs.json',dict(rows=list(selected.values()),selection='FIRSTactualrecord-ordercandidatequery perALL12nonidentityvariants*4seeds*2methods, nooutcome/marginselection; original completejournals remainimmutable.'))
write_json(F/'feasibility-plan.json',dict(question='Does rule-only A-capability ratio mapping materially change frozen-table decisions before a fresh utility experiment?',limits=dict(calls=96,seconds=120,core_visits=1000000),recipe='ONLYAboard/hand *=rawA(target)/rawA(originalrecipient); allothercoefficientssignsunchanged. Adaptivecandidateafteroriginalfitness, no parameterfitting/labels or default activation.',done='No/tiedchanges: stopfitnessproposal; genuine strictchanges: feasibilityonly, separatelyregisteredfreshutility required. Existingdirectqueryreused, no directNative rerun.',ratio_inventory_sha256=hashlib.sha256((D/'next-rule-aware-mapping-inventory.json').read_bytes()).hexdigest()))
models={};kernels={};rows=[];visits=0
sig=lambda a:json.dumps(record_value(a),sort_keys=True,separators=(',',':'))
def decode(a):
 d=dict(a);d['to_square']=Square(**d['to_square'])
 if 'from_square'in d:d['from_square']=Square(**d['from_square']);return SemanticBoardMove(**d)
 return SemanticDropMove(**d)
def poll():
 assert time.perf_counter()-started<120 and visits<1000000,'FROZEN_FEASIBILITY_CAP'
 for n in ('rollout','advisor','slack'):
  f=json.loads((STOP_ROOT/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('user_paused')and not f.get('stopped')
for item in selected.values():
 poll();rid=item['rule'];r=item['mapping']
 if rid not in models:
  models[rid]=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(json.loads((D/f'rule-{rid}.json').read_bytes())));kernels[rid]=compile_native_semantic_rules(models[rid])
 c=models[rid];s=GameSession.replay(c,deserialize_game_record(json.dumps(item['parent_record'])));before=(s.state,s.to_record(),s.history,s._search_witnesses);profiles=[dict(board_weights=r[k+'_board'],hand_weights=r[k+'_hand'])for k in ['direct','candidate']]
 def solve(st,depth,relative):
  global visits
  visits+=1
  if visits%128==0:poll()
  if st.terminal_status.is_terminal:
   z=0 if st.terminal_status.winner is None else(1 if st.terminal_status.winner==0 else -1);return [(100000000-relative)*z]*4
  if depth==0:
   return [sum((1 if pc.owner==0 else -1)*(round(cp['board_weights'][pc.current_type_id]*256)if quant else cp['board_weights'][pc.current_type_id]*256)for pc in st.position.board if pc)+sum((st.position.hands[0].count(t)-st.position.hands[1].count(t))*(round(w*256)if quant else w*256)for t,w in cp['hand_weights'].items())for quant in (False,True)for cp in profiles]
  vv=[solve(apply_action(st,a,c),depth-1,relative+1)for a in legal_actions(st,c)];fn=max if st.position.side_to_move==0 else min;return [fn(v[j]for v in vv)for j in range(4)]
 actions=s.legal_actions();vv=[solve(apply_action(s.state,a,c),1,1)for a in actions];fn=max if item['owner']==0 else min;best=[fn(v[j]for v in vv)for j in range(4)];opts=[{sig(a)for a,v in zip(actions,vv)if abs(v[j]-best[j])<1e-8}for j in range(4)];direct=decode(item['query']['returned_action']);assert sig(direct)in opts[2]and item['query']['score']*(1 if item['owner']==0 else -1)==best[2]
 cp=LearnableMaterialCheckpoint(ruleset_fingerprint=c.ruleset_fingerprint,evaluation_profile_version='adaptive-rule-A-capability-ratio',board_weights=r['candidate_board'],hand_weights=r['candidate_hand'],material_scale=256,value_scale=10.,reference_median=1.)
 result=SemanticSearchEngine(c,kernels[rid],checkpoint=cp,tt_megabytes=0).search(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=2.,quiescence_max_depth=0),root_window_pruning=False)
 assert result.completed_depth==2 and not result.used_fallback and sig(result.action)in opts[3]and result.score*(1 if item['owner']==0 else -1)==best[3]and before==(s.state,s.to_record(),s.history,s._search_witnesses)
 rows.append(dict(rule=rid,label=item['label'],source_slot=item['query']['slot'],relative_ply=item['query']['relative_ply'],ratio=r['ratio'],source_parent_sha256=item['query']['before_sha256'],changed_action=direct!=result.action,old_action_not_optimal_under_mapped_float=sig(direct)not in opts[1],new_action_not_optimal_under_direct_float=sig(result.action)not in opts[0],mapped_action_float_optimal=sig(result.action)in opts[1],direct_action_float_optimal=sig(direct)in opts[0],same_float_optsets=opts[0]==opts[1],mapped_typed_action=record_value(result.action),mapped_score=result.score,mapped_nodes=result.nodes))
write_json(F/'feasibility-result.json',dict(status='COMPLETE_96_FROZEN_RULE_A_MAPPING_CONTROLS',calls=len(rows),changed_actions=sum(r['changed_action']for r in rows),old_actions_strictly_inferior_under_mapped_float=sum(r['old_action_not_optimal_under_mapped_float']for r in rows),mapped_actions_outside_own_float=sum(not r['mapped_action_float_optimal']for r in rows),different_float_optsets=sum(not r['same_float_optsets']for r in rows),core_visits=visits,rows=rows,seconds=time.perf_counter()-started,scope='Adaptiveheuristicnotfit/default. Reuses96originaldirectqueries; new96Nativecalls/independentfourobjectiveCoreD2, notnewgames/utility/WDLproof or originalfitnessrerun. Anygenuinedecisionchanges justifyonlyseparatefreshfrozenutilitytest; same/tiedchangeswouldstopproposal.'))
print('FEASIBLE',len(rows),'calls; changed',sum(r['changed_action']for r in rows),'oldnotmappedfloatopt',sum(r['old_action_not_optimal_under_mapped_float']for r in rows),'ownfloatfail',sum(not r['mapped_action_float_optimal']for r in rows),'seconds',round(time.perf_counter()-started,3))
