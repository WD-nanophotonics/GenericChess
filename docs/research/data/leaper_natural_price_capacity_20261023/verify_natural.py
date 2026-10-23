"""Rebuild closed graphs from Core and verify the new natural-history census.

No fresh-history label is accepted without the stated repeat4/rank conditions.
It reads JSON only; optional pickle outputs are private acceleration caches.
"""
import sys,json,gzip,time,argparse,pickle,copy,subprocess,hashlib
from pathlib import Path
from collections import deque,Counter
from fractions import Fraction as F
from itertools import combinations
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_parameter_regions import material_vector
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.actions import action_to_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.config import MATE_SCORE
pa=argparse.ArgumentParser();pa.add_argument('data',type=Path);pa.add_argument('--output',type=Path,required=True);pa.add_argument('--cache',type=Path);pa.add_argument('--source-from-git',action='store_true');pa.add_argument('--census-only',action='store_true');args=pa.parse_args();p=json.loads(gzip.decompress(args.data.read_bytes()));start=time.perf_counter();counts=Counter();byid={r['id']:r for r in p['manifest']};rows={r['id']:r for r in p['rows']};details=[]
if args.cache:args.cache.mkdir(exist_ok=False)
for rule in p['rules'].values():
 assert set(rule)<=set('schema_version piece_types promotion_allowed promotion_forced repetition_limit max_ply stalemate_result board_size metadata capture_disposition initial_position initial_setup_options drop_allowed'.split())
 assert rule['board_size']==4 and rule['repetition_limit']==4 and rule['max_ply']==128
 assert rule['capture_disposition']=='remove_from_game'and not rule['promotion_allowed']and not rule['promotion_forced']
 assert all(not any(row)for rows in rule['drop_allowed'].values()for row in rows)
 assert all(not t['is_promotable']and not t['promotion_target_ids']and all(a['kind']=='leap'and any(a['offset'])for a in t['movement_atoms'])for t in rule['piece_types'])
def replay(c,r):return GameSession.replay(c,deserialize_game_record(json.dumps(r)))
def check(c,g,e,row):
 s=replay(c,e['record']);assert state_sha(s.state)==e['id'];assert len(s.state.history)==s.state.ply_count+1;assert Counter(h.position_key for h in s.state.history)==dict(s.state.repetition_counts)
 assert max(n for k,n in s.state.repetition_counts)<=2;remaining=c.max_ply-s.state.ply_count;assert remaining>max(g['ranks'].values(),default=0);i=g['idx'][s.state.position];cs=g['edges'][i];assert cs and row['root_wdl']==g['values'][i];labels=[-g['values'][ch]for ch in cs];assert labels==row['labels']and max(labels)==g['values'][i]
 actions=[action_to_dict(a)for a in legal_actions(s.state,c)];assert actions==row['actions'];assert len(actions)==len(cs);types=sorted({z.current_type_id for z in s.state.position.board if z and z.current_type_id!='K'});assert types==row['types'];sign=1 if s.state.position.side_to_move==0 else-1;forms=[]
 for j,a in enumerate(legal_actions(s.state,c)):
  ch=apply_action(s.state,a,c);assert ch.position==g['positions'][cs[j]]
  if ch.terminal_status.is_terminal:
   t=ch.terminal_status;v=0 if t.winner is None else 1 if t.winner==s.state.position.side_to_move else-1;forms.append((v*(MATE_SCORE-1),0))
  else:
   v=material_vector(ch.position);forms.append((sign*v['ABC'.index(types[0])],0 if len(types)==1 else sign*v['ABC'.index(types[1])]))
 assert list(map(list,forms))==row['forms'];cuts={F(1,4),F(1),F(4)}
 for (a,b),(d,f) in combinations(forms,2):
  if b!=f and F(1,4)<=F(d-a,b-f)<=4:cuts.add(F(d-a,b-f))
 cuts=sorted(cuts);expected=set(cuts)|{(a+b)/2 for a,b in zip(cuts,cuts[1:])};assert set(F(q['r'])for q in row['cells'])==expected
 for cell in row['cells']:
  r=F(cell['r']);scores=[a+b*r for a,b in forms];selected=[j for j,v in enumerate(scores)if v==max(scores)];assert selected==cell['selected'];bad=sum(labels[j]<max(labels)for j in selected)
  assert F(cell['expected_error'])==F(bad,len(selected));assert cell['forced']==(bad==len(selected));assert cell['unsafe']==(0<bad<len(selected));assert F(cell['expected_wdl'])==F(sum(labels[j]for j in selected),len(selected))
  if cell['served']is not None:assert cell['served']in selected and cell['served_wdl']==labels[cell['served']]and cell['completed_depth']==1
 return len(actions),len(row['cells'])
negative=False
if args.source_from_git:
 from scripts.leaper_design import match_action as match_source_action
 raw=subprocess.check_output(['git','show','55abf3de22f20ac03eb07b5260284466173a3264:docs/research/data/small_rule_family_20261022/observations.json.gz']);assert hashlib.sha256(raw).hexdigest()=='1a48f7eaf038cc7745d6dd82ebc784d7a666286a59c7d159c4c1ba3c5338d087'
 original=json.loads(gzip.decompress(raw));cc={fp:compile_rule(ruleset_from_dict(r))for fp,r in p['rules'].items()};observed={}
 for game in original['games']:
  if game['batch']!='small_ladder'or game['ruleset_fingerprint']not in cc:continue
  c=cc[game['ruleset_fingerprint']];s=replay(c,game['initial_record'])
  for q in game['queries']:
   if sum(z is not None for z in s.state.position.board)==4 and not s.state.terminal_status.is_terminal:
    hid=state_sha(s.state);entry=observed.setdefault(hid,dict(world=game['world'],fingerprint=game['ruleset_fingerprint'],origins=[]));entry['origins'].append(dict(slot=game['slot'],ply=s.state.ply_count));counts['source_references']+=1
   if q['action']is not None:s.submit(match_source_action(s,q['action']))
 assert set(observed)==set(byid)
 for hid,e in observed.items():
  assert e['world']==byid[hid]['world']and e['fingerprint']==byid[hid]['fingerprint'];assert sorted((o['slot'],o['ply'])for o in e['origins'])==sorted((o['slot'],o['ply'])for o in byid[hid]['origins'])
 assert counts['source_references']==2060;counts['source_histories']=len(observed)
if args.census_only:
 assert args.source_from_git
 result=dict(status='PASS',seconds=time.perf_counter()-start,counts=counts,scope='Original fixed55ab compressed Gitblob hash and all source query histories/origins independently re-enumerated;no graphrebuild or new scientific slots.');args.output.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);raise SystemExit(0)
for case in sorted(p['graph_manifest'],key=lambda r:r['world']):
 c=compile_rule(ruleset_from_dict(p['rules'][case['fingerprint']]));root=replay(c,case['record']).state;positions=[];idx={};todo=deque();edges=[];term={};beg=time.perf_counter()
 def add(pos):
  if pos not in idx:idx[pos]=len(positions);positions.append(pos);todo.append(pos)
  return idx[pos]
 add(root.position)
 while todo:
  if time.perf_counter()-beg>240 or time.perf_counter()-start>2400 or role_stop_requested():raise RuntimeError('VERIFY_CAP_OR_STOP')
  pos=todo.popleft();i=idx[pos];assert i==len(edges);s=fresh_state(pos,c)
  if s.terminal_status.is_terminal:
   t=s.terminal_status;term[i]=0 if t.winner is None else 1 if t.winner==pos.side_to_move else-1;edges.append(())
  else:edges.append(tuple(add(apply_action(s,a,c).position)for a in legal_actions(s,c)))
 expected=next(r for r in p['graph_rows']if r['world']==case['world']);assert len(positions)==expected['positions']and sum(map(len,edges))==expected['edges'];values,ranks=attractor(edges,term);g=dict(positions=positions,idx=idx,edges=edges,terminals=term,values=values,ranks=ranks)
 local=Counter()
 for e in p['manifest']:
  if e['world']!=case['world']:continue
  s=replay(c,e['record']);assert state_sha(s.state)==e['id'];covered=s.state.position in idx;protected=max(n for k,n in s.state.repetition_counts)<=2;margin=c.max_ply-s.state.ply_count>max(ranks.values(),default=0)
  assert (covered,protected,margin)==(e['covered'],e['protected'],e['clock_margin']);assert (e['id']in rows)==(covered and protected and margin)
  if e['id']in rows:
   actions,cells=check(c,g,e,rows[e['id']]);local['qualified_roots']+=1;local['root_actions']+=actions;local['cells']+=cells
   if not negative:
    bad=copy.deepcopy(rows[e['id']]);bad['labels'][0]=2
    try:check(c,g,e,bad)
    except AssertionError:counts['negative_controls']+=1
    else:raise AssertionError('corrupted label accepted')
    bad=copy.deepcopy(rows[e['id']]);bad['cells'][0]['selected']=[]
    try:check(c,g,e,bad)
    except AssertionError:counts['negative_controls']+=1
    else:raise AssertionError('corrupted argmax accepted')
    negative=True
  local['full_histories']+=1
 if args.cache:
  with gzip.open(args.cache/f"world{case['world']}.pkl.gz",'wb')as f:pickle.dump(g,f,protocol=5)
 counts.update(local);counts['graphs']+=1;counts['positions']+=len(positions);counts['edges']+=sum(map(len,edges));details.append(dict(world=case['world'],seconds=time.perf_counter()-beg,**local));print(json.dumps(details[-1]),flush=True)
result=dict(status='PASS',seconds=time.perf_counter()-start,counts=counts,details=details,scope='Independent Core rebuild/check,shared rules engine;declared898qualifiedfullhistories,rank/repeat4 conditions only. No originalUNKNOWN or TRAIN admission changed. Cached verification files are not new experimental slots.');args.output.write_text(json.dumps(result,indent=2));print('FINAL',json.dumps({k:v for k,v in result.items()if k!='details'}),flush=True)
