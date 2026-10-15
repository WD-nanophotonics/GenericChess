"""Independent transported-proof and complete-depth artifact audit; no new search."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import SessionStrategyCursor
O=Path('results/dev_aux/task1921')
def read(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def run():
 beg=time.perf_counter();plan=read('results/dev_aux/task1915/plan.json');rows=lines('results/dev_aux/task1915/queries.jsonl');assert len(rows)==len(plan['queries'])==132;c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text()));verified=[];coverage=[]
 for expected,row in zip(plan['queries'],rows):
  assert all(row[k]==v for k,v in expected.items() if k!='record');assert row['nodes']<=expected['max_nodes'];assert row['status'] in ('UNKNOWN','PROVEN_WIN')
  if row['usable']:
   raw=read(f"results/dev_aux/task1915/certificate-{row['query']}.json");assert raw['root_record']==expected['record'] and raw['target']==row['target'];s,certificate=decode_session_certificate(c,raw,max_nodes=262144);cursor=SessionStrategyCursor(s,certificate,max_nodes=262144,seconds=5.);assert cursor.receipt['verified'];assert hashlib.sha256(repr(s.state).encode()).hexdigest()==row['state_sha'];assert cursor.node.rank==row['root_rank'];ranks=[]
   while s.result.status is SessionStatus.ONGOING:
    r=cursor.node.rank;choice=cursor.choose(s) if s.state.position.side_to_move==row['target'] else cursor.node.edges[0][0];cursor.commit(s,choice);assert cursor.node.rank<r;ranks.append(cursor.node.rank)
   final=GameSession.replay(c,deserialize_game_record(json.dumps(row['actual_final_record'])));assert s.to_record()==final.to_record() and s.state==final.state and s.result==final.result and s.result.winner==row['target'] and ranks==row['physical_ranks'];verified.append(dict(query=row['query'],verification=cursor.receipt,physical_moves=len(ranks),actual_winner=s.result.winner))
  else:assert row['actual_final_record'] is None
 for cap in (16384,65536,262144):
  subset=[r for r in rows if r['max_nodes']==cap];resolved={(r['pair'],r['origin_ratio']):r['target'] for r in subset if r['usable']};assert len(resolved)==sum(r['usable'] for r in subset)
  pairdetails=[]
  for pair in range(11):
   a,b=resolved.get((pair,2.)),resolved.get((pair,4.));pairdetails.append(dict(pair=pair,origin2_proved_winner=a,origin4_proved_winner=b,opposite_proved_winners=a is not None and b is not None and a!=b))
  coverage.append(dict(cap=cap,queries=len(subset),proved_children=len(resolved),unknown_target_queries=sum(not r['usable'] for r in subset),nodes=sum(r['nodes'] for r in subset),seconds=sum(r['seconds_used'] for r in subset),pairs=pairdetails))
 drows=lines('results/dev_aux/task1916/queries.jsonl');assert len(drows)==66 and all(r['complete'] for r in drows);index={(r['pair'],r['depth'],r['ratio']):r for r in drows};mapping={720*(4*dr+dn):720*(2*dr+dn) for dr in (-1,0,1) for dn in (-1,0,1)};mapping.update({1000000:1000000,-1000000:-1000000});checks=[]
 for pair in range(11):
  for depth in (2,4,6):
   a,b=index[pair,depth,2.],index[pair,depth,4.];assert a['state_sha']==b['state_sha'];va={x['action']:x['score'] for x in a['values']};vb={x['action']:x['score'] for x in b['values']};assert set(va)==set(vb) and all(va[m]==mapping[vb[m]] for m in va);assert set(b['best_actions'])<=set(a['best_actions']);checks.append(dict(pair=pair,depth=depth,legal_actions=len(va),best2=a['best_actions'],best4=b['best_actions'],both_original_choices_optimal_under_both=all(v['regret']==0 for r in (a,b) for v in r['original_choices'].values())))
 out=dict(status='PASS_TRANSPORT_AND_FINITE_TREE_ORDER',actual_proofs_redecoded_verified_and_physically_won=len(verified),verification=verified,coverage=coverage,complete_depth_queries=66,full_root_action_order_map_checks=checks,independent_public_depth2_checks=sum(r['public_depth2_check'] for r in drows),depth6_pairs_both_original_choices_optimal_under_both=sum(r['both_original_choices_optimal_under_both'] for r in checks if r['depth']==6),seconds=time.perf_counter()-beg,scope='No newproof/native/depthsearch. Transport decode/public verification/actualSessioncanonicaldefense replay and exactfiniteutilitymap checks. Provedwinvsunknown isnotoppositeoutcome; rootrankiswinningstrategyupperboundNOToptimalDTM. No newprice/H/DEVselection.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({k:out[k] for k in ['status','actual_proofs_redecoded_verified_and_physically_won','complete_depth_queries','independent_public_depth2_checks','depth6_pairs_both_original_choices_optimal_under_both','seconds']}))
if __name__=='__main__':run()
