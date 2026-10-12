"""Verify or restore exact segment14 data in this sidemission checkout."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[2];BASE=R/'results/dev_aux'

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--extract',action='store_true');args=parser.parse_args()
 manifest=json.loads((BASE/'ACTUAL_MATURE_20261012_14_manifest.json').read_bytes());archive=BASE/manifest['archive']
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256'],'archive hash mismatch'
 expected={r['path']:r for r in manifest['rows']};assert len(expected)==manifest['files']
 if args.extract:
  branch=subprocess.check_output(['git','branch','--show-current'],cwd=R,text=True).strip()
  if branch!='sidemission':raise RuntimeError('Extract only in the auxiliary sidemission checkout')
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(expected) and z.testzip() is None
  pending=[]
  for name,row in expected.items():
   relative=Path(name);assert not relative.is_absolute() and '..' not in relative.parts
   assert len(relative.parts)>=4 and relative.parts[0:2]==('results','dev_aux')
   assert relative.parts[2] in {f'task{i}' for i in range(120,133)}
   dest=(R/relative).resolve();assert dest.is_relative_to((R/'results/dev_aux').resolve())
   raw=z.read(name);assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
   if args.extract:
    if dest.exists():
     if not dest.is_file() or hashlib.sha256(dest.read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('Refusing to overwrite changed file: '+name)
    else:pending.append((dest,raw))
  # All hashes/paths/existing-file collisions checked before any write.
  for dest,raw in pending:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 print(json.dumps(dict(verified_files=len(expected),extracted_files=len(pending),archive_sha256=manifest['archive_sha256'])))
if __name__=='__main__':main()