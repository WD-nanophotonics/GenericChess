"""Verify existing cache/order records without replaying searches."""
import hashlib,io,json,subprocess,zipfile
from pathlib import Path
B=Path(__file__).parent;R='313900d3b5c0d9d79a117306ecf30cf6078dba43';I='docs/research/data/physical_publication_20261011.json';P='.local_agent/physical-publication-20261011/'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(p):return subprocess.check_output(['git','show',R+':'+p])
ib=git(I);i=json.loads(ib);a=git(i['archive']['path']);assert sha(a)==i['archive']['sha256'];z=zipfile.ZipFile(io.BytesIO(a));members={m['path']:m for m in i['members']};selected={}
def read(n):
 p=P+n;b=z.read(p);m=members[p];assert sha(b)==m['sha256'] and len(b)==m['bytes'];selected[p]=m
 return json.loads(b) if n.endswith('.json') else b.decode()
def checked(c):
 d=c['decision'];s=c['stats'];assert c['actual_root_restored'] and s['runtime_depth_balanced'] and s['runtime_pushes']==s['runtime_pops']
 for k in set(d)&set(s):assert d[k]==s[k]
 assert s['native_legality_calls']>0 and s['native_legality_fallbacks']==s['native_legality_operational_failures']==0
 return {k:d[k] for k in ['action','score','completed_depth','nodes','qnodes','tt_probes','tt_hits','tt_cutoffs','result_source','result_ordinary_qdepth','result_check_hard_qdepth','termination_reason']}
v=read('tt-order-result.json');assert v['complete'] and len(v['cells'])==4;order=[]
for c in v['cells']:order.append({'pvs':c['pvs'],'mask_bound_depth':c['mask_bound_depth'],'decision':checked(c),'probe_rows':c['probe_rows']})
for pvs in [False,True]:
 pair=[c for c in order if c['pvs']==pvs];assert len(pair)==2
 for k in ['action','score','completed_depth','nodes','qnodes']:assert pair[0]['decision'][k]==pair[1]['decision'][k]
 assert pair[0]['decision']['score']==17 and pair[0]['decision']['completed_depth']==3
w=read('warm-horizon-result.json');assert w['complete'] and len(w['cells'])==3;warm=[]
for c in w['cells']:
 arms={arm['mode']:[{'requested_depth':v['requested_depth'],'decision':checked(v)} for v in arm['calls']] for arm in c['arms']}
 fresh=arms['fresh_noTT_D1'][0]['decision'];current=arms['warm_current_TT_D2_then_D1'];masked=arms['warm_depthmasked_order_only_D2_then_D1']
 assert len(current)==len(masked)==2 and [v['requested_depth'] for v in current]==[2,1]
 assert fresh['completed_depth']==current[-1]['decision']['completed_depth']==masked[-1]['decision']['completed_depth']==1
 assert fresh['score']!=current[-1]['decision']['score'] and fresh['score']==masked[-1]['decision']['score']
 assert fresh['action']==masked[-1]['decision']['action']
 assert all(v['decision']['qnodes']==0 and v['decision']['result_ordinary_qdepth']==0 for arm in arms.values() for v in arm)
 warm.append({'root':c['root'],'arms':arms})
for n in ['tt_order.py','tt-order-declaration.json','warm_horizon.py','warm-horizon-declaration.json']:read(n)
out={'complete':True,'revision':R,'index_sha256':sha(ib),'archive_sha256':sha(a),'selected_members':selected,'tt_order':order,'warm_horizon':warm,'recorded_calls':19,'scope':'Independent record/source audit, not execution. Depthmask changes only returned probe-entry depth, keeps stored replacement/order labels. Fixed EP work matches with/without sufficient bound reuse; no zero-cutoff/exact-value theorem. Warm D1/q0 metadata is iteration policy and a cache-dependent value, not fresh horizon.'}
(B/'cache_scope.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps({'verified':19,'warm':[{ 'root':c['root'],'scores':{m:arm[-1]['decision']['score'] for m,arm in c['arms'].items()}} for c in warm]}))
