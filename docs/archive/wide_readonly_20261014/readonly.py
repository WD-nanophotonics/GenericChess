"""Private readonly compiler/adapter: static compiled capture IR, no position cache."""
from pathlib import Path
import sys,ctypes as C,time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
D=Path(__file__).resolve().parent
from generic_chess.core.semantic_executor import _own_anchor
class Unsupported(ValueError):pass
class Cell(C.Structure):_fields_=[(x,C.c_int32) for x in ('base','current','owner','promoted')]
class Row(C.Structure):_fields_=[(x,C.c_uint32) for x in ('source','type','path_offset','path_count','guard_offset','guard_count','clear')]
class Guard(C.Structure):_fields_=[(x,C.c_int32) for x in ('slot','owner','ref_kind','absolute','unequal')]
Poll=C.CFUNCTYPE(C.c_int)
lib=C.CDLL(str(D/'readonly.dll'))
lib.wide_query.argtypes=[C.c_uint32,C.POINTER(Cell),C.POINTER(Row),C.c_uint32,C.POINTER(C.c_uint16),C.POINTER(Guard),C.POINTER(C.c_int32),C.c_uint32,C.c_uint32,Poll,C.POINTER(C.c_uint64)]
lib.wide_query.restype=C.c_int
class Provider:
 def __init__(self,c):
  t=time.perf_counter();self.c=c;self.n=c.support.board_size;self.area=self.n*self.n
  if not (1<=self.n<=24 and self.area<=65535 and c.ir.ir_version==2):raise Unsupported('prototype dimensions/version')
  self.types={x:i for i,x in enumerate(sorted(c.support.type_metadata))}
  self.slots={s.slot_id:i for i,s in enumerate(c.ir.aux_slots)}
  if any(s.value_kind!='square_or_none' for s in c.ir.aux_slots):raise Unsupported('only square-or-none aux in this prototype')
  guards=[];paths=[];buckets={}
  for p in c.ir.patterns:
   if p.target.kind!='target_enemy':continue
   if p.guards or p.square_zone_guards:raise Unsupported('state/zone guards require Core')
   if any(q.kind!='path_clear' for q in p.path):raise Unsupported('other path predicates require Core')
   guardstart=len(guards)
   for g in p.slot_guards:
    if g.comparison not in ('eq','ne') or g.square_ref is None or g.value is not None:raise Unsupported('non-square slot guard')
    ref=g.square_ref
    if ref.kind not in ('source','target'):raise Unsupported('other square reference')
    meta=next(s for s in c.ir.aux_slots if s.slot_id==g.slot_id)
    guards.append(Guard(self.slots[g.slot_id],-1 if meta.scope=='global' else 0,0 if ref.kind=='target' else 1,0,int(g.comparison=='ne')))
   for tid in p.type_ids:
    for owner in (0,1):
     # Preserve Core fallback pattern/type/source/geometry/path order.
     for source in range(self.area):
      for gid in p.geometry_ids:
       geo=c.ir.geometry[gid]
       if geo.kind=='drop':continue
       if geo.kind not in ('ray','leap'):raise Unsupported('other geometry')
       if geo.atom_source is not None and geo.atom_source[0]!=tid:continue
       path=geo.paths.get(str(owner),{}).get(source,())
       for endpoint,target in enumerate(path):
        if geo.kind=='ray' and endpoint+1<(geo.min_steps or 1):continue
        prefix=() if geo.kind=='leap' else path[:endpoint]
        offset=len(paths);paths.extend(prefix)
        row=Row(source,self.types[tid],offset,len(prefix),guardstart,len(p.slot_guards),int(bool(p.path)))
        buckets.setdefault((owner,target),[]).append(row)
  if sum(map(len,buckets.values()))>2000000:raise Unsupported('bounded prototype row volume')
  self.rows={k:(Row*len(v))(*v) for k,v in buckets.items()}
  self.paths=(C.c_uint16*len(paths))(*paths);self.guards=(Guard*len(guards))(*guards)
  self.stats=dict(queries=0,imports=0,fallbacks=0,pack_seconds=0.,query_seconds=0.,rows=0,eligible=0,path_reads=0,guard_reads=0,polls=0)
  self.compile_seconds=time.perf_counter()-t
  self.compile_counts=dict(rows=sum(map(len,buckets.values())),path_indices=len(paths),guards=len(guards),static_bytes=sum(C.sizeof(v) for v in self.rows.values())+C.sizeof(self.paths)+C.sizeof(self.guards))
 def pack(self,p):
  if p.ruleset_fingerprint!=self.c.support.ruleset_fingerprint or len(p.board)!=self.area:raise Unsupported('position mismatch')
  board=(Cell*self.area)()
  for i,x in enumerate(p.board):
   if x is None:board[i]=Cell(-1,-1,-1,0)
   else:board[i]=Cell(self.types[x.base_type_id],self.types[x.current_type_id],x.owner,int(x.promoted))
  aux=(C.c_int32*(len(self.slots)*3))(*([-1]*(len(self.slots)*3)))
  values=dict(p.aux_state)
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
  rows=self.rows.get((attacker,target),(Row*0)())
  error=[];polls=[0]
  def poll():
   polls[0]+=1
   try:
    if observer is not None:observer(polls[0])
    if checkpoint is not None:checkpoint()
    return 0
   except BaseException as exc:error.append(exc);return 1
  callback=Poll(poll) if checkpoint is not None or observer is not None else Poll()
  audit=(C.c_uint64*4)();t=time.perf_counter()
  result=lib.wide_query(self.area,board,rows,len(rows),self.paths,self.guards,aux,target,attacker,callback,audit)
  self.stats['query_seconds']+=time.perf_counter()-t;self.stats['queries']+=1
  for k,v in zip(('rows','eligible','path_reads','guard_reads'),audit):self.stats[k]+=v
  self.stats['polls']+=polls[0]
  if error:raise error[0]
  if result<0:raise RuntimeError('readonly kernel failed without callback exception')
  if checkpoint is not None:checkpoint()
  return bool(result)
 def __call__(self,p,side,checkpoint=None):
  anchor=_own_anchor(p,self.c.support,side)
  if anchor is None:return False
  return self.query(p,anchor,1-side,checkpoint=checkpoint)
