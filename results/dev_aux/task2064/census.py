"""Complete small-inventory Core census, history may only add draws here."""
from pathlib import Path
from dataclasses import replace
from itertools import permutations
from collections import Counter,defaultdict
import hashlib,json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state,legal_successors
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.terminal import TerminalResult,TerminalStatus,terminal_result
from generic_chess.core.attacks import is_in_check
from scripts.generic_proof_rnb_bridge import actor_state,uci
from results.dev_aux.task2064.actor import NPlusActor
from scripts.generic_session_native_material import _load_transport
OUT=Path('results/dev_aux/task2064')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert hashlib.sha256(Path(p['rules']).read_bytes()).hexdigest()==p['rules_sha'];start=time.perf_counter();rs=deserialize_ruleset(Path(p['rules']).read_text());c=compile_ruleset_for_execution(rs);base=initial_state(c);t=_load_transport();actor=NPlusActor(4)
 assert c.capture_disposition=='remove_from_game' and not c.declarations and c.repetition_policy=='draw' and c.stalemate_result=='draw'
 assert not c.automatic_adjudications and not c.consecutive_action_adjudications and not c.repeated_cycle_target_conditions and c.no_progress_draw is None and not c.pass_enabled
 assert not rs.semantic_actions and all(not p.is_promotable for p in c.piece_types) and not any(any(v for mask in masks for v in mask) for masks in c.drop_allowed.values())
 counts=defaultdict(Counter);witnesses=defaultdict(list);h=hashlib.sha256();processed=0;status='COMPLETE';edges=0
 with (OUT/'states.jsonl').open('x') as f:
  for mode in p['inventories']:
   for squares in permutations(range(16),2 if mode=='KK' else 4 if mode=='KKBN' else 3):
    for extra_owner in (range(1) if mode=='KK' else range(2)):
     for turn in (0,1):
      if time.perf_counter()-start>=p['seconds_cap']:status='PARTIAL_TIME_CAP';break
      if processed%256==0:t.stop_check(Path.cwd())
      counts[mode]['syntactic']+=1;board=[None]*16;board[squares[0]]=Piece(0,'K','K');board[squares[1]]=Piece(1,'K','K')
      if mode!='KK':board[squares[2]]=Piece(extra_owner,'B' if mode=='KKBN' else mode[-1],'B' if mode=='KKBN' else mode[-1])
      if mode=='KKBN':board[squares[3]]=Piece(extra_owner,'N','N')
      pos=replace(base.position,board=tuple(board),side_to_move=turn);raw=tuple('.' if x is None else x.current_type_id.lower() if x.owner else x.current_type_id for x in board)+(turn,)
      unsafe=is_in_check(pos,1-turn,c);assert actor.valid(raw)==(not unsafe)
      if unsafe:counts[mode]['nonmoving_anchor_unsafe']+=1;continue
      key=repetition_identity_key(pos,c);state=GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),));state=replace(state,terminal_status=terminal_result(state,c));expected=dict(actor.moves(raw));children=() if state.terminal_status.is_terminal else legal_successors(state,c);actual={uci(a):child for a,child in children};assert set(actual)==set(expected)
      terminal=state.terminal_status;counts[mode]['admissible']+=1;counts[mode][terminal.status.value]+=1
      if terminal.winner is not None:
       counts[mode]['winning_terminals']+=1
       if len(witnesses[mode])<8:witnesses[mode].append(dict(board=list(raw),winner=terminal.winner,status=terminal.status.value))
      for name,child in actual.items():
       assert actor_state(child)==expected[name] and not is_in_check(child.position,turn,c)
       assert all(not hand.total() for hand in child.position.hands)
       inv=Counter((x.owner,x.current_type_id) for x in child.position.board if x is not None);assert inv[0,'K']==inv[1,'K']==1 and sum(inv.values()) in (2,3,4)
       if mode=='KK':assert sum(inv.values())==2
       elif mode=='KKBN':assert all(tid in ('K','B','N') for _,tid in inv) and all(owner==extra_owner for owner,tid in inv if tid!='K') and inv[extra_owner,'B']<=1 and inv[extra_owner,'N']<=1
       else:assert all(tid in ('K',mode[-1]) for _,tid in inv) and sum(n for (_,tid),n in inv.items() if tid!='K')<=1
       edges+=1
      row=dict(children=[[name,list(actor_state(child))] for name,child in sorted(actual.items())],inventory=mode,board=list(raw),status=terminal.status.value,winner=terminal.winner,actions=sorted(actual),successor_sha=hashlib.sha256(repr(sorted((name,actor_state(child),child.terminal_status.status.value,child.terminal_status.winner) for name,child in actual.items())).encode()).hexdigest());text=json.dumps(row,separators=(',',':'));f.write(text+'\n');h.update(text.encode()+b'\n');processed+=1
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
 complete=status=='COMPLETE' and sum(v['syntactic'] for v in counts.values())==p['syntactic_positions'];assert not complete or sum(v['syntactic'] for v in counts.values())==202080
 out=dict(status=status,complete_inventory_and_all_edges=complete,counts={k:dict(v) for k,v in counts.items()},winning_witnesses=dict(witnesses),processed=processed,actual_legal_edges=edges,records_sha=h.hexdigest(),seconds=time.perf_counter()-start,rules_sha=p['rules_sha'],ruleset_fingerprint=c.ruleset_fingerprint,no_winning_terminal_inventories=[k for k,v in counts.items() if complete and v['winning_terminals']==0],scope=p['closure'],adoption=p['adoption'],new_native_go=0,new_reward_games=0)
 with (OUT/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({k:v for k,v in out.items() if k!='winning_witnesses'}))
if __name__=='__main__':run()
