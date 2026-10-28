"""Independent saved-data replay of the eight-family fresh resource control."""
from scripts.verify_leaper_resource_resolution_control import *
from scripts.verify_leaper_admitted_extension import endpoints

def endpoint(games):
 r=endpoints(games,16);r['resource_positive_control_passed']=r.pop('exploratory_gate_passed')
 r['interpretation']='ON2s/OFF1s sameDEFAULT policy,extensionOFF/PVSOFF. Conditional8family DEVELOPMENT resource curve;not equal-cost feature benefit,classstrength,or IID.'
 return r

def verify(prepared,folder,output):
 roots={r['id']:r for r in load(prepared/'inputs.json')['rows']};frozen=load(folder/'frozen.json');plan=frozen['plan'];input_path=prepared/'inputs.json';input_raw=input_path.read_bytes() if input_path.exists() else gzip.decompress(Path(str(input_path)+'.gz').read_bytes());assert hashlib.sha256(input_raw).hexdigest()==frozen['input_sha256']==plan['input_sha256']
 for name,text in frozen['sources'].items():assert hashlib.sha256(text.encode()).hexdigest()==plan['sources'][name]
 binary=load(folder/'loaded-binary.json');assert len(binary['sha256'])==64 and binary['bytes']>0

 assert len(roots)==8 and list(roots)==plan['root_ids']
 qids=set();pvs=0;counts=Counter();stats={False:Counter(),True:Counter()};qualification=load(folder/'qualification.json');assert len(qualification)==16
 for entry in qualification:
  assert entry['status'] in ('RETURNED',)
  root=roots[entry['case_id']];rules=ruleset_from_dict(root['RuleSet']);assert compute_fingerprint(rules)==root['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
  q=original_return(folder,entry['query_id']);assert q['decision']==entry['decision'] and q['on']==entry['on'] and q['record_before_sha256']==full_digest(s.to_record());qids.add(q['query_id'])
  assert_resource_service(q,qualification=True)
  d=q['decision'];assert d['main_check_extensions']==d['pvs_null_window_searches']==d['pvs_researches']==0;assert d['runtime_depth_balanced'] and q['provider_present'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  assert not q['actual_tuning']['use_pvs'] and not q['actual_tuning']['use_one_check_extension'] and q['limits']['max_depth']==64 and q['limits']['max_nodes']==500000
  assert q['limits']['quiescence_max_depth']==4 and q['limits']['quiescence_hard_max_depth']==8 and q['provider_delta']['availability'].get('declines',0)==0
  chosen=action(d['action'],s);pv=GameSession.replay(c,s.to_record())
  for a in d['principal_variation']:pv.submit(action(a,pv));pvs+=1
  assert entry['accepted_goal']=='legal_current_service_return'
  target=2 if q['on'] else 1
  assert q['requested_service_seconds']==target and q['timing_eligible'] and q['service_wall_seconds']<=target*1.1
  assert q['limits']['max_time_seconds']+q['construction_packing_seconds']<=target+1e-9
  assert d['main_check_extensions']==0 and d['main_extension_max_path']==0
  if d['result_source']=='root_immediate_win':
   actor=s.state.position.side_to_move;s.submit(chosen)
   assert s.state.terminal_status.is_terminal and s.state.terminal_status.winner==actor
  counts['qualification']+=1
 for i in range(0,16,2):assert qualification[i]['case_id']==qualification[i+1]['case_id']==plan['root_ids'][i//2] and {qualification[i]['on'],qualification[i+1]['on']}=={False,True}
 games=load(folder/'games.json');details=[]
 for gi,g in enumerate(games):
  assert g['game_id']==gi and g['case_id']==plan['root_ids'][gi//2]
  assert {games[gi-gi%2]['on_seat'],games[gi-gi%2+1]['on_seat']}=={0,1}
  root=roots[g['case_id']];assert root['family']==g['family'] and root['layout']==g['layout'] and root['fingerprint']==g['fingerprint'] and root['record']==g['initial_record']
  rules=ruleset_from_dict(root['RuleSet']);assert compute_fingerprint(rules)==root['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
  for q in g['queries']:
   qid=q['query_id'];assert qid not in qids;qids.add(qid);raw=original_return(folder,qid);assert all(q[k]==v for k,v in raw.items())
   assert q['seat']==s.state.position.side_to_move and q['on']==(q['seat']==g['on_seat']) and q['ply_before']==s.state.ply_count and q['record_before_sha256']==full_digest(s.to_record())
   assert not q['actual_tuning']['use_pvs'] and not q['actual_tuning']['use_one_check_extension'] and not q['actual_tuning']['use_plain_leaper_local_hash']
   assert q['evaluation_profile']['ruleset_fingerprint']==root['fingerprint']
   limits=q['limits'];assert limits['max_depth']==64 and limits['max_nodes']==500000 and limits['quiescence_max_depth']==4 and limits['quiescence_hard_max_depth']==8
   target=2 if q['on'] else 1
   assert q['requested_service_seconds']==target and 0<limits['max_time_seconds']<=target and limits['max_time_seconds']+q['construction_packing_seconds']<=target+1e-9
   assert q['timing_eligible']==(q['service_wall_seconds']<=target*1.1) and q['provider_present']
   assert_resource_service(q)
   d=q['decision'];assert d['main_check_extensions']==d['pvs_null_window_searches']==d['pvs_researches']==0;assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
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
 result=dict(endpoint=endpoint(games),posthoc_matched_prefixes=matched_prefixes(games),counts=dict(counts),literal_PV_plies=pvs,raw_returns=len(qids),reused_prior_returns=0,actual_new_returns=len(qids),by_policy={str(k):dict(v) for k,v in stats.items()},details=details,new_Player=0,new_solver=0,new_games=0,limitations='Saved full-Core/action/PV replay;ON2s/OFF1s same default policy. Not independent search reproduction,feature improvement,equalcost or classstrength. Earlier candidate48+24games remain NOT_STARTED,not resourcecontrol outcomes.')
 write_record(output,result);print(json.dumps(dict(counts=result['counts'],PV_plies=pvs,returns=len(qids),endpoint=result['endpoint'])))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.prepared,a.folder,a.output)
