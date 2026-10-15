"""Exposed late-win censorship mechanism, never relabel prior UNKNOWN reward."""
from pathlib import Path
from dataclasses import asdict
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import SessionStrategyCursor
from scripts.generic_session_native_material import _load_transport
from scripts.generic_win_proof import CertificateVerificationError
OUT=Path('results/dev_aux/task1880')
def write(n,d):
 with (OUT/n).open('x') as f:json.dump(d,f,indent=2)
def run():
 report=json.loads(Path('results/dev_aux/task1877/audit.json').read_text());chosen=[p for p in report['pairs'] if p['outcomes']==['UNKNOWN','WIN']];assert len(chosen)==1;case=chosen[0];games=[json.loads(x) for x in Path('results/dev_aux/task1877/games.jsonl').read_text().splitlines()];game=next(g for g in games if g['slot']==case['slots'][1]);plan=dict(status='FROZEN_BEFORE_PROBES',case=case,plies=[8,12,16,17],target=game['candidate_side'],proof_nodes=16384,proof_seconds=1.5,verification_nodes=16384,verification_seconds=.5,max_depth=64,seconds_cap=20,question='Was the loneH24 extraWIN already cheaply provable at H8, or did later normalplay move it within the sameprover budget?',scope='ONEexposed outcome-selected mechanism case, no newNative/learningreward/oldcap extension. Preserve oldH8UNKNOWN/H24WIN and fullsamefirst8prefix. ActualSessionverification/physicalonebranch ifproved, not newindependent sample; no besthorizon fromnonflat/sec alone.')
 write('plan.json',plan);c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text()));beg=time.perf_counter();rows=[];t=_load_transport()
 for ply in plan['plies']:
  t.stop_check(Path.cwd());assert time.perf_counter()-beg<20;raw=dict(game['record']);raw['actions']=raw['actions'][:ply];s=GameSession.replay(c,deserialize_game_record(json.dumps(raw)));before=s.to_record();r=prove_session_win_batch_pn(s,target=plan['target'],max_nodes=16384,seconds=1.5,max_depth=64,cancel=lambda:time.perf_counter()-beg>=20);row=dict(ply=ply,target=plan['target'],actual_turn=s.state.position.side_to_move,status=r.status,reason=r.reason,proof_nodes=r.nodes,proof_seconds=r.seconds,root_record=json.loads(serialize_game_record(before)),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest())
  if r.certificate is not None:
   try:
    cursor=SessionStrategyCursor(s,r.certificate,max_nodes=16384,seconds=.5);row['verification']=cursor.receipt;rank=cursor.node.rank;steps=0
    while s.result.status is SessionStatus.ONGOING:
     assert steps<64
     choice=cursor.choose(s) if s.state.position.side_to_move==plan['target'] else cursor.node.edges[0][0];cursor.commit(s,choice);steps+=1
    assert s.result.winner==plan['target'];row.update(rank=rank,physical_moves=steps,winner=s.result.winner,executed_record=json.loads(serialize_game_record(s.to_record())))
   except CertificateVerificationError as e:row['verification']=e.receipt
  rows.append(row)
 write('result.json',dict(status='COMPLETE_EXPOSED_LATE_WIN_DIAGNOSTIC',rows=rows,seconds=time.perf_counter()-beg,native_go=0,new_learning_games=0,scope=plan['scope']))
 print(json.dumps(dict(rows=[{k:r[k] for k in ('ply','actual_turn','status','reason','proof_nodes')} for r in rows],seconds=time.perf_counter()-beg)))
if __name__=='__main__':run()
