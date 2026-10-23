"""Recompute literal supports and replay the two new intervention continuations."""
import sys,json,gzip,time,copy,math,argparse,itertools
from fractions import Fraction as F
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha,record_value
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from scripts.leaper_microgames import role_stop_requested

def verify(folder):
 beg=time.perf_counter();p=json.loads(gzip.decompress((folder/'mechanisms.json.gz').read_bytes()));data=json.loads(gzip.decompress((folder/'games.json.gz').read_bytes()));worlds={w['world']:w for w in data['inputs']['worlds']};cs={w:compile_rule(ruleset_from_dict(x['rule']))for w,x in worlds.items()};counts=Counter();rows={r['id']:r for r in p['supports']['rows']+p['free_residual_support']['rows']};names=p['supports']['config']['policies']
 def replay(c,r):return GameSession.replay(c,deserialize_game_record(json.dumps(r)))
 def match(s,r):
  aa=[a for a in s.legal_actions()if action_to_dict(a)==r];assert len(aa)==1;return aa[0]
 for root in p['supports']['manifest']+p['free_residual_support']['manifest']:
  c=cs[root['world']];s=replay(c,root['record']);assert state_sha(s.state)==root['id'];stored=rows[root['id']];assert stored['status']=='COMPLETE';weights=[list(map(float,worlds[root['world']]['priors'][n]))for n in names]
  def value(st,left,ply):
   counts['tree_visits']+=1
   if counts['tree_visits']%128==0 and(time.perf_counter()-beg>600 or role_stop_requested()):raise RuntimeError('CAP_OR_STOP')
   if st.terminal_status.is_terminal:return[float(terminal_score(st.terminal_status,st.position.side_to_move,ply))]*len(names)
   if not left:
    phi=[sum((1 if x.owner==0 else-1)for x in st.position.board if x and x.current_type_id==n)for n in'ABC']+[0,0,0];sign=1 if st.position.side_to_move==0 else-1
    return[sign*sum(a*b for a,b in zip(phi,w))for w in weights]
   children=[[-v for v in value(ch,left-1,ply+1)]for a,ch in legal_successors(st,c)];assert children
   return list(map(max,zip(*children)))
  branches=[dict(action=action_to_dict(a),scores=[-v for v in value(ch,3,1)])for a,ch in legal_successors(s.state,c)]
  assert branches==stored['branches']
  for j,n in enumerate(names):
   top=max(b['scores'][j]for b in branches);assert[i for i,b in enumerate(branches)if b['scores'][j]==top]==stored['supports'][n]
  counts['literal_roots']+=1
 for z in p['supports']['controls']+p['free_residual_support']['controls']:
  r=rows[z['id']];aa=[b['action']for b in r['branches']];a=r['supports'][z['arm']];b=r['supports'][z['base']];i=aa.index(z['arm_action']);j=aa.index(z['base_action']);assert i in a and j in b
  assert(z['support_changed'],z['base_served_excluded'],z['TD_served_excluded'],z['both_cooptimal_under_both'])==(a!=b,j not in a,i not in b,i in a and j in a and i in b and j in b);counts['support_controls']+=1
 for w in worlds.values():
  base=Model(w['priors']['unit']);td=Model(w['priors']['unit_TD']);eps=F(0)
  for xyz in itertools.product((-1,0,1),repeat=3):
   phi=xyz+(0,0,0);assert base.raw(phi)==sum(xyz);eps=max(eps,abs(F.from_float(td.raw(phi))-sum(xyz)));counts['integer_leaf_vectors']+=1
  stored=next(r for r in p['integer_gap_lemma']['worlds']if r['world']==w['world']);assert str(eps)==stored['actual_float_leaf_error']and 2*eps<1
 for z in p['supports']['controls']:
  if z['arm']=='unit_TD'and z['base']=='unit':assert set(rows[z['id']]['supports']['unit_TD'])<=set(rows[z['id']]['supports']['unit'])
 intervention=p['intervention'];case=intervention['inputs']['cases'][0];c=cs[case['world']]
 for g in intervention['games']:
  s=replay(c,case['record']);assert state_sha(s.state)==g['root'];s.submit(match(s,g['forced_action']))
  expected=case['TD_action']if g['first']=='unit_TD'else case['mobility_action'];assert expected==g['forced_action']
  for q in g['queries']:
   assert(q['id'],q['ply'],q['actor'])==(state_sha(s.state),s.state.ply_count,s.state.position.side_to_move);r=q['receipt'];assert r['complete']and r['completed_depth']==4
   weights=worlds[case['world']]['priors'][g['tail']if q['actor']==case['role']else'mobility'];assert q['weights']==weights;pv=copy.copy(s)
   for a in r['pv']:pv.submit(match(pv,a));counts['intervention_PV_edges']+=1
   env=FixedScaleSessionEnv(pv,unit_type='A');v=env.terminal()
   if v is None:assert tuple(r['pv_phi'])==env.features()and math.isclose(Model(weights).raw(env.features()),r['value'],abs_tol=1e-12)and not r['pv_terminal']
   else:assert r['pv_terminal']and r['value']==MATE*v
   assert r['pv'][0]==r['action'];s.submit(match(s,r['action']));counts['new_intervention_queries']+=1
  assert record_value(s.to_record())==g['final_record'];v=FixedScaleSessionEnv(s,unit_type='A').terminal();assert g['utility']==[v*(1 if case['role']==0 else-1)]*2 and not g['censor'];counts['new_interventions']+=1
 for root in p['history']['critical_roots']:
  if'record'in root:assert state_sha(replay(cs[root['world']],root['record']).state)==root['id'];counts['history_roots_replayed']+=1
 assert counts['literal_roots']==19 and counts['support_controls']==26 and counts['new_interventions']==2 and counts['new_intervention_queries']==125
 return dict(status='PASS',seconds=time.perf_counter()-beg,counts=counts,scope='Literal shared-Core D4 support trees and all125 new intervention PVs/actual terminals. Cached old history graph labels are reused annotations,not independently rebuilt by this reader;critical retained records are replayed. No independent engine or global learning claim.')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();r=verify(a.folder);a.output.write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
