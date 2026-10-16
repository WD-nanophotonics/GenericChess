"""Independent complete-rule score/schedule/receipt checks; no new search."""
from pathlib import Path
from collections import Counter
import json,hashlib,random,itertools
from results.dev_aux.task2018.physical_audit import audit,read,lines
from results.dev_aux.task1998.audit import ci
from scripts.generic_proof_rnb_bridge import orbit
ROOT=Path('results/dev_aux/task2016');OUT=Path('results/dev_aux/task2018')
def run():
 p=read(ROOT/'run-plan.json');done=read(ROOT/'completion.json');physical=audit(ROOT)
 rows=lines(ROOT/'games.jsonl');moves=lines(ROOT/'moves.jsonl');q=read(ROOT/'qualification.json')
 assert len(q['perfts'])==160 and q['native_search_go']==0 and q['source_unchanged']
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 roots=read(p['roots'])['roots'];assert len(roots)==32 and p['H']==96
 for block in range(4):assert sorted(p['train_opponent_R'][4*block:4*block+4])==[360,720,1440,2880]
 prior=set()
 for path in Path('results/dev_aux/task2015/inputs.py').read_text(encoding='utf-8').split("for oldpath in (")[1].split('):')[0].split(','):
  path=path.strip().strip("'\" ")
  if not path:continue
  for root in read(path)['roots']:prior.update(orbit(tuple(root['root'])))
 for i,r in enumerate(roots):
  assert r['family']==i and r['phase']==('TRAIN' if i<16 else 'DEV') and tuple(r['root']) not in prior
  prior.update(orbit(tuple(r['root'])))
 profile=None;cleared=False;intents=0
 for e in lines(ROOT/'run/transport.jsonl'):
  if e['event']=='PROFILE':
   profile=e['values'];r,n,b,pawn=profile
   assert f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}' in e['ack'];cleared=False
  elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
  elif e['event']=='INTENT':assert profile==e['R'] and cleared;cleared=False;intents+=1
 assert intents==physical['actual_native']
 assert not any(x.get('bank_hit',False) for x in moves)
 result=dict(status='PARTIAL_RETAINED' if done['status']!='COMPLETE' else 'PASS_COMPLETE_RULE_COARSE_LEARNING',physical=physical,recorded_game_seconds=sum(x['seconds'] for x in rows),outer_late_steps=sum(x['seconds']>=p['step_seconds'] for x in moves),scope='One16TRAIN/16DEV learner, allactualfinite-ruleW-L/D. SamePN1K bothactors, strictUNKNOWN-onlyskip, coldperactorbanks; modifiedjointmaterialKRN4. No humanfit, precise/universal/fullChess price claim. Familyclusters16, not128 independentfamilies. Individual exploratory intervals notmultiplicityadjusted.')
 if len(rows)>=128 and all(g['outcome']!='UNKNOWN' for g in rows[:128]):
  train=rows[:128];expected=[(f,s,r,p['train_opponent_R'][f]) for f in range(16) for r in (p['prices'] if f%2==0 else p['prices'][::-1]) for s in (0,1)]
  assert [(g['family'],g['candidate_side'],g['R'],g['opponent_R']) for g in train]==expected
  assert all(g['slot']==i and g['phase']=='TRAIN' for i,g in enumerate(train))
  scores={r:sum(g['finite_event_score'] for g in train if g['R']==r) for r in p['prices']};maximizers=sorted(r for r,v in scores.items() if v==max(scores.values()));best=maximizers[0]
  lock=read(ROOT/'FULL-lock-before-dev.json');assert lock['selected_R']==best and lock['all_maximizers']==maximizers and lock['physical_games']==128 and lock['scores']=={str(k):v for k,v in scores.items()}
  result['training']=dict(scores=scores,selected_R=best,ratio=best/720,all_maximizers=maximizers,nonflat_families=sum(len({sum(g['finite_event_score'] for g in train if g['family']==f and g['R']==r) for r in p['prices']})>1 for f in range(16)),seconds=sum(g['seconds'] for g in train))
  if done['status']=='COMPLETE':
   assert all(g['outcome']!='UNKNOWN' and g['finite_event_score'] is not None for g in rows)
   prices=sorted({720,2520,best});cells={(g['family'],g['candidate_side'],g['R'],g['opponent_R']):g for g in rows[128:]}
   assert len(rows)==128+len(cells)==128+128*len(prices)<=512 and set(cells)==set(itertools.product(range(16,32),(0,1),prices,(360,720,1440,2880)))
   expecteddev=[(f,s,r,o) for f in range(16,32) for o in (360,720,1440,2880) for r in (prices if f%2==0 else prices[::-1]) for s in (0,1)]
   assert [(g['family'],g['candidate_side'],g['R'],g['opponent_R']) for g in rows[128:]]==expecteddev and all(g['phase']=='DEV' for g in rows[128:])
   labels={'UNIT':720,'PRIOR_TRAIN':2520,'NEW_FULL':best};result['contrasts']=[]
   for label,r in labels.items():
    ds=[sum(cells[f,s,r,o]['finite_event_score']-cells[f,s,720,o]['finite_event_score'] for s in (0,1) for o in (360,720,1440,2880))/8 for f in range(16,32)]
    result['contrasts'].append(dict(label=label,R=r,ratio=r/720,mean=sum(ds)/16,family_deltas=ds,bootstrap16family_interval=ci(ds,20261016682018),outcomes=dict(Counter(cells[f,s,r,o]['outcome'] for f in range(16,32) for s in (0,1) for o in (360,720,1440,2880))),per_opponent={o:sum(cells[f,s,r,o]['finite_event_score']-cells[f,s,720,o]['finite_event_score'] for f in range(16,32) for s in (0,1))/32 for o in (360,720,1440,2880)},same_price_cell=r==720))
   ds=[sum(cells[f,s,best,o]['finite_event_score']-cells[f,s,2520,o]['finite_event_score'] for s in (0,1) for o in (360,720,1440,2880))/8 for f in range(16,32)]
   result['new_vs_prior']=dict(mean=sum(ds)/16,bootstrap16family_interval=ci(ds,20261016682018),family_deltas=ds)
 with(OUT/'result.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ('physical','contrasts')}))
 if 'contrasts' in result:print(json.dumps([{k:v for k,v in c.items() if k not in ('family_deltas','per_opponent')}for c in result['contrasts']]))
if __name__=='__main__':run()
