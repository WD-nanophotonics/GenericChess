"""Package CLOSED role-local pilot outputs; does not run or resume experiments."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

def pack(output, destination):
    load=lambda name:json.loads((output/(name+'.json')).read_bytes())
    summary=load('summary')
    assert summary['status']=='CLOSED'
    slots=load('slots'); games=[]
    for slot in slots:
        path=output/('game-'+str(slot['slot'])+'.json')
        if slot['status']=='not_started':
            assert not path.exists()
        else:
            games.append(json.loads(path.read_bytes()))
    assert len(games)==summary['attempted']
    packet={k:load(k) for k in ['config','inputs','slots','summary','models']}
    for name in ['runtime','root-overlap']:
        if (output/(name+'.json')).exists(): packet[name]=load(name)
    packet['games']=games
    raw=json.dumps(packet,ensure_ascii=True,allow_nan=False,separators=(',',':')).encode()
    compressed=gzip.compress(raw,mtime=0)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as f: f.write(compressed)
    return dict(path=str(destination),bytes=len(compressed),sha256=hashlib.sha256(compressed).hexdigest(),
                uncompressed_sha256=hashlib.sha256(raw).hexdigest(),games=len(games),
                planned=len(slots),not_started=summary['not_started'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('output',type=Path); p.add_argument('destination',type=Path); a=p.parse_args()
    print(json.dumps(pack(a.output,a.destination),ensure_ascii=True))
