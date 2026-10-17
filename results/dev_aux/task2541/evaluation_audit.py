"""Full Session outcomes/records and paired rule-conditioned utility, no table labels."""

from pathlib import Path

from collections import defaultdict,Counter

from dataclasses import replace

import json,hashlib,random,time

from generic_chess.rules.schema import ruleset_from_dict

from generic_chess.rules.compiler import compile_ruleset

from generic_chess.session.session import GameSession
from results.dev_aux.task2529.incremental_replay import advance

from generic_chess.session.serialization import deserialize_game_record,serialize_game_record

from results.dev_aux.task2529.training_audit import terminal

D=Path('results/dev_aux/task2540');T=Path('results/dev_aux/task2539');O=Path('results/dev_aux/task2541')

def run():

 start=time.perf_counter();p=json.loads((D/'plan.json').read_text());done=json.loads((D/'result.json').read_text());assert json.loads((D/'started.json').read_text())['plan_sha']==hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()

 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n

 binding=json.loads((D/'pre-fitness-binding.json').read_text());assert binding['training_result_sha']==hashlib.sha256(Path(p['training']).read_bytes()).hexdigest() and binding['plan_sha']==hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()
 train=json.loads(Path(p['training']).read_text());arms={(a['generator_seed'],a['method'],a['seed']):a for a in train['arms']};cc={gs:compile_ruleset(ruleset_from_dict(json.loads((Path('results/dev_aux/task2525')/('rules-'+str(gs)+'.json')).read_text())))for gs in p['generator_seeds']if(Path('results/dev_aux/task2525')/('rules-'+str(gs)+'.json')).exists()};rr=[json.loads(x)for x in(D/'games.jsonl').read_text().splitlines()];counts=Counter();index={};tallies=defaultdict(Counter);behavior=defaultdict(Counter);positions={tuple(slot):i for i,slot in enumerate(p['slots'])};previous_pos=-1

 def readq():

  with(D/'queries.jsonl').open()as f:

   for line in f:yield json.loads(line)

 stream=iter(readq());nextq=next(stream,None)

 for pos,r in enumerate(rr):

  key=tuple(r['slot']);assert positions[key]>previous_pos and key not in index;previous_pos=positions[key];index[key]=r;gs,seed,f,c,t,foe=key;method='TD'if t=='initial'else t;a=arms[gs,method,seed];w=a['initial']if t=='initial'else a['weights'];assert r['weights']==w and r['channels']==a['channels'];previous=r['initial_record'];s=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(previous)));counts['legal_prefix_plies']+=len(s.to_record().actions);queries=[]

  while nextq is not None and tuple(nextq['slot'])==key:queries.append(nextq);nextq=next(stream,None)

  assert len(queries)==r['queries'];nodes=0

  for ply,q in enumerate(queries):

   assert q['ply']==ply and q['record_before']==previous and terminal(s)is None;expected=w if s.state.position.side_to_move==c else p['opponents'][foe];assert q['weights']==expected;assert q['effective_node_limit']==p['nodes_per_query']and q['nodes']<=q['effective_node_limit']and 0<q['effective_wall_limit']<=p['seconds_per_query']and q['effective_wall_limit']<=q['global_remaining_before_query'];counts['queries']+=1;nodes+=q['nodes']

   if q['complete']:assert q['reason']=='complete'and len(q['record_after']['actions'])==len(previous['actions'])+1

   else:assert ply==len(queries)-1 and q['record_after']==previous and q['value']is None;counts['failed_queries']+=1

   before_count=len(s.to_record().actions);after=advance(s,q['record_after'],q['complete']);counts['legal_play_plies']+=len(after.to_record().actions)-before_count;s=after;previous=q['record_after']

  replayed=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(r['record'])));assert replayed.state==s.state and replayed.result==s.result and replayed.to_record()==s.to_record();actual=terminal(s);reward=None if actual is None else actual*(1 if c==0 else-1);assert r['record']==previous and r['outcome']==actual and r['reward']==reward and r['nodes']==nodes;assert(actual is not None)==(r['ending']=='ACTUAL_TERMINAL');counts[r['ending']]+=1;tallies[gs,seed,t,foe]['U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L']+=1

 assert len(rr)==done['actual']and sum(r['nodes']for r in rr)==done['nodes']and counts['queries']==done['queries'];assert nextq is None,'UnconsumedEVALqueries'


 def interval(gs,seed,f,c,t,foe):
  v=index.get((gs,seed,f,c,t,foe),{}).get('reward');return(-1,1)if v is None else(v,v)
 def bound(gslist,seeds,fams,foe,t,base,colors=(0,1)):
  lo=hi=0
  for gs in gslist:
   for seed in seeds:
    for f in fams:
     for c in colors:
      x=interval(gs,seed,f,c,t,foe);y=interval(gs,seed,f,c,base,foe);lo+=x[0]-y[1];hi+=x[1]-y[0]
  n=len(gslist)*len(seeds)*len(fams)*len(colors);return[lo/n,hi/n]
 contrasts=[]
 for foe in p['opponents']:
  for t,base in [('TD','initial'),('WDL','initial'),('TD','WDL')]:
   args=(p['generator_seeds'],p['initial_seeds'],p['families']);rng=random.Random(92541);boot=[];behavior=Counter()
   for gs in args[0]:
    for seed in args[1]:
     for f in args[2]:
      for c in(0,1):
       x=index.get((gs,seed,f,c,t,foe));y=index.get((gs,seed,f,c,base,foe))
       if x is None or y is None:behavior['missing_pair']+=1;continue
       assert x['initial_record']==y['initial_record']
       xa=deserialize_game_record(json.dumps(x['record']));ya=deserialize_game_record(json.dumps(y['record']));i=next((i for i,(a,b)in enumerate(zip(xa.actions,ya.actions))if a!=b),None)
       if i is not None:
        before=GameSession.replay(cc[gs],replace(xa,actions=xa.actions[:i],resigned_by=None,declaration=None));assert before.state.position.side_to_move==c;behavior['candidate_first_difference']+=1
       elif xa.actions==ya.actions:behavior['identical_full_record']+=1
       else:assert x['reward']is None or y['reward']is None;behavior['censor_prefix']+=1
       if x['reward']is None or y['reward']is None:behavior['unresolved_pair']+=1
       else:behavior['improved'if x['reward']>y['reward']else'worse'if x['reward']<y['reward']else'same_reward']+=1
   for _ in range(3000):
    rules=[rng.choice(args[0])for _ in args[0]];seeds=[rng.choice(args[1])for _ in args[1]];lo=hi=0
    for gs in rules:
     fs=[rng.choice(args[2])for _ in args[2]];z=bound([gs],seeds,fs,foe,t,base);lo+=z[0];hi+=z[1]
    boot.append((lo/len(rules),hi/len(rules)))
   contrasts.append(dict(foe=foe,treatment=t,base=base,bounds=bound(*args,foe,t,base),per_rule=[dict(rule=gs,bounds=bound([gs],args[1],args[2],foe,t,base))for gs in args[0]],per_seed=[dict(seed=seed,bounds=bound(args[0],[seed],args[2],foe,t,base))for seed in args[1]],per_role=[dict(color=c,bounds=bound(*args,foe,t,base,colors=(c,)))for c in(0,1)],behavior=dict(behavior),descriptive_95=[sorted(x[0]for x in boot)[74],sorted(x[1]for x in boot)[2924]]))
 result=dict(status='PASS_FULL_RECORDS_ACTUAL_OUTCOMES_PAIRED_TD_VS_PAID_WDL',counts=dict(counts),planned=len(p['slots']),returned=len(rr),missing=len(p['slots'])-len(rr),contrasts=contrasts,tallies=[dict(rule=gs,seed=seed,treatment=t,foe=foe,counts=dict(v))for(gs,seed,t,foe),v in sorted(tallies.items())],audit_seconds=time.perf_counter()-start,scope='All4TRAIN-exposedrules/4initials/8newPRNGfamilies/bothroles/2fixedfoes; primarydirectTD-WDL, bothinitialcontrols. Unknown/missing reward interval[-1,1], neverdraw. Threelevelrule/seed/familyresampling DESCRIPTIVE smallunits notconfidenceguarantee/equivalence. Actual firstdivergencescandidate, fulltypedhistories. No selectedmodel or stableprices/unseenrule claim.')
 (O/'evaluation-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='tallies'}))
if __name__=='__main__':run()
