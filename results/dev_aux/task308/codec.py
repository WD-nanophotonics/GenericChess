"""Private research-record codec; lossless sparse *_by_ply telemetry only."""
import math,collections,importlib.util
from pathlib import Path
R=Path.cwd();sp=importlib.util.spec_from_file_location('constant_codec',R/'results/dev_aux/task253/codec.py');C=importlib.util.module_from_spec(sp);sp.loader.exec_module(C)
TAG='$dev_aux_sparse_telemetry_v1'
def ident(v):
 if type(v) not in (int,float,bool) or (type(v) is float and not math.isfinite(v)):return None
 return type(v).__name__,repr(v)
def sparse(x,key=''):
 if isinstance(x,dict):return {k:sparse(v,k) for k,v in x.items()}
 if isinstance(x,list):
  if key.endswith('_by_ply') and len(x)>=64 and all(ident(v) is not None for v in x):
   counts=collections.Counter(ident(v) for v in x);mode,n=counts.most_common(1)[0]
   if n<len(x) and n*10>=len(x)*9:
    default=next(v for v in x if ident(v)==mode);return {TAG:dict(count=len(x),default=default,entries=[[i,v] for i,v in enumerate(x) if ident(v)!=mode])}
  return [sparse(v) for v in x]
 return x
def encode(x):return C.encode(sparse(x))
def decode_sparse(x):
 if isinstance(x,dict):
  if set(x)=={TAG}:
   z=x[TAG];assert type(z['count']) is int and z['count']>=64;out=[z['default'] for _ in range(z['count'])];seen=set()
   for i,v in z['entries']:assert type(i) is int and 0<=i<len(out) and i not in seen;seen.add(i);out[i]=v
   return out
  return {k:decode_sparse(v) for k,v in x.items()}
 if isinstance(x,list):return [decode_sparse(v) for v in x]
 return x
def decode(x):return C.decode(decode_sparse(x))
canonical=C.canonical