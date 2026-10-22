"""Replay the selected evidence through shared Core/Session; no training.

Checks full-history bindings, every public PV and saved positive WIN certificate,
literal capture-root argmax, and complete ABC D4 argmax. D6 ABC tree regeneration
is optional (--literal-six); default checks its saved arithmetic/action binding.
This does not re-prove UNKNOWN, regenerate closed censored studies or establish
independent rules semantics, population performance or training usefulness.
"""
import argparse,gzip,json,sys,time
from collections import Counter
from fractions import Fraction as F
from math import isclose
from pathlib import Path
from copy import deepcopy
from itertools import product
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha,material_profiles
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import legal_successors
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate
from generic_chess.core.movement import LeapAtom

def replay(c,record):
 return GameSession.replay(c,deserialize_game_record(json.dumps(record)))

def key(x):return json.dumps(x,sort_keys=True,separators=(',',':'))

def apply(s,raw):
 if raw['kind']=='DECLARATION':s.declare(raw['declaration_id']);return
 matches=[a for a in s.legal_actions()if action_to_dict(a)==raw['action']]
 assert len(matches)==1
 s.submit(matches[0])

def literal(c,s,left,prices,ply=0):
 global literal_visits
 literal_visits+=1
 if s.terminal_status.is_terminal:
  return (F(terminal_score(s.terminal_status,s.position.side_to_move,ply)),)*len(prices)
 if not left:
  phi={t:sum((1 if p.owner==0 else-1)for p in s.position.board if p and p.current_type_id==t)for t in('A','B','C')}
  sign=1 if s.position.side_to_move==0 else-1
  return tuple(sign*(phi['A']+b*phi['B']+cc*phi['C'])for b,cc in prices)
 values=[tuple(-v for v in literal(c,ch,left-1,prices,ply+1))for a,ch in legal_successors(s,c)]
 assert values
 return tuple(max(v[j]for v in values)for j in range(len(prices)))

def check_support(c,s,row,prices,recompute):
 global full_support_checks
 legal={key(action_to_dict(a)):(a,ch)for a,ch in legal_successors(s,c)}
 bs=row['branches'];assert len({key(b['action'])for b in bs})==len(bs)
 assert all(key(b['action'])in legal for b in bs)
 if row.get('status','COMPLETE')!='COMPLETE':
  assert row.get('supports',[])==[];return
 assert {key(b['action'])for b in bs}==set(legal)
 supports=[]
 for j in range(len(prices)):
  top=max(F(b['scores'][j])for b in bs)
  supports.append([i for i,b in enumerate(bs)if F(b['scores'][j])==top])
 assert supports==row['supports']
 if recompute:
  for b in bs:
   scores=tuple(-v for v in literal(c,legal[key(b['action'])][1],row['depth']-1,prices,1))
   assert tuple(map(F,b['scores']))==scores
  full_support_checks+=1
  print(json.dumps(dict(checked_support=full_support_checks,depth=row['depth'],id=row.get('id',row.get('root_id')),literal_visits=literal_visits)),file=sys.stderr,flush=True)

def check_query(c,record,row,b,cc=0):
 global queries,pv_edges
 root=replay(c,record);assert state_sha(root.state)==row.get('root_id',row.get('id'))
 r=row['receipt'];assert r['complete'] and r['completed_depth']==row['depth']
 env=FixedScaleSessionEnv(root,unit_type='A')
 values={'A':1,'B':b,'C':cc};weights=[values[n]if kind=='board'else 0 for kind,n in env.names]
 model=Model(weights,scale=10)
 assert r['action'] is not None
 first=replay(c,record);apply(first,r['action'])
 s=replay(c,record)
 for ch in r['pv_choices']:apply(s,ch);pv_edges+=1
 assert r['pv_choices'] and r['pv_choices'][0]==r['action']
 leaf=FixedScaleSessionEnv(s,unit_type='A');actual=leaf.terminal()
 if r['pv_terminal']:
  assert actual is not None and r['value']==MATE*actual and r['pv_phi'] is None
 else:
  assert actual is None and list(leaf.features())==r['pv_phi']
  assert isclose(model.raw(r['pv_phi']),r['value'],abs_tol=1e-10)
  assert len(r['pv_choices'])==r['completed_depth']
  assert all(isclose(a,z,abs_tol=1e-12)for a,z in zip(model.gradient(r['pv_phi']),row['gradient']))
 assert sum(a['nodes']for a in r['attempts'])==r['nodes']
 queries+=1

def verify_clock_tail(path=None):
 """Independently replay a separate Session-produced rule-clock proof via Core."""
 path=Path(path)if path else Path(__file__).parent/'clock_tail.json.gz'
 p=json.loads(gzip.decompress(path.read_bytes()));assert p['status']=='COMPLETE'
 c=compile_rule(ruleset_from_dict(p['rule']));root=replay(c,p['record'])
 assert root.state.ply_count==124 and p['rule']['max_ply']==128
 assert not root.available_declarations() and state_sha(root.state)==p['root_id']
 assert p['config']['original']['utility']==[-1,1] and p['config']['original']['other_unstarted_slots']==[2,4]
 count=0;terms=Counter();beg=time.perf_counter()
 def check(s,node):
  nonlocal count
  count+=1;assert node['id']==state_sha(s)
  actual=s.terminal_status
  if actual.is_terminal:
   assert actual.status.value!='no_contest' and not node['edges']
   assert node['terminal']==dict(status=actual.status.value,winner=actual.winner)
   v=0 if actual.winner is None else 1 if actual.winner==s.position.side_to_move else-1
   terms[actual.status.value]+=1;assert node['value']==v;return v
  assert node['terminal']is None and s.ply_count<128
  legal={key(action_to_dict(a)):ch for a,ch in legal_successors(s,c)}
  edges={key(e['action']):e['child']for e in node['edges']}
  assert len(edges)==len(node['edges'])and set(edges)==set(legal)
  v=max(-check(legal[a],child)for a,child in edges.items());assert v==node['value'];return v
 value=check(root.state,p['tree']);assert count==p['nodes']and dict(terms)==p['terminal_counts']
 nodes=count;terminals=dict(terms)
 corrupted=dict(p['tree'],edges=p['tree']['edges'][:-1]);rejected=False
 try:check(root.state,corrupted)
 except AssertionError:rejected=True
 assert rejected
 return dict(status='PASS',nodes=nodes,terminal_counts=terminals,value=value,root_action_values=[-e['child']['value']for e in p['tree']['edges']],missing_root_edge_rejected=True,seconds=time.perf_counter()-beg,scope='Separate posthoc history-conditioned rule-clock proof;original game UNKNOWN and two unstarted slots unchanged.')

def main():
 global queries,pv_edges,literal_visits,full_support_checks
 queries=pv_edges=literal_visits=full_support_checks=0;beg=time.perf_counter()
 a=argparse.ArgumentParser(__doc__);a.add_argument('--literal-six',action='store_true');args=a.parse_args()
 p=json.loads(gzip.decompress((Path(__file__).parent/'evidence.json.gz').read_bytes()))
 for raw in p['rules'].values():
  rule=ruleset_from_dict(raw)
  assert rule.capture_disposition=='remove_from_game'
  assert all(not pt.is_promotable and all(isinstance(a,LeapAtom)for a in pt.movement_atoms)for pt in rule.piece_types)
  assert all(not any(owner)for masks in rule.drop_allowed.values()for owner in masks)
 compiled={fp:compile_rule(ruleset_from_dict(r))for fp,r in p['rules'].items()}
 capture=p['capture'];cfg=capture['config'];c=compiled[cfg['ruleset_fingerprint']]
 degrees={t:sum(map(len,c.empty_mobility[t][0]))for t in('A','B')};assert degrees==cfg['compiled_empty_target_totals']
 prof,_=material_profiles(c);assert dict(prof.board_value_by_type)==cfg['static_board_values']
 for row in capture['result']['rows']:
  b=cfg['weights'][row['model']][1];check_query(c,cfg['records'][str(row['ply'])],row,b)
 assert capture['result']['completed']==capture['result']['planned']==18
 assert sum(row['receipt']['nodes']for row in capture['result']['rows'])==14595
 prices=[(F(b),F(0))for b in capture['argmax']['prices']]
 for row in capture['argmax']['rows']:
  check_support(c,replay(c,cfg['records'][str(row['ply'])]).state,row,prices,True)
  for model,j in(('unit',0),('mobility5',3),('Static-material',4)):
   q=next(q for q in capture['result']['rows']if q['ply']==row['ply']and q['depth']==row['depth']and q['model']==model)
   i=next(i for i,b in enumerate(row['branches'])if b['action']==q['receipt']['action']['action'])
   assert i in row['supports'][j]
 # Selected saved-positive certificate is rebound to its full historical root.
 root,cert=decode_session_certificate(c,capture['known_win'],max_nodes=30000)
 assert verify_session_certificate(root,cert,max_nodes=30000,seconds=30)['verified']
 corrupt=deepcopy(capture['known_win']);corrupt['target']=1-corrupt['target']
 badroot,badcert=decode_session_certificate(c,corrupt,max_nodes=30000)
 assert not verify_session_certificate(badroot,badcert,max_nodes=30000,seconds=30)['verified']
 abc=p['abc'];manifest={x['id']:x for x in abc['manifest']}
 for case in manifest.values():
  state=replay(compiled[case['fingerprint']],case['record']).state
  expected=Counter(case['roster'])
  for owner in(0,1):
   actual=Counter(t.current_type_id for t in state.position.board if t and t.owner==owner and t.current_type_id!='K')
   assert actual==expected
 for row in abc['queries']:
  case=manifest[row['id']];check_query(compiled[case['fingerprint']],case['record'],row,row['B'],row['C'])
 assert abc['summary']['completed']==abc['summary']['planned']==len(abc['queries'])==480
 assert sum(row['receipt']['nodes']for row in abc['queries'])==abc['summary']['paid_nodes']
 for result in abc['analysis']:
  cohort=[r for r in abc['queries']if r['roster']==result['roster']and r['depth']==result['depth']]
  changed=sum(len({key(r['receipt']['action'])for r in cohort if r['id']==hid})>1 for hid in{r['id']for r in cohort})
  assert changed==result['changed_roots'] and len(cohort)==result['queries']
  unit=[r for r in cohort if r['B']==1 and r['C']==(1 if result['roster']=='ABC'else 0)]
  vectors=[r['receipt']['pv_phi'][1:3]for r in unit if r['receipt']['pv_phi']is not None]
  nonzero=[v for v in vectors if any(v)]
  rank=0 if not nonzero else 2 if any(a[0]*b[1]!=a[1]*b[0]for a in nonzero for b in nonzero)else 1
  assert rank==result['unit_BC_span_rank'] and len(nonzero)==result['unit_nonzero']
 for result in abc['geometry_analysis']:
  case=next(x for x in manifest.values()if x['world']==result['world']);c=compiled[case['fingerprint']]
  def sig(t):return tuple(tuple(tuple(sorted((s.file,s.rank)for s in row))for row in owner)for owner in c.empty_mobility[t])
  assert len({sig(t)for t in('A','B','C')})==result['distinct_ordinary_geometries']==3
 prices=[tuple(map(F,x))for x in abc['full_support']['config']['prices']]
 for row in abc['full_support']['rows']:
  case=manifest[row['id']];check_support(compiled[case['fingerprint']],replay(compiled[case['fingerprint']],case['record']).state,row,prices,row['depth']==4 or args.literal_six)
  if row['depth']==4 and row['status']=='COMPLETE':
   for j,(b,cc)in enumerate(prices):
    q=next(q for q in abc['queries']if q['id']==row['id']and q['depth']==4 and F(q['B'])==b and F(q['C'])==cc)
    i=next(i for i,br in enumerate(row['branches'])if br['action']==q['receipt']['action']['action'])
    assert i in row['supports'][j]
 # Local-cell completeness uses the complete bounded affine coefficient family.
 local=abc['local_cones'];cfg=local['config'];directions=[tuple(map(F,x))for x in cfg['directions']];prices=[tuple(map(F,x))for x in cfg['prices']];eps=F(cfg['epsilon'])
 def norm(v):
  m=max(map(abs,v));return tuple(F(x,m)for x in v)
 rays=set()
 for a,b,cc in product(range(-2,3),repeat=3):
  if (b or cc)and a+b+cc==0:rays.update((norm((cc,-b)),norm((-cc,b))))
 assert len(rays)==12 and set(directions[1:13])==rays and directions[0]==(0,0)
 assert all(F(3,4)<b<F(5,4)and F(3,4)<cc<F(5,4)for b,cc in prices)
 assert prices==[(1+eps*u,1+eps*v)for u,v in directions]
 for row in local['rows']:
  case=manifest[row['id']];check_support(compiled[case['fingerprint']],replay(compiled[case['fingerprint']],case['record']).state,row,prices,True)
  values=list(map(F,row['values']));assert values==[max(F(b['scores'][j])for b in row['branches'])for j in range(37)]
  fits=[]
  for sector,(i,j)in enumerate(cfg['sectors']):
   u,v=directions[i],directions[j];a,b=directions[1+sector],directions[1+(sector+1)%12]
   cross=lambda x,y:x[0]*y[1]-x[1]*y[0]
   assert cross(a,u)>0 and cross(u,b)>0 and cross(a,v)>0 and cross(v,b)>0
   ri=(values[i]-values[0])/eps;rj=(values[j]-values[0])/eps;det=cross(u,v);assert det
   bb=(ri*v[1]-rj*u[1])/det;cc=(u[0]*rj-v[0]*ri)/det;aa=values[0]-bb-cc;fits.append([str(z)for z in(aa,bb,cc)])
   assert row['supports'][i]==row['supports'][j]
  assert fits==row['sector_affines']
  assert all(F(z)in(-1,0,1)for fit in fits for z in fit)
  if row['id'].startswith('88a181'):
   assert row['locally_abs_B_minus_C'] and all(v==abs(b-cc)for v,(b,cc)in zip(values,prices))
  if row['id'].startswith('40b723'):
   assert row['locally_zero'] and set(map(tuple,fits))=={('0','0','0')} and all(v==0 for v in values)
 positive=0;proof_nodes=0
 for study in(p['natural56'],abc['short_quality']):
  for case in study['manifest']:
   assert state_sha(replay(compiled[case['fingerprint']],case['record']).state)==case['id']
  cases={case['id']:case for case in study['manifest']}
  for row in study['proof_rows']:
   if not row.get('verification',{}).get('verified'):continue
   fp=row['certificate']['ruleset_fingerprint'];root,cert=decode_session_certificate(compiled[fp],row['certificate'],max_nodes=100000)
   case=cases[row['id']];expected=replay(compiled[case['fingerprint']],case['record'])
   if row.get('kind')=='action':apply(expected,dict(kind='ACTION',action=row['action']))
   assert root.to_record()==expected.to_record() and root.state==expected.state
   assert cert.target==row['target']
   result=verify_session_certificate(root,cert,max_nodes=100000,seconds=30)
   assert result['verified']==row['verification']['verified']
   assert result['verified'];positive+=1;proof_nodes+=result['nodes']
 report=dict(status='PASS',queries=queries,pv_edges=pv_edges,literal_visits=literal_visits,full_support_checks=full_support_checks,new_positive_certificates=positive,reference_win_certificates=1,target_flip_controls=1,proof_nodes=proof_nodes,seconds=time.perf_counter()-beg,literal_six=args.literal_six,scope='SharedCore/Session;selected evidence only. No UNKNOWN imputation or independent rules engine.')
 if (Path(__file__).parent/'clock_tail.json.gz').exists():report['clock_tail']=verify_clock_tail()
 print(json.dumps(report,indent=2))

if __name__=='__main__':main()
