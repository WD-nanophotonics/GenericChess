from pathlib import Path
import json,random,hashlib
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2525.run import RecordedSessionEnv
T=Path('results/dev_aux/task2546');E=Path('results/dev_aux/task2547');O=Path('results/dev_aux/task2548')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run():
 p=json.loads((E/'plan.json').read_text());arms={(x['generator_seed'],x['method'],x['seed']):x for x in json.loads((T/'result.json').read_text())['arms']};train={}
 for line in(T/'games.jsonl').open():
  x=json.loads(line);train.setdefault(x['generator_seed'],set()).add(digest(x['initial_record']))
 roots={};rows=[]
 for gs in p['generator_seeds']:
  cc=compile_ruleset(ruleset_from_dict(json.loads((Path('results/dev_aux/task2525')/f'rules-{gs}.json').read_text())));names=next(a['channels']for key,a in arms.items()if key[0]==gs)
  for f in p['families']:
   env=RecordedSessionEnv(GameSession(cc),names);rng=random.Random(gs*1000000+f)
   for _ in range(p['prefix_plies']):
    if env.terminal()is not None:break
    env.push(rng.choice(sorted(env.actions(),key=repr)))
   rec=env.record();h=digest(rec);roots[gs,f]=rec;rows.append(dict(rule=gs,family=f,fullrecord_sha=h,overlap_current_TRAIN=h in train.get(gs,set()),terminal=env.terminal(),prefix_plies=len(rec['actions'])))
 count=0
 for line in(E/'games.jsonl').open():
  r=json.loads(line);assert r['initial_record']==roots[r['generator_seed'],r['family']];count+=1
 result=dict(status='PASS_ALL_NEW_PRNG_ROOTS_FULL_HISTORY',registered=len(roots),distinct_full_records=len({digest(x)for x in roots.values()}),overlap_current_TRAIN=sum(x['overlap_current_TRAIN']for x in rows),already_terminal=sum(x['terminal']is not None for x in rows),game_prefixes_verified=count,rows=rows,scope='NEW PRNGrecipes notstrictunseenfullstates; ALLroots retained/nooutcomefilter. OnlyCURRENT93TRAINoverlaptested; olderexposure notexcluded. FouralreadyTRAIN-exposedrules. Fullrecordhistorynotboardcoalescing.')
 (O/'roots.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
if __name__=='__main__':run()
