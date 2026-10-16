"""Posthoc actual-history WIN admission at first low-inventory entry.
Table guides candidate construction only. Public graph verifier/cursor decide
admission. This never supplies learning reward or modifies a saved game.
"""
from pathlib import Path
from collections import Counter
from copy import copy
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import SessionChoice,execute
from scripts.generic_win_proof import _Budget,_Interrupted
from scripts.generic_proof_rnb_bridge import actor_state,uci
from results.dev_aux.task2220.study import Guide,key
from results.dev_aux.task2179.graph import GraphNode,GraphCertificate
from results.dev_aux.task2199.semantic_graph import canonical,verify_graph,GraphStrategyCursor
from results.dev_aux.task2181.run import encode as encode_graph
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2246')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):
 with(OUT/n).open('x')as f:json.dump(v,f,indent=2)
def freeze():
 save('plan.json',dict(source_sha=sha(OUT/'entry_proofs.py'),game_task=2230,context=2228,games_sha=sha('results/dev_aux/task2230/games.jsonl'),selection='ALL128context2228actualgames, FIRST<=4actorentryinactualrecord irrespectiveofprice/outcome. PrepaidcanonicalrowusedONLYtoconstruepositivecandidate,notactualhistorylabel. NO newoutcomes/learning/refit. Firstentryterminalseparate; nonpositivecanonicalcandidateNOTactualDRAW.',build_nodes=8192,build_seconds=2.,verify_nodes=16384,verify_seconds=3.,cursor_seconds=3.,one_cap_seconds=900,estimated_seconds=400,scope='Posthocmechanismrecordaudit: currentfullGameSessionroot/rules/pastcounts/remainingplyindependentlyverified beforepositiveentryclaim. ActualsavedcontinuationcheckedthroughsameGraphStrategyCursor. NO genericMateSolver adoption/onlinebudgetclaim; thisscopedtableassistedcandidatebuilderandprepaymentfullyexplicit. UNKNOWNkept,notreward; entry/conversionassociationnotcausalmediationproof.'))
 print('FROZEN_ALL128_FIRST_ENTRIES_POSTHOC_ONLY')
def build(s,guide,target,p,cancel):
 b=_Budget(p['build_nodes'],p['build_seconds'],cancel);nodes=[];ids={};visiting=set()
 def add(position):
  b.poll();token=key(actor_state(canonical(position,s.compiled).state))
  if token in ids:
   if token in visiting:raise ValueError('cyclic_table_strategy')
   return ids[token]
  b.visit();i=len(nodes);ids[token]=i;nodes.append(None);visiting.add(token);v=canonical(position,s.compiled);b.poll();r=guide.rows[token]
  if v.result.status is not SessionStatus.ONGOING:
   if v.result.winner!=target:raise ValueError('nonWINcanonicalterminal')
   nodes[i]=GraphNode(0,(),v.result)
  else:
   winner=v.state.position.side_to_move if r['label']=='WIN'else 1-v.state.position.side_to_move if r['label']=='LOSS'else None
   if winner!=target:raise ValueError('notpositivecanonicalstrategy')
   actions={uci(a):a for a in v.legal_actions()};names=[r['winning_action']]if position.side_to_move==target else sorted(actions);edges=[]
   for name in names:
    b.poll();child=copy(v);choice=SessionChoice('ACTION',action=actions[name]);execute(child,choice);j=add(child.state.position);assert nodes[j].rank<r['rank'];edges.append((choice,j))
   nodes[i]=GraphNode(r['rank'],tuple(edges))
  visiting.remove(token);return i
 add(s.state.position);return GraphCertificate(s.compiled.ruleset_fingerprint,s.to_record(),s.state,target,tuple(nodes)),dict(nodes=b.nodes,seconds=b.elapsed())
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());assert sha(OUT/'entry_proofs.py')==p['source_sha']and sha('results/dev_aux/task2230/games.jsonl')==p['games_sha'];save('started.json',dict(plan_sha=sha(OUT/'plan.json')));start=time.perf_counter();deadline=start+p['one_cap_seconds'];stop=EvidenceStopReader(Path.cwd());guide=Guide();roots={r['family']:r for r in json.loads(Path('results/dev_aux/task2228/inputs.json').read_text())['roots']};games=[json.loads(l)for l in Path('results/dev_aux/task2230/games.jsonl').read_text().splitlines()if json.loads(l)['context']==2228];assert len(games)==128;rows=[];status='COMPLETE'
 def cancel():stop();return time.perf_counter()>=deadline
 with(OUT/'queries.jsonl').open('x')as qf,(OUT/'certificates.jsonl').open('x')as cf:
  for g in games:
   if cancel():status='PARTIAL_GLOBAL_CAP';break
   root=roots[g['family']];s=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text())));actions=deserialize_game_record(json.dumps(g['record'])).actions;entry=None
   for ply,a in enumerate(actions):
    if sum(pc is not None for pc in s.state.position.board)<=4:entry=ply;break
    s.submit(a)
   if entry is None and sum(pc is not None for pc in s.state.position.board)<=4:entry=len(actions)
   row=dict(slot=g['slot'],family=g['family'],ratio=g['ratio'],opponent_ratio=g['opponent_ratio'],candidate_color=g['candidate_color'],actual_outcome=g['outcome'],first_entry_ply=entry,status='NO_LOW_ENTRY',positive_entry_verified=False,actual_cursor_converted=False)
   if entry is not None:
    row['root_record']=json.loads(serialize_game_record(s.to_record()));row['root_state_sha']=hashlib.sha256(repr(s.state).encode()).hexdigest()
    if s.result.status is not SessionStatus.ONGOING:row['status']='ACTUAL_ENTRY_TERMINAL';row['entry_terminal_winner']=s.result.winner
    else:
     canonical_row=guide.rows[key(actor_state(s.state))];winner=s.state.position.side_to_move if canonical_row['label']=='WIN'else 1-s.state.position.side_to_move if canonical_row['label']=='LOSS'else None;row['canonical_candidate_winner']=winner;row['status']='NO_POSITIVE_CANDIDATE_FOR_ACTOR'
     if winner==g['candidate_color']:
      try:
       cert,work=build(s,guide,winner,p,cancel);row['builder']=work;row['status']='CANDIDATE_REQUIRES_VERIFY';cf.write(json.dumps(dict(slot=g['slot'],certificate=encode_graph(cert)))+'\n');cf.flush()
       v=verify_graph(s,cert,max_nodes=p['verify_nodes'],seconds=min(p['verify_seconds'],max(0.,deadline-time.perf_counter())),cancel=cancel);row['verification']=v
       if v['verified']:
        row['positive_entry_verified']=True;row['status']='VERIFIED_CURRENT_HISTORY_WIN';cursor=GraphStrategyCursor(s,cert,max_nodes=p['verify_nodes'],seconds=min(p['cursor_seconds'],max(0.,deadline-time.perf_counter())),cancel=cancel);row['cursor_receipt']=cursor.receipt
        for a in actions[entry:]:
         stop();before=copy(s);choice=SessionChoice('ACTION',action=a)
         if s.state.position.side_to_move==winner:assert cursor.choose(s)==choice
         execute(s,choice);cursor.observe(before,choice,s)
        assert s.result.status is not SessionStatus.ONGOING and s.result.winner==winner;row['actual_cursor_converted']=True;row['actual_remaining_moves']=len(actions)-entry
       else:row['status']='UNKNOWN_VERIFICATION'
      except _Interrupted as error:row['status']='UNKNOWN_BUILD_BUDGET';row['reason']=str(error)
      except(ValueError,AssertionError)as error:row['status']='UNKNOWN_CANDIDATE_OR_CURSOR_REJECTION';row['reason']=str(error)
   rows.append(row);qf.write(json.dumps(row)+'\n');qf.flush()
   if len(rows)%16==0:print(json.dumps(dict(entries=len(rows),seconds=time.perf_counter()-start,verified=sum(r['positive_entry_verified']for r in rows))),flush=True)
 save('result.json',dict(status=status,rows=len(rows),expected=128,missing=128-len(rows),seconds=time.perf_counter()-start,profiles={str(x):dict(games=sum(r['ratio']==x for r in rows),statuses=dict(Counter(r['status']for r in rows if r['ratio']==x)),verified_positive_entries=sum(r['ratio']==x and r['positive_entry_verified']for r in rows),actual_cursor_conversions=sum(r['ratio']==x and r['actual_cursor_converted']for r in rows))for x in(1.,2.)},scope=p['scope']));print('CLOSED_FIRST_ENTRY_PROOF_AUDIT',status,len(rows))
if __name__=='__main__':import sys;{'freeze':freeze,'run':run}[sys.argv[1]]()
