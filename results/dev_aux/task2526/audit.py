"""Full Session outcomes/records and paired rule-conditioned utility, no table labels."""
from pathlib import Path
from collections import defaultdict,Counter
from dataclasses import replace
import json,hashlib,random,time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from results.dev_aux.task2525.audit import terminal
D=Path('results/dev_aux/task2526');T=Path('results/dev_aux/task2525')
def run():
 start=time.perf_counter();p=json.loads((D/'plan.json').read_text());done=json.loads((D/'result.json').read_text());assert json.loads((D/'started.json').read_text())['plan_sha']==hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 train=json.loads(Path(p['training']).read_text());arms={(a['generator_seed'],a['seed']):a for a in train['arms']};cc={gs:compile_ruleset(ruleset_from_dict(json.loads((T/('rules-'+str(gs)+'.json')).read_text())))for gs in p['generator_seeds']};rr=[json.loads(x)for x in(D/'games.jsonl').read_text().splitlines()];qq=defaultdict(list);counts=Counter();index={};tallies=defaultdict(Counter);behavior=Counter()
 for line in(D/'queries.jsonl').open():
  q=json.loads(line);qq[tuple(q['slot'])].append(q)
 for pos,r in enumerate(rr):
  key=tuple(r['slot']);assert list(key)==p['slots'][pos]and key not in index;index[key]=r;gs,seed,f,c,t=key;a=arms[gs,seed];w=a['initial']if t=='initial'else a['weights'];assert r['weights']==w and r['channels']==a['channels'];previous=r['initial_record'];s=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(previous)));counts['legal_prefix_plies']+=len(s.to_record().actions);queries=qq[key];assert len(queries)==r['queries'];nodes=0
  for ply,q in enumerate(queries):
   assert q['ply']==ply and q['record_before']==previous and terminal(s)is None;expected=w if s.state.position.side_to_move==c else[1.]*len(w);assert q['weights']==expected;assert q['effective_node_limit']==p['nodes_per_query']and q['nodes']<=q['effective_node_limit']and 0<q['effective_wall_limit']<=p['seconds_per_query']and q['effective_wall_limit']<=q['global_remaining_before_query'];counts['queries']+=1;nodes+=q['nodes']
   if q['complete']:assert q['reason']=='complete'and len(q['record_after']['actions'])==len(previous['actions'])+1
   else:assert ply==len(queries)-1 and q['record_after']==previous and q['value']is None;counts['failed_queries']+=1
   after=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(q['record_after'])));assert json.loads(serialize_game_record(after.to_record()))==q['record_after'];counts['legal_play_plies']+=len(after.to_record().actions)-len(s.to_record().actions);s=after;previous=q['record_after']
  actual=terminal(s);reward=None if actual is None else actual*(1 if c==0 else-1);assert r['record']==previous and r['outcome']==actual and r['reward']==reward and r['nodes']==nodes;assert(actual is not None)==(r['ending']=='ACTUAL_TERMINAL');counts[r['ending']]+=1;tallies[gs,seed,t]['U'if reward is None else'D'if reward==0 else'W'if reward==1 else'L']+=1
 assert len(rr)==done['actual']and sum(r['nodes']for r in rr)==done['nodes']and counts['queries']==done['queries'];assert sum(len(q)for q in qq.values())==done['queries']
 def interval(gs,s,f,c,t):
  v=index.get((gs,s,f,c,t),{}).get('reward');return(-1,1)if v is None else(v,v)
 def bound(gslist,seeds,fams):
  lo=hi=0
  for gs in gslist:
   for s in seeds:
    for f in fams:
     for c in(0,1):
      x=interval(gs,s,f,c,'trained');y=interval(gs,s,f,c,'initial');lo+=x[0]-y[1];hi+=x[1]-y[0]
  n=len(gslist)*len(seeds)*len(fams)*2;return[lo/n,hi/n]
 perrule=[dict(generator_seed=gs,bounds=bound([gs],p['initial_seeds'],p['families']))for gs in p['generator_seeds']];perseed=[dict(seed=s,bounds=bound(p['generator_seeds'],[s],p['families']))for s in p['initial_seeds']];pooled=bound(p['generator_seeds'],p['initial_seeds'],p['families']);rng=random.Random(891026);boot=[]
 for _ in range(5000):
  gslist=[rng.choice(p['generator_seeds'])for _ in p['generator_seeds']];seeds=[rng.choice(p['initial_seeds'])for _ in p['initial_seeds']];lo=hi=0.
  for gs in gslist:
   fams=[rng.choice(p['families'])for _ in p['families']];v=bound([gs],seeds,fams);lo+=v[0];hi+=v[1]
  boot.append([lo/len(gslist),hi/len(gslist)])
 for gs in p['generator_seeds']:
  for seed in p['initial_seeds']:
   for fam in p['families']:
    for c in(0,1):
     x=index.get((gs,seed,fam,c,'trained'));y=index.get((gs,seed,fam,c,'initial'))
     if x is None or y is None:behavior['missing_pair']+=1;continue
     assert x['initial_record']==y['initial_record'];xm=deserialize_game_record(json.dumps(x['record']));ym=deserialize_game_record(json.dumps(y['record']));i=next((i for i,(a,b)in enumerate(zip(xm.actions,ym.actions))if a!=b),None)
     if i is None:
      if xm.actions==ym.actions:behavior['identical_full_record']+=1
      else:assert x['reward']is None or y['reward']is None;behavior['censor_strict_prefix']+=1
     else:
      before=GameSession.replay(cc[gs],replace(xm,actions=xm.actions[:i],resigned_by=None,declaration=None));assert before.state.position.side_to_move==c;behavior['candidate_first_difference']+=1
     if x['reward']is None or y['reward']is None:behavior['unresolved_pair']+=1
     else:behavior['improved'if x['reward']>y['reward']else'worse'if x['reward']<y['reward']else'same_reward']+=1
 result=dict(status='PASS_ALL_RETURNED_GENERIC_ACTUAL_OUTCOMES_FULL_RECORDS_AND_PAIRED_GAINS',planned=len(p['slots']),returned=len(rr),missing=len(p['slots'])-len(rr),counts=dict(counts),tallies=[dict(generator_seed=gs,seed=s,treatment=t,counts=dict(v))for(gs,s,t),v in sorted(tallies.items())],pooled_gain_bounds=pooled,per_rule=perrule,per_seed=perseed,descriptive_rule_seed_family_95_envelope=[sorted(x[0]for x in boot)[124],sorted(x[1]for x in boot)[4874]],behavior=dict(behavior),scope='SAME4TRAIN-exposedgeneratedrules/2initials/4NEWbindingpaths/bothroles, allmodelskept. Rule-conditionedprices NOT pooled acrossdifferentP/X/Arules. Fulltypedrecordidentities/history and actualSessionterminal authority; H64U/missing[-1,1], notdraw. Hierarchicalrule/seed/family resampling DESCRIPTIVE withonly4rules/2seeds; no unseenrule/general-domain/strengthfromupdates orformalconfidence/equivalence. SameCore, notexternalengine.',audit_seconds=time.perf_counter()-start);(D/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k!='tallies'}))
if __name__=='__main__':run()
