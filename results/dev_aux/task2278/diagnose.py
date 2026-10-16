"""Closed-pair first-divergence diagnosis; canonical quality is NEVER reward."""
from pathlib import Path
from collections import Counter
from copy import copy
from types import SimpleNamespace
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_win_proof import _Interrupted
from results.dev_aux.task2246.entry_proofs import build
from results.dev_aux.task2199.semantic_graph import verify_graph
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2278')
def key(b):return ''.join(b[:-1])+str(b[-1])
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(plan=p)));labels={};indices={}
 def cancel():stop();return time.perf_counter()-start>=p['cap_seconds']
 for i,line in enumerate(Path('results/dev_aux/task2249/labels.jsonl').open(encoding='utf-8')):
  if i%1024==0 and cancel():raise TimeoutError('first_divergence_cap')
  r=json.loads(line);labels[key(r['board'])]=r;indices[r['index']]=r
 guide=SimpleNamespace(rows=labels,indices=indices);roots={r['family']:r for r in json.loads(Path('results/dev_aux/task2261/inputs.json').read_text())['roots']};games=[json.loads(x)for x in Path('results/dev_aux/task2261/games.jsonl').read_text().splitlines()];idx={(g['phase'],g['family'],g['ratio'],g['opponent_ratio'],g['candidate_color']):g for g in games};value={'WIN':1,'DRAW':0,'LOSS':-1};rows=[];proofs={};rawcerts=[]
 for a in games:
  if a['ratio']!=1.:continue
  if cancel():raise TimeoutError('first_divergence_cap')
  b=idx[(a['phase'],a['family'],2.,a['opponent_ratio'],a['candidate_color'])];root=roots[a['family']];c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession(c);left=deserialize_game_record(json.dumps(a['record'])).actions;right=deserialize_game_record(json.dumps(b['record'])).actions;common=0
  while common<min(len(left),len(right)) and left[common]==right[common]:s.submit(left[common]);common+=1
  row=dict(phase=a['phase'],family=a['family'],opponent_ratio=a['opponent_ratio'],candidate_color=a['candidate_color'],actual_reward_before=a['reward'],actual_reward_after=b['reward'],actual_reward_delta=b['reward']-a['reward'],diverged=common<len(left)or common<len(right),common_total_plies=common)
  if row['diverged']:
   assert common<len(left)and common<len(right)and s.result.status is SessionStatus.ONGOING;actor=s.state.position.side_to_move;row.update(first_actor=actor,first_actor_is_candidate=actor==a['candidate_color'],canonical_root_label=labels[key(actor_state(s.state))]['label'],children=[])
   for price,action in [(1.,left[common]),(2.,right[common])]:
    t=copy(s);execute(t,SessionChoice('ACTION',action=action));l=labels[key(actor_state(t.state))];utility=-value[l['label']];child=dict(price=price,action=uci(action),canonical_actor_utility=utility,actual_positive_proof=None)
    if utility==1:
     record=json.loads(serialize_game_record(t.to_record()));token=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()
     if token not in proofs:
      try:
       cert,work=build(t,guide,actor,p,cancel);verification=verify_graph(t,cert,max_nodes=p['verify_nodes'],seconds=p['verify_seconds'],cancel=cancel);proofs[token]=dict(status='VERIFIED_ACTUAL_ACTOR_WIN'if verification['verified']else'UNKNOWN_ACTUAL_HISTORY',builder=work,verification=verification);rawcerts.append(dict(key=token,rules=root['rules'],root_record=record,certificate=encode(cert)))
      except(_Interrupted,ValueError,AssertionError)as error:proofs[token]=dict(status='UNKNOWN_BUILD_OR_CONTEXT',reason=str(error))
     child['actual_positive_proof']=token
    row['children'].append(child)
   row['canonical_quality_delta']=row['children'][1]['canonical_actor_utility']-row['children'][0]['canonical_actor_utility']
  else:assert a['reward']==b['reward']and len(left)==len(right)
  rows.append(row)
 assert len(rows)==192
 (OUT/'pairs.json').write_text(json.dumps(rows,separators=(',',':')));(OUT/'certificates.json').write_text(json.dumps(rawcerts,separators=(',',':')));(OUT/'proof_receipts.json').write_text(json.dumps(proofs,indent=2));result=dict(status='COMPLETE_192_CLOSED_FIRST_DIVERGENCE_DIAGNOSIS',pairs=len(rows),panels={phase:dict(pairs=sum(r['phase']==phase for r in rows),divergent=sum(r['phase']==phase and r['diverged']for r in rows),reward_changing=sum(r['phase']==phase and r['actual_reward_delta']!=0 for r in rows),quality_changing=sum(r['phase']==phase and r.get('canonical_quality_delta',0)!=0 for r in rows),contingency=dict(Counter(str((r.get('canonical_quality_delta'),r['actual_reward_delta']))for r in rows if r['phase']==phase and r['diverged'])))for phase in ['TRAIN','DEV']},noncandidate_first_divergences=sum(r['diverged']and not r['first_actor_is_candidate']for r in rows),positive_child_statuses=dict(Counter(v['status']for v in proofs.values())),positive_child_contexts=len(proofs),seconds=time.perf_counter()-start,scope='ALL128TRAIN+64DEVunity/selected2pairs fromclosed2261, no newfit/player/rewardgame/rootfilter. Firstactualcommonrecorddivergence fullyreplayed. canonicalactionquality vsactualrewarddistinct, posthocassociationNOTcausalmediation. Positivechildrenactualhistoryverified onlywhereexplicit; reference0/notpositive staysunproved, noDRAWreward. Actualprice-learningusesoriginaltruefiniteW-L only.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
