"""Read frozen cold-child returns; no search or label-dependent selection."""
import argparse, gzip, hashlib, json
from pathlib import Path

def raw_bytes(p):
    p=Path(p)
    if not p.exists() and Path(str(p)+'.gz').exists(): p=Path(str(p)+'.gz')
    return gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()

def load(p):
    p=Path(p)
    if not p.exists() and Path(str(p)+'.gz').exists(): p=Path(str(p)+'.gz')
    raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
    return json.loads(raw)
def lines(p):
    p=Path(p)
    if not p.exists() and Path(str(p)+'.gz').exists(): p=Path(str(p)+'.gz')
    raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
    return [json.loads(x)for x in raw.decode('utf-8').splitlines()if x]
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'))

def assess(d):
    d=Path(d);p=load(d/'plan.json');data=load(d/'inputs.json');labels=load(d/'labels.json');r=load(d/'receipt.json');rows=lines(d/'queries.jsonl');qual=lines(d/'qualification.jsonl')
    assert hashlib.sha256(raw_bytes(d/'inputs.json')).hexdigest()==p['inputs_sha256']
    assert r['source_sha256']==p['source_sha256']
    assert r['status']=='CLOSED' and r['attempted']==r['queries']==len(rows)==len(p['slots'])
    assert len(qual)==len(rows)
    truth={canonical(x['action']):x['truth']['value']for x in labels['labelled_actions']}
    assert set(truth)=={canonical(x)for x in data['actions']}
    grouped={};seconds=0;pv=0
    for slot,row,q in zip(p['slots'],rows,qual):
        assert row['slot']==q['slot']==slot
        i=slot['branch'];assert row['child_state_sha256']==data['children'][i]['state_sha256']
        assert data['children'][i]['actor']==1-data['root']['actor']
        dec=row['decision'];target=slot['limits']['max_depth']; complete=dec['completed_depth']>=target
        # Full-window complete iterations give policy scores; incomplete target is UNKNOWN.
        score=next((x['score']for x in row['iterations']if x['depth']==target),None)
        assert (score is not None)==complete
        if complete: assert score==dec['score']
        item=dict(branch=i,action=data['actions'][i],truth_global_WDL=truth[canonical(data['actions'][i])],complete=complete,target=target,completed_depth=dec['completed_depth'],score_child=score,score_root=None if score is None else -score,termination=dec['termination_reason'],seconds=row['seconds'],nodes=dec['nodes'],qnodes=dec['qnodes'])
        grouped.setdefault(slot['phase'],[]).append(item);seconds+=row['seconds'];pv+=q['pv_steps']
    result={}
    for phase,items in grouped.items():
        assert sorted(x['branch']for x in items)==list(range(len(data['actions'])))
        full=all(x['complete']for x in items)
        winners=[]
        if full:
            best=max(x['score_root']for x in items);winners=[x['branch']for x in items if x['score_root']==best]
        result[phase]=dict(all_complete=full,best_branches=winners,best_global_WDL=[truth[canonical(data['actions'][i])]for i in winners],rows=items)
    return dict(queries=len(rows),query_seconds=seconds,pv_steps=pv,phases=result,scope='Same exposed root, cold independent child histories, fixed policy; not original warm-root causal reconstruction or holdout.')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('directory',type=Path);args=a.parse_args();print(json.dumps(assess(args.directory),ensure_ascii=False,indent=2))
