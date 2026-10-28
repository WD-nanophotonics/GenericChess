"""Independent literal replay of CLOSED qualifier stages; no Player imports."""
from pathlib import Path
import json,hashlib,argparse,gzip
from collections import Counter
from scripts.verify_leaper_pvs_quality_pilot import load,action,full_digest,original_return
from scripts.research_record import record_value,write_record
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.config import MATE_SCORE

def verify(prepared,folder,expected,output):
 rows={r['id']:r for r in load(prepared/'inputs.json')['rows']};entries=load(folder/'qualification.json');qs=set();pvs=0;statuses=Counter()
 frozen=load(folder/'frozen.json');ip=prepared/'inputs.json';raw=ip.read_bytes() if ip.exists() else gzip.decompress(Path(str(ip)+'.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==frozen['input_sha256']==frozen['plan']['input_sha256']
 assert len(entries)==2*len(rows) and {e['slot'] for e in entries}==set(range(len(entries)))
 for name,text in frozen['sources'].items():assert hashlib.sha256(text.encode()).hexdigest()==frozen['plan']['sources'][name]
 for entry in entries:
  statuses[entry['status']]+=1
  if entry['status']=='NOT_RUN':assert 'query_id' not in entry;continue
  assert entry['status'] in ('RETURNED','FAILED')
  q=original_return(folder,entry['query_id']);assert q['decision']==entry['decision'] and q['on']==entry['on'];qs.add(entry['query_id']);r=rows[entry['case_id']]
  rules=ruleset_from_dict(r['RuleSet']);assert compute_fingerprint(rules)==r['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));assert full_digest(s.to_record())==q['record_before_sha256']
  d=q['decision'];assert q['actual_tuning']['use_one_check_extension']==q['on'] and not q['actual_tuning']['use_pvs']
  assert d['main_extension_max_path']<=1 and d['runtime_depth_balanced']
  assert q['provider_present'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
  assert q['limits']['max_depth']==expected and q['limits']['max_nodes']==500000 and q['limits']['quiescence_max_depth']==4 and q['limits']['quiescence_hard_max_depth']==8
  assert q['requested_service_seconds']==3 and q['limits']['max_time_seconds']+q['construction_packing_seconds']<=3+1e-9
  chosen=action(d['action'],s);pv=GameSession.replay(c,s.to_record())
  if d['principal_variation']:assert d['principal_variation'][0]==d['action']
  for a in d['principal_variation']:pv.submit(action(a,pv));pvs+=1
  if entry['status']=='RETURNED':
   if entry['accepted_goal'].startswith('completed_'):assert d['completed_depth']==expected
   else:
    assert entry['accepted_goal']=='Core_verified_immediate_WIN' and d['result_source']=='root_immediate_win' and d['score']==MATE_SCORE-1
    actor=s.state.position.side_to_move;s.submit(chosen);assert s.state.terminal_status.is_terminal and s.state.terminal_status.winner==actor
  else:
   assert d['completed_depth']!=expected and entry['error_type']=='AssertionError'
 games=load(folder/'games.json');assert len(games)==len(entries) and {g['game_id'] for g in games}==set(range(len(entries)));assert all(g['status']=='NOT_STARTED' and not g['queries'] for g in games)
 observed={p.stem for p in (folder/'returns').glob('*.json')} if (folder/'returns').exists() else set(load(folder/'returns.json'));assert observed==qs
 report=dict(statuses=dict(statuses),original_slots=len(entries),verified_original_returns=len(qs),PV_plies=pvs,game_slots=len(games),games_started=0,new_Player=0,new_solver=0,limits='Legal raw return is not passed qualification;FAILED and NOT_RUN preserved. No value/WDL or feature benefit verification.')
 write_record(output,report);print(report)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--folder',type=Path,required=True);p.add_argument('--expected',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.prepared,a.folder,a.expected,a.output)
