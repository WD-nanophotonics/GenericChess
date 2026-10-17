"""Independent full-history and matched-prefix/opportunity diagnostic; no new play."""
from pathlib import Path
from collections import Counter
from dataclasses import replace
import json,random,hashlib,time
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2525.run import RecordedSessionEnv
from results.dev_aux.task2529.incremental_replay import advance
from results.dev_aux.task2529.training_audit import terminal
D=Path('results/dev_aux/task2544');T=Path('results/dev_aux/task2539')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run():
 began=time.perf_counter();p=json.loads((D/'plan.json').read_text());done=json.loads((D/'result.json').read_text());bind=json.loads((D/'pre-fitness-binding.json').read_text());assert bind['plan_sha']==hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()and bind['training_result_sha']==hashlib.sha256((T/'result.json').read_bytes()).hexdigest();assert json.loads((D/'started.json').read_text())['plan_sha']==bind['plan_sha']
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 train=json.loads((T/'result.json').read_text());arms={(a['generator_seed'],a['method'],a['seed']):a for a in train['arms']};cc={g:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{g}.json').read_text())))for g in p['generator_seeds']};roots={};actors={};rootstatus={};index={};counts=Counter();positions={tuple(v):i for i,v in enumerate(p['slots'])};last=-1
 for g in p['generator_seeds']:
  names=next(a['channels']for a in train['arms']if a['generator_seed']==g)
  for family in p['families']:
   for k in p['prefix_plies_options']:
    env=RecordedSessionEnv(GameSession(cc[g]),names);rng=random.Random(g*1000000+family)
    for _ in range(k):
     if env.terminal()is not None:break
     env.push(rng.choice(sorted(env.actions(),key=repr)))
    roots[g,family,k]=env.record();actors[g,family,k]=env.player();rootstatus[g,family,k]=env.terminal()
   a=roots[g,family,4];b=roots[g,family,5];s=GameSession.replay(cc[g],deserialize_game_record(json.dumps(a)))
   if terminal(s)is not None:assert a==b;counts['terminal_parent_retained']+=1
   else:advance(s,b,True);counts['legal_parent_child_prefix_edges']+=1
 def queries():
  for line in(D/'queries.jsonl').open():yield json.loads(line)
 stream=iter(queries());q=next(stream,None)
 for line in(D/'games.jsonl').open():
  r=json.loads(line);key=tuple(r['slot']);assert key in positions and positions[key]>last and key not in index;last=positions[key];index[key]=r;g,seed,family,color,treatment,foe,k=key;a=arms[g,'TD'if treatment=='initial'else treatment,seed];weights=a['initial']if treatment=='initial'else a['weights'];assert r['weights']==weights and r['initial_record']==roots[g,family,k]and r['root_actor']==actors[g,family,k]and r['prefix_plies']==k;s=GameSession.replay(cc[g],deserialize_game_record(json.dumps(r['initial_record'])));previous=r['initial_record'];counts['legal_prefix_plies']+=len(s.to_record().actions);n=0;ns=0
  while q is not None and tuple(q['slot'])==key:
   assert q['ply']==n and q['record_before']==previous and terminal(s)is None;expected=weights if s.state.position.side_to_move==color else p['opponents'][foe];assert q['weights']==expected and q['effective_node_limit']==p['nodes_per_query']and q['nodes']<=q['effective_node_limit']and 0<q['effective_wall_limit']<=p['seconds_per_query']and q['effective_wall_limit']<=q['global_remaining_before_query'];n+=1;ns+=q['nodes']
   if not q['complete']:assert q['record_after']==previous;counts['failed_queries']+=1
   s=advance(s,q['record_after'],q['complete']);counts['legal_play_plies']+=q['complete'];previous=q['record_after'];q=next(stream,None)
  public=GameSession.replay(cc[g],deserialize_game_record(json.dumps(r['record'])));assert s.state==public.state and s.result==public.result and s.to_record()==public.to_record();z=terminal(s);assert r['record']==previous and r['outcome']==z and r['reward']==(None if z is None else z*(1 if color==0 else-1))and r['queries']==n and r['nodes']==ns;assert(z is not None)==(r['ending']=='ACTUAL_TERMINAL');counts['games']+=1;counts['queries']+=n;counts['nodes']+=ns;counts['actual_terminal']+=z is not None;counts['unknown']+=z is None;counts[r['ending']]+=1
 assert q is None and counts['games']==done['actual']and counts['nodes']==done['nodes']and counts['queries']==done['queries']
 def iv(g,s,f,c,t,foe,k):
  v=index.get((g,s,f,c,t,foe,k),{}).get('reward');return(-1,1)if v is None else(v,v)
 def bound(gs,ss,fs,foe,t,base,ks,colors=(0,1),match=None):
  lo=hi=n=0
  for g in gs:
   for seed in ss:
    for f in fs:
     for k in ks:
      for c in colors:
       if match is not None and(c==actors[g,f,k])!=match:continue
       x=iv(g,seed,f,c,t,foe,k);y=iv(g,seed,f,c,base,foe,k);lo+=x[0]-y[1];hi+=x[1]-y[0];n+=1
  return dict(bounds=[lo/n,hi/n],pairs=n)
 contrasts=[]
 for foe in p['opponents']:
  for k in p['prefix_plies_options']:
   for t,base in(('TD','initial'),('WDL','initial'),('TD','WDL')):
    z=bound(p['generator_seeds'],p['initial_seeds'],p['families'],foe,t,base,[k]);contrasts.append(dict(foe=foe,prefix_plies=k,treatment=t,base=base,**z,per_color=[dict(color=c,**bound(p['generator_seeds'],p['initial_seeds'],p['families'],foe,t,base,[k],colors=(c,)))for c in(0,1)],per_rule=[dict(rule=g,**bound([g],p['initial_seeds'],p['families'],foe,t,base,[k]))for g in p['generator_seeds']],per_seed=[dict(seed=s,**bound(p['generator_seeds'],[s],p['families'],foe,t,base,[k]))for s in p['initial_seeds']]))
 opportunity=[];deltas=[]
 for foe in p['opponents']:
  for match in(True,False):opportunity.append(dict(foe=foe,root_side_matches_candidate=match,**bound(p['generator_seeds'],p['initial_seeds'],p['families'],foe,'TD','WDL',p['prefix_plies_options'],match=match)))
  aa=next(c['bounds']for c in contrasts if(c['foe'],c['prefix_plies'],c['treatment'],c['base'])==(foe,4,'TD','WDL'));bb=next(c['bounds']for c in contrasts if(c['foe'],c['prefix_plies'],c['treatment'],c['base'])==(foe,5,'TD','WDL'));deltas.append(dict(foe=foe,prefix5_minus_prefix4_TD_WDL_bounds=[bb[0]-aa[1],bb[1]-aa[0]]))
 oldtrain={digest(json.loads(x)['initial_record'])for x in(T/'games.jsonl').read_text().splitlines()};oldval={digest(json.loads(x)['initial_record'])for x in Path('results/dev_aux/task2540/games.jsonl').read_text().splitlines()};rootrows=[dict(rule=g,family=f,prefix_plies=k,actor=actors[g,f,k],terminal=rootstatus[g,f,k],fullrecord_sha=digest(rec),overlap_original_TRAIN=digest(rec)in oldtrain,overlap_original_EVAL=digest(rec)in oldval)for(g,f,k),rec in roots.items()]
 unchanged=Counter()
 for a in train['arms']:
  if a['weights']!=a['initial']:continue
  unchanged['models']+=1
  for f in p['families']:
   for c in(0,1):
    for foe in p['opponents']:
     for k in p['prefix_plies_options']:
      x=index.get((a['generator_seed'],a['seed'],f,c,a['method'],foe,k));y=index.get((a['generator_seed'],a['seed'],f,c,'initial',foe,k))
      if x is None or y is None:unchanged['missing']+=1;continue
      if x['ending']in('SEARCH_RESOURCE_UNKNOWN','GLOBAL_CAP_UNKNOWN')or y['ending']in('SEARCH_RESOURCE_UNKNOWN','GLOBAL_CAP_UNKNOWN'):unchanged['resource_unknown']+=1;continue
      assert x['record']==y['record']and x['reward']==y['reward'];unchanged['identical']+=1
 out=dict(status='PASS_ADAPTIVE_MATCHED_PREFIX_FULL_HISTORIES_AND_BOUNDED_UTILITIES',counts=dict(counts),planned=len(p['slots']),returned=len(index),missing=len(p['slots'])-len(index),contrasts=contrasts,opportunity=opportunity,prefix_interaction=deltas,roots=dict(registered=len(roots),distinct=len({digest(r)for r in roots.values()}),already_terminal=sum(z is not None for z in rootstatus.values()),TRAIN_overlap=sum(r['overlap_original_TRAIN']for r in rootrows),original_EVAL_overlap=sum(r['overlap_original_EVAL']for r in rootrows),rows=rootrows),unchanged=dict(unchanged),audit_seconds=time.perf_counter()-began,scope='AdaptiveFOLLOWUPafteroriginalfitness/ALLfrozenmodels/newPRNGfamilies/parent4-child5. FinitepanelboundsONLY/no formalCI/newmethodwinner/purecolorcausalclaim. Root_side_matches_candidate usesACTUALtypedstate, terminalrootsretained/noactionopportunityimputed. Addedrandommovechangespositions/history aswellasside, canonicalpolicyorderingbyfullprefixlength. AllU/missing[-1,1]/oldcapsunchanged/no refit.')
 (D/'audit.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items()if k not in('contrasts','roots')}))
if __name__=='__main__':run()
