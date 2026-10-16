"""Complete two-sided low-inventory Core census, independent literal move check."""
from pathlib import Path
from dataclasses import replace
from itertools import permutations
from collections import Counter,defaultdict
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state,legal_successors
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.terminal import TerminalResult,TerminalStatus,terminal_result
from generic_chess.core.attacks import is_in_check
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_session_native_material import _load_transport
OUT=Path('results/dev_aux/task2097')
def run():
 if (OUT/'started.json').exists():raise RuntimeError('Originalcap already started')
 p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));assert hashlib.sha256(Path(p['rules']).read_bytes()).hexdigest()==p['rules_sha'];start=time.perf_counter();(OUT/'started.json').write_text(json.dumps(dict(one_clock=True,cap_seconds=900,restart_forbidden=True,started_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())),encoding='utf-8');c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text(encoding='utf-8')));base=initial_state(c);actor=RoyalActor(4);t=_load_transport();counts=defaultdict(Counter);h=hashlib.sha256();processed=0;edges=0;status='COMPLETE'
 with (OUT/'states.jsonl').open('x',encoding='utf-8')as f:
  for mode in p['inventories']:
   for squares in permutations(range(16),2+len(mode)):
    for turn in(0,1):
     if time.perf_counter()-start>=900:status='PARTIAL_TIME_CAP';break
     if processed%256==0:t.stop_check(Path.cwd())
     counts[mode]['syntactic']+=1;board=[None]*16;board[squares[0]]=Piece(0,'K','K');board[squares[1]]=Piece(1,'K','K')
     for sq,ch in zip(squares[2:],mode):board[sq]=Piece(int(ch.islower()),ch.upper(),ch.upper())
     pos=replace(base.position,board=tuple(board),side_to_move=turn);raw=tuple('.'if x is None else x.current_type_id.lower()if x.owner else x.current_type_id for x in board)+(turn,);unsafe=is_in_check(pos,1-turn,c);assert actor.valid(raw)==(not unsafe)
     if unsafe:counts[mode]['nonmoving_anchor_unsafe']+=1;continue
     key=repetition_identity_key(pos,c);state=GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),));state=replace(state,terminal_status=terminal_result(state,c));actual={uci(a):s for a,s in(()if state.terminal_status.is_terminal else legal_successors(state,c))};expected=dict(actor.moves(raw));assert set(actual)==set(expected)
     for a,child in actual.items():
      assert actor_state(child)==expected[a] and not is_in_check(child.position,turn,c) and all(not h.total()for h in child.position.hands);chars=[x for x in actor_state(child)[:-1]if x!='.'];assert chars.count('K')==chars.count('k')==1 and all(chars.count(ch)<=1 for ch in 'BNbn')
     terminal=state.terminal_status;counts[mode]['admissible']+=1;counts[mode][terminal.status.value]+=1;edges+=len(actual)
     row=dict(children=[[name,list(actor_state(child))]for name,child in sorted(actual.items())],inventory='KK'+mode,board=list(raw),status=terminal.status.value,winner=terminal.winner);text=json.dumps(row,separators=(',',':'));f.write(text+'\n');h.update(text.encode()+b'\n');processed+=1
    if status!='COMPLETE':break
   if status!='COMPLETE':break
 complete=status=='COMPLETE'and sum(v['syntactic']for v in counts.values())==p['syntactic_positions'];result=dict(status=status,complete_inventory_and_all_edges=complete,counts={k:dict(v)for k,v in counts.items()},processed=processed,actual_legal_edges=edges,records_sha=h.hexdigest(),seconds=time.perf_counter()-start,rules_sha=p['rules_sha'],ruleset_fingerprint=c.ruleset_fingerprint,scope=p['scope'],new_native_go=0,new_reward_games=0);(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
