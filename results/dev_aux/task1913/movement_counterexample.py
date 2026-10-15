"""Bounded same-N-ID movement counterexample to inventory-only deadness."""
from pathlib import Path
from dataclasses import replace,asdict
from itertools import permutations
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.movement import RayAtom
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state,legal_successors
from generic_chess.core.attacks import is_in_check
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.terminal import terminal_result,TerminalResult,TerminalStatus
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_inventory_proof_filter import InventoryNoWinFilter
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor
from scripts.generic_session_certificate_json import export_session_certificate
from scripts.generic_session_native_material import _load_transport
from scripts.generic_proof_rnb_bridge import uci
O=Path('results/dev_aux/task1913')
def write(n,d):
 with (O/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def run():
 plan=json.loads((O/'plan.json').read_text());beg=time.perf_counter();rs=deserialize_ruleset(Path(plan['rules']).read_text());neutral=[None]*16;neutral[0]=Piece(0,'K','K');neutral[15]=Piece(1,'K','K');rs=replace(rs,initial_position=tuple(tuple(neutral[y*4:y*4+4]) for y in range(4)),initial_setup_options=());changed=replace(rs,piece_types=tuple(replace(p,movement_atoms=p.movement_atoms+tuple(RayAtom(d) for d in ((1,0),(-1,0),(0,1),(0,-1)))) if p.type_id=='N' else p for p in rs.piece_types));c=compile_ruleset_for_execution(changed);base=initial_state(c);transport=_load_transport();seen=0;witness=None
 for squares in permutations(range(16),3):
  if time.perf_counter()-beg>60:break
  if seen%128==0:transport.stop_check(Path.cwd())
  seen+=1;board=[None]*16;board[squares[0]]=Piece(0,'K','K');board[squares[1]]=Piece(1,'K','K');board[squares[2]]=Piece(0,'N','N');pos=replace(base.position,board=tuple(board),side_to_move=0)
  if is_in_check(pos,1,c) or is_in_check(pos,0,c):continue
  key=repetition_identity_key(pos,c);state=GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),));state=replace(state,terminal_status=terminal_result(state,c))
  if state.terminal_status.status is not TerminalStatus.ONGOING:continue
  wins=[(a,s) for a,s in legal_successors(state,c) if s.terminal_status.winner==0]
  if wins:witness=(squares,board,wins);break
 if witness is None:write('result.json',dict(status='NO_WITNESS_WITHIN_FROZEN_SCAN',scanned=seen,seconds=time.perf_counter()-beg));return
 squares,board,wins=witness;rows=tuple(tuple(board[y*4:y*4+4]) for y in range(4));rules=replace(changed,initial_position=rows,initial_setup_options=());oldrules=replace(rs,initial_position=rows,initial_setup_options=());new=GameSession(compile_ruleset_for_execution(rules));old=GameSession(compile_ruleset_for_execution(oldrules));guard=InventoryNoWinFilter('results/dev_aux/task1895','results/dev_aux/task1896/coverage.json')
 from collections import Counter
 pattern=tuple(sorted(Counter((p.owner,p.current_type_id) for p in new.state.position.board if p is not None).items()));assert pattern in guard.patterns and not guard.eligible(new)
 assert old.result.status.value=='ongoing' and new.result.status.value=='ongoing'
 result=guard(new,max_nodes=16384,seconds=3.,max_depth=1);assert result.status=='PROVEN_WIN' and result.reason!='certified_inventory_no_win' and result.nodes>0
 verification=verify_session_certificate(new,result.certificate,max_nodes=16384,seconds=3.);assert verification['verified'];certificate=export_session_certificate(new,result.certificate);record=json.loads(serialize_game_record(new.to_record()));cursor=SessionStrategyCursor(new,result.certificate,max_nodes=16384,seconds=3.);choice=cursor.choose(new);terminal=cursor.commit(new,choice);assert terminal.winner==0 and terminal.status.value=='checkmate';GameSession.replay(new.compiled,new.to_record())
 (O/'rules.json').write_text(serialize_ruleset(rules));(O/'old_movement_rules.json').write_text(serialize_ruleset(oldrules));write('certificate.json',certificate)
 write('result.json',dict(status='PASS_ACTUAL_RULE_MATE',scan_syntactic=seen,squares=squares,changed_mechanism='N originalknight+rayorthogonal; samepieceID. Freshsmallsetup replacesoriginalsixpieceinput, not an oldtrajectory or movement-only causalW-L estimate.',old_fingerprint=old.compiled.ruleset_fingerprint,new_fingerprint=new.compiled.ruleset_fingerprint,census_fingerprint=guard.fingerprint,inventory_pattern_matches_old_filter=True,eligible=False,actual_proof_status=result.status,actual_proof_reason=result.reason,proof_nodes=result.nodes,verification=verification,first_action=uci(choice.action),actual_winner=terminal.winner,actual_result=terminal.status.value,initial_record=record,final_record=json.loads(serialize_game_record(new.to_record())),seconds=time.perf_counter()-beg,scope='OnepositiveactualSessionmechanismcounterexample; no new fullinventorycensus, no learnedprices/defaultchanges. Exactfp gate successfully delegates. IDs/inventoryalonewouldbeunsound.'))
 print(json.dumps(dict(status='PASS',scan=seen,proof_nodes=result.nodes,action=uci(choice.action),seconds=time.perf_counter()-beg)))
if __name__=='__main__':run()
