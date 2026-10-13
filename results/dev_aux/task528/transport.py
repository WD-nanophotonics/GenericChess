import json,time,os
from warm_adapter import ControlledEngine
class TransportEngine(ControlledEngine):
 def __init__(self,w,journal=None,policy='warm_game',transport='separate'):
  assert transport in ['separate','batched'];self.transport=transport;super().__init__(w,journal,policy)
 def search(self,initial,history,nodes=1024):
  ready=[];t0=time.perf_counter()
  if self.policy=='cold_per_query':self.send('isready');ready=self.until(lambda x:x=='readyok')
  else:assert self.start_ready and self.start_ready[-1]=='readyok'
  t1=time.perf_counter();position='position sfen '+initial+(' moves '+' '.join(history) if history else '');cmd=f'go nodes {nodes}'
  if self.transport=='batched':
   commands=[position,'auxstate',cmd]
   for command in commands:self.transcript.append({'in':command})
   self.p.stdin.write('\n'.join(commands)+'\n');self.p.stdin.flush();sent=time.perf_counter();state=self.until(lambda x:x.startswith('info string auxstate '))[-1];gotstate=time.perf_counter();lines=self.until(lambda x:x.startswith('bestmove '))
  else:
   self.position(initial,history);self.send('auxstate');state=self.until(lambda x:x.startswith('info string auxstate '))[-1];gotstate=time.perf_counter();self.send(cmd);sent=time.perf_counter();lines=self.until(lambda x:x.startswith('bestmove '))
  end=time.perf_counter();q=dict(initial_sfen=initial,history=list(history),weights=self.w,nodes_limit=nodes,cold_isready=ready,state=state,command=cmd,lines=lines,bestmove=lines[-1].split()[1],seconds=end-t0,reset_policy=self.policy,query_index_in_game=self.qindex,game_start_ready=list(self.start_ready),transport=self.transport,transport_costs=dict(cold_ready=t1-t0,position_to_go_sent=sent-t1,position_to_state=gotstate-t1,query_wall=end-t0))
  self.qindex+=1
  if self.journal:self.journal.write(json.dumps(q)+'\n');self.journal.flush();os.fsync(self.journal.fileno())
  return q
