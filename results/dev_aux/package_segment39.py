from pathlib import Path
import json,hashlib,zipfile,ast,time
R=Path.cwd();start=time.monotonic();files=[]
for n in range(884,962):
 P=R/f'results/dev_aux/task{n}'
 if P.exists():files.extend(p for p in P.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.py','.json','.jsonl','.txt'])
# Preserve executed analysis source, including operational mistakes and failed scientific paths.
s=(R/'.local_agent/dual39_analyze.py').read_text(encoding='utf-8-sig');(R/'results/dev_aux/task961/analyze.py').write_text(s,encoding='utf-8');files.append(R/'results/dev_aux/task961/analyze.py');files=sorted(set(files));members=[];archives=[];z=None;index=0
try:
 for p in files:
  if z is None or (z.fp.tell()>=12*1024*1024):
   if z:z.close()
   index+=1;name=f'ACTUAL_MATURE_20261014_39_{index:02}.zip';archives.append(name);z=zipfile.ZipFile(R/'results/dev_aux'/name,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)
  raw=p.read_bytes();rel=p.relative_to(R).as_posix();z.writestr(rel,raw);members.append(dict(path=rel,size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),archive=archives[-1]))
finally:
 if z:z.close()
manifest=dict(status='FROZEN_ALL39_SCIENTIFIC_OR_FAILED_RECORDS',committed_base='3b5ca8bae14b09e331c008b8f8de329c65a2468a',members=members,archives=[dict(name=n,size=(R/'results/dev_aux'/n).stat().st_size,sha256=hashlib.sha256((R/'results/dev_aux'/n).read_bytes()).hexdigest()) for n in archives],raw_bytes=sum(m['size'] for m in members),seconds=time.monotonic()-start,scope='ExactoriginalAgentgeneratedcode/params/positive/negative/censored/faileddata. InvalidB4records preserved, qualificationjson governsclaim. No rawSlack/account/userinput/privatecredentials.')
(R/'results/dev_aux/ACTUAL_MATURE_20261014_39_manifest.json').write_text(json.dumps(manifest,indent=2));print('PACK',len(members),manifest['raw_bytes'],[(a['name'],a['size']) for a in manifest['archives']],round(manifest['seconds'],3))
