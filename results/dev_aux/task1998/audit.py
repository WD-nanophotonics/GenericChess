"""Independent schedule, physical history and predeclared family-cluster audit."""
from pathlib import Path
from collections import Counter
import json,hashlib,random,itertools
from results.dev_aux.task1998.physical_audit import audit,read,lines
from scripts.generic_proof_rnb_bridge import orbit
ROOT=Path('results/dev_aux/task1997');OUT=Path('results/dev_aux/task1998')
def ci(ds,seed=20261016671998):
 rng=random.Random(seed);n=len(ds);vals=sorted(sum(ds[rng.randrange(n)] for _ in range(n))/n for _ in range(10000))
 return [vals[250],vals[9749]]
def dump(name,value):
 with (OUT/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
def training(rows,p):
 assert len(rows)>=832
 train=rows[:832];actual={};grid=p['prices'];seen=set();offset=0;active=list(grid);previous=0;rounds=[]
 assert all(x['phase']!='DEV' and x['family']<32 for x in train)
 assert all(x['candidate_cached'] and x['candidate_proof'] and x['candidate_proof_nodes']==1024 for x in train)
 assert p['opponent_cached'] and p['opponent_proof_nodes']==1024
 for block in range(8):assert sorted(p['train_opponent_R'][4*block:4*block+4])==[360,720,1440,2880]
 def consume(f,r,side,phase):
  nonlocal offset
  x=train[offset];key=(f,side,r,p['train_opponent_R'][f]);assert key not in seen;seen.add(key)
  assert (x['family'],x['candidate_side'],x['R'],x['opponent_R'])==key and x['phase']==phase and x['slot']==offset
  actual[key]=x;offset+=1
 for i,(end,keep) in enumerate(zip((4,8,16,32),(7,4,2,1))):
  for f in range(previous,end):
   for r in active if f%2==0 else active[::-1]:
    for side in (0,1):consume(f,r,side,'RACE')
  scores={r:sum(x['finite_event_score'] for x in train[:offset] if x['R']==r) for r in active}
  active=sorted(active,key=lambda r:(-scores[r],r))[:keep]
  saved=read(ROOT/f'race-round-{i}.json');assert saved['retained']==active and saved['physical_games']==offset and saved['scores']=={str(k):v for k,v in scores.items()}
  rounds.append(dict(end=end,retained=active,physical_games=offset));previous=end
 assert offset==288
 race=read(ROOT/'RACE-lock-before-control.json');assert race['selected_R']==active[0] and race['physical_games']==288
 for f in range(32):
  for r in grid if f%2==0 else grid[::-1]:
   for side in (0,1):
    if (f,side,r,p['train_opponent_R'][f]) not in seen:consume(f,r,side,'CONTROL')
 assert offset==832 and len(actual)==832
 assert set(actual)=={(f,s,r,p['train_opponent_R'][f]) for f in range(32) for s in (0,1) for r in grid}
 scores={r:sum(x['finite_event_score'] for x in train if x['R']==r) for r in grid};best=min(grid,key=lambda r:(-scores[r],r))
 full=read(ROOT/'FULL-lock-before-dev.json');assert full['selected_R']==best and full['scores']=={str(k):v for k,v in scores.items()} and full['RACE_R']==race['selected_R']
 # Actual transition order is immutable in append journal, not file modification time.
 assert not any(x['family']>=32 for x in rows[:832]) and all(x['phase']=='DEV' and x['family']>=32 for x in rows[832:])
 return dict(selected_R=best,ratio=best/720,scores=scores,tied_best=[r for r,v in scores.items() if v==scores[best]],race_R=race['selected_R'],race_score=scores[race['selected_R']],race_fullTRAIN_regret=scores[best]-scores[race['selected_R']],RACE_games=288,FULL_games=832,RACE_recorded_seconds=sum(x['seconds'] for x in train[:288]),FULL_recorded_seconds=sum(x['seconds'] for x in train),rounds=rounds)
def run():
 p=read(ROOT/'run-plan.json');done=read(ROOT/'completion.json');physical=audit(ROOT)
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 rows=lines(ROOT/'games.jsonl');moves=lines(ROOT/'moves.jsonl');qual=read(ROOT/'qualification.json')
 assert len(qual['perfts'])==624 and qual['native_search_go']==0 and qual['source_unchanged']
 roots=read(p['roots'])['roots'];assert len(roots)==48
 prior=set()
 oldpaths=('task1822/qualification.json','task1846/qualification.json','task1919/feasibility.json','task1922/feasibility.json','task1933/feasibility.json','task1938/feasibility.json','task1941/feasibility.json','task1963/cohort0/feasibility.json','task1963/cohort1/feasibility.json','task1967/feasibility.json','task1978/cohort0/feasibility.json','task1978/cohort1/feasibility.json','task1986/feasibility.json')
 for name in oldpaths:
  for r in read(Path('results/dev_aux')/name)['roots']:prior.update(orbit(tuple(r['root'])))
 for i,r in enumerate(roots):
  raw=tuple(r['root']);assert raw not in prior and r['phase']==('TRAIN' if i<32 else 'DEV');prior.update(orbit(raw))
 profile=None;cleared=False;intents=0
 for e in lines(ROOT/'run/transport.jsonl'):
  if e['event']=='PROFILE':
   profile=e['values'];r,n,b,pawn=profile
   assert f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}' in e['ack'];cleared=False
  elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
  elif e['event']=='INTENT':assert profile==e['R'] and cleared;cleared=False;intents+=1
 assert intents==physical['actual_native']
 assert not any(x.get('bank_hit',False) for x in moves)
 result=dict(status='PARTIAL_RETAINED' if done['status']!='COMPLETE' else 'PASS_COMMON_POLICY_FRESH_LEARNING',physical=physical,scope='ActualH24eventW-L/UNKNOWNdistinct; one32TRAIN learner,16sharedDEVfamilyclusters; modifiedjointmaterialNative4x4KRN only. FULL13grid notcontinuousoptimum/humanvalues/unlimitedWDL. No new search in audit.')
 if len(rows)>=832:
  t=training(rows,p);result['training']=t
 if done['status']=='COMPLETE':
  prices=sorted({720,1260,2160,t['selected_R']});cells={(x['family'],x['candidate_side'],x['R'],x['opponent_R']):x for x in rows[832:]}
  assert len(rows)==832+16*4*2*len(prices)<=1344
  assert set(cells)==set(itertools.product(range(32,48),(0,1),prices,(360,720,1440,2880)))
  labels={'UNIT':720,'PRIOR_POOLED':1260,'PRIOR_SEED1':2160,'NEW_FULL':t['selected_R']};result['labels']=labels;contrasts=[]
  for label,r in labels.items():
   ds=[sum(cells[f,s,r,o]['finite_event_score']-cells[f,s,720,o]['finite_event_score'] for s in (0,1) for o in (360,720,1440,2880))/8 for f in range(32,48)]
   m=sum(ds)/16;u=0 if r==720 else sum((cells[f,s,r,o]['outcome']=='UNKNOWN')+(cells[f,s,720,o]['outcome']=='UNKNOWN') for f in range(32,48) for s in (0,1) for o in (360,720,1440,2880))/128
   contrasts.append(dict(label=label,R=r,ratio=r/720,mean=m,family_deltas=ds,bootstrap16family_interval=ci(ds),UNKNOWN_WDL_bounds=[max(-2,m-u),min(2,m+u)],outcomes=dict(Counter(cells[f,s,r,o]['outcome'] for f in range(32,48) for s in (0,1) for o in (360,720,1440,2880))),per_opponent={o:sum(cells[f,s,r,o]['finite_event_score']-cells[f,s,720,o]['finite_event_score'] for f in range(32,48) for s in (0,1))/32 for o in (360,720,1440,2880)},same_price_cell=r==720))
  result['contrasts']=contrasts
  # All fixed-anchor pairwise contrasts reported, no chosen winner from DEV.
  result['new_vs_prior']={r:dict(mean=sum(ds)/16,bootstrap16family_interval=ci(ds),family_deltas=ds) for r in (1260,2160) for ds in [[sum(cells[f,s,t['selected_R'],o]['finite_event_score']-cells[f,s,r,o]['finite_event_score'] for s in (0,1) for o in (360,720,1440,2880))/8 for f in range(32,48)]]}
 result['recorded_game_seconds']=sum(x['seconds'] for x in rows);result['outer_late_steps']=sum(x['seconds']>=p['step_seconds'] for x in moves)
 dump('result.json',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ('physical','training','contrasts','new_vs_prior')}))
 if 'training'in result:print(json.dumps(result['training']))
 if 'contrasts'in result:print(json.dumps([{k:v for k,v in c.items() if k not in ('family_deltas','per_opponent')} for c in result['contrasts']]))
if __name__=='__main__':run()
