from pathlib import Path
import gzip,hashlib,json
root=Path('results/dev_aux')
checked=[]
for task in ('task2606','task2609','task2610/attempt-2'):
    d=root/task
    manifest_path=d/'compressed-streams.json'
    if not manifest_path.exists():
        checked.append({'task':task,'status':'NO_MANIFEST'})
        continue
    entries=json.loads(manifest_path.read_text())
    for item in entries:
        archive=d/item['archive']; original=d/item['original']
        ah=hashlib.sha256(archive.read_bytes()).hexdigest()
        assert ah==item['archive_sha256'],(task,item['archive'],'archive hash')
        raw_hash=hashlib.sha256(); size=rows=0
        with gzip.open(archive,'rb') as f:
            for line in f:
                size+=len(line);rows+=1;raw_hash.update(line)
        assert size==item['original_bytes'],(task,item['original'],'size')
        assert raw_hash.hexdigest()==item['original_sha256'],(task,item['original'],'original digest')
        if original.exists():
            h=hashlib.sha256(); n=0
            with original.open('rb') as f:
                for block in iter(lambda:f.read(1024*1024),b''):
                    h.update(block); n+=len(block)
            assert n==size and h.hexdigest()==raw_hash.hexdigest(),(task,item['original'],'local original mismatch')
        checked.append({'task':task,'archive':item['archive'],'rows':rows,'bytes':size,
          'archive_sha256':ah,'decompressed_sha256':raw_hash.hexdigest(),'status':'PASS'})
out=root/'task2610/archive-verification.json'
out.write_text(json.dumps(checked,indent=2)+'\n',encoding='utf-8')
print(json.dumps(checked,indent=2))
