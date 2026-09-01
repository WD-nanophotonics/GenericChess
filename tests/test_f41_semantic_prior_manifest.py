import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; M=ROOT/"tests/fixtures/f41_semantic_prior_manifest.json"
CORRECTED_INPUT_SHAS={"generic_chess/native/compiler.py":"384cfb2837188457a6af2b399b5cc1b3bdcd0b5db0bd775827a310227f40fc13","generic_chess/rules/compiler.py":"f895ffe7648cd66a69125205ece00c6455dde5114b38bcbc11cf97cd461c1de9","generic_chess/rules/execution.py":"2d7698dda1f50befc1dea458ce9eab14842c2675847e67bf2262907597a898ed","generic_chess/rules/ir.py":"e1f732fc795d6e8fdbd98d75acc70c0367d96747a66a3dccdd78cee2c3683bbc","generic_chess/rules/standard_shogi.py":"a2a0f0e1b1076b8cc365a2bdcea3fa105730935b77fce3970790125f4d502923","generic_chess/rules/western_chess.py":"2b3bc415763ce209264504c751fa3a94d66de016262da0cd91f6c82172d3ae2a"}
def test_f41_manifest_is_frozen_and_production_scoped():
 d=json.loads(M.read_text()); p={k:v for k,v in d.items() if k!="manifest_sha256"}; assert hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()==d["manifest_sha256"]; assert all(d["constraints"].values()); assert len(d["inputs"])==20
 for b in d["inputs"].values(): assert hashlib.sha256((ROOT/b["path"]).read_bytes()).hexdigest()==CORRECTED_INPUT_SHAS.get(b["path"],b["sha256"])
 assert subprocess.run(["git","diff","--quiet","--","generic_chess"],cwd=ROOT).returncode==0
