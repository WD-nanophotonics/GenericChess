"""Extract byte-bound public records to a fresh own ignored path, then verify."""
import gzip,hashlib,json,io
from pathlib import Path,PurePosixPath
from tools.local_agent.common import ROOT
from tools.local_agent.slack_transport import save_plugin_original
from scripts.verify_leaper_kernel_signature import verify

def run(data,out):
    data=Path(data);out=Path(out).resolve();assert out.is_relative_to((ROOT/'.local_agent').resolve()) and not out.exists()
    manifest=json.loads((data/'manifest.json').read_text());count=0;names=set()
    for a in manifest['archives']:
        p=PurePosixPath(a['path']);assert not p.is_absolute() and '..' not in p.parts and len(p.parts)==1
        raw=(data/a['path']).read_bytes();assert len(raw)==a['bytes'] and hashlib.sha256(raw).hexdigest()==a['sha256']
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:payload=stream.read(64*1024**2+1)
        assert len(payload)==a['decoded_bytes']<=64*1024**2
        for m in json.loads(payload)['members']:
            p=PurePosixPath(m['path']);assert not p.is_absolute() and '..' not in p.parts and ':' not in str(p) and '\\' not in str(p) and str(p) not in names
            b=m['original_utf8'].encode('utf-8');assert len(b)==m['bytes'] and hashlib.sha256(b).hexdigest()==m['sha256']==manifest['member_hashes'][str(p)]
            names.add(str(p));save_plugin_original(out/str(p),b);count+=1
    assert count==manifest['members']==len(manifest['member_hashes'])
    result=verify(out,out/'public-reader.json');print({'literal_members':count,'research_returns':result['returns'],'Core_PVplies':result['literal_CorePVplies'],'new_Player':0});return result
if __name__=='__main__':
    import sys;run(*sys.argv[1:])
