"""Exposed consumer cases, including the real old verifier-timeout input."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_proof_player import commit_session_decision
from scripts.generic_win_proof import _same_state
OUT=Path('results/dev_aux/task1862')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def run():
 plan=dict(status='FROZEN_BEFORE_CHECKS',source_sha={p:sha(p) for p in ['scripts/generic_session_cached_phase_player.py','scripts/generic_session_phase_player.py','scripts/generic_session_proof_bank.py',__file__]},seconds_cap=60,scope='4exposed winning requests/2unique roots plus old1860 verifier-timeout record, each cold/miss/hit; real currentchecks, no price fitting, no Native.')
 write('plan.json',plan);beg=time.perf_counter();c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1846/rules.json').read_text()));rows=[]
 positive=json.loads(Path('results/dev_aux/task1857/result.json').read_text())['rows']
 moves=[json.loads(x) for x in Path('results/dev_aux/task1848/moves.jsonl').read_text().splitlines()];games={x['slot']:x for x in (json.loads(y) for y in Path('results/dev_aux/task1848/games.jsonl').read_text().splitlines())}
 inputs=[]
 for item in positive:
  raw=dict(games[item['slot']]['record']);raw['actions']=raw['actions'][:item['ply']];inputs.append(dict(case='positive',slot=item['slot'],record=raw))
 negative=json.loads(Path('results/dev_aux/task1860/verification_timeout_case.json').read_text());inputs.append(dict(case='old_verifier_timeout',slot=negative['slot'],record=negative['before_record']))
 for item in inputs:
  s=GameSession.replay(c,deserialize_game_record(json.dumps(item['record'])));bank=SessionLogicalProofBank(prove_session_win_batch_pn);root=s.to_record();rootstate=s.state
  for mode in ('MISS','HIT_ATTEMPT'):
   def normal(state,n,seconds,cancel):return s.legal_actions()[0],1
   p=SessionCachedPhasePlayer(c,lambda p,t:0,bank=bank,normal_search=normal,proof_depth=64)
   d=p.choose(s,max_nodes=4096,seconds=2.75,cancel=lambda:time.perf_counter()-beg>=60)
   assert _same_state(s.state,rootstate) and _same_state(s.to_record(),root)
   fields={k:v for k,v in d.__dict__.items() if k not in ('root_record','root_state','root_result','normal_receipt','choice')};fields.update(case=item['case'],slot=item['slot'],mode=mode,paid_nodes=d.nodes)
   if d.source=='PROOF':
    assert d.verification_nodes>0 and p.cursor.receipt['verified']
    trial=GameSession.replay(c,root);steps=0
    while trial.result.status is SessionStatus.ONGOING:
     assert steps<64
     choice=p.cursor.choose(trial) if trial.state.position.side_to_move==p.cursor.certificate.target else p.cursor.node.edges[0][0]
     p.cursor.commit(trial,choice);steps+=1
    assert trial.result.winner==s.state.position.side_to_move
    fields.update(physical_moves=steps,winner=trial.result.winner,record=json.loads(serialize_game_record(trial.to_record())))
   else:assert p.cursor is None
   if item['case']=='positive':assert d.source=='PROOF'
   rows.append(fields)
 # Force an actual failed check on the SAME previously problematic full input,
 # with explicit changed verification cap; never claim replayed original timing.
 s=GameSession.replay(c,deserialize_game_record(json.dumps(negative['before_record'])))
 def normal(state,n,seconds,cancel):return s.legal_actions()[0],1
 d=SessionCachedPhasePlayer(c,lambda p,t:0,normal_search=normal,proof_depth=64,limits=PhaseLimits(verification_nodes=0)).choose(s,seconds=2.75)
 assert d.source=='EXTERNAL_SEARCH' and d.proof_reason=='bank_fill_verification_node_budget' and not d.bank_stored
 write('qualification.json',dict(status='PASS',source_unchanged=all(sha(p)==h for p,h in plan['source_sha'].items()),seconds=time.perf_counter()-beg,rows=rows,negative_changed_cap=dict(proof_reason=d.proof_reason,actualproof=d.proof_nodes,stored=d.bank_stored,currentverification=d.verification_nodes),scope=plan['scope']+' Oldtimefailure may or maynot recur under current load; zero-node qualification is separately declared, not an oldresult rewrite.'))
 print(json.dumps(dict(status='PASS',queries=len(rows)+1,seconds=time.perf_counter()-beg)))
if __name__=='__main__':run()
