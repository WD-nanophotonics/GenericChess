"""Pinned producer function excerpts; injected globals supplied by oracle_audit. No import-time jobs."""

def pushed(self,*a,**kw):
 global peak
 values=Counter();stack.append(values)
 try:out=push(self,*a,**kw)
 finally:stack.pop()
 pending[id(self._frames[-1])]=(c.iteration,bool(c.qlevel),values);peak=max(peak,len(pending));return out

def consume(frame,outcome):
 data=pending.pop(id(frame),None)
 if data is None:return
 iteration,qphase,values=data;totals[(iteration,qphase,outcome,'children')]+=1
 for k,v in values.items():totals[(iteration,qphase,outcome,k)]+=v

def popped(self,*a,**kw):
 if self._frames:consume(self._frames[-1],'unclassified')
 return pop(self,*a,**kw)

def stage(name,fn):
 def run(*a,**kw):
  bucket=p.stack[-1] if p.stack else outside
  frame=[time.perf_counter(),0.0];calls.append(frame)
  try:return fn(*a,**kw)
  finally:
   elapsed=time.perf_counter()-frame[0];calls.pop()
   bucket[name+'_calls']+=1;bucket[name+'_inclusive_seconds']+=elapsed;bucket[name+'_exclusive_seconds']+=elapsed-frame[1]
   if calls:calls[-1][1]+=elapsed
 return run
