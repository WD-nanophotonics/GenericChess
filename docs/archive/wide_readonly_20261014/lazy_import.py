"""Private C-owned importer, shares declared scalar compiler only."""
from readonly import *
import _wide_readonly_lazy as native
class CProvider(Provider):
 def __init__(self,c):
  super().__init__(c);t=time.perf_counter();chunks=[];offsets=[0]
  for owner in (0,1):
   for target in range(self.area):
    rows=self.rows.get((owner,target),())
    if rows:chunks.append(bytes(rows))
    offsets.append(offsets[-1]+len(rows))
  self.capsule=native.compile(self.n,len(self.types),len(self.slots),self.types,b''.join(chunks),bytes(self.paths),bytes(self.guards),bytes((C.c_uint32*len(offsets))(*offsets)))
  self.compile_seconds+=time.perf_counter()-t
 def pack(self,p):
  if p.ruleset_fingerprint!=self.c.support.ruleset_fingerprint or len(p.board)!=self.area:raise Unsupported('position mismatch')
  types=self.types
  board=p.board
  aux=[-1]*(len(self.slots)*3);values=dict(p.aux_state)
  for s in self.c.ir.aux_slots:
   for owner in ((-1,) if s.scope=='global' else (0,1)):
    key=(s.slot_id,owner)
    if key not in values:raise Unsupported('required aux value missing')
    v=values[key]
    if v is not None:
     if not isinstance(v,tuple) or len(v)!=2 or not all(type(x)is int and 0<=x<self.n for x in v):raise Unsupported('aux square malformed')
     aux[self.slots[s.slot_id]*3+(0 if owner==-1 else owner+1)]=v[1]*self.n+v[0]
  return board,aux
 def query(self,p,target,attacker,checkpoint=None,observer=None):
  if checkpoint is not None:checkpoint()
  t=time.perf_counter()
  try:board,aux=self.pack(p)
  except Unsupported:self.stats['fallbacks']+=1;return None
  self.stats['pack_seconds']+=time.perf_counter()-t;self.stats['imports']+=1
  polls=[0]
  def poll():
   polls[0]+=1
   if observer is not None:observer(polls[0])
   if checkpoint is not None:checkpoint()
  t=time.perf_counter()
  result,*audit=native.query(self.capsule,board,aux,target,attacker,poll if checkpoint is not None or observer is not None else None)
  self.stats['query_seconds']+=time.perf_counter()-t;self.stats['queries']+=1
  for k,v in zip(('rows','eligible','path_reads','guard_reads','polls'),audit):self.stats[k]+=v
  if checkpoint is not None:checkpoint()
  return bool(result)
