"""Independent literal replay of resource-contrast games; no Players/solvers."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,json,hashlib,gzip
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

def load(path):
 path=Path(path)
 b=path.read_bytes() if path.exists() else gzip.decompress(Path(str(path)+'.gz').read_bytes())
 return json.loads(b)
_RAW_RETURN_CACHE={}
def raw_return(root,qid):
 p=root/'returns'/f'{qid:04d}.json'
 if p.exists():return load(p)
 key=str(root.resolve())
 if key not in _RAW_RETURN_CACHE:_RAW_RETURN_CACHE[key]=load(root/'returns.json')
 item=_RAW_RETURN_CACHE[key][str(qid)]
 b=item['original_utf8'].encode()
 assert hashlib.sha256(b).hexdigest()==item['sha256'],'raw return original byte hash mismatch'
 return json.loads(b)
def rh(record):return hashlib.sha256(json.dumps(record_value(record),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def full_action(raw,session):
 matches=[a for a in session.legal_actions()if record_value(a)==raw]
 assert len(matches)==1,'complete action not uniquely legal';return matches[0]

def outcome(game):
 if game['status']!='TERMINAL':return None
 terminal=game['Core_terminal'];assert terminal['status']!='ongoing'
 winner=terminal['winner']
 if winner is None:
  return .5 if terminal['status']in {'stalemate','repetition','max_ply'} else None
 return 1. if winner==game['long_seat'] else 0.

def verify_game(game,case,root,plan):
 assert game['fingerprint']==case['fingerprint'];rr=ruleset_from_dict(case['RuleSet']);assert compute_fingerprint(rr)==case['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rr)
 assert game['initial_record']==case['record'];s=GameSession.replay(c,deserialize_game_record(json.dumps(game['initial_record'])))
 count=0;pv_plies=0;overshoots=0;cpu=0.;wall=0.;depths=Counter();sources=Counter()
 for q in game['queries']:
  assert q['game_id']==game['game_id'] and q['case_id']==case['id'];assert q['seat']==s.state.position.side_to_move;assert q['ply_before']==s.state.ply_count
  assert q['record_before_sha256']==rh(s.to_record()),'lost or altered complete query history'
  policy='long'if q['seat']==game['long_seat']else'short';budget=plan['policies'][policy]['seconds'];assert q['policy']==policy and q['requested_seconds']==budget
  raw=raw_return(root,q['query_id'])
  for key,val in raw.items():assert q[key]==val,'raw successful return was changed'
  expected=q['choose_wall_seconds']<=budget+max(.025,.10*budget);assert q['timing_eligible']==expected
  assert q['validated_root_unchanged'] and q['pv_legal'];overshoots+=not expected
  d=q['decision'];a=full_action(d['action'],s);pv=GameSession.replay(c,s.to_record())
  for token in d['principal_variation']:pv.submit(full_action(token,pv));pv_plies+=1
  s.submit(a);assert rh(s.to_record())==q['record_after_sha256'];count+=1;cpu+=q['choose_cpu_seconds'];wall+=q['choose_wall_seconds'];depths[str(d['completed_depth'])]+=1;sources[d['result_source']]+=1
 assert record_value(s.to_record())==game['final_record'];assert record_value(s.state.terminal_status)==game['Core_terminal'];assert record_value(s.result)==game['Session_result']
 assert game['timing_eligible']==(overshoots==0)
 assert (game['status']=='TERMINAL')==s.state.terminal_status.is_terminal
 if game['status']=='TERMINAL':assert s.state.terminal_status.winner==game['Core_terminal']['winner']
 return {'game_id':game['game_id'],'case_id':case['id'],'queries':count,'pv_plies':pv_plies,'long_seat':game['long_seat'],'Core_status':game['Core_terminal']['status'],'Core_winner':game['Core_terminal']['winner'],'long_points':outcome(game),'timing_eligible':game['timing_eligible'],'over_tolerance_calls':overshoots,'Player_wall_seconds':wall,'Player_cpu_seconds':cpu,'completed_depth_histogram':dict(depths),'result_source_histogram':dict(sources)}

def run(data,partial=False):
 plan=load(data/'population-budget-frozen.json');inputs=load(data/'prepared-v2/inputs.json');cases={r['id']:r for r in inputs['rows']};root=data/'population-games'
 if partial:
  games=[load(f)for f in sorted(root.glob('game-??.json'))];summary=None
 else:
  summary=load(root/'summary.json');games=load(root/'games.json');assert len(games)==plan['games'];assert summary['ended_at']
 roots=[r['id']for r in inputs['rows']if r['prefix_length']==2]
 caps=load(root/'executed-source.json')
 input_path=data/'prepared-v2/inputs.json';plan_path=data/'population-budget-frozen.json'
 input_bytes=input_path.read_bytes()if input_path.exists()else gzip.decompress(Path(str(input_path)+'.gz').read_bytes())
 plan_bytes=plan_path.read_bytes()if plan_path.exists()else gzip.decompress(Path(str(plan_path)+'.gz').read_bytes())
 assert caps['input_sha256']==hashlib.sha256(input_bytes).hexdigest()
 assert caps['plan_sha256']==hashlib.sha256(plan_bytes).hexdigest()
 assert plan['driver_sha256']==hashlib.sha256(caps['driver'].encode()).hexdigest()
 assert caps['root_ids']==roots
 schedule=[(case,seat)for case in roots for seat in [0,1]]
 reports=[];missing=[];query_ids=[]
 for g in games:
  assert (g['case_id'],g['long_seat'])==schedule[g['game_id']]
  if g['status']=='NOT_STARTED':missing.append(g['game_id']);continue
  reports.append(verify_game(g,cases[g['case_id']],root,plan));query_ids.extend(q['query_id']for q in g['queries'])
 assert len(set(query_ids))==len(query_ids)
 groups=defaultdict(list)
 for r in reports:groups[r['case_id']].append(r)
 terminal=[r for r in reports if r['long_points']is not None];eligible=[r for r in terminal if r['timing_eligible']]
 pairs=[rs for rs in groups.values()if len(rs)==2 and all(r['long_points']is not None and r['timing_eligible']for r in rs)]
 result={'mode':'PARTIAL_CLOSED_GAMES_ONLY'if partial else'CLOSED_ALL_PLANNED_SLOTS','games_replayed':len(reports),'not_started':missing,'query_returns_replayed':len(query_ids),'literal_PV_plies_replayed':sum(r['pv_plies']for r in reports),'terminal_games':len(terminal),'all_actual_long_points':sum(r['long_points']for r in terminal),'timing_eligible_terminal_games':len(eligible),'eligible_long_points':sum(r['long_points']for r in eligible),'complete_eligible_color_pairs':len(pairs),'eligible_pair_long_points':[{'case':rs[0]['case_id'],'points':sum(r['long_points']for r in rs)}for rs in pairs],'all_game_endings':dict(Counter(r['Core_status']for r in reports)),'over_tolerance_calls':sum(r['over_tolerance_calls']for r in reports),'games':reports,'new_Player':0,'new_solver':0,'new_games':0,'limits':'Literal replay of actual Core results and stored histories, not independent search reproduction; curated exposed inputs not iid rule draws; long budget not assumed stronger. Partial/missing cannot be assigned DRAW.'}
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--partial',action='store_true');a=p.parse_args();assert not a.output.exists();r=run(a.data,a.partial);a.output.write_bytes((json.dumps(r,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in r.items()if k!='games'}))
