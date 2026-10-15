"""Independent prospective schedule/lock/physical audit, no new search."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,random,statistics,itertools
from results.dev_aux.task1966.physical_audit import audit,read,lines
from scripts.generic_proof_rnb_bridge import orbit
ROOT=Path('results/dev_aux/task1965');OUT=Path('results/dev_aux/task1966')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
def interval(deltas,seed):
    rng=random.Random(seed);n=len(deltas)
    samples=sorted(sum(deltas[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
    return [samples[250],samples[9749]]
def audit_cohort(index):
    folder=ROOT/f'cohort{index}';p=read(folder/'run-plan.json');ap=read(folder/'audit-plan.json')
    assert p['slots']==[] and ap['selector'].startswith('Prospective')
    assert all(sha(file)==digest for file,digest in p['source_sha'].items())
    physical=audit(folder);rows=lines(folder/'games.jsonl');moves=lines(folder/'moves.jsonl')
    assert len(rows)==len(ap['slots']) and all({k:x[k] for k in expected}==expected for x,expected in zip(rows,ap['slots']))
    assert rows and all(x['candidate_cached'] and x['candidate_proof_nodes']==4096 for x in rows)
    cached=[x for x in moves if 'bank_hit' in x];assert not any(x['bank_hit'] for x in cached)
    # Fixed real history strictly grows, a new bank is created each game: no keys repeat.
    assert all(len({x['ply'] for x in moves if x['slot']==game['slot']})==game['moves'] for game in rows)
    slots={};prefix=[];active=list(p['prices']);previous=0
    def key(g):return g['family'],g['candidate_side'],g['R'],g['opponent_nodes']
    for g in rows:assert key(g) not in slots;slots[key(g)]=g
    ordinal=0
    for round_index,(end,keep) in enumerate(zip((4,8,12,16),(7,4,2,1))):
        for family in range(previous,end):
            for r in (active if family%2==0 else list(reversed(active))):
                for side in (0,1):
                    g=rows[ordinal];assert key(g)==(family,side,r,512) and g['phase']=='RACE';prefix.append(g);ordinal+=1
        scores={r:sum(g['finite_event_score'] for g in prefix if g['R']==r) for r in active}
        active=sorted(active,key=lambda r:(-scores[r],r))[:keep]
        lock=read(folder/f'race-round-{round_index}.json')
        assert lock['retained']==active and {int(k):v for k,v in lock['scores'].items()}==scores and lock['physical_games']==ordinal
        previous=end
    race=read(folder/'RACE-lock-before-control.json');assert ordinal==208 and race['selected_R']==active[0]
    assert race['case_keys']==[list(x) for x in sorted(key(g) for g in prefix)]
    train=[x for x in rows if x['phase']!='DEV'];assert len(train)==416
    assert all((f,side,r,512) in slots for f in range(16) for side in (0,1) for r in p['prices'])
    scores={r:sum(x['finite_event_score'] for x in train if x['R']==r) for r in p['prices']}
    selected=min(scores,key=lambda r:(-scores[r],r));full=read(folder/'FULL-lock-before-dev.json')
    assert full['selected_R']==selected and full['RACE_R']==race['selected_R'] and full['RACE_fullTRAIN_regret']==scores[selected]-scores[race['selected_R']]
    assert {int(k):v for k,v in full['scores'].items()}==scores and full['physical_games']==416
    assert all(x['phase']=='RACE' for x in rows[:208]) and all(x['phase']=='CONTROL' for x in rows[208:416]) and all(x['phase']=='DEV' for x in rows[416:])
    prices=sorted({720,race['selected_R'],selected})
    expected=list(itertools.product(range(16,32),(0,1),prices,(512,4096)))
    assert {key(x) for x in rows[416:]}==set(expected)
    # Actual Native profile ACK / cold CLEAR must precede EVERY search intent.
    events=lines(folder/'run/transport.jsonl');profile=None;cleared=False;intents=0
    for e in events:
        if e['event']=='PROFILE':
            profile=e['values'];r,n,b,pawn=profile
            ack=f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}'
            assert ack in e['ack'];cleared=False
        elif e['event']=='CLEAR':assert e['values']==profile;cleared=True
        elif e['event']=='INTENT':assert profile==e['R'] and cleared;intents+=1;cleared=False
    assert intents==physical['actual_native']
    contrasts=[]
    for name,r in [('RACE',race['selected_R']),('FULL',selected)]:
        for opponent in (512,4096):
            pairs=[(slots[f,side,r,opponent],slots[f,side,720,opponent]) for f in range(16,32) for side in (0,1)]
            deltas=[sum(slots[f,side,r,opponent]['finite_event_score']-slots[f,side,720,opponent]['finite_event_score'] for side in (0,1))/2 for f in range(16,32)]
            u=sum((a['outcome']=='UNKNOWN')+(b['outcome']=='UNKNOWN') for a,b in pairs)/32 if r!=720 else 0
            mean=sum(deltas)/16
            contrasts.append(dict(cohort=index,selector=name,R=r,ratio=r/720,opponent_nodes=opponent,actual_same_price_cell=r==720,mean_finite_event_delta=mean,family_deltas=deltas,bootstrap10000_family_interval=interval(deltas,20261016651966+100*index+opponent),unknown_WDL_delta_bounds=[max(-2,mean-u),min(2,mean+u)],candidate_outcomes=dict(Counter(a['outcome'] for a,b in pairs)),baseline_outcomes=dict(Counter(b['outcome'] for a,b in pairs))))
    return dict(status='PASS_PROSPECTIVE_PHYSICAL_LOCKS',cohort=index,physical=physical,race=race,full=full,contrasts=contrasts,cold_bank_queries=len(cached),cold_bank_hits=0,actual_game_seconds=sum(x['seconds'] for x in rows),race_game_seconds=sum(x['seconds'] for x in rows[:208]),fullTRAIN_game_seconds=sum(x['seconds'] for x in rows[:416]),source_unchanged=True)
def main():
    result=read(ROOT/'completion.json');assert result['status']=='COMPLETE' and result['finished_cohorts']==[0,1] and result['source_unchanged']
    cohorts=[audit_cohort(i) for i in (0,1)]
    # New family sets must be independent orbits acrosscohorts, TRAIN/DEV and oldinputs.
    seen=set();count=0
    for path in ('task1822/qualification.json','task1846/qualification.json','task1919/feasibility.json','task1922/feasibility.json','task1933/feasibility.json','task1938/feasibility.json','task1941/feasibility.json'):
        for r in read(Path('results/dev_aux')/path)['roots']:seen.update(orbit(tuple(r['root'])))
    for i in (0,1):
        data=read(Path('results/dev_aux/task1963')/f'cohort{i}/feasibility.json')
        assert data['status']=='FULL_32_INPUTS' and not data['prices_or_WDL_filter']
        for r in data['roots']:
            raw=tuple(r['root']);assert raw not in seen;seen.update(orbit(raw));count+=1
    aggregate=[]
    for name,opp in itertools.product(('RACE','FULL'),(512,4096)):
        cs=[next(c for c in x['contrasts'] if c['selector']==name and c['opponent_nodes']==opp) for x in cohorts]
        ds=[v for c in cs for v in c['family_deltas']]
        aggregate.append(dict(selector=name,opponent_nodes=opp,mean_finite_event_delta=sum(ds)/32,bootstrap32family_interval=interval(ds,20261016651967+opp),perseed_mean=[c['mean_finite_event_delta'] for c in cs],scope='Equal predeclaredcohortweight;32independentDEVfamilies shared acrossmethods/opponents. TWOtrainingseeds, not32trainingreplications; intervals conditional onlearnedselectors.'))
    out=dict(status='PASS',campaign=result,cohorts=cohorts,aggregate=aggregate,independent_fresh_families=count,scope='FiniteH24actualeventW-L/UNKNOWNdistinct, notunlimitedWDL, humanprice/recovereduniversalvalue or generalgenerateddomain. No newsearch bythisaudit.')
    write(OUT/'result.json',out);print(json.dumps(out))
if __name__=='__main__':main()
