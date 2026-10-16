"""Independent total-coverage/Bellman/rank and real full-history execution audit."""
from pathlib import Path
from collections import Counter
from dataclasses import replace
from itertools import permutations
import json,hashlib,time,random
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state
from scripts.generic_inventory_proof_transport import execution_differences
ROOT=Path('results/dev_aux/task2221');LAB=Path('results/dev_aux/task2222');OUT=Path('results/dev_aux/task2223')
class RangeTwoRoyalActor(RoyalActor):
 def hit(self,state,a,b):
  if state[a].upper()=='R' and max(abs(b%self.width-a%self.width),abs(b//self.width-a//self.width))>2:return False
  return super().hit(state,a,b)

def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def read(p):return json.loads(Path(p).read_text())
def check_labels(rows,labels):
 ids={key(r['board']):i for i,r in enumerate(rows)};assert len(ids)==len(rows)==len(labels)
 value={'WIN':1,'DRAW':0,'LOSS':-1};checked=0
 for i,(r,l) in enumerate(zip(rows,labels)):
  assert l['index']==i and l['board']==r['board'] and l['status']==r['status'] and l['inventory']==r['inventory']
  edges=[(a,ids[key(raw)]) for a,raw in r['children']]
  assert [(e['action'],e['child']) for e in l['actions']]==edges
  assert all(e['child_value']==value[labels[e['child']]['label']] for e in l['actions'])
  if r['status']!='ongoing':
   expected=0 if r['winner'] is None else 1 if r['winner']==r['board'][-1] else -1
   assert value[l['label']]==expected and l['rank']==0 and not edges;continue
  utility=[-value[labels[j]['label']] for a,j in edges]
  assert value[l['label']]==max(utility)
  if l['label']=='WIN':
   choices=[(labels[j]['rank']+1,a) for (a,j),v in zip(edges,utility) if v==1]
   assert l['rank']==min(d for d,a in choices) and (l['rank'],l['winning_action']) in choices
  elif l['label']=='LOSS':assert l['rank']==1+max(labels[j]['rank'] for a,j in edges)
  else:assert l['rank'] is None and 0 in utility and max(utility)==0
  assert l['quality']=='EXACT_CANONICAL_FRESH_ROOT' and (l['rank'] is None or l['rank']<=96)
  checked+=len(edges)
 return checked

def run():
 assert not(OUT/'started.json').exists();p=read(OUT/'plan.json');start=time.perf_counter();(OUT/'started.json').write_text(json.dumps(dict(cap=p['seconds_cap'],source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())));stop=EvidenceStopReader(Path.cwd())
 def poll():
  stop()
  if time.perf_counter()-start>=p['seconds_cap']:raise TimeoutError('independentauditglobalcap')
 rows=[json.loads(x) for x in (ROOT/'states.jsonl').read_text().splitlines()];labels=[json.loads(x) for x in (LAB/'labels.jsonl').read_text().splitlines()];actor=RangeTwoRoyalActor(4)
 for folder in (ROOT,LAB):
  path=folder/('states.jsonl' if folder==ROOT else 'labels.jsonl');raw=b'\n'.join(path.read_bytes().splitlines())+b'\n';assert hashlib.sha256(raw).hexdigest()==read(folder/'result.json')['records_sha' if folder==ROOT else 'labels_sha']
 actual={key(r['board']) for r in rows};expected=set();syntactic=0
 for inventory in read(ROOT/'plan.json')['inventories']:
  for sq in permutations(range(16),2+len(inventory)):
   for turn in(0,1):
    if syntactic%1024==0:poll()
    raw=['.']*16;raw[sq[0]]='K';raw[sq[1]]='k'
    for at,tid in zip(sq[2:],inventory):raw[at]=tid
    raw=tuple(raw)+(turn,);syntactic+=1
    if actor.valid(raw):expected.add(key(raw))
 assert syntactic==read(ROOT/'plan.json')['syntactic_positions'] and actual==expected
 edges=check_labels(rows,labels);assert edges==read(ROOT/'result.json')['actual_legal_edges']
 rs=deserialize_ruleset(Path(read(ROOT/'plan.json')['rules']).read_text());c=compile_ruleset_for_execution(rs)
 assert c.repetition_policy=='draw' and c.repetition_limit==3 and c.max_ply==96 and c.no_progress_draw is None and not c.pass_enabled and not c.declarations
 assert c.capture_disposition=='remove_from_game' and c.stalemate_result=='draw' and not c.automatic_adjudications and not c.repeated_cycle_target_conditions and not c.consecutive_action_adjudications
 assert not rs.semantic_actions and all(not p.is_promotable for p in c.piece_types) and not any(any(mask) for masks in c.drop_allowed.values() for mask in masks)
 # Start fresh GameSessions; one root per decisive rank/role, plus stratified draw controls.
 selected=[];buckets={}
 for l in labels:
  if l['status']=='ongoing' and l['inventory']in('KKRNr','KKRrn'):buckets.setdefault((l['label'],l['rank'],l['board'][-1]),l['index'])
 selected=list(buckets.values());random.Random(20261016702059).shuffle(selected);selected=selected[:128]
 ids={key(l['board']):i for i,l in enumerate(labels)};executions=[];moves=0
 for initial in selected:
  poll();raw=labels[initial]['board'];board=tuple(None if x=='.' else Piece(int(x.islower()),x.upper(),x.upper()) for x in raw[:-1]);cc=replace(c,initial_position=replace(c.initial_position,board=board,side_to_move=raw[-1]),initial_setup_positions={})
  assert not execution_differences(c,cc)
  session=GameSession(cc);assert key(actor_state(session.state))==key(raw)
  begin=labels[initial];seen=set();trace=[]
  while session.result.status is SessionStatus.ONGOING:
   poll();i=ids[key(actor_state(session.state))];l=labels[i];legal={uci(a):a for a in session.legal_actions()};assert set(legal)=={e['action'] for e in l['actions']}
   if begin['label']!='DRAW':
    assert i not in seen;seen.add(i)
    if l['label']=='WIN':name=l['winning_action']
    else:name=max(l['actions'],key=lambda e:(labels[e['child']]['rank'],e['action']))['action']
    chosen=next(e for e in l['actions'] if e['action']==name);assert labels[chosen['child']]['rank']<l['rank']
   else:name=min(e['action'] for e in l['actions'] if e['child_value']==0)
   session.submit(legal[name]);trace.append(name);moves+=1
   replayed=GameSession.replay(cc,session.to_record());assert _same_state(replayed.state,session.state) and _same_state(replayed.result,session.result)
   assert len(trace)<=96
  actual_value=0 if session.result.winner is None else 1 if session.result.winner==raw[-1] else -1
  assert actual_value=={'WIN':1,'DRAW':0,'LOSS':-1}[begin['label']]
  executions.append(dict(root=initial,label=begin['label'],rank=begin['rank'],moves=trace,result_status=session.result.status.value,winner=session.result.winner,record=json.loads(serialize_game_record(session.to_record()))))
 (OUT/'executions.json').write_text(json.dumps(executions,separators=(',',':')))
 # Deliberate false label must fail the independent verifier.
 import copy
 bad=list(labels);index=next(i for i,l in enumerate(labels)if l['status']=='ongoing'and l['label']=='WIN');bad[index]=dict(labels[index],label='DRAW',rank=None)
 rejected=False
 try:check_labels(rows,bad)
 except AssertionError:rejected=True
 assert rejected
 result=dict(status='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY',syntactic=syntactic,states=len(labels),checked_edges=edges,all_winning_strategies_strict_rank_decrease=True,max_rank=max(l['rank'] or 0 for l in labels),full_history_execution_roots=len(executions),full_history_execution_moves=moves,actual_outcomes=dict(Counter(e['result_status'] for e in executions)),deliberate_label_corruption_rejected=rejected,seconds=time.perf_counter()-start,scope='ExactWDL forfreshcanonicalroots only: WIN/LOSS all-defense rank<=96 prevents repetition beforemate; DRAW hasclosed nonlosing choices forbothsides untilactualrepetition/maxply. ALLCoregraph edges/captureclosure checked. ActualGameSession samples corroborate semantics; not allpossiblehistories certificate/not universalGenericteacher. New4x4RN-vsRteacher, no2092policychange/noNN/newNativecalls.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':
 try:run()
 except (TimeoutError,AssertionError)as e:
  (OUT/'failure.json').write_text(json.dumps(dict(status='AUDIT_FAILED_NO_TEACHER_ADMISSION',error_type=type(e).__name__,message=str(e))))
  raise
