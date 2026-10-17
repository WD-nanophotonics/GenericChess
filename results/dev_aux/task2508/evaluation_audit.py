"""Replay every deployed game; paired estimates with shared baseline and family clusters."""
from pathlib import Path
from collections import Counter
import json,hashlib,random,chess
OUT=Path('results/dev_aux/task2508')
def run(study=2507):
 base=Path(f'results/dev_aux/task{study}');p=json.loads((base/'plan.json').read_text());result=json.loads((base/'result.json').read_text());train=json.loads(Path(p['training']).read_text());assert hashlib.sha256(Path(p['training']).read_bytes()).hexdigest()==p['training_sha'];trained={(a['seed'],a['quiet']):a for a in train['arms']};snap={}if study==2507 else{(r['seed'],r['treatment']):r['weights']for r in json.loads((base/'weights.json').read_text())};rr=[json.loads(s)for s in(base/'games.jsonl').read_text().splitlines()];keys={};moves=0
 if study!=2507:
  episodes=[json.loads(x)for x in Path(p['episodes']).read_text().splitlines()];registered=json.loads((base/'weights.json').read_text())
  for rec in registered:
   q=rec['treatment'].startswith('q2_');target=int(rec['treatment'].split('_')[1]);assert target in p['node_checkpoints'];count=0;selected_count=0;selected=trained[(rec['seed'],q)]['initial']
   for ep in episodes:
    if ep['seed']!=rec['seed']or ep['quiet']!=q:continue
    count+=ep['nodes']
    if count<=target:selected_count=count;selected=ep['weights']
   assert rec['weights']==selected and rec['actual_closed_episode_nodes']==selected_count
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
 for r in rr:
  key=(r['seed'],r['family'],r['color'],r['treatment']);assert r['seed']in p['seeds']and r['family']in p['families']and r['color']in(0,1);assert key not in keys;keys[key]=r;initial=trained[(r['seed'],False)]['initial'];expected=initial if r['treatment']=='initial'else trained[(r['seed'],r['treatment']=='q2_trained')]['weights']if study==2507 else snap[(r['seed'],r['treatment'])];assert r['weights']==expected;start=chess.Board();rng=random.Random(r['family']);expected_prefix=[]
  for _ in range(p['opening_plies']):
   if start.outcome(claim_draw=True)is not None:break
   m=rng.choice(sorted(start.legal_moves,key=lambda a:a.uci()));expected_prefix.append(m.uci());start.push(m)
  assert r['initial_record']['moves']==expected_prefix and r['initial_record']['fen']==start.fen();b=chess.Board(r['record']['initial']);prefix=r['initial_record']['moves'];assert r['record']['initial']==r['initial_record']['initial']==chess.Board().fen();assert r['record']['moves'][:len(prefix)]==prefix
  for u in r['record']['moves']:
   m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);moves+=1
  assert b.fen()==r['record']['fen'];o=b.outcome(claim_draw=True);actual=None if o is None else 0 if o.winner is None else 1 if o.winner else -1;reward=None if actual is None else actual*(1 if r['color']==0 else -1);assert r['reward']==reward
  assert (r['ending']=='ACTUAL_TERMINAL')==(reward is not None)
 assert len(rr)==result['actual'];
 for summary in result['results']:
  tags=summary['tallies']if study==2507 else{summary['treatment']:summary}
  for tag,tally in tags.items():
   selected=[r for r in rr if r['seed']==summary['seed']and r['treatment']==tag]
   for label,value in [('W',1),('L',-1),('D',0),('U',None)]:assert tally[label]==sum(r['reward']==value for r in selected)
 assert sum(r['nodes']for r in rr)==result['nodes']
 treatments=('initial','plain_trained','q2_trained')if study==2507 else tuple(['initial']+[s+'_'+str(n)for n in p['node_checkpoints']for s in('plain','q2')]);assert all(r['treatment']in treatments for r in rr);comparisons=(('plain_trained','initial'),('q2_trained','initial'),('q2_trained','plain_trained'))if study==2507 else tuple([(t,'initial')for t in treatments if t!='initial']+[('q2_'+str(n),'plain_'+str(n))for n in p['node_checkpoints']]);estimates=[]
 def interval(k):
  v=keys.get(k,{}).get('reward');return(-1,1)if v is None else(v,v)
 for a,b in comparisons:
  for seed in p['seeds']+[None]:
   ss=p['seeds']if seed is None else[seed];family=[]
   for f in p['families']:
    diffs=[]
    for s in ss:
     for c in(0,1):
      x=interval((s,f,c,a));y=interval((s,f,c,b));diffs.append((x[0]-y[1],x[1]-y[0]))
    family.append((sum(v[0]for v in diffs)/len(diffs),sum(v[1]for v in diffs)/len(diffs)))
   lo=sum(v[0]for v in family)/len(family);hi=sum(v[1]for v in family)/len(family);rng=random.Random(87001);boots=[]
   for _ in range(5000):
    ff=[rng.choice(family)for _ in family];boots.append((sum(x[0]for x in ff)/len(ff),sum(x[1]for x in ff)/len(ff)))
   envelope=[sorted(v[0]for v in boots)[124],sorted(v[1]for v in boots)[4874]]
   estimates.append(dict(candidate=a,baseline=b,seed=seed,missing_or_U_bounds=[lo,hi],family_bootstrap_descriptive_95_envelope=envelope,families=family))
 # Two-way descriptive resampling of the SAME16 families and4initial seeds.
 rng=random.Random(87002);two_way=[]
 for a,b in comparisons:
  boot=[]
  for _ in range(5000):
   ss=[rng.choice(p['seeds'])for _ in p['seeds']];ff=[rng.choice(p['families'])for _ in p['families']];low=high=0
   for s in ss:
    for f in ff:
     for c in(0,1):
      x=interval((s,f,c,a));y=interval((s,f,c,b));low+=x[0]-y[1];high+=x[1]-y[0]
   den=len(ss)*len(ff)*2;boot.append((low/den,high/den))
  two_way.append(dict(candidate=a,baseline=b,descriptive_seed_and_family_95_envelope=[sorted(x[0]for x in boot)[124],sorted(x[1]for x in boot)[4874]]))
 data=dict(status='PASS_ALL_ACTUAL_DEPLOYMENT_RECORDS',games=len(rr),legal_plies=moves,planned=p['expected_games'],missing=p['expected_games']-len(rr),baseline_physical_games=sum(r['treatment']=='initial'for r in rr),counts=result['results'],estimates=estimates,two_way=two_way,scope=f'Same{len(p["families"])}families repeated across4initial seeds, NOT64independentfamilies. Bothroles averaged withinfamily. Sharedinitialbaseline paidonce; directq2-plain contrasts cancelit. Unknown/missing bounded[-1,+1], neverdraw. Capmissing is time-ordered, NOTassumedrandom; bootstrapdoesnotfixmissingness. Bootstrapdescriptive only, fourseeds too few for universal/convergence claims. Actualmove replay with samepython-chess rules, no externalsolver. Fulltrainingregime effect undercommonplain D2deployment, not puretarget intervention or qdeployment benefit.')
 (OUT/('evaluation-audit.json'if study==2507 else'curve-evaluation-audit.json')).write_text(json.dumps(data,indent=2));print(json.dumps({k:v for k,v in data.items()if k not in('estimates','counts')}))
if __name__=='__main__':
 import sys
 run(int(sys.argv[1])if len(sys.argv)>1 else 2507)
