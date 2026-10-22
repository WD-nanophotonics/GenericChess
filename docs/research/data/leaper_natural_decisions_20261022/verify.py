"""Public arithmetic,actual win trees,and the price witness;no private caches."""
import gzip,hashlib,json,sys,time,importlib.util
from datetime import datetime
from collections import Counter,defaultdict,deque
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_from_dict,action_to_dict
from generic_chess.core.transition import legal_successors
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
from generic_chess.learning.mainline_search import search
from scripts.leaper_retrograde import fresh_state

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def verify(directory):
 start=time.perf_counter();m=json.loads((directory/'manifest.json').read_text());blob=(directory/m['file']).read_bytes()
 assert len(blob)==m['bytes']and hashlib.sha256(blob).hexdigest()==m['sha256']
 raw=gzip.decompress(blob);assert len(raw)==m['uncompressed_bytes'];p=json.loads(raw)
 compiled={fp:compile_rule(ruleset_from_dict(rule))for fp,rule in p['rules'].items()};assert all(c.ruleset_fingerprint==fp for fp,c in compiled.items())
 arithmetic={}
 for name in('four','five'):
  part=p[name];roots=part['roots'];counts=defaultdict(Counter);policy=defaultdict(Counter)
  for i,slot,ply,who,ai in part['visits']:
   r=roots[i];v=r['branches'][ai]['WDL'];policy[who]['visits']+=1;policy[who]['forks']+=r['distinct_WDL'];policy[who]['errors']+=v<r['root_WDL']
  assert len(part['queries'])==part['player_summary']['recorded']
  for q in part['queries']:
   i,b,d,done,nodes,secs,ai,v,score,phi,terminal,reason=q;r=roots[i]
   assert ai is None and v is None or ai is not None and r['branches'][ai]['WDL']==v
   stat=counts[f'{b}:D{d}'];stat['queries']+=1;stat['nodes']+=nodes;stat['seconds']+=secs;stat['errors']+=v is not None and v<r['root_WDL'];stat['full_depth']+=v is not None and done==d
  for key,stat in counts.items():
   old=part['player_summary']['conditions'][key]
   for field in('queries','nodes','errors','full_depth'):assert stat[field]==old[field]
   assert abs(stat['seconds']-old['seconds'])<1e-8
  assert sum(s['nodes']for s in counts.values())==part['player_summary']['nodes']
  arithmetic[name]=dict(histories=len(roots),visits=len(part['visits']),queries=len(part['queries']),nodes=sum(s['nodes']for s in counts.values()),policies=dict(policy))
 # Reuse the already public all-defense verifier,not a second rules/proof API.
 old=directory.parent/'leaper_primary_AB_truth_20261022'/'verify.py'
 spec=importlib.util.spec_from_file_location('existing_public_proof_verifier',old);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 proof_nodes=sum(module.verify_proof(compiled[r['record']['ruleset_fingerprint']],r)for r in p['proofs'])
 assert len(p['proofs'])==20 and proof_nodes==9168
 negative=0
 for kind in('wrong_winner','missing_defense'):
  row=deepcopy(next(r for r in p['proofs']if len(r['leaf_paths'])>1))
  if kind=='wrong_winner':row['winner']=1-row['winner']
  else:
   row['leaf_paths'].pop();prefixes={()}
   for path in row['leaf_paths']:
    path=tuple(action_from_dict(a)for a in path)
    prefixes.update(path[:i]for i in range(1,len(path)+1))
   row['nodes']=len(prefixes)
  try:module.verify_proof(compiled[row['record']['ruleset_fingerprint']],row)
  except(AssertionError,KeyError):negative+=1
  else:raise AssertionError('corrupted proof accepted')
 w=p['witness'];c=compiled[w['ruleset_fingerprint']];session=GameSession.replay(c,deserialize_game_record(json.dumps(w['record'])));prices=w['prices'];literal_nodes=0
 def solve(state,depth,ply):
  nonlocal literal_nodes
  literal_nodes+=1;assert literal_nodes<=200000 and time.perf_counter()-start<120
  if state.terminal_status.is_terminal:
   v=terminal_score(state.terminal_status,state.position.side_to_move,ply);return[v]*len(prices)
  if depth==0:
   phi={name:sum((1 if a.owner==0 else -1)for a in state.position.board if a and a.current_type_id==name)for name in('A','B')};sign=1 if state.position.side_to_move==0 else -1
   return[sign*(phi['A']+b*phi['B'])for b in prices]
  best=[-float('inf')]*len(prices)
  for a,ch in legal_successors(state,c):best=[max(v,-q)for v,q in zip(best,solve(ch,depth-1,ply+1))]
  assert all(v!=-float('inf')for v in best);return best
 actual_queries=0
 for row in w['rows']:
  branches=[]
  for a,ch in legal_successors(session.state,c):branches.append((action_to_dict(a),[-x for x in solve(ch,row['depth']-1,1)]))
  assert len(branches)==len(row['branches'])
  for (action,scores),saved in zip(branches,row['branches']):assert canonical(action)==canonical(saved['action'])and scores==saved['scores']
  for b in prices:
   env=FixedScaleSessionEnv(session,unit_type='A');model=Model([b if name=='B'else 1. for kind,name in env.names]);receipt=search(env,model,depth=row['depth'],nodes=8192,seconds=1.5,pv_reserve_fraction=.1)
   assert receipt.complete and receipt.completed_depth==row['depth'];actual_queries+=1
   a=action_to_dict(receipt.action.action);i=next(i for i,(aa,_)in enumerate(branches)if canonical(aa)==canonical(a));assert i in row['supports'][str(b)]
   # Bind independent replay to the full compact receipt table.
   root_index=next(i for i,r in enumerate(p['four']['roots'])if r['id']==w['root_id'])
   oldq=next(q for q in p['four']['queries']if q[0]==root_index and q[1]==b and q[2]==row['depth'])
   assert canonical(a)==canonical(p['four']['roots'][root_index]['branches'][oldq[6]]['action'])
 # The safe capture removes B. Its complete physical closure has no winning
 # terminal;the actual repetition and clock can only add draws in this rule.
 draw=p['draw_control'];safe=GameSession.replay(c,deserialize_game_record(json.dumps(draw['record'])));safe.submit(action_from_dict(draw['action']));seen={safe.state.position};queue=deque(seen);edges=0
 assert sum(a is not None for a in safe.state.position.board)==3
 while queue:
  assert len(seen)<=10000 and time.perf_counter()-start<120
  state=fresh_state(queue.popleft(),c);assert state.terminal_status.winner is None
  for a,ch in legal_successors(state,c):
   assert ch.terminal_status.winner is None;edges+=1
   if ch.position not in seen:seen.add(ch.position);queue.append(ch.position)
 assert len(seen)==draw['states']==2298 and edges==draw['edges']==9510
 critical=next(r for r in p['proofs']if r.get('counterfactual'))
 root_index=next(i for i,r in enumerate(p['four']['roots'])if r['id']==w['root_id']);badq=next(q for q in p['four']['queries']if q[0]==root_index and q[1]==.5 and q[2]==2);bad=p['four']['roots'][root_index]['branches'][badq[6]]['action']
 assert critical['record']['actions']==w['record']['actions']+[bad]
 for s in p['sources'].values():assert hashlib.sha256(s['text'].encode()).hexdigest()==s['text_sha256']
 ledger=p['effective_work'];credit=sum((datetime.fromisoformat(x['ended_at'])-datetime.fromisoformat(x['started_at'])).total_seconds()for x in ledger['intervals'])
 assert abs(credit-ledger['confirmed_seconds'])<1e-6 and credit>=3600
 compatibility=p['consumer_compatibility'];compat_nodes=0
 for row in compatibility['rows']:
  cc=compile_rule(ruleset_from_dict(row['rule']));assert cc.ruleset_fingerprint==row['fingerprint'];ss=GameSession.replay(cc,deserialize_game_record(json.dumps(row['record'])))
  env=FixedScaleSessionEnv(ss,unit_type='A');assert list(map(list,env.names))==row['names']
  rr=search(env,Model([1.]*len(env.names)),depth=1,nodes=256,seconds=2,pv_reserve_fraction=.1)
  assert rr.complete and rr.completed_depth==1 and canonical(action_to_dict(rr.action.action))==canonical(row['action']);compat_nodes+=rr.nodes
 assert len(compatibility['rows'])==10 and compat_nodes==compatibility['nodes']==103
 return dict(status='COMPLETE',arithmetic=arithmetic,actual_win_certificates=20,proof_Core_nodes=proof_nodes,negative_controls=negative,literal_price_nodes=literal_nodes,independent_public_queries=actual_queries,safe_draw_positions=len(seen),safe_draw_Core_edges=edges,canonical_compatibility_queries=10,canonical_compatibility_nodes=compat_nodes,effective_research_seconds=credit,seconds=time.perf_counter()-start,scope='Allcompactreceiptarithmeticandselectedliteralcontrols;fullgraph/history-WDLcensusesarenotrecomputedwithoutthelocalcaches. No training,newfitnessor network.')

if __name__=='__main__':print(json.dumps(verify(Path(__file__).resolve().parent),indent=2))
