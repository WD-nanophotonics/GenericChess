"""Root recipe replay and full-record exposure accounting; no outcome filtering."""
from pathlib import Path
import json,hashlib,random
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession
from results.dev_aux.task2525.run import RecordedSessionEnv
O=Path('results/dev_aux/task2553')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run():
 train={}
 for line in Path('results/dev_aux/task2546/games.jsonl').open():
  g=json.loads(line);train.setdefault(g['generator_seed'],set()).add(digest(g['initial_record']))
 arms=json.loads(Path('results/dev_aux/task2546/result.json').read_text())['arms'];rows=[];records={}
 for task in[2552,2556]:
  D=Path(f'results/dev_aux/task{task}');p=json.loads((D/'plan.json').read_text());local={}
  for gs in p['generator_seeds']:
   cc=compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{gs}.json').read_text())));channels=next(a['channels']for a in arms if a['generator_seed']==gs)
   for f in p['families']:
    e=RecordedSessionEnv(GameSession(cc),channels);rr=random.Random(gs*1000000+f)
    for _ in range(p['prefix_plies']):
     if e.terminal()is not None:break
     e.push(rr.choice(sorted(e.actions(),key=repr)))
    rec=e.record();h=digest(rec);local[gs,f]=rec;records[task,gs,f]=rec;rows.append(dict(task=task,rule=gs,family=f,record_sha=h,prefix_plies=len(rec['actions']),terminal=e.terminal(),overlap93TRAIN=h in train[gs]))
  count=0
  if(D/'result.json').exists():
   for line in(D/'games.jsonl').open():
    g=json.loads(line);assert g['initial_record']==local[g['generator_seed'],g['family']];count+=1
  p2=O/f'roots-{task}.json';rr=[v for v in rows if v['task']==task];p2.write_text(json.dumps(dict(status='FULL_ROOT_RECIPES_REPLAYED_NO_FILTER',registered=len(local),distinct=len({digest(x)for x in local.values()}),overlap93TRAIN=sum(v['overlap93TRAIN']for v in rr),already_terminal=sum(v['terminal']is not None for v in rr),closed_game_prefixes_checked=count,rows=rr,scope='Rules already TRAINexposed. NewPRNGIDs do not guarantee unseen fullrecords; only93TRAIN overlap tested, notallhistoricalexposure. ALLrootsincludingterminal/overlaps retained.'),indent=2))
 print('Both new panels root recipes reconstructed and original TRAIN exposure checked; no filtering')
if __name__=='__main__':run()
