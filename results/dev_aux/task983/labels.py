from pathlib import Path
import json,urllib.request,urllib.parse,time,hashlib,chess
R=Path.cwd();O=R/'results/dev_aux/task985';O.mkdir(exist_ok=False);rows=[];start=time.monotonic();d=json.loads((R/'results/dev_aux/task984/roots.json').read_bytes())
with (O/'responses.jsonl').open('x',encoding='utf-8') as f:
 for r in d['roots']:
  if time.monotonic()-start>=300:break
  url='https://tablebase.lichess.ovh/standard?'+urllib.parse.urlencode({'fen':r['fen']})
  try:
   with urllib.request.urlopen(url,timeout=min(15,max(1,300-(time.monotonic()-start)))) as response:raw=response.read(2000001);assert len(raw)<=2000000;z=json.loads(raw)
   assert sorted(m['uci'] for m in z['moves'])==r['legal'];row=dict(seed=r['seed'],fen=r['fen'],status=200,raw_utf8=raw.decode(),sha256=hashlib.sha256(raw).hexdigest(),seconds=time.monotonic()-start);print(r['ordinal'],z['category'],len(z['moves']),round(time.monotonic()-start,2),flush=True)
  except Exception as ex:row=dict(seed=r['seed'],fen=r['fen'],error=type(ex).__name__+': '+str(ex));print(row['error'],flush=True)
  f.write(json.dumps(row)+'\n');f.flush();rows.append({k:v for k,v in row.items() if k!='raw_utf8'})
(O/'result.json').write_text(json.dumps(dict(status='API_LABEL_READ_COMPLETE' if len(rows)==32 else 'PARTIAL_FUSE',actual_requests=len(rows),rows=rows,seconds=time.monotonic()-start),indent=2),encoding='utf-8')
