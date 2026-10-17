from pathlib import Path
import urllib.request,json,hashlib,zipfile,sys,shutil
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
P=R/'.local_agent/paid-td-20261017';u='https://raw.githubusercontent.com/WD-nanophotonics/GenericChess/3792d83068d5d0e61a0a33ebbf6850b414202c6f/results/dev_aux/DELTA_REPRO_20261017_92.zip'
with urllib.request.urlopen(u,timeout=45)as h:b=h.read()
assert hashlib.sha256(b).hexdigest()=='4ac271995a5c61d9ec8303a717dfc0be6be523926107a4c9a25653c79a2d9874';(P/'92.zip').write_bytes(b)
with zipfile.ZipFile(P/'92.zip')as z:
 m=json.loads(z.read('MANIFEST_20261017_92.json'));required=sum(e['file_size']if'file_size'in e else z.getinfo(n).file_size for n,e in m['files'].items());assert shutil.disk_usage(R).free>required+2*1024**3
 X=P/'exact';X.mkdir()
 for n,e in m['files'].items():
  p=(X/n).resolve();assert p.is_relative_to(X.resolve());a=z.read(n);assert hashlib.sha256(a).hexdigest()==e['sha256'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(a)
write_json(P/'exact-source-hashes.json',dict(status='ALL205_PAYLOAD_HASHES_PASS',source_sha='3792d83068d5d0e61a0a33ebbf6850b414202c6f',payloads=len(m['files']),raw_bytes=required,zip_bytes=len(b),zip_sha256=hashlib.sha256(b).hexdigest(),scope='Exactfixedpublishedsource/data, privatePRIMARYextractiononly. No AUXcheckout or actualexperimentproducer execution inferred.'))
print('EXACT',len(m['files']),'payloads',required,'rawbytes/',len(b),'zipbytes')
