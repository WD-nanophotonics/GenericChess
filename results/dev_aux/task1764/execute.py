"""All valid4x4 KRK roots, independent answers and public proof execution."""
import json,time,array,hashlib
from pathlib import Path
from generic_chess.core.actions import action_to_dict
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.terminal import terminal_result
from scripts.generic_proof_fixtures import compile_krk,krk_state
from scripts.generic_win_proof import prove_win,PROVEN_WIN
p=Path('results/dev_aux/task1764');d=json.loads((p/'plan.json').read_text());start=time.perf_counter();deadline=start+d['total_seconds'];c=compile_krk()
assert hashlib.sha256(Path('scripts/generic_win_proof.py').read_bytes()).hexdigest()==d['solver_sha256']
w=Path('results/dev_aux/task1741/wdl4.bin').read_bytes();ranks=array.array('H');ranks.frombytes(Path('results/dev_aux/task1741/rank4.bin').read_bytes())
counts={};proofnodes=defenses=leaves=nodes=0;rows=0;failures=[]
with (p/'calls.jsonl').open('x') as log:
 for i in d['ids']:
  if time.perf_counter()>=deadline:break
  k,b,r,t=i//512,(i//32)%16,(i//2)%16,i%2;s=krk_state(c,k,b,r,t)
  result=prove_win(c,s,target=0,max_nodes=d['cap'],seconds=d['seconds'],max_depth=d['max_depth'],cancel=lambda:time.perf_counter()>=deadline)
  key=str((int(ranks[i]) if w[i] else None,result.status,result.reason));counts[key]=counts.get(key,0)+1;nodes+=result.nodes
  if result.status==PROVEN_WIN:
   assert w[i] in (1,2) and result.certificate.tree.rank==ranks[i]
   stack=[(s,result.certificate.tree)]
   while stack:
    state,tree=stack.pop();proofnodes+=1;term=terminal_result(state,c)
    if term.is_terminal:
     assert term.winner==0 and tree.rank==0 and not tree.edges and tree.terminal_kind==term.status.value;leaves+=1;continue
    aa=[a for a,_ in tree.edges];ll=set(legal_actions(state,c));assert aa and set(aa)<=ll
    if state.position.side_to_move==0:assert len(aa)==1
    else:assert set(aa)==ll;defenses+=1
    for action,child in tree.edges:assert child.rank<tree.rank;stack.append((apply_action(state,action,c),child))
  log.write(json.dumps(dict(id=i,library_wdl=w[i],library_DTM=int(ranks[i]) if w[i] else None,status=result.status,reason=result.reason,nodes=result.nodes,seconds=result.seconds,rank=result.certificate.tree.rank if result.certificate else None))+'\n');log.flush();rows+=1
  if rows%256==0:print('ROOTS',rows,'SECONDS',time.perf_counter()-start,flush=True)
out=dict(status='COMPLETE_ALL_VALID_ROOTS' if rows==len(d['ids']) else 'PARTIAL_CAP_PRESERVED',roots=rows,planned=len(d['ids']),counts=counts,nodes=nodes,
         proof_nodes_publicly_replayed=proofnodes,all_defense_frontiers=defenses,actual_winning_leaves=leaves,seconds=time.perf_counter()-start)
(p/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='counts'})
