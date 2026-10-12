"""Independentactualtrace/controller replay for samebinaryalignment learning."""
import json,math,random,sys,importlib.util,time,hashlib,statistics
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task143';O.mkdir(exist_ok=True)
for alias,path in [('E','results/dev_aux/task108/evolution.py'),('G','results/dev_aux/task104/short_game.py')]:
 s=importlib.util.spec_from_file_location(alias+'143',R/path);module=importlib.util.module_from_spec(s);s.loader.exec_module(module);globals()[alias]=module
def audit(task,output):
 P=R/f'results/dev_aux/task{task}';D=json.loads((R/'results/dev_aux/task140/declaration.json').read_bytes());F=json.loads((R/'results/dev_aux/task140/fixtures.json').read_bytes());C=json.loads((P/'controller.json').read_bytes());calls=C['calls'];counts=dict(games=0,moves=0,searches=0,probes=0,acks=0);nodes=[];start=time.monotonic()
 for c in calls:
  if c['result'] is None:assert F[str(c['context']['opening_seed'])]['terminal'];continue
  counts['games']+=1;r=c['result'];x=c['context'];w=c['weights'];b=chess.Board()
  assert r['opening']==F[str(x['opening_seed'])]['moves']
  for m in r['opening']:assert chess.Move.from_uci(m) in b.legal_moves;b.push_uci(m)
  rng=random.Random(x['random_seed']);si=0
  for text in r['actions']:
   assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(text);assert m in b.legal_moves
   if b.turn==x['agent_color']:
    meta=r['search_records'][si];assert meta['full_history']==[m.uci() for m in b.move_stack];assert meta['nodes_limit']==1024 and meta['backend'].endswith(D['binary_sha256']);assert isinstance(meta['reported_nodes'],int) and meta['reported_nodes']>0;nodes.append(meta['reported_nodes']);si+=1;counts['searches']+=1
   else:assert m==rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
   b.push(m);counts['moves']+=1
  assert si==len(r['search_records']);assert len(r['actions'])<=16 and b.fen()==r['final_fen']
  assert G.score(b,x['agent_color'],len(r['actions']),16)==r['score'];assert r['reward']==r['score']['reward'];assert len(r['candidate_leaf_probes'])==5
  for p in r['candidate_leaf_probes']:assert math.isfinite(p['measured_white_pawns']) and abs(p['measured_white_pawns']-w[p['type']]/208)<=.011;counts['probes']+=1
  parts=r['search_table_ack'].split();assert int(parts[4])==x['alignment'];table={int(q.split(':')[0]):tuple(map(int,q.split(':')[1:])) for q in parts[5:]}
  mg=(126,781,825,1276,2538);eg=(208,854,915,1380,2682);expected={i+1:(w[k],w[k]) if x['alignment'] else (mg[i],eg[i]) for i,k in enumerate('PNBRQ')};assert table==expected;counts['acks']+=1
 index=0;updates_verified=0;ends={};partial=False
 def block(w,seed,aligned,sweep,k,arm,phase):
  nonlocal index,partial
  rewards=[]
  for oi in range(8):
   for color in (True,False):
    if index==len(calls):partial=True;return None
    offset=(sweep*4+k)*8+oi if phase=='train' else oi
    x=dict(opening_seed=(1007000 if phase=='train' else 1009000)+offset,random_seed=(1107000 if phase=='train' else 1109000)+offset,agent_color=color,phase=phase,name=f's{seed}-align{aligned}-{phase}-g{sweep}-k{k}-a{arm}-o{oi}-c{int(color)}',start_seed=seed,alignment=aligned)
    c=calls[index];assert c['context']==x and c['weights']==w,(index,x,c['context']);rewards.append(0 if c['result'] is None else c['result']['reward']);index+=1
  return rewards
 for seed,aligned in D['seed_alignment_order']:
  theta=E.starts(seed);actual=next((r for r in C['runs'] if r['seed']==seed and r['alignment']==aligned),None)
  if actual is None:assert index==len(calls);partial=True;break
  assert actual['initial_weights']==E.weights(theta)
  ui=0
  for sweep,step in enumerate(D['steps']):
   for k in range(4):
    candidate=[theta[:],theta[:],theta[:]];candidate[1][k]=min(E.HIGH,theta[k]+step);candidate[2][k]=max(E.LOW,theta[k]-step)
    groups=[]
    for a,t in enumerate(candidate):
     rs=block(E.weights(t),seed,aligned,sweep,k,a,'train')
     if rs is None:break
     groups.append(rs)
    if partial:break
    means=[sum(z)/16 for z in groups];chosen=E.select(means);update=actual['updates'][ui]
    expected=dict(sweep=sweep,coordinate=E.TYPES[k],step=step,before=E.weights(theta),candidate_weights=[E.weights(t) for t in candidate],means=means,rewards=groups,selected=chosen,after=E.weights(candidate[chosen]))
    assert update==expected;theta=candidate[chosen][:];updates_verified+=1;ui+=1
   if partial:break
  if partial:break
  assert actual['final_weights']==E.weights(theta);ends[(seed,aligned)]=actual['final_weights']
 if not partial:
  assert index==D['training_slots'];assert len(ends)==6 and C['global_endpoint_freeze_at']
  endpoint=json.loads((P/'endpoints.json').read_bytes());assert endpoint['training_calls']==index and endpoint['complete'];assert endpoint['all_endpoints_frozen_at']==C['global_endpoint_freeze_at']
  for run in C['runs']:
   for arm in ('initial','final'):
    rs=block(run[arm+'_weights'],run['seed'],run['alignment'],0,0,arm,'heldout');assert rs is not None
    observed=[x['reward'] for x in run['heldout'] if x['arm']==arm];assert observed==rs
  assert index==len(calls)==D['total_slots'] and C['completed']
 else:assert not C['completed'] and index==len(calls)
 out=dict(complete=True,source_task=task,source_controller_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),validated_actual_prefix=not C['completed'],verified_calls=index,updates_verified=updates_verified,counts=counts,reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),reported_nodes_total=sum(nodes),wall_seconds=time.monotonic()-start,allends_beforeheldout=not partial,scope='Independentcompletehistory/legal/randomopponent/reward/probes/pricetable/schedule replay; notindependentlyreproducedengineexecution.')
 (O/output).write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2));return out
if __name__=='__main__':audit(sys.argv[1],sys.argv[2])
