"""Bind reviewed Windows-source hashes to immutable product Git text."""
import hashlib,json,subprocess
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2]
v=json.loads((B/'generator_scope.json').read_bytes())
base='b4108a68a7ee06327be39cb3a222939644085a52';rows=[]
for p,expected in v['source_sha256'].items():
 raw=(ROOT/p).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
 blob=subprocess.check_output(['git','-C',str(ROOT),'show',base+':'+p])
 assert raw.replace(b'\r\n',b'\n')==blob,(p,'source differs beyond CRLF')
 rows.append(dict(path=p,working_raw_sha256=expected,immutable_git_blob_sha256=hashlib.sha256(blob).hexdigest(),
  working_crlf_count=raw.count(b'\r\n'),lf_normalization_equals_immutable_blob=True))
out=dict(complete=True,immutable_product_git_sha=base,scope='Original Task042 raw hashes describe Windows working-file bytes; immutable Git blobs are normalized LF. Both byte meanings are explicit; original fields unchanged.',rows=rows,engine_calls=0)
(B/'source_binding.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('5reviewed sources bind to fixed product Git blobs by exact LF normalization; raw hashes preserved')
