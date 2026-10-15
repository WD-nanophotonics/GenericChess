"""Complete equal-depth material root values, public-history runtime, no selective pruning."""
from pathlib import Path
from collections import Counter
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.transition import legal_successors
from generic_chess.core.terminal import TerminalStatus
from scripts.generic_proof_rnb_bridge import uci
from scripts.generic_session_native_material import _load_transport
O=Path('results/dev_aux/task1916');M=1000000
class Cut(Exception):pass
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def leaf(position,target,r):return sum((1 if p.owner==target else -1)*({'R':r,'N':720}.get(p.current_type_id,0)) for p in position.board if p is not None)
def terminal(t,target):return 0 if t.winner is None else M if t.winner==target else -M

def run():
 plan=json.loads((O/'plan.json').read_text());assert all(sha(p)==h for p,h in plan['source_sha'].items());pairs=json.loads(Path(plan['inputs']).read_text())['pairs'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text()));transport=_load_transport();started=time.perf_counter();done=0;status='COMPLETE'
 with (O/'queries.jsonl').open('x') as f:
  for d in plan['depths']:
   for pair in pairs:
    for ratio in (2.,4.):
     transport.stop_check(Path.cwd())
     if time.perf_counter()-started>=plan['seconds_cap']:status='GLOBAL_CAP';break
     record=deserialize_game_record(json.dumps(pair['common_record']));s=GameSession.replay(c,record);w=GameSession(c,record.initial_setup_key);witnesses=[w.state.position]
     for a in record.actions:w.submit(a);witnesses.append(w.state.position)
     assert w.state==s.state
     rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=tuple(witnesses));assert rt.history_witness_misses==0;target=pair['role'];r=int(720*ratio);begin=time.perf_counter();nodes=0;values=[];cuts=0
     def poll():
      if time.perf_counter()-started>=plan['seconds_cap'] or time.perf_counter()-begin>=plan['query_seconds'] or nodes>=plan['query_nodes']:raise Cut()
     def ab(depth,alpha,beta):
      nonlocal nodes,cuts
      poll();nodes+=1;t=rt.terminal_status
      if t.status is not TerminalStatus.ONGOING:return terminal(t,target)
      if depth==0:return leaf(rt.position,target,r)
      maximizing=rt.position.side_to_move==target;v=-M*2 if maximizing else M*2
      for a in sorted(rt.legal_actions(checkpoint=poll),key=uci):
       rt.push(a,checkpoint=poll)
       try:child=ab(depth-1,alpha,beta)
       finally:rt.pop()
       if maximizing:v=max(v,child);alpha=max(alpha,v)
       else:v=min(v,child);beta=min(beta,v)
       if beta<=alpha:cuts+=1;break
      return v
     complete=True;public_check=True
     try:
      for a in sorted(rt.legal_actions(checkpoint=poll),key=uci):
       rt.push(a,checkpoint=poll)
       try:v=ab(d-1,-M*2,M*2)
       finally:rt.pop()
       values.append(dict(action=uci(a),score=v))
      if d==2:
       # Independent public immutable depth2 values, same full historical root.
       direct=[]
       for a,child in legal_successors(s.state,c):
        if child.terminal_status.status is not TerminalStatus.ONGOING:v=terminal(child.terminal_status,target)
        else:
         vs=[terminal(grand.terminal_status,target) if grand.terminal_status.status is not TerminalStatus.ONGOING else leaf(grand.position,target,r) for _,grand in legal_successors(child,c)];v=min(vs)
        direct.append(dict(action=uci(a),score=v))
       assert sorted(direct,key=lambda x:x['action'])==values
     except Cut:complete=False
     assert rt.depth==0 and rt.position==s.state.position and rt.terminal_status==s.state.terminal_status
     best=max((v['score'] for v in values),default=None) if complete else None;scoremap={v['action']:v['score'] for v in values};chosen={str(a['ratio']):dict(action=a['uci'],score=scoremap.get(a['uci']),regret=None if best is None else best-scoremap[a['uci']]) for a in pair['alternatives']};row=dict(pair=pair['pair'],family=pair['family'],role=target,depth=d,ratio=ratio,complete=complete,nodes=nodes,cuts=cuts,seconds=time.perf_counter()-begin,values=values,best=best,best_actions=[v['action'] for v in values if v['score']==best] if complete else None,original_choices=chosen,public_depth2_check=(d==2 and complete),history_witnesses=len(witnesses),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest())
     f.write(json.dumps(row)+'\n');f.flush();done+=1
     if done%6==0:print(json.dumps(dict(done=done,seconds=time.perf_counter()-started)),flush=True)
    if status!='COMPLETE':break
   if status!='COMPLETE':break
 with (O/'completion.json').open('x') as f:json.dump(dict(status=status,completed=done,expected=66,seconds=time.perf_counter()-started,source_unchanged=all(sha(p)==h for p,h in plan['source_sha'].items())),f,indent=2)
if __name__=='__main__':run()
