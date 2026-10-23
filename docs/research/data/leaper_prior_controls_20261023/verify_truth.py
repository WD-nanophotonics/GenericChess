"""Rebuild only the five new components, then check all published history bounds.

Shared Core is authoritative; this is not an independent rules implementation.
Raw ledgers and pickle files are neither required nor read.
"""
import sys,json,gzip,time,argparse,subprocess,copy
from pathlib import Path
from collections import Counter,deque
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha,record_value,match_action as match_primary
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_parameter_regions import draw_only_closure
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.actions import action_to_dict
from generic_chess.session.serialization import deserialize_game_record
ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--source-from-git',action='store_true');a=ap.parse_args();start=time.perf_counter();counts=Counter()
def read(n):return json.loads(gzip.decompress((a.directory/n).read_bytes()))
p=read('truth.json.gz');new=read('new_context.json.gz');mechanism=read('mechanisms.json.gz');rules=p['rules'];compiled={fp:compile_rule(ruleset_from_dict(r))for fp,r in rules.items()};graphs={};census={e['id']:e for e in p['source_census']['histories']}
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def replay(c,r):return GameSession.replay(c,deserialize_game_record(json.dumps(r)))
def match(s,raw):
 aa=[z for z in s.legal_actions()if action_to_dict(z)==raw];assert len(aa)==1;return aa[0]
for fp,r in rules.items():
 assert set(r)<=set('schema_version piece_types promotion_allowed promotion_forced repetition_limit max_ply stalemate_result board_size metadata capture_disposition initial_position initial_setup_options drop_allowed'.split())
 assert r['repetition_limit']==4 and r['max_ply']==128 and r['capture_disposition']=='remove_from_game'and not r['promotion_allowed']and not r['promotion_forced'];assert all(not t['is_promotable']and not t['promotion_target_ids']and all(z['kind']=='leap'for z in t['movement_atoms'])for t in r['piece_types']);assert all(not any(row)for vv in r['drop_allowed'].values()for row in vv)
for e in p['graph_manifest']:
 group=[z for z in census.values()if z['world']==e['world']];assert e['selection_hash']==min(z['selection_hash']for z in group)
if a.source_from_git:
 import hashlib
 raw=subprocess.check_output(['git','show','bf725532ea38deb5242538575c4065a63615b8c2:docs/research/data/leaper_prefix_label_20261023/observations.json.gz']);assert hashlib.sha256(raw).hexdigest()=='6d758fc8f2b255f458585485e084c8327be5a0ad0e4bcf4c5a25f7bcd3e75d73';original=json.loads(gzip.decompress(raw));worlds={w['world']:w for w in original['runs']['commonfoe']['files']['inputs.json']['worlds']};seen=set();refs=Counter()
 for g in original['games']:
  if g['run']!='commonfoe':continue
  game=g['game'];w=worlds[game['world']]
  if w['encoding']!=0:continue
  s=replay(compiled[w['fingerprint']],game['initial_record'])
  for q in game['queries']:
   if sum(z is not None for z in s.state.position.board)==4 and not s.state.terminal_status.is_terminal:seen.add(state_sha(s.state));refs[str(w['original_world'])]+=1
   if q['action']is not None:s.submit(match_primary(s,q['action']))
 assert seen==set(census)and dict(refs)==p['source_census']['references'];counts['source_references']=sum(refs.values());counts['source_histories']=len(seen)
def build(e,expected):
 c=compiled[e['fingerprint']];root=replay(c,e['record']).state;positions=[];idx={};todo=deque();edges=[];actions=[];term={};beg=time.perf_counter()
 def add(pos):
  if pos not in idx:assert len(positions)<101280;idx[pos]=len(positions);positions.append(pos);todo.append(pos)
  return idx[pos]
 add(root.position)
 while todo:
  if time.perf_counter()-beg>180 or time.perf_counter()-start>1200 or role_stop_requested():raise RuntimeError('VERIFY_CAP_OR_STOP')
  pos=todo.popleft();i=idx[pos];assert i==len(edges);st=fresh_state(pos,c)
  if st.terminal_status.is_terminal:
   t=st.terminal_status;term[i]=0 if t.winner is None else 1 if t.winner==pos.side_to_move else-1;edges.append(());actions.append(())
  else:
   aa=list(legal_actions(st,c));edges.append(tuple(add(apply_action(st,z,c).position)for z in aa));actions.append(tuple(action_to_dict(z)for z in aa))
 assert len(positions)==expected['positions']and sum(map(len,edges))==expected['edges'];values,ranks=attractor(edges,term);counts['graph_entries']+=len(positions);counts['graph_edges']+=sum(map(len,edges));counts['graphs']+=1;print('GRAPH',e['world'],len(positions),round(time.perf_counter()-beg,3),flush=True)
 return dict(idx=idx,edges=edges,actions=actions,terminals=term,values=values,ranks=ranks,root=0)
def label(st,c,g):
 hid=state_sha(st)
 if st.position not in g['idx']:return dict(status='UNCOVERED',id=hid)
 assert not st.terminal_status.is_terminal;i=g['idx'][st.position];prior=max(n for k,n in st.repetition_counts);remaining=128-st.ply_count;protected=prior<=2
 def bound(ch,left):
  v=g['values'][ch]
  if ch in g['terminals']or v==0:return[v,v]
  if g['ranks'][ch]>left:return[0,0]
  return[v,v]if protected else[0,1]if v==1 else[-1,0]
 branches=[];aa=list(legal_actions(st,c));assert [action_to_dict(z)for z in aa]==list(g['actions'][i])
 for z,ch in zip(aa,g['edges'][i]):
  actual=apply_action(st,z,c)
  if actual.terminal_status.is_terminal:
   t=actual.terminal_status;v=0 if t.winner is None else 1 if t.winner==st.position.side_to_move else-1;bb=[v,v]
  else:lo,hi=bound(ch,remaining-1);bb=[-hi,-lo]
  branches.append(dict(action=action_to_dict(z),bounds=bb))
 return dict(status='EXACT'if all(b['bounds'][0]==b['bounds'][1]for b in branches)else'BOUNDED',id=hid,root_bounds=[max(z['bounds'][0]for z in branches),max(z['bounds'][1]for z in branches)],actions=branches,prior=prior,remaining=remaining,protected=protected,rank=g['ranks'].get(i))
for e in p['graph_manifest']:graphs[e['world']]=build(e,next(z for z in p['graph_rows']if z['id']==e['id']))
for row in p['source_labels']:
 e=census[row['id']];c=compiled[e['fingerprint']];actual=label(replay(c,e['record']).state,c,graphs[e['world']]);assert dict(world=e['world'],**actual)==row;counts['source_bounds_checked']+=1
worlds={w['world']:w for w in new['inputs']['worlds']};openings={(o['world'],o['prefix']):o for o in new['inputs']['openings']};truth={(r['world'],r['id']):r for r in p['query_truth']['histories']};paths={};states={}
for ri,record in enumerate(new['records']):
 w=next(w for w in worlds.values()if w['fingerprint']==record['ruleset_fingerprint']);s=GameSession(compiled[w['fingerprint']]);path=[]
 for raw in record['actions']:
  key=(w['world'],state_sha(s.state));path.append((key,s.state,raw));states[key]=s.state;s.submit(match(s,raw))
 paths[ri]=path
for key,row in truth.items():
 st=states[key];c=compiled[worlds[key[0]]['fingerprint']];assert dict(world=key[0],**label(st,c,graphs[key[0]]))==row;counts['query_bounds_checked']+=1
quality={name:{}for name in('unit','B2C1','mobility','Static')};refs=Counter()
for g in new['games']:
 o=openings[g['world'],g['prefix']];path=paths[g['record']][len(o['record']['actions']):];assert len(path)==g['query_count'];refs['all_query_references']+=len(path)
 for key,st,raw in path:
  if sum(z is not None for z in st.position.board)>4:continue
  refs['capture_reduced_references']+=1;row=truth[key]
  if st.position.side_to_move!=g['role']:continue
  name=g['price'];refs[name]+=1;z=dict(status=row['status'])
  if row['status']!='UNCOVERED':
   b=next(b for b in row['actions']if b['action']==raw);z.update(definitely_worse=b['bounds'][1]<row['root_bounds'][0],possibly_worse=b['bounds'][0]<row['root_bounds'][1])
  quality[name][(*key,canon(raw))]=z
assert {k:refs[k]for k in p['intersection']['counts']}==p['intersection']['counts']
for name,unique in quality.items():
 cc=Counter(z['status']for z in unique.values());cc['definitely_worse']=sum(z.get('definitely_worse',False)for z in unique.values());cc['possibly_worse']=sum(z.get('possibly_worse',False)for z in unique.values());assert p['intersection']['candidate_actions'][name]==dict(reference_count=refs[name],distinct_history_actions=len(unique),counts=dict(cc))
counter=mechanism['counter_truth'];e=counter['manifest'][0];g=build(e,counter['rows'][0]);c=compiled[e['fingerprint']];st=replay(c,e['record']).state;row=label(st,c,g);assert max(n for k,n in st.repetition_counts)==3 and row['root_bounds']==[0,0]and all(z['bounds']==[0,0]for z in row['actions']);dead=draw_only_closure(g['edges'],g['terminals']);assert (g['root']in dead)==counter['structural']['root_in_structural_drawonly'];counts['counter_actions']=len(row['actions'])
bad=copy.deepcopy(row);bad['actions'][0]['bounds']=[1,1];assert bad!=label(st,c,g);counts['negative_controls']+=1
result=dict(status='PASS',seconds=time.perf_counter()-start,counts=counts,scope='FiveNEWcompleteCoregraphrebuilds,133sourcehistories,3367queryhistories andall512slot decisionreferences checked. Sum entries includes overlapping/isomorphic components,notindependentstates. No oldgraphs/runs refilled;nonzero saturated bounds retain uncertainty.');a.output.write_text(json.dumps(result,indent=2),encoding='utf8');print('FINAL',json.dumps(result),flush=True)
