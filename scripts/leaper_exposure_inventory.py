"""Bounded published-archive movement exposure inventory; never executes rules.

Signature equality is conservative exposure; unequal finite registry entries are
not proof of global novelty or an independent holdout. Literal JSON capsules are
parsed as data only. Every error/oversize/unparsed semantic movement is a gap.
"""
import argparse,gzip,hashlib,json,subprocess,time
from pathlib import Path
from scripts.leaper_motion_signature import motion_family_signature
from scripts.research_record import write_record

def sha(b): return hashlib.sha256(b).hexdigest()

def inspect(paths, *, deadline_seconds=240, maximum_bytes=64*1024*1024, projection=motion_family_signature):
    started=time.perf_counter(); result={'files':[], 'rules':[], 'semantic':[], 'gaps':[], 'representative_piece_types':{}}; seen=set()
    def visit(value,where,depth=0):
        if depth>80:
            result['gaps'].append({'where':where,'reason':'nesting cap'});return
        if isinstance(value,dict):
            if isinstance(value.get('piece_types'),list) and value['piece_types']:
                pieces=value['piece_types']
                if all(isinstance(p,dict) and 'movement_atoms' in p for p in pieces):
                    try:
                        sig=projection(value)
                        result['representative_piece_types'].setdefault(sig,value['piece_types'])
                        payload=sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
                        if (where,payload) not in seen:
                            seen.add((where,payload));result['rules'].append({'where':where,'rule_json_sha256':payload,'motion_signature':sig,'board':value.get('board_size',[value.get('board_width'),value.get('board_height')]),'piece_count':len(pieces)})
                    except (ValueError,KeyError,TypeError) as e:
                        result['gaps'].append({'where':where,'reason':'nonprojectable RuleSet: '+str(e)[:160]})
            if 'patterns' in value and ('geometry' in value or 'ir_version' in value):
                result['semantic'].append({'where':where,'keys':sorted(value)[:24],'status':'IR needs metadata equivalence review; not projected'})
            for k,v in value.items():
                if k=='text' and isinstance(v,str) and v.lstrip().startswith(('{','[')):
                    try: visit(json.loads(v),where+'/literal:'+str(value.get('path','text')),depth+1)
                    except (ValueError,RecursionError) as e:result['gaps'].append({'where':where+'/text','reason':type(e).__name__})
                else:visit(v,where+'/'+str(k),depth+1)
        elif isinstance(value,list):
            for i,v in enumerate(value):visit(v,where+'/'+str(i),depth+1)
    for path in paths:
        if time.perf_counter()-started>deadline_seconds:
            result['gaps'].append({'where':str(path),'reason':'dispatch time cap; remaining files NOT_READ'});break
        p=Path(path);raw=p.read_bytes();entry={'path':p.as_posix(),'bytes':len(raw),'sha256':sha(raw)};result['files'].append(entry)
        try:
            if p.suffix=='.gz':
                import io
                with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:b=f.read(maximum_bytes+1)
            else:b=raw
            if len(b)>maximum_bytes:raise ValueError('decompressed size cap')
            value=json.loads(b);entry['decoded_bytes']=len(b);visit(value,p.as_posix())
        except (ValueError,OSError,EOFError,RecursionError) as e:
            result['gaps'].append({'where':p.as_posix(),'reason':type(e).__name__+':'+str(e)[:180]})
    result.update(seconds=time.perf_counter()-started,unique_signatures=sorted({x['motion_signature'] for x in result['rules']}),scope='enumerated tracked JSON and gzip files only; source/test/private/history/non-JSON exposure remains explicit UNKNOWN')
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    paths=subprocess.check_output(['git','ls-files','docs/research/data'],text=True).splitlines();paths=[p for p in paths if p.endswith(('.json','.json.gz'))]
    if Path(a.out).exists():raise FileExistsError(a.out)
    r=inspect(paths);draft=json.loads(Path('docs/research/data/leaper_static_eval_20261029/fresh-family-draft.json').read_text());r['proposal_source_sha256']=sha(Path('docs/research/data/leaper_static_eval_20261029/fresh-family-draft.json').read_bytes());r['proposals']=draft['proposed'];write_record(Path(a.out),r);print(json.dumps({'files':len(r['files']),'rules':len(r['rules']),'signatures':len(r['unique_signatures']),'semantic':len(r['semantic']),'gaps':len(r['gaps']),'seconds':r['seconds']}))
if __name__=='__main__':main()
