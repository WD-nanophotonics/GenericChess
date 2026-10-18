"""Independent typed-history, episode TD and per-query mean bounded-loss audit."""


from pathlib import Path


from collections import Counter,defaultdict


from math import tanh,isclose,isfinite


import json,time,random,hashlib


from generic_chess.rules.compiler import compile_ruleset


from generic_chess.rules.schema import ruleset_from_dict


from generic_chess.session.session import GameSession


from generic_chess.session.serialization import deserialize_game_record,serialize_game_record


from results.dev_aux.task2529.training_audit import terminal,feat


from results.dev_aux.task2529.incremental_replay import advance


from scripts.generic_session_win_proof import SessionChoice


from results.dev_aux.task2392.reader import SharedDeleteStopReader


D=Path('results/dev_aux/task2555');O=Path('results/dev_aux/task2557')


CHANNELS=(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X'))


def near(a,b):return isclose(a,b,rel_tol=1e-10,abs_tol=1e-11)


def vector(a,b):assert len(a)==len(b)and all(near(x,y)for x,y in zip(a,b))


def run(prefix_rule=None,stop_root=None):


 began=time.perf_counter();p=json.loads((D/'plan.json').read_text());assert json.loads((D/'started.json').read_text())['plan_sha']==hashlib.sha256((D/'plan.json').read_bytes()).hexdigest()


 for name,h in json.loads((D/'pins.json').read_text())['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name


 stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop();games=[]


 for l in(D/'games.jsonl').open():


  try:r=json.loads(l)


  except json.JSONDecodeError:break


  if prefix_rule is None or r['generator_seed']==prefix_rule:games.append(r)


 limit=None


 if prefix_rule is not None:


  keys={(r['method'],r['seed'])for r in games};assert len(keys)==8 and all(max(r['total_nodes']for r in games if(r['method'],r['seed'])==k)==p['nodes_per_arm']for k in keys),'First rule not closed'


  limit=max(r['gameid']for r in games)


 def reader():


  for l in(D/'queries.jsonl').open():


   q=json.loads(l)


   if limit is not None and q['gameid']>limit:break


   yield q


 stream=iter(reader());nextq=next(stream,None);cc={gs:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{gs}.json').read_text())))for gs in p['generator_seeds']};counts=Counter();by=defaultdict(Counter);nodes=Counter();arms=defaultdict(list);index={}


 for g in games:


  stop();gid=g['gameid'];key=g['generator_seed'],g['method'],g['seed'];gs,method,seed=key;arms[key].append(g);index[gid]=g;w=list(g['initial_weights']);s=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(g['initial_record'])));previous=g['initial_record'];counts['prefix_plies']+=len(s.to_record().actions)


  fresh=GameSession(cc[gs]);rng=random.Random(gs*1000000+g['family'])


  for _ in range(p['prefix_plies']):


   if terminal(fresh)is not None:break


   aa=[SessionChoice('ACTION',action=a)for a in fresh.legal_actions()];fresh.submit(rng.choice(sorted(aa,key=repr)).action)


  assert json.loads(serialize_game_record(fresh.to_record()))==previous


  qs=[]


  while nextq is not None and nextq['gameid']==gid:qs.append(nextq);nextq=next(stream,None)


  preds=[];grads=[];observed=0;changedqueries=0;game_nodes=0


  for ply,q in enumerate(qs):


   assert q['ply']==ply and q['record_before']==previous and terminal(s)is None and q['actor']==s.state.position.side_to_move and q['color']==g['color']and q['family']==g['family'];actor=q['actor'];candidate=actor==g['color'];assert q['effective_depth']==(p['depth']if candidate else p['opponent_depth']);assert q['effective_nodes']<= (p['nodes_per_query']if candidate else p['opponent_nodes_per_query']);expected=w if candidate else p['foe'];vector(q['weights'],expected);expected=list(q['weights'])


   assert q['ordering_seed']==gs*100000000+g['family']*1000+ply+p['ordering_seed_offset'];assert q['nodes']<=q['effective_nodes']<=p['nodes_per_query']and 0<q['effective_seconds']<=p['seconds_per_query'];nodes[key]+=q['nodes'];game_nodes+=q['nodes'];assert q['total_nodes']==nodes[key];observe=candidate and q['complete'];assert q['observed']==observe;after=list(expected)


   if q['complete']:


    samples=q['samples'];assert samples and samples[-1]['depth']==q['effective_depth']and samples[-1]['phi']==list(feat(s,CHANNELS));assert float(samples[-1]['lower'])==float(samples[-1]['upper'])==q['value'];assert all(1<=a['depth']<=q['effective_depth']and float(a['lower'])<=float(a['upper'])for a in samples)


   else:assert not q['samples']and q['value']is None and not observe and ply==len(qs)-1;counts['failed_queries']+=1;counts['failed_query_nodes']+=q['nodes'];counts['full_limit_failed_queries']+=q['effective_nodes']==(p['nodes_per_query']if candidate else p['opponent_nodes_per_query'])


   if observe:


    observed+=1;value=tanh(q['value']/10);grad=[0.]*6 if q['pv_terminal']else[x*(1-value*value)/10 for x in q['pv_phi']]


    if not q['pv_terminal']:assert near(q['value'],sum(a*b for a,b in zip(expected,q['pv_phi'])))


    else:assert q['value']in(-1e6,0,1e6)


    if method=='TD':preds.append(value);grads.append(grad);assert not q['learning']['changed']


    else:


     delta=[0.]*6;loss=0.;active=0


     for sample in q['samples']:


      phi=sample['phi'];pred=tanh(sum(a*b for a,b in zip(expected,phi))/10);lo=tanh(float(sample['lower'])/10);hi=tanh(float(sample['upper'])/10);error=lo-pred if pred<lo else hi-pred if pred>hi else 0.;loss+=error*error/2;active+=error!=0


      for j in range(6):delta[j]+=error*phi[j]*(1-pred*pred)/10


      kind='exact'if sample['lower']==sample['upper']else'upper'if float(sample['lower'])==float('-inf')else'lower';by[method]['samples_'+kind]+=1;by[method]['inactive_'+kind]+=error==0


     n=len(q['samples']);after=[a+p['eta']*b/n for a,b in zip(expected,delta)];st=q['learning'];assert st['samples']==n and st['active']==active and near(st['loss'],loss/n)and st['changed']==any(delta);changedqueries+=st['changed'];by[method]['samples']+=n;by[method]['active']+=active;by[method]['loss_sum']+=loss;w=list(after)


   else:assert q['learning']is None


   vector(q['weights_after'],after)

   if candidate:w=list(q['weights_after'])

   if prefix_rule is None and q['complete']:
    action=q['record_after']['actions'][-1];counts['committed_drop_moves']+=action['kind']=='drop';counts['committed_promotion_moves']+=action.get('promotion_target_id')is not None
   s=advance(s,q['record_after'],q['complete']);counts['training_plies']+=q['complete'];previous=q['record_after'];by[method]['queries']+=1;by[method]['candidate_queries'if candidate else'foe_queries']+=1


  actual=terminal(s);assert previous==g['record']and actual==g['outcome']and g['reward']==(None if actual is None else actual*(1 if g['color']==0 else-1))and g['nodes']==game_nodes and g['total_nodes']==nodes[key]and g['queries']==len(qs)and g['observed']==observed and g['changed_queries']==changedqueries


  replay=GameSession.replay(cc[gs],deserialize_game_record(json.dumps(g['record'])));assert replay.state==s.state and replay.result==s.result and replay.to_record()==s.to_record()


  if method=='TD':


   errors=[preds[i+1]-preds[i]for i in range(len(preds)-1)]


   if actual is not None and preds:errors.append(actual-preds[-1])


   delta=[0.]*6;future=0.


   for i in reversed(range(len(preds))):


    future=(errors[i]if i<len(errors)else 0)+p['lam']*future;delta=[a+future*b for a,b in zip(delta,grads[i])]


   w=[a+p['eta']*b for a,b in zip(w,delta)];assert g['stats']['samples']==len(errors)and g['stats']['observed_searches']==len(preds)and g['stats']['censored']==(actual is None)and near(g['stats']['loss'],sum(x*x/2 for x in errors)/max(1,len(errors)));by[method]['samples']+=len(errors);by[method]['loss_sum']+=sum(x*x/2 for x in errors)


   if g['color']==1 and actual is not None and qs and qs[-1]['actor']==0 and preds:counts['black_candidate_white_foe_finisher']+=1;assert g['reward']==-actual and not qs[-1]['observed']


  else:assert g['stats']is None


  vector(g['after_weights'],w);counts['games']+=1;counts['actual_terminal']+=actual is not None;counts['unknown']+=actual is None;counts['queries']+=len(qs);counts['observed']+=observed;counts['query_updates']+=changedqueries;counts['nodes']+=game_nodes;by[method]['nodes']+=game_nodes;by[method]['games']+=1;by[method]['query_updates']+=changedqueries;by[method]['actual_terminal']+=actual is not None;by[method]['unknown']+=actual is None


 assert nextq is None


 updates={}


 for line in(D/'updates.jsonl').open():


  try:u=json.loads(line)


  except json.JSONDecodeError:break


  if prefix_rule is not None and u['generator_seed']!=prefix_rule:continue


  assert len(u['gameids'])==1;gid=u['gameids'][0];assert gid not in updates;updates[gid]=u


 for g in games:


  u=updates[g['gameid']];assert (u['generator_seed'],u['method'],u['seed'],u['index'])==(g['generator_seed'],g['method'],g['seed'],g['index']);assert u['nodes']==g['total_nodes']and u['before']==g['initial_weights']and u['after']==g['after_weights']and u['changed']==(u['before']!=u['after'])


 counts['update_records']=len(games)


 for key,gg in arms.items():


  rng=random.Random(key[2]);w=[1.]+[rng.uniform(.5,1.5)for _ in range(5)]


  for i,g in enumerate(gg):assert g['index']==i and g['color']==i%2 and g['family']==p['training_family_offset']+i//2;vector(g['initial_weights'],w);w=g['after_weights']


 if prefix_rule is None:


  done=json.loads((D/'result.json').read_text());assert counts['nodes']==done['nodes']and all(counts[k]==v for k,v in done['counts'].items())


  for a in done['arms']:


   key=a['generator_seed'],a['method'],a['seed'];gg=arms[key];vector(a['weights'],gg[-1]['after_weights']);assert a['nodes']==nodes[key]and len(gg)==a['games']and sum(g['initial_weights']!=g['after_weights']for g in gg)==a['updates']and sum(g['changed_queries']for g in gg)==a['query_updates']


 result=dict(status='PASS_TYPED_HISTORY_EPISODE_TD_AND_MEAN_BOUND_AWARE_TREESTRAP',prefix_rule=prefix_rule,arms=len(arms),counts=dict(counts),by_method={k:dict(v)for k,v in by.items()},seconds=time.perf_counter()-began,scope='Every paid candidate/foe/failed search, independent signedwhite feature-gradient math and reverseTD/one-sidedloss reconstruction; full typed legal replay and final public Session equality. Does not rerun every search. Bound correctness independently sampled by separate unpruned D3 audit; noexternalrulesengine.')


 (O/('training-audit.json'if prefix_rule is None else'training-audit-first-rule.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result))


if __name__=='__main__':run()
