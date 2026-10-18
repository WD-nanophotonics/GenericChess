"""Actual rule-terminal categories and material/PV signal coverage, all records."""
from pathlib import Path
import json,sys
from collections import Counter,defaultdict
from results.dev_aux.task2565.train import restore

def run(directory):
 d=Path(directory);answer={}
 for label,name in [('TRAIN','games.jsonl'),('EVAL','eval-games.jsonl')]:
  counts=Counter();by=defaultdict(Counter)
  for row in map(json.loads,(d/name).open()):
   method=row['method']if label=='TRAIN'else row['slot'][4];e=restore(0,None,row['record']);result=e.board.outcome(claim_draw=True)
   assert(result is None)==(row['outcome']is None)
   if result is None:kind='UNKNOWN:'+row['ending']
   else:
    expected=0 if result.winner is None else 1 if result.winner else-1;assert expected==row['outcome'];kind=result.termination.name;counts['wins_actual']+=expected!=0;counts['draws_actual']+=expected==0;color=row['color']if label=='TRAIN'else row['slot'][3];reward=expected*(1 if color==0 else-1);by[method]['candidate_wins']+=reward>0;by[method]['candidate_losses']+=reward<0;by[method]['draws']+=reward==0
   counts[kind]+=1;by[method][kind]+=1;counts['trajectories']+=1;counts['played_plies']+=len(row['record']['moves'])-len(row['initial_record']['moves'])
  answer[label]=dict(counts=dict(counts),by_method=dict(by))
 p=json.loads((d/'plan.json').read_text());e=json.loads((d/'eval-plan.json').read_text());roots={}
 from results.dev_aux.task2492.adapters import ChessEnv
 from results.dev_aux.task2565.train import prefix
 for family in sorted({s[2]for s in e['slots']}):
  env=ChessEnv();prefix(env,0,family,e['prefix_plies']);roots[str(family)]=dict(record=env.record(),features=env.features(),outcome=env.terminal())
 answer.update(status='PASS',eval_roots=roots,scope='Samepython-chess fullhistory actualoutcome/claimpolicy; realdraw subtypes are outcomes, Uresources remainU. Piececounts/features describe inputs, neverterminalpayoff orhumanpricetarget.')
 (d/'terminal-profile.json').write_text(json.dumps(answer,indent=2));print(json.dumps({k:v['counts']for k,v in answer.items()if k in('TRAIN','EVAL')}))
if __name__=='__main__':run(sys.argv[1])
