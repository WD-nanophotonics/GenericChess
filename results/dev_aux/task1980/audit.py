"""Independent schedule, physical terminal and fixed-nu validation audit; no search."""
from pathlib import Path
from collections import Counter
import json,hashlib,random,itertools
from results.dev_aux.task1980.physical_audit import audit,read,lines
from scripts.generic_proof_rnb_bridge import orbit
ROOT=Path('results/dev_aux/task1979');OUT=Path('results/dev_aux/task1980')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ci(ds,seed):
 rng=random.Random(seed);n=len(ds);bs=sorted(sum(ds[rng.randrange(n)] for _ in range(n))/n for rep in range(10000));return [bs[250],bs[9749]]
def stratified(groups,seed):
 rng=random.Random(seed);bs=[]
 for rep in range(10000):bs.append(sum(sum(g[rng.randrange(len(g))] for _ in g)/len(g) for g in groups)/len(groups))
 bs.sort();return[bs[250],bs[9749]]
def cohort(i):
 folder=ROOT/f'cohort{i}';p=read(folder/'run-plan.json');rows=lines(folder/'games.jsonl');moves=lines(folder/'moves.jsonl');physical=audit(folder)
 assert physical['full_study_complete'] and all(sha(k)==v for k,v in p['source_sha'].items())
 assert Counter(p['train_opponent_R'])=={360:4,720:4,1440:4,2880:4}
 for f in range(0,16,4):assert set(p['train_opponent_R'][f:f+4])=={360,720,1440,2880}
 assert all(x['candidate_proof_nodes']==1024 and x['opponent_nodes']==4096 and x['candidate_cached'] and x['candidate_proof'] for x in rows)
 def key(x):return x['family'],x['candidate_side'],x['R'],x['opponent_R']
 cells={key(x):x for x in rows};assert len(cells)==len(rows)
 active=list(p['prices']);prefix=[];ordinal=0;previous=0
 for round_index,(end,keep) in enumerate(zip((4,8,12,16),(7,4,2,1))):
  for f in range(previous,end):
   for r in (active if f%2==0 else list(reversed(active))):
    for side in (0,1):
     g=rows[ordinal];assert key(g)==(f,side,r,p['train_opponent_R'][f]) and g['phase']=='RACE';prefix.append(g);ordinal+=1
  scores={r:sum(g['finite_event_score'] for g in prefix if g['R']==r) for r in active}
  active=sorted(active,key=lambda r:(-scores[r],r))[:keep]
  lock=read(folder/f'race-round-{round_index}.json');assert lock['retained']==active and {int(k):v for k,v in lock['scores'].items()}==scores and lock['physical_games']==ordinal
  previous=end
 race=read(folder/'RACE-lock-before-control.json');assert ordinal==208 and race['selected_R']==active[0]
 assert race['case_keys']==[list(x) for x in sorted(key(g) for g in prefix)]
 train=rows[:416];assert all(x['phase']=='CONTROL' for x in rows[208:416])
 assert {key(x) for x in train}=={(f,side,r,p['train_opponent_R'][f]) for f in range(16) for side in (0,1) for r in p['prices']}
 scores={r:sum(x['finite_event_score'] for x in train if x['R']==r) for r in p['prices']};selected=min(scores,key=lambda r:(-scores[r],r));full=read(folder/'FULL-lock-before-dev.json')
 assert full['selected_R']==selected and full['RACE_R']==race['selected_R'] and full['RACE_fullTRAIN_regret']==scores[selected]-scores[race['selected_R']]
 assert {int(k):v for k,v in full['scores'].items()}==scores and full['physical_games']==416
 prices=sorted({720,race['selected_R'],selected});assert all(x['phase']=='DEV' for x in rows[416:])
 assert {key(x) for x in rows[416:]}==set(itertools.product(range(16,32),(0,1),prices,(360,720,1440,2880)))
 # Every real Native query has a matching profile ACK and cold CLEAR.
 profile=None;cleared=False;count=0
 for e in lines(folder/'run/transport.jsonl'):
  if e['event']=='PROFILE':
   profile=e['values'];r,n,b,pawn=profile
   assert f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}' in e['ack'];cleared=False
  elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
  elif e['event']=='INTENT':assert profile==e['R'] and cleared;cleared=False;count+=1
 assert count==physical['actual_native'] and not any(m.get('bank_hit',False) for m in moves)
 contrasts=[]
 for name,r in [('FULL',selected),('RACE',race['selected_R'])]:
  per=[]
  for opp in (360,720,1440,2880):
   ds=[sum(cells[f,side,r,opp]['finite_event_score']-cells[f,side,720,opp]['finite_event_score'] for side in (0,1))/2 for f in range(16,32)]
   pairs=[(cells[f,side,r,opp],cells[f,side,720,opp]) for f in range(16,32) for side in (0,1)]
   u=0 if r==720 else sum((a['outcome']=='UNKNOWN')+(b['outcome']=='UNKNOWN') for a,b in pairs)/32
   item=dict(opponent_R=opp,mean=sum(ds)/16,family_deltas=ds,interval16family=ci(ds,20261016661980+i+opp),candidate_outcomes=dict(Counter(a['outcome'] for a,b in pairs)),baseline_outcomes=dict(Counter(b['outcome'] for a,b in pairs)),unknown_WDLbounds=[max(-2,sum(ds)/16-u),min(2,sum(ds)/16+u)])
   per.append(item)
  ds=[sum(x['family_deltas'][f] for x in per)/4 for f in range(16)]
  contrasts.append(dict(selector=name,R=r,ratio=r/720,per_opponent=per,family_deltas=ds,mean=sum(ds)/16,interval16family=ci(ds,20261016661985+i),same_price_cell=r==720))
 return dict(status='PASS',cohort=i,physical=physical,race=race,full=full,contrasts=contrasts,game_seconds=sum(x['seconds'] for x in rows),race_seconds=sum(x['seconds'] for x in rows[:208]),fullTRAIN_seconds=sum(x['seconds'] for x in rows[:416]),outer_late_steps=sum(m['seconds']>=p['step_seconds'] for m in moves))
def main():
 completion=read(ROOT/'completion.json');assert completion['status']=='COMPLETE' and completion['finished_cohorts']==[0,1] and completion['source_unchanged']
 cohorts=[cohort(i) for i in (0,1)];aggregates=[]
 for selector in ('FULL','RACE'):
  cs=[next(c for c in x['contrasts'] if c['selector']==selector) for x in cohorts];groups=[c['family_deltas'] for c in cs]
  aggregates.append(dict(selector=selector,mean=sum(c['mean'] for c in cs)/2,stratified32family_interval=stratified(groups,20261016661980),percohort=[c['mean'] for c in cs],unknown_WDL_delta_bounds=[sum(sum(v['unknown_WDLbounds'][j] for v in c['per_opponent'])/4 for c in cs)/2 for j in (0,1)],ratios=[c['ratio'] for c in cs],scope='Two independently trained prices,32DEVfamilyclusters, equalcohort/opponent/role weights. Not32independentlearners or one universalprice. Identical RACE/FULL prices share physical DEV cells.'))
 seen=set()
 for old in ('task1822/qualification.json','task1846/qualification.json','task1919/feasibility.json','task1922/feasibility.json','task1933/feasibility.json','task1938/feasibility.json','task1941/feasibility.json','task1963/cohort0/feasibility.json','task1963/cohort1/feasibility.json','task1967/feasibility.json'):
  for r in read(Path('results/dev_aux')/old)['roots']:seen.update(orbit(tuple(r['root'])))
 for i in (0,1):
  for r in read(Path('results/dev_aux/task1978')/f'cohort{i}/feasibility.json')['roots']:
   raw=tuple(r['root']);assert raw not in seen;seen.update(orbit(raw))
 result=dict(status='PASS',campaign=completion,cohorts=cohorts,aggregate=aggregates,independent_input_families=64,primary_selector='FULL',scope='True finiteH24actualevent W-L, UNKNOWNdistinct. Prices jointly alter leaf/native/capture. KRN4 protectedR distribution only, not unlimitedWDL/humanprices/fullgeneratedsearch. No new search/proof/Native calls by audit.')
 with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(status=result['status'],aggregate=aggregates,games=sum(c['physical']['games'] for c in cohorts),moves=sum(c['physical']['moves'] for c in cohorts))))
if __name__=='__main__':main()
