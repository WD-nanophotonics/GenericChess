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

D=Path('results/dev_aux/task2528');T=Path('results/dev_aux/task2527');O=Path('results/dev_aux/task2529')

def run():

 start=time.perf_counter();p=json.loads((D/'plan.json').read_text());done=json.loads((D/'result.json').read_text());assert json.loads((D/'started.json').read_text())['plan_sha']==hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()

 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n

 train=json.loads(Path(p['training']).read_text());arms={(a['generator_seed'],a['seed']):a for a in train['arms']};cc={gs:compile_ruleset(ruleset_from_dict(json.loads((T/('rules-'+str(gs)+'.json')).read_text())))for gs in p['generator_seeds']if(T/('rules-'+str(gs)+'.json')).exists()};rr=[json.loads(x)for x in(D/'games.jsonl').read_text().splitlines()];counts=Counter();index={};tallies=defaultdict(Counter);behavior=defaultdict(Counter);positions={tuple(slot):i for i,slot in enumerate(p['slots'])};previous_pos=-1

 def readq():

  with(D/'queries.jsonl').open()as f:

   for line in f:yield json.loads(line)

 stream=iter(readq());nextq=next(stream,None)

 for pos,r in enumerate(rr):

  key=tuple(r['slot']);assert positions[key]>previous_pos and key not in index;previous_pos=positions[key];index[key]=r;gs,seed,f,c,t=key;a=arms[gs,seed];w=a['initial']if t=='initial'else next(x['weights']for x in a['snapshots']if 'n'+str(x['target_nodes'])==t);assert r['weights']==w and r['channels']==a['channels'];previous=r['initial_record'];s=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(previous)));counts['legal_prefix_plies']+=len(s.to_record().actions);queries=[]

  while nextq is not None and tuple(nextq['slot'])==key:queries.append(nextq);nextq=next(stream,None)

  assert len(queries)==r['queries'];nodes=0

  for ply,q in enumerate(queries):

   assert q['ply']==ply and q['record_before']==previous and terminal(s)is None;expected=w if s.state.position.side_to_move==c else[1.]*len(w);assert q['weights']==expected;assert q['effective_node_limit']==p['nodes_per_query']and q['nodes']<=q['effective_node_limit']and 0<q['effective_wall_limit']<=p['seconds_per_query']and q['effective_wall_limit']<=q['global_remaining_before_query'];counts['queries']+=1;nodes+=q['nodes']

   if q['complete']:assert q['reason']=='complete'and len(q['record_after']['actions'])==len(previous['actions'])+1

   else:assert ply==len(queries)-1 and q['record_after']==previous and q['value']is None;counts['failed_queries']+=1

   before_count=len(s.to_record().actions);after=advance(s,q['record_after'],q['complete']);counts['legal_play_plies']+=len(after.to_record().actions)-before_count;s=after;previous=q['record_after']

  replayed=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(r['record'])));assert replayed.state==s.state and replayed.result==s.result and replayed.to_record()==s.to_record();actual=terminal(s);reward=None if actual is None else actual*(1 if c==0 else-1);assert r['record']==previous and r['outcome']==actual and r['reward']==reward and r['nodes']==nodes;assert(actual is not None)==(r['ending']=='ACTUAL_TERMINAL');counts[r['ending']]+=1;tallies[gs,seed,t]['U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L']+=1

 assert len(rr)==done['actual']and sum(r['nodes']for r in rr)==done['nodes']and counts['queries']==done['queries'];assert nextq is None,'UnconsumedEVALqueries'

 def interval(gs,s,f,c,t):

  v=index.get((gs,s,f,c,t),{}).get('reward');return(-1,1)if v is None else(v,v)

 def bound(gslist,seeds,fams,level,base='initial',colors=(0,1)):

  lo=hi=0

  for gs in gslist:

   for s in seeds:

    for f in fams:

     for c in colors:

      x=interval(gs,s,f,c,level);y=interval(gs,s,f,c,base);lo+=x[0]-y[1];hi+=x[1]-y[0]

  n=len(gslist)*len(seeds)*len(fams)*len(colors);return[lo/n,hi/n]

 curves=[]

 for level in p['levels'][1:]:

  perrule=[dict(generator_seed=gs,bounds=bound([gs],p['initial_seeds'],p['families'],level))for gs in p['generator_seeds']];perseed=[dict(seed=s,bounds=bound(p['generator_seeds'],[s],p['families'],level))for s in p['initial_seeds']];pooled=bound(p['generator_seeds'],p['initial_seeds'],p['families'],level);rng=random.Random(902926);boot=[]

  for _ in range(5000):

   gslist=[rng.choice(p['generator_seeds'])for _ in p['generator_seeds']];seeds=[rng.choice(p['initial_seeds'])for _ in p['initial_seeds']];lo=hi=0.

   for gs in gslist:

    fams=[rng.choice(p['families'])for _ in p['families']];v=bound([gs],seeds,fams,level);lo+=v[0];hi+=v[1]

   boot.append([lo/len(gslist),hi/len(gslist)])

  curves.append(dict(level=level,pooled_gain_bounds=pooled,per_rule=perrule,per_seed=perseed,per_role=[dict(color=c,bounds=bound(p['generator_seeds'],p['initial_seeds'],p['families'],level,colors=(c,)))for c in(0,1)],descriptive_rule_seed_family_95_envelope=[sorted(x[0]for x in boot)[124],sorted(x[1]for x in boot)[4874]]))

 adjacent=[dict(level=level,base=base,bounds=bound(p['generator_seeds'],p['initial_seeds'],p['families'],level,base))for base,level in zip(p['levels'],p['levels'][1:])]

 for gs in p['generator_seeds']:

  for seed in p['initial_seeds']:

   for fam in p['families']:

    for c in(0,1):

     for level in p['levels'][1:]:

      x=index.get((gs,seed,fam,c,level));y=index.get((gs,seed,fam,c,'initial'))

      if x is None or y is None:behavior[level]['missing_pair']+=1;continue

      assert x['initial_record']==y['initial_record'];xm=deserialize_game_record(json.dumps(x['record']));ym=deserialize_game_record(json.dumps(y['record']));i=next((i for i,(a,b)in enumerate(zip(xm.actions,ym.actions))if a!=b),None)

      if i is None:

       if xm.actions==ym.actions:behavior[level]['identical_full_record']+=1

       else:assert x['reward']is None or y['reward']is None;behavior[level]['censor_strict_prefix']+=1

      else:

       before=GameSession.replay(cc[gs],replace(xm,actions=xm.actions[:i],resigned_by=None,declaration=None));assert before.state.position.side_to_move==c;behavior[level]['candidate_first_difference']+=1

      if x['reward']is None or y['reward']is None:behavior[level]['unresolved_pair']+=1

      else:behavior[level]['improved'if x['reward']>y['reward']else'worse'if x['reward']<y['reward']else'same_reward']+=1

 result=dict(status='PASS_ALL_RETURNED_GENERIC_ACTUAL_OUTCOMES_FULL_RECORDS_AND_PAIRED_GAINS',planned=len(p['slots']),returned=len(rr),missing=len(p['slots'])-len(rr),counts=dict(counts),tallies=[dict(generator_seed=gs,seed=s,treatment=t,counts=dict(v))for(gs,s,t),v in sorted(tallies.items())],curves=curves,adjacent=adjacent,behavior={k:dict(v)for k,v in behavior.items()},scope='SAME4TRAIN-exposedrules/ALL4initials/NEW4bindingpaths/bothroles/ALLthreefixedcheckpoints/initialpaidonce. RuleconditionedpricesnotsharedacrossP/X/Ameanings. Fulltypedhistory/actualSessionterminal/incrementalsubmit+everyqueryrecordequality+finalpublicreplay, H128U/missing[-1,1]notdraw; allcurves retained/nochoosebest. Hierarchical4rule/4seed/4familyresamplingDESCRIPTIVE/smallunits, notformalcoverage/equivalence/unseenrule/full-domain claim. Actualperqueryfoe/roles/budgets preserved; sameruleauthority notexternalengine.',audit_seconds=time.perf_counter()-start);(O/'evaluation-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k!='tallies'}))

if __name__=='__main__':run()
