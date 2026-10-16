"""Independent first-B actual-terminal pilot audit, no new search."""
from pathlib import Path
from collections import Counter
import hashlib,json,itertools
from results.dev_aux.task2021.physical_audit import audit,read,lines
from results.dev_aux.task1998.audit import ci
from scripts.generic_proof_rnb_bridge import orbit
ROOT=Path('results/dev_aux/task2020');OUT=Path('results/dev_aux/task2021')
def run():
 p=read(ROOT/'run-plan.json');done=read(ROOT/'completion.json');physical=audit(ROOT)
 rows=lines(ROOT/'games.jsonl');moves=lines(ROOT/'moves.jsonl');q=read(ROOT/'qualification.json')
 assert len(q['perfts'])==48 and q['native_search_go']==0 and q['source_unchanged']
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 roots=read(p['roots'])['roots'];assert len(roots)==16 and p['H']==96
 prior=set()
 for r in read('results/dev_aux/task2007/feasibility.json')['roots']:prior.update(orbit(tuple(r['root'])))
 for i,r in enumerate(roots):
  assert r['family']==i and r['phase']==('TRAIN' if i<8 else 'DEV') and tuple(r['root']) not in prior;prior.update(orbit(tuple(r['root'])))
 profile=None;cleared=False;intents=0
 for e in lines(ROOT/'run/transport.jsonl'):
  if e['event']=='PROFILE':
   profile=e['values'];r,n,b,pawn=profile
   assert f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}' in e['ack'];cleared=False
  elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
  elif e['event']=='INTENT':assert profile==e['R'] and cleared;cleared=False;intents+=1
 assert intents==physical['actual_native'] and not any(x.get('bank_hit',False) for x in moves)
 result=dict(status='PARTIAL_B_PILOT_RETAINED' if done['status']!='COMPLETE' else 'PASS_FIRST_B_COMPLETE_RULE_PILOT',physical=physical,recorded_game_seconds=sum(x['seconds'] for x in rows),outer_late_steps=sum(x['seconds']>=p['step_seconds'] for x in moves),scope='FirstB/N coarsepilot8TRAIN8DEV, fixedR1260/N720, actualrulemax96 commonPN1K. NoKRNfilter/utilityshortcut, modifiedjointmaterialNative. Tiny8familyconditional effect not human/fullChessB/Ntable or universalprice. Noresultbasedroots/DEVfit. Exploratory individual intervals.')
 declared_expected=48+48*len({720,read(ROOT/'FULL-lock-before-dev.json')['selected_B']}) if (ROOT/'FULL-lock-before-dev.json').exists() else None
 result['declared_complete_expected_games']=declared_expected
 result['unrun_frozen_games']=None if declared_expected is None else declared_expected-len(rows)
 result['unrun_TRAIN_games']=max(0,48-len(rows))
 if len(rows)>=48 and all(g['outcome']!='UNKNOWN' for g in rows[:48]):
  train=rows[:48];expected=[(f,s,b,720) for f in range(8) for b in (p['prices'] if f%2==0 else p['prices'][::-1]) for s in (0,1)]
  assert [(g['family'],g['candidate_side'],g['B'],g['opponent_B']) for g in train]==expected and all(g['phase']=='TRAIN' and g['slot']==i for i,g in enumerate(train))
  scores={b:sum(g['finite_event_score'] for g in train if g['B']==b) for b in p['prices']};maximizers=sorted(b for b,v in scores.items() if v==max(scores.values()));best=maximizers[0]
  lock=read(ROOT/'FULL-lock-before-dev.json');assert lock['selected_B']==best and lock['all_maximizers']==maximizers and lock['physical_games']==48 and lock['scores']=={str(k):v for k,v in scores.items()}
  result['training']=dict(scores=scores,selected_B=best,ratio=best/720,all_maximizers=maximizers,nonflat_families=sum(len({sum(g['finite_event_score'] for g in train if g['family']==f and g['B']==b) for b in p['prices']})>1 for f in range(8)),seconds=sum(g['seconds'] for g in train))
  if done['status']=='COMPLETE':
   assert all(g['outcome']!='UNKNOWN' and g['finite_event_score'] is not None for g in rows)
   prices=sorted({720,best});cells={(g['family'],g['candidate_side'],g['B'],g['opponent_B']):g for g in rows[48:]}
   assert len(rows)==48+48*len(prices)<=144 and set(cells)==set(itertools.product(range(8,16),(0,1),prices,(360,720,1440)))
   expecteddev=[(f,s,b,o) for f in range(8,16) for o in (360,720,1440) for b in (prices if f%2==0 else prices[::-1]) for s in (0,1)]
   assert [(g['family'],g['candidate_side'],g['B'],g['opponent_B']) for g in rows[48:]]==expecteddev and all(g['phase']=='DEV' for g in rows[48:])
   ds=[sum(cells[f,s,best,o]['finite_event_score']-cells[f,s,720,o]['finite_event_score'] for s in (0,1) for o in (360,720,1440))/6 for f in range(8,16)]
   result['NEW_vs_UNIT']=dict(mean=sum(ds)/8,family_deltas=ds,bootstrap8family_interval=ci(ds,20261016682021),same_price_cell=best==720,outcomes={b:dict(Counter(cells[f,s,b,o]['outcome'] for f in range(8,16) for s in (0,1) for o in (360,720,1440))) for b in prices},per_opponent={o:sum(cells[f,s,best,o]['finite_event_score']-cells[f,s,720,o]['finite_event_score'] for f in range(8,16) for s in (0,1))/16 for o in (360,720,1440)})
 with(OUT/'result.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='physical'}))
if __name__=='__main__':run()
