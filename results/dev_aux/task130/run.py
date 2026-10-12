"""Run already-frozen actual material geometry/side/clock traces."""
import sys,time,json,math,hashlib
from pathlib import Path
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task130';sys.path.insert(0,str(ROOT/'results/dev_aux/task109'));import adapter
D=json.loads((OUT/'declaration.json').read_bytes());stop=lambda:adapter.stop_check(ROOT);stop();deadline=time.monotonic()+60;started=time.monotonic();binary,digest,q=adapter.validated_entry(ROOT/'.local_agent/material-selfplay/fairy-material.exe',ROOT/'results/dev_aux/task120/qualification.json');rows=[];configs=[]
if (OUT/'trace.json').exists():raise FileExistsError('No repeatedfrozenprobes')
for profile,w in enumerate(D['profiles']):
 e=None
 try:
  e=adapter.UCI(binary,ROOT,deadline,stop);configs.append(adapter.configure(e,w,OUT/'variant.ini',deadline,stop))
  for f in D['fixtures']:
   e.send('position fen '+f['fen']);e.send('eval');reply=e.ready();final=[z for z in reply if z.startswith('Final evaluation')];assert len(final)==1
   measured=float(final[0].split()[2]);expected=sum(w[k]*v for k,v in f['count_differences'].items())/208
   assert math.isfinite(measured) and abs(measured-expected)<=.011
   rows.append(dict(profile=profile,**f,measured_white_pawns=measured,expected_white_pawns=expected,reply=reply))
 finally:
  if e:e.close()
result=dict(complete=True,binary_sha256=digest,actual_trace_rows=len(rows),config_leaf_probes=25,rows=rows,configs=configs,geometry_side_clock_linear_agreement=True,wall_seconds=time.monotonic()-started,scope='Finiteactualtraceevidenceonly; no legalgamehistory/searchstrength/source-to-binaryproof')
adapter.atomic_json(OUT/'trace.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('rows','configs')}))