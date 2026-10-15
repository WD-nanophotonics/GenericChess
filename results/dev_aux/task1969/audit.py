"""Fixed equalnu and finite-event paired contrasts; no price/opponent selection."""
from pathlib import Path
from collections import Counter
import json,hashlib,random
from results.dev_aux.task1969.physical_audit import audit,read,lines
from scripts.generic_proof_rnb_bridge import orbit
OUT=Path('results/dev_aux/task1969');ROOT=Path('results/dev_aux/task1968')
def ci(ds,seed):
    rng=random.Random(seed);n=len(ds);bs=sorted(sum(ds[rng.randrange(n)] for i in range(n))/n for rep in range(10000));return[bs[250],bs[9749]]
def main():
    physical=audit(ROOT);p=read(ROOT/'run-plan.json');rows=lines(ROOT/'games.jsonl');moves=lines(ROOT/'moves.jsonl');assert physical['full_study_complete']
    cells={(x['family'],x['candidate_side'],x['R'],x['opponent_R'],x['candidate_proof']):x for x in rows};assert len(cells)==512
    contrasts=[]
    for proof in (False,True):
        for opp in (360,720,1440,2880):
            ds=[sum(cells[f,side,1440,opp,proof]['finite_event_score']-cells[f,side,720,opp,proof]['finite_event_score'] for side in (0,1))/2 for f in range(16)]
            contrasts.append(dict(proof=proof,opponent_R=opp,mean=sum(ds)/16,family_deltas=ds,interval16family=ci(ds,20261016651969+opp+proof),outcomes={str(r):dict(Counter(cells[f,side,r,opp,proof]['outcome'] for f in range(16) for side in (0,1))) for r in (720,1440)}))
    aggregate=[]
    for proof in (False,True):
        cs=[x for x in contrasts if x['proof']==proof];ds=[sum(x['family_deltas'][f] for x in cs)/4 for f in range(16)]
        unknown=sum(x['outcome']=='UNKNOWN' for x in rows if x['candidate_proof']==proof)/128
        mean=sum(ds)/16
        aggregate.append(dict(proof=proof,equalopponentweights=[.25]*4,mean=mean,family_deltas=ds,interval16family=ci(ds,20261016651970+proof),unknown_infinite_WDLbounds=[max(-2,mean-unknown),min(2,mean+unknown)]))
    interaction=[aggregate[1]['family_deltas'][i]-aggregate[0]['family_deltas'][i] for i in range(16)]
    cached=[m for m in moves if 'bank_hit' in m];assert not any(m['bank_hit'] for m in cached)
    # Independently bind allnewprofileACKs and everycoldquery.
    events=lines(ROOT/'run/transport.jsonl');profile=None;cleared=False;count=0
    for e in events:
        if e['event']=='PROFILE':
            profile=e['values'];r,n,b,pawn=profile
            ack=f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}'
            assert ack in e['ack'];cleared=False
        elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
        elif e['event']=='INTENT':assert profile==e['R'] and cleared;cleared=False;count+=1
    assert count==physical['actual_native']
    seen=set()
    for old in ('task1822/qualification.json','task1846/qualification.json','task1919/feasibility.json','task1922/feasibility.json','task1933/feasibility.json','task1938/feasibility.json','task1941/feasibility.json','task1963/cohort0/feasibility.json','task1963/cohort1/feasibility.json'):
        for r in read(Path('results/dev_aux')/old)['roots']:seen.update(orbit(tuple(r['root'])))
    for r in read('results/dev_aux/task1967/feasibility.json')['roots']:
        raw=tuple(r['root']);assert raw not in seen;seen.update(orbit(raw))
    out=dict(status='PASS',physical=physical,contrasts=contrasts,equalnu=aggregate,interaction=dict(mean=sum(interaction)/16,interval16family=ci(interaction,20261016651971)),source_unchanged=all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in p['source_sha'].items()),cost_seconds=sum(x['seconds'] for x in rows),scope='16freshfamilies/512physicalcases, fixedPRIOR64learned2vs1, equalfourfixedopponentprices, proofON/OFFmatched. NOT512independentfamilies, current65bestpricefit, unboundedWDL/humanprice orfullgeneratedrules; nosearch duringaudit.')
    with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
    print(json.dumps(out))
if __name__=='__main__':main()
