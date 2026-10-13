import os,json,time
import adapter as A
BASE=A.Engine
class ControlledEngine(BASE):
 def __init__(self,w,journal=None,policy='cold_per_query'):
  assert policy in ['cold_per_query','warm_game'];self.policy=policy;self.qindex=0;self.start_ready=[];super().__init__(w,journal)
 def begin_game(self):
  self.qindex=0;self.start_ready=[]
  if self.policy=='warm_game':self.send('isready');self.start_ready=self.until(lambda x:x=='readyok')
 def search(self,initial,history,nodes=1024):
  ready=[]
  if self.policy=='cold_per_query':self.send('isready');ready=self.until(lambda x:x=='readyok')
  else:assert self.start_ready and self.start_ready[-1]=='readyok'
  self.position(initial,history);self.send('auxstate');state=self.until(lambda x:x.startswith('info string auxstate '))[-1];t=time.monotonic();cmd=f'go nodes {nodes}';self.send(cmd);out=self.until(lambda x:x.startswith('bestmove '));q=dict(initial_sfen=initial,history=list(history),weights=self.w,nodes_limit=nodes,cold_isready=ready,state=state,command=cmd,lines=out,bestmove=out[-1].split()[1],seconds=time.monotonic()-t,reset_policy=self.policy,query_index_in_game=self.qindex,game_start_ready=list(self.start_ready));self.qindex+=1
  if self.journal:self.journal.write(json.dumps(q)+'\n');self.journal.flush();os.fsync(self.journal.fileno())
  return q
