import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; M=ROOT/"tests/fixtures/f41_semantic_prior_manifest.json"
def test_f41_manifest_is_frozen_and_production_scoped():
 d=json.loads(M.read_text()); p={k:v for k,v in d.items() if k!="manifest_sha256"}; assert hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()==d["manifest_sha256"]; assert all(d["constraints"].values()); assert len(d["inputs"])==20
 for b in d["inputs"].values(): assert hashlib.sha256((ROOT/b["path"]).read_bytes()).hexdigest()==b["sha256"]
 assert subprocess.run(["git","diff","--quiet","--","generic_chess"],cwd=ROOT).returncode==0
