from pathlib import Path
from collections import Counter,defaultdict
import json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_win_proof import _ordered
from results.dev_aux.task2100.campaign import sha_state
OUT=Path('results/dev_aux/task2160')
def run():
 start=time.perf_counter();root=Path('results/dev_aux/task2158');p=json.loads((root/'plan.json').read_text(encoding='utf-8'));inputs=json.loads((root/'inputs.json').read_text(encoding='utf-8'))['roots'];games=list(map(json.loads,(root/'games.jsonl').read_text(encoding='utf-8').splitlines()));by=defaultdict(list)
 for d in map(json.loads,(root/'decisions.jsonl').read_text(encoding='utf-8').splitlines()):by[d['physical_id']].append(d)
 counts=Counter();fallbacks=[];pairdata={};physical={g['physical_id']:g for g in games if g['reused_from']is None};compiled={}
 for pid,g in physical.items():
  family=g['family']
  if family not in compiled:compiled[family]=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[family]['rules']).read_text(encoding='utf-8')))
  s=GameSession(compiled[family]);dd=by[pid];assert len(dd)==g['moves']
  for ply,d in enumerate(dd):
   assert d['physical_id']==pid and d['logical_slot']==g['logical_slot']and d['ply']==ply and d['side']==s.state.position.side_to_move
   assert d['root_record']==json.loads(serialize_game_record(s.to_record()))and d['root_state_sha']==sha_state(s.state)and d['ruleset_fingerprint']==s.compiled.ruleset_fingerprint
   assert d['choice']is not None and all(d['requested_limits'][k]==p[k]for k in d['requested_limits'])
   action=next(a for a in s.legal_actions()if action_to_dict(a)==d['choice']['action']);nr=d['normal_receipt'];counts[d['source']]+=1
   if d['source']=='PRECOMPUTED_LEGAL_FALLBACK':
    assert d['exit_cause']in('time_budget','node_budget')and nr is not None and nr['action']is None and nr['completed_depth']==0 and action==_ordered(s.legal_actions())[0]
    assert d['actual_phase_limits']['normal_seconds']==.05 and d['actual_phase_limits']['total_seconds']==.75
    fallbacks.append(dict(physical_id=pid,family=family,phase=g['phase'],ratio=g['ratio'],foe=g['opponent_ratio'],candidate=g['candidate_side'],ply=ply,decision=d,original_game_outcome=g['outcome']))
   elif nr is not None:assert nr['action']==d['choice']['action']and nr['nodes']==d['search_nodes']
   s.submit(action)
  assert json.loads(serialize_game_record(s.to_record()))==g['record'];counts['all_decisions']+=len(dd)
 for family in range(32,48):
  for role in(0,1):
   a=next(g for g in games if g['phase']=='DEV'and g['family']==family and g['candidate_side']==role and g['ratio']==1.)
   b=next(g for g in games if g['phase']=='DEV'and g['family']==family and g['candidate_side']==role and g['ratio']==.25)
   if a['score']==b['score']:continue
   x,y=by[a['physical_id']],by[b['physical_id']];i=next(i for i in range(min(len(x),len(y)))if x[i]['choice']!=y[i]['choice']);assert x[i]['root_state_sha']==y[i]['root_state_sha'];assert x[i]['source']==y[i]['source']=='MATERIAL_SEARCH'and x[i]['normal_receipt']['completed_depth']==y[i]['normal_receipt']['completed_depth']==2;assert x[i]['side']==y[i]['side']==role
   pairdata[str(family)+'_'+str(role)]=dict(family=family,candidate=role,first_different_ply=i,baseline_choice=x[i]['choice'],selected_choice=y[i]['choice'],baseline_score=a['score'],selected_score=b['score'],first_difference='CANDIDATE_PRICE_NORMAL_COMPLETED2')
 assert counts['all_decisions']==15179 and len(fallbacks)==1 and not(root/'abort.json').exists()
 out=dict(status='PASS_ALL15179_PRECOMMIT_RECEIPTS_ACTUAL_FALLBACK_AND_DEV_FIRSTDIFFERENCES',counts=dict(counts),actual_fallbacks=fallbacks,DEV_outcome_changed_pairs=pairdata,DEV_mean_family_gain=0.,observed_stop_failures=0,seconds=time.perf_counter()-start,scope='Fallbackbelongsdeclarednewpolicyandactuallegalaction, notbackfill2134. Actualnormalphasecanfailbeforedepth1 withoutabortingwholelearnedassay. BothchangedDEVpairsfirstdivergeatcandidatecompleteddepth2; no proof/fallback-firstconfound inthesecomparisons. Gain0notstability/benefit/equivalence.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items()if k!='actual_fallbacks'}),flush=True)
if __name__=='__main__':run()
