from pathlib import Path
import gzip, hashlib, json, re
D=Path('results/dev_aux/task2610/attempt-2')
manifest=[]
for name in ('eval-queries.jsonl','eval-games.jsonl'):
    src=D/name; dst=D/(name+'.gz')
    h=hashlib.sha256(); n=0; rows=0; sensitive=[]
    key_bad=re.compile(r'(password|secret|credential|api[_-]?key|bearer|email|phone)',re.I)
    text_bad=re.compile(r'(gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{15,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)',re.I)
    with src.open('rb') as fin, dst.open('wb') as rawout:
        with gzip.GzipFile(fileobj=rawout,mode='wb',compresslevel=9,mtime=0,filename='') as gz:
            for line in fin:
                n+=len(line); rows+=1; h.update(line)
                obj=json.loads(line)
                def walk(x,path=''):
                    if isinstance(x,dict):
                        for k,v in x.items():
                            if key_bad.search(k): sensitive.append(f'key:{path}.{k}')
                            walk(v,f'{path}.{k}')
                    elif isinstance(x,list):
                        for i,v in enumerate(x): walk(v,f'{path}[{i}]')
                    elif isinstance(x,str) and text_bad.search(x): sensitive.append(f'value:{path}')
                walk(obj)
                gz.write(line)
    assert not sensitive, sensitive[:10]
    archive_sha=hashlib.sha256(dst.read_bytes()).hexdigest()
    rh=hashlib.sha256(); rn=0; rrows=0
    with gzip.open(dst,'rb') as f:
        for line in f:
            rn+=len(line); rrows+=1; rh.update(line)
    assert (rn,rh.hexdigest(),rrows)==(n,h.hexdigest(),rows)
    manifest.append({'original':name,'original_bytes':n,'original_sha256':h.hexdigest(),
      'rows':rows,'archive':dst.name,'archive_bytes':dst.stat().st_size,
      'archive_sha256':archive_sha,'compression':'gzip level 9, mtime=0, empty filename',
      'decompressed_exactly':True,'credential_pattern_scan':'PASS'})
(D/'compressed-streams.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(manifest,indent=2))
