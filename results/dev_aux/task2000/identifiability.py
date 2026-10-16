"""TRAIN-only complete-trajectory identifiability; no new search or DEV reads."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib
ROOT=Path('results/dev_aux/task1997');OUT=Path('results/dev_aux/task2000')
def run():
 p=json.loads((ROOT/'run-plan.json').read_text());lock=json.loads((ROOT/'FULL-lock-before-dev.json').read_text());rows=[]
 with (ROOT/'games.jsonl').open() as f:
  for _ in range(832):
   x=json.loads(next(f));assert x['family']<32 and x['phase']!='DEV';rows.append(x)
 cells={(x['family'],x['candidate_side'],x['R']):x for x in rows};assert len(cells)==832
 wanted={x['slot'] for x in rows};moves=defaultdict(list)
 with (ROOT/'moves.jsonl').open() as f:
  for line in f:
   x=json.loads(line)
   if x['slot'] not in wanted:break
   moves[x['slot']].append(x)
 groups=defaultdict(list);first=Counter();byprice={}
 for r in p['prices']:
  records=[cells[f,s,r]['record'] for f in range(32) for s in (0,1)]
  signature=hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest();groups[signature].append(r)
  differences=Counter()
  for f in range(32):
   for side in (0,1):
    a,b=cells[f,side,720],cells[f,side,r]
    assert len(moves[a['slot']])==a['moves'] and len(moves[b['slot']])==b['moves']
    if a['record']==b['record']:differences['IDENTICAL_FULL_RECORD']+=1;continue
    left,right=moves[a['slot']],moves[b['slot']]
    for x,y in zip(left,right):
     if x['choice']!=y['choice']:
      assert x['before_state_sha']==y['before_state_sha'];differences[('CANDIDATE' if y['side']==side else 'OPPONENT')+'_FIRST_'+y['source']]+=1;break
    else:differences['DIFFERENT_LENGTH_OR_RECORD_WITH_SAME_PREFIX']+=1
  byprice[r]=dict(score=sum(cells[f,s,r]['finite_event_score'] for f in range(32) for s in (0,1)),trajectory_signature=signature,vsUNIT=dict(differences));first.update(differences)
  assert sum(differences.values())==64
 result=dict(status='PASS_ALL32TRAIN_IDENTIFIABILITY',training_games=832,training_moves=sum(x['moves'] for x in rows),all13prices=p['prices'],trajectory_equivalence_classes=list(groups.values()),by_price=byprice,selected_R=lock['selected_R'],empirical_tied_best=[r for r in p['prices'] if byprice[r]['score']==max(v['score'] for v in byprice.values())],source='Only832TRAIN rows/TRAINTrajectories read; aggregate includesUNITselfpair. Samepath empiricalsample equivalence, notallstates/genericuniquevalue; actiondifferences alone notgains. Nativeclock/load may alter finitebudgetpolicy; no new proving/engine/labelselection.')
 with (OUT/'result.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='by_price'}))
if __name__=='__main__':run()
