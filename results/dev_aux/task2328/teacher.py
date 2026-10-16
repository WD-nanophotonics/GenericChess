"""Actual-history forced-WIN versus NO_FORCED_WIN tiers, never actual WDL."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2199.semantic_graph import verify_graph
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2328')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());assert read('results/dev_aux/task2322/result.json')['status']=='PASS_ALL14_SELECTION_NEGATIVE_CANDIDATES_AND_ACTUAL_CURSOR_ROLLOUTS';data=read('results/dev_aux/task2311/inputs.json');p=read('results/dev_aux/task2325/plan.json');roots={r['index']:r for r in read(p['input'])};games={r['slot']:r for r in map(json.loads,Path('results/dev_aux/task2325/games.jsonl').read_text().splitlines())};positive=defaultdict(list)
 def token(c,record,target):return(c.ruleset_fingerprint,json.dumps(record,sort_keys=True),target)
 for i,row in enumerate(map(json.loads,Path('results/dev_aux/task2325/certificates.jsonl').read_text().splitlines())):
  stop();g=games[row['slot']]
  if row['side']!=g['candidate_color']:continue
  r=roots[g['root']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));cert=decode_graph(s,row['certificate']);v=verify_graph(s,cert,max_nodes=65536,seconds=5.,cancel=lambda:False);assert v['verified'];positive[token(c,row['root_record'],row['side'])].append(dict(source_certificate=i,slot=row['slot'],verification=v))
 negative=defaultdict(list)
 for q in map(json.loads,Path('results/dev_aux/task2321/queries.jsonl').read_text().splitlines()):
  if q['admitted']:negative[q['context']].append(dict(query=q['query'],mode=q['mode']))
 rows=[]
 for r in data['contexts']:
  stop();c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text()));pp=positive.get(token(c,r['root_record'],r['side']),[]);nn=negative.get(r['context'],[]);assert not(pp and nn),'ContradictoryactualhistoryforcedWIN/refutationcertificates';label='FORCED_WIN'if pp else'NO_FORCED_WIN'if nn else'UNKNOWN';generic=bool(pp)or any(x['mode']=='GENERIC_FULL_REACHABILITY'for x in nn);rows.append(dict(context=r['context'],occurrences=len(r['occurrences']),label=label,positive_proofs=pp,negative_proofs=nn,generic_only_certified=generic))
 result=dict(status='PASS_ACTUAL_HISTORY_BINARY_TEACHER_TIERS_NO_CONTRADICTIONS',contexts=14,occurrences=27,labels=dict(Counter(r['label']for r in rows)),weighted_labels={k:sum(r['occurrences']for r in rows if r['label']==k)for k in('FORCED_WIN','NO_FORCED_WIN','UNKNOWN')},generic_only_certified_contexts=sum(r['generic_only_certified']for r in rows),all_sources_certified_contexts=sum(r['label']!='UNKNOWN'for r in rows),contradictions=0,rows=rows,seconds=time.perf_counter()-t,scope='ALL14actualfrozenroots; actualgenericpositivecerts versusoriginaltimedadmittednegativecerts afterindependent2322check. ExposedreferenceWDLnotusedtoassigntheselabels. Generic-onlyseparatefromreference-assistedconstruction; allcost/prepayexplicit. Binaryforced-WINability NOTactualWDLorwinprobability/zeroNprice ornewholdout. No classifier/NN/pricefit/defaultadoption.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
if __name__=='__main__':run()
