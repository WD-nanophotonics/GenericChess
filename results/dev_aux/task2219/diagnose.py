"""Unroll saved semantic DAGs into the original full-history tree verifier."""
from pathlib import Path
import json,hashlib,time
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from results.dev_aux.task2205.consume import decode_graph
from results.dev_aux.task2200.controls import unroll
from scripts.generic_session_win_proof import verify_session_certificate,SessionProofNode,SessionWinCertificate
OUT=Path('results/dev_aux/task2219')
def exact_height_tree(s,cert):
 gaps=[]
 def node(i):
  n=cert.nodes[i]
  edges=tuple((choice,node(j))for choice,j in n.edges)
  rank=0 if not edges else 1+max(child.rank for _,child in edges)
  assert rank<=n.rank
  if rank!=n.rank:gaps.append(dict(graph_index=i,graph_upper_rank=n.rank,exact_tree_height=rank))
  return SessionProofNode(rank,edges,n.terminal)
 tree=node(0)
 return SessionWinCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,cert.target,tree),gaps

def run():
 start=time.perf_counter();deadline=start+120;roots={r['index']:r for r in json.loads(Path('results/dev_aux/task2208/roots.json').read_text())};seen={};checks=[];refs=[]
 for task in(2208,2209):
  folder=Path(f'results/dev_aux/task{task}');assert json.loads((folder/'completion.json').read_text())['status']=='COMPLETE'
  for line in(folder/'certificates.jsonl').read_text().splitlines():
   x=json.loads(line)
   if x['arm']!='SEMANTIC_GRAPH':continue
   root=roots[x['root']];digest=hashlib.sha256((root['state_sha']+json.dumps(x['certificate'],sort_keys=True)).encode()).hexdigest();refs.append(dict(task=task,query=x['query'],certificate_key=digest))
   if digest in seen:continue
   if time.perf_counter()>=deadline:raise TimeoutError('closedunrollconsumer120cap')
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));cert=decode_graph(s,x['certificate']);tree=unroll(s,cert)
   receipt=verify_session_certificate(s,tree,max_nodes=262144,seconds=min(20.,max(0.,deadline-time.perf_counter())),cancel=lambda:time.perf_counter()>=deadline)
   normalized,gaps=exact_height_tree(s,cert)
   fixed=verify_session_certificate(s,normalized,max_nodes=262144,seconds=min(20.,max(0.,deadline-time.perf_counter())),cancel=lambda:time.perf_counter()>=deadline)
   seen[digest]=len(checks);checks.append(dict(root=x['root'],rank=cert.nodes[0].rank,graph_nodes=len(cert.nodes),certificate_key=digest,raw_unroll_receipt=receipt,rank_gaps=gaps,normalized_height=normalized.tree.rank,full_actual_history_tree_verification=fixed))
   with(OUT/'diagnostic-progress.json').open('w',encoding='utf-8')as f:json.dump(checks,f,indent=2)
   assert fixed['verified']
   if not receipt['verified']:assert receipt['reason']=='invalid_certificate'and gaps
 result=dict(status='PASS_EXACT_HEIGHT_ADAPTER_ORIGINAL_FULLHISTORY_TREE_VERIFIER',references=refs,unique_certificate_checks=checks,seconds=time.perf_counter()-start,new_proof_queries=0,scope='Original2218failurepreserved: graphstrictdecreasingranksareupperbounds,originaltreeverifierrequiresexactheight. DeriveexacttreeheightfromSAMEsavededgesonly, nopolicy/action/terminal/rootchange. Observedfinitepositiveproofs ONLY. TreeverifierreplaysALLdefenses withactualfullGameStatehistory, independentofgraphcanonicalmerging. SharedpublicCoreauthority, no universalquotient/generateddomain claim; no newstatistics/pricefit.')
 with(OUT/'result.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(status=result['status'],unique=len(checks),references=len(refs),seconds=result['seconds'])))
if __name__=='__main__':run()
