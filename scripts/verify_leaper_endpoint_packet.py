"""Verify/extract public literal data to a FRESH own ignored directory only.

Capsule sources remain DATA and are never executed. Existing project reader and
Core inspect the saved rules/records. No Player, game producer or solver runs.
"""
import argparse,gzip,hashlib,json
from pathlib import Path,PurePosixPath
from tools.local_agent.slack_transport import save_plugin_original
from tools.local_agent.common import ROOT
from scripts.verify_leaper_endpoint_runtime import verify,verify_curve

def run(data,out):
    data=Path(data);out=Path(out).resolve();assert out.is_relative_to((ROOT/'.local_agent').resolve()) and not out.exists();manifest=json.loads((data/'manifest.json').read_text());members=0
    for archive in manifest['archives']:
        raw=(data/archive['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==archive['sha256'];payload=gzip.decompress(raw);assert len(payload)==archive['decoded_bytes'];bundle=json.loads(payload)
        for item in bundle['members']:
            p=PurePosixPath(item['path']);assert not p.is_absolute() and '..' not in p.parts and ':' not in str(p)
            b=item['original_utf8'].encode('utf-8');assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'];save_plugin_original(out/str(p),b);members+=1
    assert members==manifest['members'];a=verify(out,out/'public-reader.json');b=verify_curve(out,out/'public-curve-reader.json');print({'literal_members':members,'research_returns':a['total_returns']+b['returns'],'Core_PVplies':a['total_literal_CorePVplies']+b['literal_CorePVplies'],'new_Player':0})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.data,a.out)
