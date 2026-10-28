"""Stream explicit piece_types arrays from large JSON without executing content.

Limited lexical extraction; escaped keys or nested quoted JSON remain UNKNOWN.
The hash records exact compressed bytes. Decoding a list must consume its whole
array. This complements, not erases, a general JSON-reader size-censoring gap.
"""
import gzip,json,re,time,hashlib
from pathlib import Path
from scripts.leaper_motion_signature import motion_family_signature
from scripts.research_record import write_record

def scan(path,cap=300*1024*1024):
    dec=json.JSONDecoder();pattern=re.compile(r'(?<!\\)"piece_types"\s*:\s*(\[)');buf='';total=0;found=[];start=time.perf_counter()
    with gzip.open(path,'rt',encoding='utf-8') as f:
        while True:
            part=f.read(65536);total+=len(part)
            if total>cap:raise ValueError('stream decoded cap')
            buf+=part
            while True:
                m=pattern.search(buf)
                if not m:
                    buf=buf[-256:];break
                try:
                    pieces,end=dec.raw_decode(buf,m.start(1));sig=motion_family_signature({'piece_types':pieces});found.append({'motion_signature':sig,'piece_types':pieces})
                except json.JSONDecodeError:
                    if not part:raise
                    buf=buf[m.start():]
                    if len(buf)>2*1024*1024:raise ValueError('piece_types array cap')
                    break
                except (ValueError,KeyError,TypeError):
                    found.append({'status':'NON_LEAP_OR_UNSUPPORTED'});end=m.end()
                buf=buf[end:]
            if not part:break
    return {'path':str(path),'compressed_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'decoded_characters':total,'arrays':found,'seconds':time.perf_counter()-start,'limitations':'Explicit lexical piece_types only; escaped keys/nested quoted JSON not covered; not full JSON validation.'}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--inventory',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    if Path(a.out).exists():raise FileExistsError(a.out)
    r=json.loads(Path(a.inventory).read_text());out=[]
    for g in r['gaps']:
        if g['reason']=='ValueError:decompressed size cap':
            x=scan(g['where']);out.append(x);write_record(Path(a.out),out);print(x['path'],len(x['arrays']),round(x['seconds'],3),flush=True)
