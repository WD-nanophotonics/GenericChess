"""Read the compact natural-history evidence through committed shared Core.

Default checks every queried PV, local critic tree, TD sum, D4 support and the
complete representative graph. --literal-six additionally regenerates saved
D6 trees; --corpus rebuilds the other complete four-actor graphs from their
fixed records. These are verification calls, not extra experimental slots.
No training or original observed UNKNOWN is changed.
"""
import argparse,gzip,json,sys,time,math,itertools,functools
from pathlib import Path
from fractions import Fraction as F
from dataclasses import replace
from collections import Counter,deque
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,match_action,state_sha,record_value
from scripts.leaper_retrograde import fresh_state,attractor
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import legal_successors,apply_action
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from scripts.leaper_parameter_regions import draw_only_closure
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate

def key(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def replay(c,r):return GameSession.replay(c,deserialize_game_record(json.dumps(r)))
def act(s,ch):
 assert ch['kind']=='ACTION'
 a=[a for a in s.legal_actions()if action_to_dict(a)==ch['action']];assert len(a)==1;s.submit(a[0])

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--literal-six',action='store_true');parser.add_argument('--corpus',action='store_true');parser.add_argument('--output');args=parser.parse_args()
 p=json.loads(gzip.decompress((Path(__file__).parent/'evidence.json.gz').read_bytes()));start=time.perf_counter();rules=p['trace']['inputs']['rules']|p['corpus']['rules'];compiled={fp:compile_rule(ruleset_from_dict(r))for fp,r in rules.items()};roots={};counters=Counter()
 for game in p['trace']['inputs']['games']:
  c=compiled[game['ruleset_fingerprint']];s=replay(c,game['initial_record'])
  for q in game['queries']:
   roots[state_sha(s.state)]=(c,record_value(s.to_record()))
   if q['action']is not None:s.submit(match_action(s,q['action']))
  assert state_sha(s.state)==game['final_state_sha256'];roots[state_sha(s.state)]=(c,record_value(s.to_record()))
 for case in p['corpus']['manifest']:
  c=compiled[case['fingerprint']];s=replay(c,case['record']);assert state_sha(s.state)==case['id'];roots[case['id']]=(c,case['record'])

 def receipt(row,default_depth=4):
  c,record=roots[row['id']];s=replay(c,record);r=row['receipt'];assert r['complete']and r['completed_depth']==row.get('depth',default_depth)
  env=FixedScaleSessionEnv(s,unit_type='A');weights=row.get('weights')
  if weights is None:
   price={'A':1,'B':row.get('B',1),'C':row.get('C',1)};weights=[price[t]if kind=='board'else 0 for kind,t in env.names]
  model=Model(weights);assert r['pv_choices']and r['pv_choices'][0]==r['action']
  for ch in r['pv_choices']:act(s,ch);counters['pv_edges']+=1
  leaf=FixedScaleSessionEnv(s,unit_type='A');actual=leaf.terminal()
  if r['pv_terminal']:assert actual is not None and MATE*actual==r['value']and r['pv_phi']is None
  else:
   assert actual is None and len(r['pv_choices'])==r['completed_depth']and tuple(r['pv_phi'])==leaf.features()
   assert model.raw(leaf.features())==r['value']
   if row.get('gradient')is not None:assert tuple(row['gradient'])==model.gradient(leaf.features())
  assert sum(a['nodes']for a in r['attempts'])==r['nodes'];counters['queries']+=1

 for row in p['float']['rows']:
  receipt(row);expected=-abs(F(row['B'])-F(row['C']))if row['world']==16 else F(0);assert F(row['receipt']['value'])==expected==F(row['expected'])
 for row in p['sensitivity']['rows']:
  receipt(row);assert F(row['receipt']['value'])==min(F(row['B']),F(row['C']))-1==F(row['expected'])
 for row in p['trace']['rows']:receipt(row)
 for row in p['late']['rows']:receipt(row|{'C':0})
 for row in p['corpus_queries'].get('rows',[]):receipt(row)
 truth_by_id={r['id']:r for r in p['corpus']['rows']}
 for row in p['corpus_queries'].get('rows',[]):
  label=truth_by_id.get(row['id'],{}).get('labels')
  if label is None:assert row['root_wdl_bounds']==[-1,1]and row['chosen_wdl_bounds']==[-1,1];continue
  assert row['root_wdl_bounds']==label['root_bounds']
  a=row['receipt']['action']['action'];assert row['chosen_wdl_bounds']==next(z['wdl_bounds']for z in label['actions']if z['action']==a)
 if p.get('saturated',{}).get('summary',{}).get('status')=='PROVEN_WIN':
  raw=p['saturated']['certificate'];cc=compiled[raw['ruleset_fingerprint']];ss,cert=decode_session_certificate(cc,raw);verified=verify_session_certificate(ss,cert,max_nodes=100000,seconds=30);assert verified['verified']
  assert not verify_session_certificate(ss,replace(cert,target=1-cert.target),max_nodes=100000,seconds=30)['verified'];counters['negative_controls']+=1;counters['session_certificates']+=1

 # Exact backward sum independently checks the forward library updates.
 for game in p['trace']['results']:
  for update in game['updates']:
   rr=[r for r in p['trace']['rows']if r['slot']==game['slot']and r['actor']==update['actor']];v=[F(math.tanh(r['receipt']['value']/10))for r in rr]
   grads=[(F(0),)*6 if r['receipt']['pv_terminal']else tuple(F(x)for x in r['gradient'])for r in rr];err=[v[i+1]-v[i]for i in range(len(v)-1)]
   if game['outcome']is not None:err.append(F(game['outcome'])-v[-1])
   for j in range(6):
    delta=F(.05)*sum(grads[k][j]*sum(F(.95)**(i-k)*err[i]for i in range(k,len(err)))for k in range(len(err)))
    assert math.isclose((1 if j<3 else 0)+float(delta),update['weights_after_off_policy_arithmetic'][j],abs_tol=2e-15)
   counters['td_streams']+=1

 prices9=list(itertools.product((F(1,2),F(1),F(2)),repeat=2))
 def literal(c,s,d,prices,ply=0):
  counters['literal_visits']+=1
  if s.terminal_status.is_terminal:
   t=s.terminal_status;v=0 if t.winner is None else 1 if t.winner==s.position.side_to_move else-1
   return (F(terminal_score(t,s.position.side_to_move,ply)),)*len(prices),(v,v)
  if not d:
   phi={t:sum(1 if z.owner==0 else-1 for z in s.position.board if z and z.current_type_id==t)for t in('A','B','C')};assert all(-1<=v<=1 for v in phi.values());sign=1 if s.position.side_to_move==0 else-1
   return tuple(sign*(phi['A']+b*phi['B']+cc*phi['C'])for b,cc in prices),(-1,1)
  res=[literal(c,ch,d-1,prices,ply+1)for a,ch in legal_successors(s,c)];assert res
  return tuple(max(-r[0][j]for r in res)for j in range(len(prices))),(max(-r[1][1]for r in res),max(-r[1][0]for r in res))
 for row in p['support']['rows']:
  if row['status']not in('COMPLETE','REUSED'):assert not row['supports'];continue
  c,record=roots[row['id']];s=replay(c,record).state;legal={key(action_to_dict(a)):ch for a,ch in legal_successors(s,c)}
  assert len(row['branches'])==len(legal)and set(legal)=={key(b['action'])for b in row['branches']}
  assert row['supports']==[[i for i,b in enumerate(row['branches'])if F(b['scores'][j])==max(F(x['scores'][j])for x in row['branches'])]for j in range(9)]
  if row['depth']==6 and not args.literal_six:continue
  for branch in row['branches']:
   scores,(lo,hi)=literal(c,legal[key(branch['action'])],row['depth']-1,prices9,1);assert tuple(map(F,branch['scores']))==tuple(-v for v in scores)
   if 'wdl_bounds'in branch:assert branch['wdl_bounds']==[-hi,-lo]
  counters['full_supports']+=1

 # Independently use rational arithmetic for the integer-producer local cones.
 lc=p['local']['config'];prices=[tuple(map(F,x))for x in lc['prices']];dirs=[tuple(map(F,x))for x in lc['directions']];eps=F(1,8)
 def norm(v):
  m=max(map(abs,v));return tuple(F(x,m)for x in v)
 rays=set()
 for a,b,c in itertools.product(range(-2,3),repeat=3):
  if(b or c)and a+b+c==0:rays.update((norm((c,-b)),norm((-c,b))))
 assert len(rays)==12 and set(dirs[1:13])==rays and prices==[(1+eps*u,1+eps*v)for u,v in dirs]
 trace_by_id={r['id']:r for r in p['trace']['rows']}
 for row in p['local']['rows']:
  c,record=roots[row['id']];vals,_=literal(c,replay(c,record).state,4,prices);assert tuple(map(F,row['values']))==vals
  for k,(i,j)in enumerate(lc['sectors']):
   a,b,cc=map(F,row['sector_affines'][k]);assert all(a+b*prices[z][0]+cc*prices[z][1]==vals[z]for z in(i,j,0));assert b in(-1,0,1)and cc in(-1,0,1)
  served=trace_by_id[row['id']]['receipt'];phi=served['pv_phi'];sgn=1 if row['mover']==0 else-1
  assert row['chosen_mover_PV_BC']==([0,0]if phi is None else[sgn*phi[1],sgn*phi[2]])
  if row['slot']==136 and row['ply']==3:assert all(v==1-min(b,cc)for v,(b,cc)in zip(vals,prices))and row['chosen_mover_PV_BC']==[-1,1]
  counters['local_roots']+=1

 # Compact representative graph: regenerate every authoritative edge and terminal.
 gp=p['graph'];cfg=gp['config'];c=compiled[cfg['cases'][0]['fingerprint']];base=replay(c,cfg['cases'][0]['record']).state.position
 codes={0:None,1:Piece(0,'K','K'),2:Piece(1,'K','K'),3:Piece(1,'A','A'),4:Piece(1,'B','B')}
 positions=[replace(base,side_to_move=t,board=tuple(codes[int(x)]for x in board))for t,board in gp['positions']];idx={pos:i for i,pos in enumerate(positions)};edges=gp['edges'];values=gp['values'];ranks=gp['ranks'];term={int(k):v for k,v in gp['terminals'].items()}
 def edge_check(i,saved):
  s=fresh_state(positions[i],c)
  if s.terminal_status.is_terminal:
   t=s.terminal_status;v=0 if t.winner is None else 1 if t.winner==s.position.side_to_move else-1;assert not saved and term[i]==v==values[i];return
  actual=[idx[apply_action(s,a,c).position]for a in legal_actions(s,c)];assert actual==saved
  if values[i]==1:assert ranks[i]==1+min(ranks[ch]for ch in saved if values[ch]==-1)
  elif values[i]==-1:assert all(values[ch]==1 for ch in saved)and ranks[i]==1+max(ranks[ch]for ch in saved)
  else:assert all(values[ch]!=-1 for ch in saved)and any(values[ch]==0 for ch in saved)
  counters['graph_edges']+=len(actual)
 for i,row in enumerate(edges):edge_check(i,row)
 seen=set(gp['roots']);todo=list(seen)
 while todo:
  for ch in edges[todo.pop()]:
   if ch not in seen:seen.add(ch);todo.append(ch)
 assert len(seen)==len(positions);counters['graph_positions']=len(positions)
 for case,row,i in zip(cfg['cases'],gp['labels'],gp['roots']):
  s=replay(c,case['record']).state;assert state_sha(s)==row['id']==case['id']and positions[i]==s.position
  assert Counter(h.position_key for h in s.history)==dict(s.repetition_counts)and max(n for k,n in s.repetition_counts)<=2
  assert cfg['rule']['max_ply']-s.ply_count>max(r for r in ranks if r is not None)
  assert row['wdl']==values[i]and row['rank']==ranks[i]
  for z,ch in zip(row['actions'],edges[i]):assert z['wdl']==-values[ch]and z['child_rank']==ranks[ch]
  counters['history_roots']+=1
 for row in p['late']['rows']:
  label=next(x for x in gp['labels']if x['id']==row['id']);a=row['receipt']['action']['action'];assert row['chosen_wdl']==next(z['wdl']for z in label['actions']if z['action']==a)and row['root_wdl']==label['wdl']
 i=gp['roots'][0]
 try:edge_check(i,edges[i][1:])
 except AssertionError:counters['negative_controls']+=1
 else:raise AssertionError('missing graph edge accepted')

 # Closed no-B transfer rechecks semantics under the other fixed fingerprint.
 game=p['trace']['inputs']['games'][0];other=compiled[game['ruleset_fingerprint']];other_rule=rules[game['ruleset_fingerprint']]
 assert {k:v for k,v in other_rule.items()if k not in('initial_position','metadata')}=={k:v for k,v in cfg['rule'].items()if k not in('initial_position','metadata')}
 subset={i for i,pos in enumerate(positions)if not any(z and z.current_type_id=='B'for z in pos.board)}
 for i in subset:
  assert values[i]==0 and all(ch in subset for ch in edges[i]);pos=replace(positions[i],ruleset_fingerprint=other.ruleset_fingerprint);s=fresh_state(pos,other)
  if s.terminal_status.is_terminal:assert s.terminal_status.winner is None
  else:assert [idx[replace(apply_action(s,a,other).position,ruleset_fingerprint=c.ruleset_fingerprint)]for a in legal_actions(s,other)]==edges[i]
 for row in p['deadzone']['covered_natural_roots']+[p['deadzone']['endpoint']]:
  cc,record=roots[row['id']];s=replay(cc,record).state;i=idx[replace(s.position,ruleset_fingerprint=c.ruleset_fingerprint)];assert i in subset and row['wdl']==0
 counters['deadzone_positions']=len(subset)

 if args.corpus:
  for row in p['corpus']['rows']:
   if row['status']!='COMPLETE':continue
   case=next(x for x in p['corpus']['manifest']if x['id']==row['id']);cc=compiled[case['fingerprint']];root=replay(cc,case['record']).state;positions2=[];idx2={};queue=deque();edges2=[];term2={};beg=time.perf_counter()
   def add(pos):
    if pos not in idx2:idx2[pos]=len(positions2);positions2.append(pos);queue.append(pos)
    return idx2[pos]
   add(root.position)
   while queue:
    if time.perf_counter()-beg>180 or time.perf_counter()-start>3600:raise RuntimeError('VERIFY_LIMIT: no new corpus labels')
    pos=queue.popleft();i=idx2[pos];s=fresh_state(pos,cc)
    if s.terminal_status.is_terminal:
     t=s.terminal_status;term2[i]=0 if t.winner is None else 1 if t.winner==pos.side_to_move else-1;edges2.append(())
    else:edges2.append(tuple(add(apply_action(s,a,cc).position)for a in legal_actions(s,cc)))
   assert len(positions2)==row['positions']and sum(map(len,edges2))==row['edges'];v,r=attractor(edges2,term2)
   assert v[0]==row['labels']['fresh_root_value']and r.get(0)==row['labels']['fresh_root_rank']
   dc=draw_only_closure(edges2,term2)
   if 'analysis'in p['corpus']:
    a=next(z for z in p['corpus']['analysis']if z['world']==row['world']);assert a['structural_deadzone']==(0 in dc)
   protected=max(n for k,n in root.repetition_counts)<=2;remaining=p['corpus']['rules'][case['fingerprint']]['max_ply']-root.ply_count
   def bound(i,left):
    if i in term2:return[v[i],v[i]]
    if v[i]==0 or r[i]>left:return[0,0]
    return[v[i],v[i]]if protected else[0,1]if v[i]==1 else[-1,0]
   assert bound(0,remaining)==row['labels']['root_bounds']
   assert [z['action']for z in row['labels']['actions']]==[action_to_dict(a)for a in legal_actions(root,cc)]
   for z,ch in zip(row['labels']['actions'],edges2[0]):
    lo,hi=bound(ch,remaining-1);assert z['wdl_bounds']==[-hi,-lo]
   counters['corpus_graphs_rebuilt']+=1;print(json.dumps(dict(world=row['world'],verified=True,seconds=time.perf_counter()-beg)),flush=True)
 result=dict(status='PASS',seconds=time.perf_counter()-start,literal_six=args.literal_six,corpus=args.corpus,counts=dict(counters),scope='Shared Core verification,not an independent rule implementation. Capped graphs/trees and original observed UNKNOWN unchanged. Corpus graphs rebuilt only with --corpus.')
 if args.output:Path(args.output).write_text(json.dumps(result,indent=2))
 print(json.dumps(result),flush=True)

if __name__=='__main__':main()
