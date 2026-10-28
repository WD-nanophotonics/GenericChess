"""Independent saved-game/qualification replay; zero Player or solver calls."""
from __future__ import annotations
import argparse,json,hashlib,gzip
from collections import Counter,defaultdict
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.config import MATE_SCORE
from scripts.research_record import record_value,write_record
from scripts.verify_leaper_pvs_quality_pilot import load,action,full_digest,fixed_bounds,points,original_return

def endpoint(games):
 assert len(games)==24 and {g['game_id'] for g in games}==set(range(24))
 pairs=defaultdict(list)
 for g in games:pairs[g['case_id']].append(g)
 assert len(pairs)==12
 paired={};pair_rows=[]
 for case,gs in pairs.items():
  assert len(gs)==2 and {g['on_seat'] for g in gs}=={0,1}
  assert gs[0]['initial_record']==gs[1]['initial_record'] and gs[0]['fingerprint']==gs[1]['fingerprint']
  valid=all(g['status']=='TERMINAL' and g['timing_eligible'] for g in gs)
  for g in gs:paired[g['game_id']]=points(g) if valid else None
  pair_rows.append(dict(case=case,eligible=valid,raw=fixed_bounds([points(g) for g in gs],2),paired=fixed_bounds([paired[g['game_id']] for g in gs],2)))
 families=[]
 for f in range(6):
  gs=[g for g in games if g['family']==f];assert len(gs)==4 and {g['layout'] for g in gs}=={0,1}
  raw=[points(g) for g in gs];valid=all(g['status']=='TERMINAL' and g['timing_eligible'] for g in gs)
  families.append(dict(family=f,raw=fixed_bounds(raw,4),paired=fixed_bounds([paired[g['game_id']] for g in gs],4),net=None if None in raw else 2*sum(raw)-4,eligible=valid,terminal_reasons=dict(Counter(g.get('Core_terminal',{}).get('status',g['status']) for g in gs))))
 raw=fixed_bounds([points(g) for g in games],24);timing=fixed_bounds([points(g) if g['status']=='TERMINAL' and g['timing_eligible'] else None for g in games],24);paired_bounds=fixed_bounds([paired[g['game_id']] for g in games],24)
 all24=all(f['eligible'] for f in families);positive=sum(f['eligible'] and f['net']>0 for f in families)
 return dict(raw=raw,timing_games=timing,timing_pairs=paired_bounds,pairs=pair_rows,families=families,positive_eligible_families=positive,all24eligible=all24,amended_exploratory_screen=all24 and positive>=3 and raw['score_sum_known']>12,original_registration_gate='FAILED_D2_ONLY_NOT_RELABELED',limits='Knownrawoutcomesretained;timingmismatchdoesnotdeleteactualterminal. Paired bounds conservativelyunknownbothseatpartners;noIID/Elo/populationsignificance.')

def matched_prefixes(games):
 """Posthoc mechanism description, never attach WDL to changed actions."""
 grouped=defaultdict(list)
 for g in games:grouped[g['case_id']].append(g)
 result=[]
 for case,gs in sorted(grouped.items()):
  assert len(gs)==2
  assert gs[0]['fingerprint']==gs[1]['fingerprint'] and gs[0]['initial_record']==gs[1]['initial_record']
  left,right=(g['queries'] for g in gs);different=None
  for i,(a,b) in enumerate(zip(left,right)):
   # Only the actually shared complete history is a matched position.
   assert a['record_before_sha256']==b['record_before_sha256']
   if a['decision']['action']!=b['decision']['action']:
    different=i;break
  same_complete=(different is None and len(left)==len(right) and all(g['status']=='TERMINAL' for g in gs))
  first=[]
  for qs in (left,right):
   first.append(None if not qs else {k:qs[0]['decision'][k] for k in ('action','score','completed_depth','nodes','qnodes')})
  result.append(dict(case=case,first_decisions=first,first_action_differs=None if not left or not right else first[0]['action']!=first[1]['action'],first_divergent_relative_ply=different,common_complete_path=same_complete,limits='posthocdescriptionofALLfixedroots;afterdivergencehistoriesunmatched;rootdifference/depth/scorearenotWDLlabelsorqualitygates'))
 return result

def verify(prepared,folder,output):
 roots={r['id']:r for r in load(prepared/'inputs.json')['rows']};frozen=load(folder/'frozen.json');plan=frozen['plan'];input_path=prepared/'inputs.json';input_raw=input_path.read_bytes() if input_path.exists() else gzip.decompress(Path(str(input_path)+'.gz').read_bytes());assert hashlib.sha256(input_raw).hexdigest()==frozen['input_sha256']==plan['input_sha256']
 for name,text in frozen['sources'].items():assert hashlib.sha256(text.encode()).hexdigest()==plan['sources'][name]
 prior=Path(plan['qualification_continuation_from'])
 oldfrozen=load(folder/'original-frozen.json') if (folder/'original-frozen.json.gz').exists() or (folder/'original-frozen.json').exists() else load(prior/'frozen.json')
 oldbinary=load(folder/'original-loaded-binary.json') if (folder/'original-loaded-binary.json.gz').exists() or (folder/'original-loaded-binary.json').exists() else load(prior/'loaded-binary.json')
 binary=load(folder/'loaded-binary.json');assert oldbinary['sha256']==binary['sha256'] and oldbinary['bytes']==binary['bytes'], 'reused qualification binary changed'
 assert oldfrozen['input_sha256']==frozen['input_sha256']
 changed=[name for name,h in oldfrozen['plan']['sources'].items() if plan['sources'].get(name)!=h]
 assert changed==['scripts/leaper_new_family_pvs.py'], 'amendment changed more than disclosed caller'
 assert plan['whole_deadline_utc']==oldfrozen['plan']['whole_deadline_utc'] and plan['input_sha256']==oldfrozen['plan']['input_sha256']

 qids=set();pvs=0;counts=Counter();stats={False:Counter(),True:Counter()};qualification=load(folder/'qualification.json');assert len(qualification)==24
 for entry in qualification:
  assert entry['status'] in ('RETURNED','RETURNED_REUSED')
  root=roots[entry['case_id']];rules=ruleset_from_dict(root['RuleSet']);assert compute_fingerprint(rules)==root['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
  q=original_return(folder,entry['query_id']);assert q['decision']==entry['decision'] and q['on']==entry['on'] and q['record_before_sha256']==full_digest(s.to_record());qids.add(q['query_id'])
  if entry['status']=='RETURNED_REUSED':
   path=folder/'returns'/(q['query_id']+'.json');raw=path.read_bytes() if path.exists() else load(folder/'returns.json')[q['query_id']]['original_utf8'].encode();assert hashlib.sha256(raw).hexdigest()==plan['prior_return_hashes'][q['query_id']+'.json']
  d=q['decision'];assert d['runtime_depth_balanced'] and q['provider_present'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  assert q['actual_tuning']['use_pvs']==q['on'] and q['limits']['max_depth']==2 and q['limits']['max_nodes']==500000
  assert q['limits']['quiescence_max_depth']==4 and q['limits']['quiescence_hard_max_depth']==8 and q['provider_delta']['availability'].get('declines',0)==0
  chosen=action(d['action'],s);pv=GameSession.replay(c,s.to_record())
  for a in d['principal_variation']:pv.submit(action(a,pv));pvs+=1
  if entry['accepted_goal']=='completed_D2':assert d['completed_depth']==2
  else:
   assert entry['accepted_goal']=='Core_verified_immediate_WIN' and d['completed_depth']==0 and d['result_source']=='root_immediate_win' and d['score']==MATE_SCORE-1
   actor=s.state.position.side_to_move;s.submit(chosen);assert s.state.terminal_status.is_terminal and s.state.terminal_status.winner==actor
  counts['qualification']+=1
 for i in range(0,24,2):assert qualification[i]['case_id']==qualification[i+1]['case_id'] and qualification[i]['decision']['score']==qualification[i+1]['decision']['score']
 games=load(folder/'games.json');details=[]
 for g in games:
  root=roots[g['case_id']];assert root['family']==g['family'] and root['layout']==g['layout'] and root['fingerprint']==g['fingerprint'] and root['record']==g['initial_record']
  rules=ruleset_from_dict(root['RuleSet']);assert compute_fingerprint(rules)==root['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
  for q in g['queries']:
   qid=q['query_id'];assert qid not in qids;qids.add(qid);raw=original_return(folder,qid);assert all(q[k]==v for k,v in raw.items())
   assert q['seat']==s.state.position.side_to_move and q['on']==(q['seat']==g['on_seat']) and q['ply_before']==s.state.ply_count and q['record_before_sha256']==full_digest(s.to_record())
   assert q['actual_tuning']['use_pvs']==q['on'] and not q['actual_tuning']['use_plain_leaper_local_hash']
   assert q['evaluation_profile']['ruleset_fingerprint']==root['fingerprint']
   limits=q['limits'];assert limits['max_depth']==64 and limits['max_nodes']==500000 and limits['quiescence_max_depth']==4 and limits['quiescence_hard_max_depth']==8
   assert q['requested_service_seconds']==1 and 0<limits['max_time_seconds']<=1 and limits['max_time_seconds']+q['construction_packing_seconds']<=1.000000001
   assert q['timing_eligible']==(q['service_wall_seconds']<=1.1) and q['provider_present']
   d=q['decision'];assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
   assert q['provider_delta']['availability'].get('declines',0)==0
   chosen=action(d['action'],s);pv=GameSession.replay(c,s.to_record())
   if d['principal_variation']:assert d['principal_variation'][0]==d['action']
   for a in d['principal_variation']:pv.submit(action(a,pv));pvs+=1
   before=s.state.position;s.submit(chosen);after=s.state.position
   cells={i for i,(x,y) in enumerate(zip(before.board,after.board)) if x!=y};width=c.board_shape.width
   assert cells=={chosen.from_square.rank*width+chosen.from_square.file,chosen.to_square.rank*width+chosen.to_square.file}
   assert before.hands==after.hands and before.aux_state==after.aux_state and before.ruleset_fingerprint==after.ruleset_fingerprint and after.side_to_move==1-before.side_to_move
   assert q['record_after_sha256']==full_digest(s.to_record());counts['game_transitions']+=1
   stats[q['on']].update(calls=1,wall=q['service_wall_seconds'],cpu=q['cpu_seconds'],nodes=d['nodes'],qnodes=d['qnodes'],overtime=not q['timing_eligible'],PVS_null=d['pvs_null_window_searches'],PVS_research=d['pvs_researches'])
  if g['status'] in ('TERMINAL','UNFINISHED'):
   assert record_value(s.to_record())==g['final_record'] and record_value(s.state.terminal_status)==g['Core_terminal'] and record_value(s.result)==g['Session_result']
   assert s.state.terminal_status.is_terminal==(g['status']=='TERMINAL')
   assert g['timing_eligible']==all(q['timing_eligible'] for q in g['queries'])
  details.append(dict(game_id=g['game_id'],family=g['family'],status=g['status'],queries=len(g['queries']),terminal=g.get('Core_terminal')))
  write_record(output.with_suffix('.progress.json'),dict(games=len(details),transitions=counts['game_transitions'],PV_plies=pvs))
 observed={p.stem for p in (folder/'returns').glob('*.json')} if (folder/'returns').exists() else set(load(folder/'returns.json'));assert observed==qids,'orphan/missing original return'
 result=dict(endpoint=endpoint(games),posthoc_matched_prefixes=matched_prefixes(games),counts=dict(counts),literal_PV_plies=pvs,raw_returns=len(qids),reused_prior_returns=19,actual_new_returns=len(qids)-19,by_policy={str(k):dict(v) for k,v in stats.items()},details=details,new_Player=0,new_solver=0,new_games=0,limitations='Saved full-Core/action/PV replay,not independent search reproduction or external WDL/playingstrength certificate;originalgateFAILED,explicitamendment retained.')
 write_record(output,result);print(json.dumps(dict(counts=result['counts'],PV_plies=pvs,returns=len(qids),endpoint=result['endpoint'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.prepared,a.folder,a.output)
