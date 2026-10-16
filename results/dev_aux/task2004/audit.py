"""Bothactor noWIN scheduling cost, all fixed exposed paths; no new search."""
from pathlib import Path
from collections import Counter
import json,hashlib
from results.dev_aux.task1998.physical_audit import audit,read,lines
from scripts.generic_inventory_proof_transport import execution_differences,SetupTransportedNoWinFilter
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
OUT=Path('results/dev_aux/task2004');ROOT=Path('results/dev_aux/task2003')
def run():
 physical=audit(ROOT);p=read(ROOT/'run-plan.json');rows=lines(ROOT/'games.jsonl');moves=lines(ROOT/'moves.jsonl');cov=read('results/dev_aux/task2002/result.json')
 assert physical['full_study_complete'] and len(rows)==64 and cov['total_states']==15240 and cov['total_edges']==69360
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));reference=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text()))
 assert execution_differences(reference,c)==()
 filt=SetupTransportedNoWinFilter('results/dev_aux/task1895','results/dev_aux/task1896/coverage.json',c)
 old=read('results/dev_aux/task2002/baseline64.json')['games'];key=lambda x:(x['family'],x['candidate_side'],x['R'],x['opponent_R']);oldmap={key(g):g for g in old};assert len(oldmap)==64 and set(oldmap)=={key(g)for g in rows}
 oldmoves=lines('results/dev_aux/task2002/baseline64-moves.jsonl');assert len(oldmoves)==sum(x['moves']for x in old)
 prior=[oldmap[key(g)]for g in rows];actual=sum(g['seconds']for g in rows);before=sum(g['seconds']for g in prior)
 transitions=Counter((a['outcome'],b['outcome'])for a,b in zip(prior,rows));hits=Counter()
 for m in moves:
  if m.get('logical_reason')=='certified_inventory_no_win' or m['proof_reason']=='certified_inventory_no_win':
   assert m['source'] not in ('PROOF','PROOF_CONTINUATION') and m['proof_nodes']==0
   hits['CANDIDATE'if m['side']==rows[m['slot']]['candidate_side']else'OPPONENT']+=1
 result=dict(status='PASS_BOTH_ACTOR_COMMON1K_FILTER_COST',physical=physical,actual_game_seconds=actual,historical_samecases_seconds=before,cost_ratio=actual/before,identical_full_records=sum(a['record']==b['record']for a,b in zip(prior,rows)),outcome_transitions={a+'->'+b:n for (a,b),n in transitions.items()},filter_skips_by_role=dict(hits),bank_hits=sum(m.get('bank_hit',False)for m in moves),proof_visit_counts=dict(historical=sum(x['proof_nodes']for x in oldmoves),filtered=sum(x['proof_nodes']for x in moves)),native_reported_nodes=dict(historical=sum(x['search_nodes']for x in oldmoves),filtered=sum(x['search_nodes']for x in moves)),source_unchanged=True,scope='ALL64exposedfirst8ordinalfamilies/fourfoes/bothroles/oldfixedR1260. BOTHactorsPN1K/coldbank/normal4096, strictabsencefilterUNKNOWNonly. Chronologicalhistoricaltiming/concurrentload notnoisefreecausalspeedup. No current1997learningchange/default/genericdeadness/DRAW or freshlearningclaim.')
 with (OUT/'result.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='physical'}))
if __name__=='__main__':run()
