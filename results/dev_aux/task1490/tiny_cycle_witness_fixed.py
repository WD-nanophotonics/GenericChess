from pathlib import Path
import json,collections,importlib.util,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1514';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1495';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));oracle=json.loads((G/'values.json').read_bytes())['value'];edges=[json.loads(x)['moves'] for x in (G/'edges.jsonl').read_text().splitlines()];study=json.loads((R/'results/dev_aux/task1503/study.json').read_bytes());dev=[i for f in study['families'] if f['phase']=='DEV' for i in f['state_ids']];policy={p:{} for p in [720,1728]}
for line in (R/'results/dev_aux/task1507/choices.jsonl').open():
 x=json.loads(line);policy[x['leafR']][x['state_id']]=x['child_id']
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1490/tiny_rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);witnesses=[];coverage=[]
for price in [720,1728]:
 for color in [0,1]:
  actual=json.loads((R/f'results/dev_aux/task1512/B16_R{price}_C{color}.json').read_bytes())['value'];allowed=lambda i:actual[i]==0 and oracle[i]*(1 if states[i][6]==color else -1)==1
  adj={i:([(u,j) for u,j in edges[i] if j==policy[price][i] and allowed(j)] if states[i][6]==color else [(u,j) for u,j in edges[i] if allowed(j)]) for i in range(len(states)) if allowed(i)};seen=set();found=None
  candidates=[i for i in dev if states[i][6]==color and allowed(i)];allroots=candidates+[i for i in adj if i not in candidates]
  for root in allroots:
   if root in seen:continue
   stack=[(root,iter(adj[root]))];active={root:0};pathmoves=[]
   while stack and found is None:
    i,it=stack[-1]
    try:u,j=next(it)
    except StopIteration:
     seen.add(i);active.pop(i);stack.pop()
     if pathmoves:pathmoves.pop()
     continue
    if j in active:
     ids=[x[0] for x in stack]+[j];moves=pathmoves+[u];cut=active[j];found={'price':price,'candidatecolor':color,'root_state_id':root,'root_basis':'FROZEN_DEV' if root in candidates else 'ALLGRAPH_EXPOSED_MECHANISM','path_state_ids':ids,'path_moves':moves,'cycle_start_index':cut,'cycle_state_ids':ids[cut:],'cycle_moves':moves[cut:]};break
    if j in seen:continue
    active[j]=len(stack);stack.append((j,iter(adj[j])));pathmoves.append(u)
   if found is not None:break
  coverage.append({'price':price,'color':color,'eligible_preserved_win_policy_draw_states':len(adj),'searched_closed_nodes':len(seen),'frozenDEVeligible':len(candidates),'found':found is not None})
  if found:
   for i,u,j in zip(found['path_state_ids'],found['path_moves'],found['path_state_ids'][1:]):
    assert [u,j] in edges[i] and allowed(i) and allowed(j)
    if states[i][6]==color:assert policy[price][i]==j
   assert found['cycle_state_ids'][0]==found['cycle_state_ids'][-1];found['fens']=[T.fen(states[i]) for i in found['path_state_ids']];witnesses.append(found)
needed={(x['price'],i) for x in witnesses for i in x['path_state_ids'] if states[i][6]==x['candidatecolor']};raw=[]
for line in (R/'results/dev_aux/task1507/choices.jsonl').open():
 x=json.loads(line)
 if (x['leafR'],x['state_id']) in needed:raw.append(x)
assert len(raw)==len(needed)
out={'status':'ACTUAL_CACHED_WIN_PRESERVING_CYCLE_WITNESSES','coverage':coverage,'witnesses':witnesses,'cached_own_choice_rows':raw,'scope':'Cold deterministic16node strategy only; all states stay originaloracle candidate-winning and full-policy DRAW. Each ownchosenedge actualcached or solelegal; opponentlegal drawsafe. Complete explicit cycle proves non-realization under one legal defense, not warm/history strategy claim. Allgraph fallback is exposedmechanism, not newDEV success.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(coverage);print([{k:v for k,v in x.items() if k!='fens'} for x in witnesses])

