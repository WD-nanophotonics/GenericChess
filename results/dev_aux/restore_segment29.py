"""Verify exactarchive and optionallyrestore only frozen sciencepaths in sidemission."""
import json,hashlib,zipfile,sys,subprocess
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux';M=json.loads((O/'ACTUAL_MATURE_20261012_29_manifest.json').read_bytes());P=O/M['archive']
assert hashlib.sha256(P.read_bytes()).hexdigest()==M['archive_sha256']
extract='--extract' in sys.argv[1:]
if extract:
 assert subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip()=='sidemission'
with zipfile.ZipFile(P) as z:
 assert set(z.namelist())=={r['path'] for r in M['files']}
 for r in M['files']:
  data=z.read(r['path']);assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256']
  target=(R/r['path']).resolve();assert target.is_relative_to(O.resolve()) and r['path'].split('/')[2] in {f'task{n:03d}' for n in [467, 468, 469, 470, 472, 477, 478, 479, 480, 481, 482, 484, 491, 492, 493, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518]}
  if extract:
   if target.exists():assert target.read_bytes()==data,'refusetooverwritechangedscience:'+r['path']
   else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
print(json.dumps(dict(verified=True,members=M['members'],archive_sha256=M['archive_sha256'],extracted=extract)))
