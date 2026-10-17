"""Opt-in fixed-depth search with coefficient-independent path-seeded ordering.

Both arms use identical normal search and terminal constants. QUIET adds all
captures/promotions and all check evasions, stand-pat ONLY outside check.
Node/time/qstack limits reject whole query; no truncated qleaf training label.
This is a heuristic training search, never a complete rule WDL prover.
"""
from math import inf,isfinite
import time,random,hashlib
from results.dev_aux.task2492.learning import MATE,Sample,Receipt,BudgetEnd

class TrainingSearch:
 def __init__(self,depth=2,*,quiet=False,qstack=96):
  if type(depth)is not int or depth<1 or type(qstack)is not int or qstack<1:raise ValueError('invalid search limits')
  self.depth,self.quiet,self.qstack=depth,bool(quiet),qstack;self.last_stats={}
 def search(self,env,model,*,nodes=8192,seconds=5.,seed=0,cancel=lambda:None):
  began=time.perf_counter();count=0;samples=[];qnodes=0;qmax=0;standpat=0;evasions=0;terminal_nodes=0;leaves=0
  def poll():
   nonlocal count
   if count>=nodes or time.perf_counter()-began>=seconds:raise BudgetEnd('resource limit')
   if count%128==0:cancel()
   count+=1
  def ordered(actions,path):
   # Path (not transposition key) preserves history; extra qcalls cannot consume
   # randomness needed by a normal sibling or the opposite treatment.
   rng=random.Random(int.from_bytes(hashlib.sha256((str(seed)+'|'+path).encode()).digest()[:8],'big'))
   items=list(actions);rng.shuffle(items);return items
  def walk(depth,alpha,beta,path,qply):
   nonlocal qnodes,qmax,standpat,evasions,terminal_nodes,leaves
   poll();terminal=env.terminal()
   if terminal is not None:terminal_nodes+=1;return MATE*terminal,None,True,None
   phi=env.features();own=env.player()==0;a0,b0=alpha,beta
   if depth==0 and not self.quiet:leaves+=1;return model.raw(phi),phi,False,None
   if depth==0:
    qnodes+=1;qmax=max(qmax,qply)
    if qply>=self.qstack:raise BudgetEnd('qstack limit')
    checked=env.in_check();actions=list(env.actions())
    if checked:best=-inf if own else inf;best_phi=None;best_terminal=False;chosen=None;evasions+=1
    else:
     actions=[a for a in actions if env.tactical(a)];best=model.raw(phi);best_phi=phi;best_terminal=False;chosen=None;standpat+=1
     if own:alpha=max(alpha,best)
     else:beta=min(beta,best)
     if alpha>=beta:return best,best_phi,False,None
   else:actions=list(env.actions());best=-inf if own else inf;best_phi=None;best_terminal=False;chosen=None
   for a in ordered(actions,path):
    key=a.uci()if hasattr(a,'uci')else repr(a);env.push(a)
    try:score,pv,pvt,_=walk(max(0,depth-1),alpha,beta,path+'/'+key,qply+1 if depth==0 else 0)
    finally:env.pop()
    if(own and score>best)or(not own and score<best):best,best_phi,best_terminal,chosen=score,pv,pvt,a
    if own:alpha=max(alpha,best)
    else:beta=min(beta,best)
    if alpha>=beta:break
   if not isfinite(best):raise ValueError('ongoing state without legal actions')
   if depth>0:
    lo,hi=(-inf,best)if best<=a0 else(best,inf)if best>=b0 else(best,best)
    samples.append(Sample(tuple(phi),lo,hi,depth))
   if depth==0 and not actions:leaves+=1
   return best,best_phi,best_terminal,chosen
  try:
   cancel();value,pv,pvt,action=walk(self.depth,-inf,inf,'',0)
   receipt=Receipt(action,value,pv,pvt,tuple(samples),count,True,0,time.perf_counter()-began,'complete')
  except BudgetEnd as error:receipt=Receipt(None,None,None,False,(),count,False,0,time.perf_counter()-began,str(error))
  self.last_stats=dict(qnodes=qnodes,max_qply=qmax,standpat_nodes=standpat,check_evasion_nodes=evasions,actual_terminal_nodes=terminal_nodes,static_or_quiet_leaves=leaves,ordering='sha256(seed,full action path), coefficient-independent; strict best only',q_truncated_leaf_labels=0)
  return receipt
