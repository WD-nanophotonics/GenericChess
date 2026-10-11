"""Existing raw backend records, no engine execution or archive extraction."""
import hashlib,io,json,statistics,subprocess,zipfile
from pathlib import Path
B=Path(__file__).parent
REV='ee48d0a55c7bda3d702f45ce2dc4162cc3bbc0ac'
def blob(p):return subprocess.check_output(['git','show',REV+':'+p])
index=json.loads(blob('docs/research/data/availability_core_20261011.json'));raw=blob(index['archive']['path'])
assert hashlib.sha256(raw).hexdigest()==index['archive']['sha256']
z=zipfile.ZipFile(io.BytesIO(raw));name='.local_agent/availability-core-20261011/residual-bridge.json';rec=z.read(name)
entry=next(x for x in index['members'] if x['member']==name);assert hashlib.sha256(rec).hexdigest()==entry['sha256']
d=json.loads(rec);assert d['complete'] and len(d['rows'])==80
rows=[]
for root in sorted({r['root'] for r in d['rows']}):
 cohort=[r for r in d['rows'] if r['root']==root]
 assert all(r["native_provider_active"] and r["runtime_counters"]["legal_provider_calls"]==r["work"]["legal_queries"] and r["runtime_counters"]["legal_provider_fallbacks"]==r["runtime_counters"]["legal_provider_operational_failures"]==0 for r in cohort if r["arm"].startswith("hybrid"))
 assert len(cohort)==10 and all(r['reason']=='completed_depth' and r['completed_depth']==2 for r in cohort)
 assert len({json.dumps(r['work'],sort_keys=True) for r in cohort})==1
 assert len({(r['move'],r['score']) for r in cohort})==1
 arms={}
 for arm in ('core','core-memo','hybrid','hybrid-memo','specialized'):
  rs=[r for r in cohort if r['arm']==arm];assert len(rs)==2 and {r['order'] for r in rs}=={0,1}
  fields=('legal_provider_seconds','legal_provider_payload_seconds','legal_provider_decode_binding_seconds','legal_provider_calls','legal_provider_actions','legal_provider_fallbacks','legal_provider_operational_failures')
  arms[arm]=dict(wall_mean=statistics.mean(r['wall_seconds'] for r in rs),setup_mean=statistics.mean(r['setup_seconds'] for r in rs),runtime={f:statistics.mean(r.get('runtime_counters',{}).get(f,0) for r in rs) for f in fields})
 h=arms['hybrid-memo'];s=arms['specialized'];T=h['wall_mean'];P=h['runtime']['legal_provider_seconds'];D=h['runtime']['legal_provider_decode_binding_seconds'];Y=h['runtime']['legal_provider_payload_seconds']
 assert 0<=D+Y<=P<=T and h['runtime']['legal_provider_fallbacks']==h['runtime']['legal_provider_operational_failures']==0
 rows.append(dict(root=root,work=cohort[0]['work'],arms=arms,ratio=T/s['wall_mean'],provider_share=P/T,decode_share=D/T,payload_share=Y/T,outside_provider=T-P,provider_unassigned=P-D-Y,
  hypothetical_decode_removed_ratio=(T-D)/s['wall_mean'],hypothetical_whole_provider_removed_ratio=(T-P)/s['wall_mean'],actions_per_push=h['runtime']['legal_provider_actions']/cohort[0]['work']['pushes'],
  setup_included_ratio=(T+h['setup_mean'])/(s['wall_mean']+s['setup_mean'])))
out=dict(complete=True,primary_revision=REV,archive_sha256=index['archive']['sha256'],member=name,member_sha256=entry['sha256'],source_only=True,rows=rows,
 limits='Two original correlated repeats; nested provider/payload/decode times. Perfect removal is a conditional arithmetic ceiling retaining all other work, not an implementation forecast. Provider residual includes kernel and validation; outside-provider includes sorting/evaluation/transition/terminal/history. Zero missing specialized runtime fields are not measured zero costs.')
(B/'frozen_attribution.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
for r in rows:print(r['root'], 'ratio',round(r['ratio'],3),'provider%',round(r['provider_share']*100,2),'decode%',round(r['decode_share']*100,2),'no-decode ratio',round(r['hypothetical_decode_removed_ratio'],3),'no-provider ratio',round(r['hypothetical_whole_provider_removed_ratio'],3),'actions/push',round(r['actions_per_push'],2))
