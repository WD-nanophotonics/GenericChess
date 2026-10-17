"""Full actual deployment/query replay and paired family/seed uncertainty bounds."""
from pathlib import Path
from collections import defaultdict,Counter
from math import isclose
import json,hashlib,random,chess,time,sys
from results.dev_aux.task2514.training_audit import outcome
OUT=Path('results/dev_aux/task2520');BASE=Path('results/dev_aux/task2519')
def run(panel):
 start=time.perf_counter();base=Path('results/dev_aux/task2516')if panel=='different_foe'else BASE;p=json.loads((base/'plan.json').read_text());cfg=p['panels'][panel];bdir=base/panel;done=json.loads((bdir/'result.json').read_text());train=json.loads(Path(p['training']).read_text());arms={(r['seed'],r['method']):r for r in train['arms']};snaps=json.loads((bdir/'weights.json').read_text());weights={(r['seed'],r['method']):r['weights']for r in snaps};rr=[json.loads(x)for x in(bdir/'games.jsonl').read_text().splitlines()];qq=defaultdict(list);counts=Counter();index={};tallies=defaultdict(Counter)
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 for r in snaps:
  a=arms[(r['seed'],r['method'])];w=a['weights'];nodes=a['nodes'];game=a['checkpoints'][-1]['game']
  if cfg['checkpoint']<p['training_ceiling']:
   w=a['initial'];nodes=0;game=None
   for c in a['checkpoints']:
    if c['nodes']<=cfg['checkpoint']:w=c['weights'];nodes=c['nodes'];game=c['game']
  assert r['weights']==w and r['actual_closed_episode_nodes']==nodes and r['game']==game
 for x in(bdir/'queries.jsonl').open():
  q=json.loads(x);qq[tuple(q['slot'])].append(q)
 for pos,r in enumerate(rr):
  key=(r['seed'],r['family'],r['color'],r['treatment']);assert list(key)==cfg['slots'][pos]and key not in index;index[key]=r;w=arms[(r['seed'],'root')]['initial']if r['treatment']=='initial'else weights[(r['seed'],r['treatment'])];assert w==r['weights'];b=chess.Board();rng=random.Random(r['family'])
  for _ in range(p['opening_plies']):
   if outcome(b)is not None:break
   b.push(rng.choice(sorted(b.legal_moves,key=lambda m:m.uci())))
  prefix=[m.uci()for m in b.move_stack];counts['legal_prefix_plies']+=len(prefix);assert r['initial_record']['moves']==prefix and r['initial_record']['fen']==b.fen();queries=qq[key];assert len(queries)==r['queries'];nodes=0
  for ply,q in enumerate(queries):
   assert q['ply']==ply and q['root_fen']==b.fen()and outcome(b)is None;assert q['effective_node_limit']==p['nodes_per_query'];assert 0<q['effective_wall_limit']<=p['seconds_per_query']and q['effective_wall_limit']<=q['global_remaining_before_query'];assert q['nodes']<=q['effective_node_limit'];nodes+=q['nodes'];counts['queries']+=1;counts['failed_queries']+=not q['complete'];counts['search_microseconds']+=round(q['seconds']*1e6)
   if not q['complete']:assert ply==len(queries)-1 and q['action']is None and q['value']is None;continue
   assert q['reason']=='complete';m=chess.Move.from_uci(q['action']);assert m in b.legal_moves;b.push(m);counts['legal_play_plies']+=1
  assert nodes==r['nodes']and b.fen()==r['record']['fen']and[m.uci()for m in b.move_stack]==r['record']['moves'];actual=outcome(b);reward=None if actual is None else actual*(1 if r['color']==0 else-1);assert reward==r['reward'];assert(reward is not None)==(r['ending']=='ACTUAL_TERMINAL');counts[r['ending']]+=1;tallies[(r['seed'],r['treatment'])]['U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L']+=1
 assert len(rr)==done['actual']and len(cfg['slots'])==done['expected']and sum(r['nodes']for r in rr)==done['nodes']and sum(len(v)for v in qq.values())==done['queries'];assert set(qq)<={tuple(x)for x in cfg['slots']}
 for summary in done['results']:
  for tag,t in summary['tallies'].items():
   for k in('W','L','D','U'):assert t[k]==tallies[(summary['seed'],tag)][k]
 def interval(s,f,c,t):
  v=index.get((s,f,c,t),{}).get('reward');return(-1.,1.)if v is None else(float(v),float(v))
 comparisons=[('root','initial'),('tree','initial'),('tree','root')];estimates=[];twoway=[]
 for a,b in comparisons:
  for seed in p['seeds']+[None]:
   seeds=p['seeds']if seed is None else[seed];families=[]
   for f in cfg['families']:
    low=high=0.
    for s in seeds:
     for c in(0,1):
      x=interval(s,f,c,a);y=interval(s,f,c,b);low+=x[0]-y[1];high+=x[1]-y[0]
    den=len(seeds)*2;families.append([low/den,high/den])
   bounds=[sum(x[j]for x in families)/len(families)for j in(0,1)];rng=random.Random(88001);boot=[]
   for _ in range(5000):
    sample=[rng.choice(families)for _ in families];boot.append([sum(x[j]for x in sample)/len(sample)for j in(0,1)])
   envelope=[sorted(x[0]for x in boot)[124],sorted(x[1]for x in boot)[4874]];estimates.append(dict(candidate=a,baseline=b,seed=seed,missing_or_U_bounds=bounds,descriptive_family_95_envelope=envelope,family_bounds=families))
  rng=random.Random(88002);boot=[]
  for _ in range(5000):
   ss=[rng.choice(p['seeds'])for _ in p['seeds']];ff=[rng.choice(cfg['families'])for _ in cfg['families']];low=high=0.
   for s in ss:
    for f in ff:
     for c in(0,1):
      x=interval(s,f,c,a);y=interval(s,f,c,b);low+=x[0]-y[1];high+=x[1]-y[0]
   den=len(ss)*len(ff)*2;boot.append([low/den,high/den])
  twoway.append(dict(candidate=a,baseline=b,descriptive_seed_family_95_envelope=[sorted(x[0]for x in boot)[124],sorted(x[1]for x in boot)[4874]]))
 behavior=[]
 for a,b in comparisons:
  cc=Counter()
  for s in p['seeds']:
   for f in cfg['families']:
    for c in(0,1):
     x=index.get((s,f,c,a));y=index.get((s,f,c,b))
     if x is None or y is None:cc['missing_pair']+=1;continue
     assert x['initial_record']==y['initial_record'];xm=x['record']['moves'];ym=y['record']['moves'];different=next((i for i,(u,v)in enumerate(zip(xm,ym))if u!=v),None)
     if different is None:
      if xm==ym:cc['identical_full_record']+=1
      else:cc['strict_prefix_due_censor']+=1;assert x['reward']is None or y['reward']is None
     else:
      board=chess.Board(x['record']['initial'])
      for u in xm[:different]:board.push_uci(u)
      assert int(not board.turn)==c;cc['candidate_first_difference']+=1
     if x['reward']is None or y['reward']is None:cc['unresolved_pair']+=1
     else:
      gain=x['reward']-y['reward'];cc['improved'if gain>0 else'worse'if gain<0 else'same_reward']+=1
  behavior.append(dict(candidate=a,baseline=b,counts=dict(cc)))
 result=dict(status='PASS_ALL_ACTUAL_DEPLOYMENT_AND_QUERY_RECORDS',panel=panel,planned=len(cfg['slots']),returned=len(rr),missing=len(cfg['slots'])-len(rr),counts=dict(counts),tallies=done['results'],estimates=estimates,two_way=twoway,behavior=behavior,shared_initial_physical_games=sum(r['treatment']=='initial'for r in rr),scope='Complete actuallegalrecord/query/resource/weights replay, same rulelibrary; no allsearchrerun. Samefamilies repeatedacross4seeds/roles; family+seed envelopes descriptive, notindependentgames. U/missing[-1,1], neverdraw. Capmissingnotassumedrandom. NEW8family95000-95007Rootcontrol, singlepoint500k/notconvergencecurve. InitialRMSmatchedonlyoncalibrationdistribution; laternormsmaydrift. Commondeploymentwholelearningregimes, notpureallnode information/equalstepunit/TTpaperreplication.',audit_seconds=time.perf_counter()-start);(OUT/(panel+'-audit.json')).write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('estimates','tallies','behavior')}))
if __name__=='__main__':run(sys.argv[1])
