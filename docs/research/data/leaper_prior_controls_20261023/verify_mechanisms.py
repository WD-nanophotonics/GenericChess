"""Independent two-point-per-cone local-critic check, plus public PV replay."""
import sys,json,gzip,time,argparse,copy,math
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha
from scripts.leaper_microgames import role_stop_requested
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.learning.incremental import Model,FixedScaleSessionEnv,MATE
ap=argparse.ArgumentParser();ap.add_argument('directory',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();p=json.loads(gzip.decompress((a.directory/'mechanisms.json.gz').read_bytes()));new=json.loads(gzip.decompress((a.directory/'new_context.json.gz').read_bytes()));worlds={w['world']:w for w in new['inputs']['worlds']};compiled={w:compile_rule(ruleset_from_dict(z['rule']))for w,z in worlds.items()};start=time.perf_counter();counts=Counter()
def hull(points):
 pts=sorted(set(points))
 if len(pts)<3:return pts
 def cr(o,a,b):return(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 low=[];high=[]
 for x in pts:
  while len(low)>1 and cr(low[-2],low[-1],x)<=0:low.pop()
  low.append(x)
 for x in reversed(pts):
  while len(high)>1 and cr(high[-2],high[-1],x)<=0:high.pop()
  high.append(x)
 return low[:-1]+high[:-1]
def match(s,raw):
 aa=[z for z in s.legal_actions()if action_to_dict(z)==raw];assert len(aa)==1;return aa[0]
allrows={r['id']:r for r in p['rows']};verified={};dirs=[tuple(d)for d in p['rows'][0]['tangent']['directions']];second={(3,1):(4,1),(3,2):(4,3),(2,3):(3,4),(1,3):(1,4)}
for e in p['manifest']:
 c=compiled[e['world']];s=GameSession.replay(c,deserialize_game_record(json.dumps(e['record'])));assert state_sha(s.state)==e['id'];r=allrows[e['id']];assert r['status']=='COMPLETE';models=[Model(worlds[e['world']]['priors'][name])for name in('unit','B2C1','mobility','Static')];rat=[list(map(F.from_float,m.weights))for m in models];scales=[math.lcm(*(x.denominator for x in v))for v in rat];iw=[[int(x*scale)for x in ww]for scale,ww in zip(scales,rat)];points=[]
 for b in(1,2):
  for dx,dy in dirs:
   x,y=second[abs(dx),abs(dy)];dx2=x*(1 if dx>0 else-1);dy2=y*(1 if dy>0 else-1);points.extend([(32,b*32+dx,32+dy),(32,b*32+dx2,32+dy2)])
 leafcache={};visits=0
 def exact(st,left,ply):
  global visits
  visits+=1;counts['tree_visits']+=1
  if visits%128==0 and(time.perf_counter()-start>600 or role_stop_requested()):raise RuntimeError('VERIFY_CAP_OR_STOP')
  if st.terminal_status.is_terminal:
   z=terminal_score(st.terminal_status,st.position.side_to_move,ply);return[float(z)]*4+[z*v for v in scales]+[z*32]*64
  if not left:
   phi=tuple(sum((1 if z.owner==0 else-1)for z in st.position.board if z and z.current_type_id==name)for name in'ABC')+(0,0,0);assert all(-1<=z<=1 for z in phi);sgn=1 if st.position.side_to_move==0 else-1;key=(phi,sgn)
   if key not in leafcache:leafcache[key]=[sgn*m.raw(phi)for m in models]+[sgn*sum(x*y for x,y in zip(phi,ww))for ww in iw]+[sgn*sum(x*y for x,y in zip(phi[:3],ww))for ww in points]
   return leafcache[key]
  children=[[-x for x in exact(ch,left-1,ply+1)]for z,ch in legal_successors(st,c)];assert children;return[max(v[j]for v in children)for j in range(72)]
 branches=[]
 for action,ch in legal_successors(s.state,c):branches.append((action_to_dict(action),[-v for v in exact(ch,3,1)]))
 assert len(branches)==len(r['branches'])
 for(actual,values),stored in zip(branches,r['branches']):
  assert actual==stored['action']and values[:4]==stored['float_scores'];assert[F(values[4+j],scales[j])for j in range(4)]==list(map(F,stored['rational_scores']))
 for j in range(4):
  support=[i for i,(_,v)in enumerate(branches)if v[j]==max(z[1][j]for z in branches)];rsupport=[i for i,(_,v)in enumerate(branches)if v[4+j]==max(z[1][4+j]for z in branches)];assert support==r['supports'][j]and rsupport==r['rational_supports'][j]
 root=[max(v[j]for _,v in branches)for j in range(72)];sgn=1 if s.state.position.side_to_move==0 else-1;grads=[]
 for pi in range(2):
  base=sgn*root[4+pi]*32
  for di,(dx,dy)in enumerate(dirs):
   x,y=second[abs(dx),abs(dy)];dx2=x*(1 if dx>0 else-1);dy2=y*(1 if dy>0 else-1);v1=sgn*root[8+pi*32+2*di]-base;v2=sgn*root[9+pi*32+2*di]-base;det=dx*dy2-dx2*dy;gb=F(v1*dy2-v2*dy,det);gc=F(dx*v2-dx2*v1,det);assert gb.denominator==gc.denominator==1;grads.append((int(gb),int(gc)))
 assert grads[:16]==list(map(tuple,r['tangent']['unit_gradients']))and grads[16:]==list(map(tuple,r['tangent']['B2C1_gradients']));assert list(map(list,hull(grads[:16])))==r['tangent']['unit_hull'];verified[e['id']]=r;counts['roots']+=1;counts['integer_cone_points']+=64
target=p['probe']['config']['root'];c=compiled[target['world']];s=GameSession.replay(c,deserialize_game_record(json.dumps(target['record'])));weights_seen=set()
for q in p['probe']['rows']:
 weights=q['weights'];r=q['receipt'];assert tuple(weights)not in weights_seen;weights_seen.add(tuple(weights));assert r['value']==weights[2]-1==q['expected_value'];pv=copy.copy(s)
 for action in r['pv']:pv.submit(match(pv,action));counts['probe_PV_edges']+=1
 env=FixedScaleSessionEnv(pv,unit_type='A');assert env.terminal()is None and tuple(env.features()[1:3])==(0,1)and tuple(r['pv_phi'])==env.features()and Model(weights).raw(env.features())==r['value'];assert r['pv'][0]==r['action']and r['completed_depth']==4;counts['probe_queries']+=1
for q in p.get('base_receipts',[]):
 pv=copy.copy(s);r=q['receipt']
 for action in r['pv']:pv.submit(match(pv,action));counts['base_PV_edges']+=1
 env=FixedScaleSessionEnv(pv,unit_type='A');v=env.terminal();grad=[0,0]if v is not None else list(env.features()[1:3]);assert grad==[0,0]and r['value']==0
 if v is not None:assert r['pv_terminal']and v==0
 counts['reused_base_queries']+=1
assert counts['roots']==16 and counts['probe_queries']==64 and counts['reused_base_queries']==2
if 'residual'in p:
 residual=p['residual'];rw={w['world']:w for w in residual['inputs']['worlds']};cases={e['id']:e for e in residual['manifest']};rc={w:compile_rule(ruleset_from_dict(z['rule']))for w,z in rw.items()}
 for row in residual['rows']:
  e=cases[row['id']];c=rc[e['world']];s=GameSession.replay(c,deserialize_game_record(json.dumps(e['record'])));assert state_sha(s.state)==e['id'];models=[Model(rw[e['world']]['priors'][n])for n in('B2C1','mobility')]
  def ref(st,left,ply):
   counts['residual_visits']+=1
   if counts['residual_visits']%128==0 and(time.perf_counter()-start>600 or role_stop_requested()):raise RuntimeError('VERIFY_CAP_OR_STOP')
   if st.terminal_status.is_terminal:
    t=st.terminal_status;v=0 if t.winner is None else 1 if t.winner==st.position.side_to_move else-1;z=terminal_score(t,st.position.side_to_move,ply);return z,z,v,v
   if not left:
    phi=tuple(sum((1 if z.owner==0 else-1)for z in st.position.board if z and z.current_type_id==n)for n in'ABC')+(0,0,0);sgn=1 if st.position.side_to_move==0 else-1;return sgn*models[0].raw(phi),sgn*models[1].raw(phi),-1,1
   children=[]
   for z,ch in legal_successors(st,c):
    x,y,lo,hi=ref(ch,left-1,ply+1);children.append((-x,-y,-hi,-lo))
   return tuple(max(z[j]for z in children)for j in range(4))
  branches=[]
  for action,ch in legal_successors(s.state,c):
   x,y,lo,hi=ref(ch,row['depth']-1,1);branches.append(dict(action=action_to_dict(action),scores=[-x,-y],bounds=[-hi,-lo]))
  assert row['status']=='COMPLETE'and branches==row['branches'];assert row['bounds']==[max(z['bounds'][j]for z in branches)for j in(0,1)];counts['residual_trees']+=1
 oldbase=json.loads(gzip.decompress((a.directory.parent/'leaper_natural_price_capacity_20261023/abc_validation.json.gz').read_bytes()));positive=json.loads(gzip.decompress((a.directory/'positive_controls.json.gz').read_bytes()))
 for e in cases.values():
  og=next(g for g in oldbase['games']if g['slot']==e['old_slot']);ng=next(g for g in positive['games']if g['slot']==e['new_slot']);assert og['utility']==[1,1]and ng['utility']==[0,0]and og['role']==ng['role']==0;assert og['world']==ng['world']==e['world']and og['prefix']==ng['prefix']==e['prefix'];n=len(e['record']['actions']);orr=oldbase['records'][og['record']];nrr=positive['records'][ng['record']];assert orr['actions'][:n]==nrr['actions'][:n]==e['record']['actions'];assert orr['actions'][n]==e['B2C1_action']and nrr['actions'][n]==e['mobility_action'];counts['reused_intervention_views']+=2
 for game in p['intervention']['games']:
  e=cases[game['root']];c=rc[e['world']];assert game['forced_action']==e['B2C1_action'if game['first']=='B2C1'else'mobility_action'];s=GameSession.replay(c,deserialize_game_record(json.dumps(e['record'])));s.submit(match(s,game['forced_action']));assert len(game['final_record']['actions'])==len(e['record']['actions'])+1+len(game['queries'])
  for q in game['queries']:
   assert state_sha(s.state)==q['id']and s.state.ply_count==q['ply']and s.state.position.side_to_move==q['actor'];assert q['weights']==rw[e['world']]['priors'][game['tail']if q['actor']==0 else'mobility'];r=q['receipt'];assert r['complete']and r['completed_depth']==4;pv=copy.copy(s)
   for raw in r['pv']:pv.submit(match(pv,raw));counts['intervention_PV_edges']+=1
   env=FixedScaleSessionEnv(pv,unit_type='A');v=env.terminal()
   if v is None:assert tuple(r['pv_phi'])==env.features()and math.isclose(Model(q['weights']).raw(env.features()),r['value'],abs_tol=1e-12)and not r['pv_terminal']
   else:assert r['pv_terminal']and r['value']==MATE*v
   s.submit(match(s,r['action']));counts['intervention_queries']+=1
  assert json.loads(json.dumps(game['final_record']))==json.loads(__import__('generic_chess.session.serialization',fromlist=['serialize_game_record']).serialize_game_record(s.to_record()));v=FixedScaleSessionEnv(s,unit_type='A').terminal();assert game['utility']==[v,v];counts['new_interventions']+=1
if(a.directory/'next_step.json.gz').exists():
 step=json.loads(gzip.decompress((a.directory/'next_step.json.gz').read_bytes()))
 for q in step['query_rows']:
  c=rc[q['world']];s=GameSession.replay(c,deserialize_game_record(json.dumps(q['record'])));assert state_sha(s.state)==q['id']
  for r,weights in((q['base_receipt'],q['base']),(q['receipt'],q['weights'])):
   pv=copy.copy(s)
   for raw in r['pv']:pv.submit(match(pv,raw));counts['shadow_PV_edges']+=1
   env=FixedScaleSessionEnv(pv,unit_type='A');v=env.terminal();assert r['complete']and r['completed_depth']==4 and r['pv'][0]==r['action']
   if v is None:assert tuple(r['pv_phi'])==env.features()and math.isclose(Model(weights).raw(env.features()),r['value'],abs_tol=1e-12)
   else:assert r['pv_terminal']and r['value']==MATE*v
   counts['shadow_new_or_reused_queries']+=1
result=dict(status='PASS',seconds=time.perf_counter()-start,counts=counts,scope='All16fullhistoryD4trees independently recomputed and1024integer cone-points checked;fourresidualD4/D6trees,66originalprobe/basePVreceipts,fourNEWinterventions and32next-stepnew/reusedPVreceipts checked. ShadowmeanTD arithmetic is reportedpreparation,not fullytarget-boundbythisreader. Finitecritic/conditionalpolicymechanisms,not improved learning.');a.output.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result),flush=True)
