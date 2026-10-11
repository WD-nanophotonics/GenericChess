"""Pair and validate completion-policy evidence; no search execution."""
import argparse,collections,json
from pathlib import Path
from scripts.research_record import write_record

def analyze(folder):
    data=json.loads((folder/'result.json').read_bytes());assert data['complete']
    rows=data['rows'];pairs=[]
    groups=collections.defaultdict(dict)
    for r in rows:
        s=r['stats'];assert r['root_restored'] and s['runtime_pushes']==s['runtime_pops']
        assert len({e['budget_identity'] for e in r['events']})<=1 and len({e['deadline'] for e in r['events']})<=1
        assert all(e['runtime_restored'] and e['runtime_balanced'] for e in r['events'])
        groups[(r['root'],r['seconds'],r.get('max_nodes'),r['native_requested'],r['order'])][r['arm']]=r
        phases={e['phase']:e for e in r['events']}
        if 'aborted' in phases:
            reserve=phases['reserve'];d=r['decision']
            assert d['action']==reserve['action'] and d['score']==reserve['score'] and d['principal_variation']==reserve['pv'] and d['result_ordinary_qdepth']==0
    for key,g in sorted(groups.items()):
        assert set(g)=={'baseline','fullq4_refresh'}
        a,b=g['baseline'],g['fullq4_refresh'];x,y=a['decision'],b['decision'];ph={e['phase']:e for e in b['events']};beg=ph.get('begin');end=ph.get('complete') or ph.get('aborted')
        pairs.append(dict(root=key[0],seconds=key[1],max_nodes=key[2],native_requested=key[3],order=key[4],baseline_depth=x['completed_depth'],refresh_depth=y['completed_depth'],delta_depth=y['completed_depth']-x['completed_depth'],baseline_q=x['result_ordinary_qdepth'],refresh_q=y['result_ordinary_qdepth'],same_action=x['action']==y['action'],same_score=x['score']==y['score'],baseline_source=x['result_source'],refresh_source=y['result_source'],refresh_completed='complete' in ph,refresh_aborted='aborted' in ph,refresh_seconds=None if not beg or not end else end['at']-beg['at'],refresh_visits=None if not beg or not end else end['nodes']+end['qnodes']-beg['nodes']-beg['qnodes'],baseline_visits=x['nodes']+x['qnodes'],refresh_total_visits=y['nodes']+y['qnodes'],baseline_native_enabled=a['stats']['native_legality_enabled'],refresh_native_enabled=b['stats']['native_legality_enabled'],baseline_native_calls=a['stats']['native_legality_calls'],refresh_native_calls=b['stats']['native_legality_calls'],baseline_fallbacks=a['stats']['native_legality_fallbacks'],refresh_fallbacks=b['stats']['native_legality_fallbacks']))
    counts=collections.Counter('lost' if p['delta_depth']<0 else 'gained' if p['delta_depth']>0 else 'same' for p in pairs)
    result=dict(calls=len(rows),pairs=len(pairs),depth=dict(counts),support_gains=sum(p['baseline_q']==0 and p['refresh_q']==4 for p in pairs),action_changes=sum(not p['same_action'] for p in pairs),refresh_abort_pairs=sum(p['refresh_aborted'] for p in pairs),wall_sum=sum(r['wall'] for r in rows),main=sum(r['decision']['nodes'] for r in rows),q=sum(r['decision']['qnodes'] for r in rows),pushes=sum(r['stats']['runtime_pushes'] for r in rows),pops=sum(r['stats']['runtime_pops'] for r in rows),legal_calls=sum(r['stats']['legal_generation_calls'] for r in rows),evaluation_calls=sum(r['stats']['evaluation_calls'] for r in rows),native_calls=sum(r['stats']['native_legality_calls'] for r in rows),native_fallbacks=sum(r['stats']['native_legality_fallbacks'] for r in rows),native_operational_failures=sum(r['stats']['native_legality_operational_failures'] for r in rows),cells=pairs)
    write_record(folder/'analysis.json',result);return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();r=analyze(a.folder);print(json.dumps({k:v for k,v in r.items() if k!='cells'},indent=2));print(json.dumps([p for p in r['cells'] if p['delta_depth'] or not p['same_action'] or p['refresh_aborted']],indent=2))