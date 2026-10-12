import json,math
TAG='$dev_aux_constant_telemetry_v1'
def encode(x,stats=None):
 if stats is None:stats={'arrays':0,'elements':0}
 if isinstance(x,dict):
  assert TAG not in x,'reserved marker collision'
  out={}
  for k,v in x.items():
   if k.endswith('_by_ply') and isinstance(v,list) and len(v)>=16 and type(v[0]) in (int,float,bool,str,type(None)):
    h=v[0];same=all(type(z) is type(h) and z==h and (type(h) is not float or h!=0 or math.copysign(1,z)==math.copysign(1,h)) for z in v)
    if same:out[k]={TAG:{'count':len(v),'value':h}};stats['arrays']+=1;stats['elements']+=len(v);continue
   out[k]=encode(v,stats)
  return out
 if isinstance(x,list):return [encode(v,stats) for v in x]
 return x

def decode(x):
 if isinstance(x,dict):
  if TAG in x:
   assert set(x)=={TAG};v=x[TAG];assert set(v)=={'count','value'} and type(v['count']) is int and v['count']>=16;return [v['value']]*v['count']
  return {k:decode(v) for k,v in x.items()}
 if isinstance(x,list):return [decode(v) for v in x]
 return x

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
