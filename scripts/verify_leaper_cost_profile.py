"""Read saved matched profiler results without executing Player or source capsules."""
from __future__ import annotations
import argparse,json,math,statistics,gzip,hashlib
from pathlib import Path
from collections import defaultdict
from scripts.leaper_cost_profile_trial import signature
from scripts.research_record import write_record

def load_json_file(path):
 return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())

def saved_returns(folder):
 archive=folder/'returns.json.gz'
 if not archive.exists():return [json.loads(p.read_bytes()) for p in sorted(folder.glob('return-*.json'))]
 rows=[]
 for key,entry in sorted(load_json_file(archive).items(),key=lambda kv:int(kv[0])):
  original=entry['original_utf8'].encode('utf-8')
  assert hashlib.sha256(original).hexdigest()==entry['sha256'],'return original hash mismatch'
  row=json.loads(original);assert row['slot']==int(key);rows.append(row)
 return rows

def analyze(folder):
 rows=saved_returns(folder)
 groups=defaultdict(dict)
 for r in rows:
  assert r['arm'] not in groups[(r['case_id'],r['depth'])], 'duplicate case/depth arm'
  groups[(r['case_id'],r['depth'])][r['arm']]=r
 output=[]
 totals=defaultdict(lambda:defaultdict(float))
 for (case,depth),arms in sorted(groups.items()):
  if set(arms)!=set(('before','profile','after')):continue
  b,p,a=[arms[k] for k in ('before','profile','after')]
  complete=all(r['decision']['completed_depth']==depth for r in (b,p,a))
  parity=signature(b['decision'])==signature(p['decision'])==signature(a['decision'])
  measured=[b['choose_seconds'],a['choose_seconds']]
  profile_path=folder/f'profile-{p["slot"]:03}.json'
  profile=(load_json_file(folder/'profiles.json.gz')[str(p['slot'])]['publication_copy'] if (folder/'profiles.json.gz').exists() else json.loads(profile_path.read_bytes()))
  funcs=profile['functions']
  exclusive=sum(f['exclusive_instrumented_cpu'] for f in funcs)
  assert math.isclose(exclusive,profile['total_tt'],abs_tol=1e-7),'profile exclusive conservation'
  assert all(f['exclusive_instrumented_cpu']>=0 for f in funcs)
  bucket=defaultdict(float)
  for f in funcs:
   path=f['file'].replace('\\','/')
   if '/generic_chess/' in path or path.startswith('generic_chess/'):
    project_path=path.split('/generic_chess/',1)[1] if '/generic_chess/' in path else path[len('generic_chess/'):]
    category=project_path.split('/')[0]
   elif path=='~':category='recorded_builtin_or_native'
   else:category='stdlib_or_other'
   bucket[category]+=f['exclusive_instrumented_cpu']
   if complete and parity:
    label=(path.split('/generic_chess/',1)[-1] if '/generic_chess/' in path else path[len('generic_chess/'):]) if ('/generic_chess/' in path or path.startswith('generic_chess/')) else '<external>/'+path.rsplit('/',1)[-1]
    key=(label,f['line'],f['name'])
    totals[depth][key]+=f['exclusive_instrumented_cpu']
  output.append({'case_id':case,'depth':depth,'complete':complete,'parity':parity,'profile_wall_ratio':p['choose_seconds']/statistics.mean(measured),'bracket_after_before_ratio':a['choose_seconds']/b['choose_seconds'],'before_seconds':measured[0],'after_seconds':measured[1],'profile_seconds':p['choose_seconds'],'instrumented_total_cpu':profile['total_tt'],'category_exclusive_instrumented_cpu':dict(bucket),'profile_slot':p['slot']})
 summaries={}
 for d in sorted({x['depth'] for x in output}):
  group=[x for x in output if x['depth']==d];eligible=[x for x in group if x['complete'] and x['parity']]
  summaries[str(d)]={'groups':len(group),'eligible':len(eligible),'incomplete':sum(not x['complete'] for x in group),'parity_failures':sum(x['complete'] and not x['parity'] for x in group),'median_profile_wall_ratio':statistics.median([x['profile_wall_ratio'] for x in eligible]) if eligible else None,'median_bracket_drift':statistics.median([x['bracket_after_before_ratio'] for x in eligible]) if eligible else None,'top_exclusive_instrumented_cpu':[{'file':k[0],'line':k[1],'name':k[2],'seconds':v} for k,v in sorted(totals[d].items(),key=lambda kv:kv[1],reverse=True)[:30]]}
 return {'rows':len(rows),'groups':output,'summary':summaries,'claims':'Instrumented process CPU and call attribution only. Not unbiased function cost, exclusive uninstrumented wall, Native-internal cost, removable fraction, speedup or strength.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=analyze(a.folder);write_record(a.output,r);print(json.dumps({'rows':r['rows'],'summary':r['summary']}))
