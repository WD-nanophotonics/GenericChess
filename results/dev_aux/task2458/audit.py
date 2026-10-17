"""Closed standalone-query and normalization-scope consumer, no search rerun."""
from pathlib import Path
from fractions import Fraction as Q
from math import inf
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_proof_rnb_bridge import actor_state,orbit
from results.dev_aux.task2397.material import channels
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2458')
def run():
 stop=SharedDeleteStopReader(Path.cwd());t=time.perf_counter();folder=Path('results/dev_aux/task2440/family-2');nodes=[json.loads(x)for x in(folder/'nodes.jsonl').read_text().splitlines()];root=json.loads((folder/'root.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));vectors={}
 for n in nodes:
  stop();ss=GameSession.replay(c,deserialize_game_record(json.dumps(n['record'])));f=channels(ss.state.position,nodes[0]['side'],excluded_type_ids={'K'});vectors[n['index']]=[f['board'].get('R',0),f['hand'].get('R',0),f['hand'].get('N',0),f['board'].get('N',0)]
 assert {str(k):v for k,v in vectors.items()}==json.loads(Path('results/dev_aux/task2457/features.json').read_text())
 def fold(weights):
  def rec(i):
   n=nodes[i]
   if n['status']!='ongoing':return Q(0)if n['winner']is None else inf if n['winner']==nodes[0]['side']else-inf
   if n['depth_remaining']==0:return sum(Q(x)*y for x,y in zip(vectors[i],weights))
   return(max if n['side']==nodes[0]['side']else min)(rec(j)for ch,j in n['children'])
  vals=[rec(j)for ch,j in nodes[0]['children']];v=max(vals);index=vals.index(v);return index,v
 for row in json.loads(Path('results/dev_aux/task2456/queries.json').read_text()):
  stop();a,b=(Q(float.fromhex(x))for x in row['float_point']);index,val=fold((a,b,Q(1),Q(1)));assert index==row['quantized_exact_action']==row['actual_action'];assert row['receipt']['choice']==nodes[0]['children'][index][0]and row['receipt']['completed_depth']==3;assert row['receipt']['score']==float(val)
 nrows=json.loads(Path('results/dev_aux/task2457/rows.json').read_text())
 for row in nrows:
  stop();a,b,h=map(Q,row['point']);index,val=fold((a,b,h,Q(1)));assert row['choice']==nodes[0]['children'][index][0]and row['score']==float(val)
 ng=json.loads(Path('results/dev_aux/task2457/result.json').read_text())
 for row in ng['actual_normal_queries']:
  index,val=fold((Q(3,4),Q(3,4),Q(row['N_hand']),Q(1)));assert row['choice']==nodes[0]['children'][index][0]and row['score']==float(val)and row['completed_depth']==3
 proof=json.loads(Path('results/dev_aux/task2448/result.json').read_text());assert len(proof['rows'])==2 and not json.loads(Path('results/dev_aux/task2448/certificates.json').read_text())
 for row in proof['rows']:
  stop();assert row['verified']is False and row['proof_reason']=='time_budget';r=deserialize_game_record(json.dumps(row['record']));assert len(r.actions)==1;a=r.actions[0];assert action_to_dict(a)==row['root_action'];victim=s.state.position.board[a.to_square.rank*4+a.to_square.file];assert victim.current_type_id==victim.base_type_id==row['victim'];child=GameSession.replay(c,r);assert child.state.position.side_to_move==1 and hashlib.sha256(repr(child.state).encode()).hexdigest()==row['state_sha'];assert json.loads(Path('results/dev_aux/task2448/plan.json').read_text())['target']==0
 initial=json.loads(Path('results/dev_aux/task2439/inputs.json').read_text());groups=[]
 for rr in initial:
  stop();ss=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(rr['rules']).read_text())));groups.append(min(map(repr,orbit(actor_state(ss.state)))))
 assert len(set(groups))==12 and not(set(groups[:4])&set(groups[4:]));result=dict(status='PASS_CLOSED_FLOAT_NHAND_AND_UNPROVED_ACTION_CONTEXTS',Core_positions=709,float_completed_receipts=71,Nhand_finite_folds=24,Nhand_completed_normal_receipts=3,standalone_action_WDL_queries=2,action_WDL_verified=0,actual_initial_symmetry_orbits=12,DESIGN_RESERVE_orbit_overlap=0,seconds=time.perf_counter()-t,scope='IndependentCoretypedfeatures/recursiveexactmaterialfolds matchclosedactualD3receipts; no newsearch/game/pricefitness. BothactionproofsremainUNKNOWNnotLOSS/WIN. Exactquartergridunchanged; floatingqualificationonly71pointsnotallIEEEvalues. FixNboard1scaleplusNhand1modelconstraint. InitialorbitseparationverifiedPOSTHOC, nevera changedselectionfilter; all12frozenrootsretained.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
