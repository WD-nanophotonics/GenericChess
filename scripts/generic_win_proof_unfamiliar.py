"""Complete finite unfamiliar 3x3 custody/drop game, independent public DP."""
import itertools,json,time,hashlib
from dataclasses import replace
from pathlib import Path
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.position import GameState,Hands,HistoryRecord
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import initial_state,apply_action
from generic_chess.core.terminal import TerminalStatus,TerminalResult,terminal_result
from generic_chess.rules.schema import RuleSet
from generic_chess.rules.compiler import compile_ruleset
from scripts.generic_win_proof import prove_win,verify_certificate,PROVEN_WIN
from scripts.generic_win_proof_pn import prove_win_pn

def run():
    p=Path('results/dev_aux/task1769');p.mkdir(exist_ok=False);start=time.perf_counter();deadline=start+300
    king=PieceType('K','Anchor',tuple(LeapAtom((x,y)) for x in (-1,0,1) for y in (-1,0,1) if x or y),is_anchor=True)
    a=PieceType('A','Asymmetric mixed actor',(RayAtom((1,0)),LeapAtom((1,1)),LeapAtom((-1,1))))
    board=[None]*9;board[0],board[1],board[8]=Piece(0,'K','K'),Piece(0,'A','A'),Piece(1,'K','K')
    rs=RuleSet(board_size=3,piece_types=(king,a),initial_position=tuple(tuple(board[y*3:y*3+3]) for y in range(3)),drop_allowed={'A':((True,)*9,)*2},capture_disposition='capture_to_hand',max_ply=6,repetition_limit=100)
    c=compile_ruleset(rs);base=initial_state(c);roots=[]
    for k,b in itertools.permutations(range(9),2):
     for loc in [i for i in range(9) if i not in (k,b)]+['HAND']:
      for owner,turn in itertools.product((0,1),repeat=2):
       board=[None]*9;board[k],board[b]=Piece(0,'K','K'),Piece(1,'K','K');hands=[Hands.empty(),Hands.empty()]
       if loc=='HAND':hands[owner]=Hands((('A',1),))
       else:board[loc]=Piece(owner,'A','A')
       pos=replace(base.position,board=tuple(board),hands=tuple(hands),side_to_move=turn)
       if is_in_check(pos,1-turn,c):continue
       key=repetition_identity_key(pos,c);s=GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),));s=replace(s,terminal_status=terminal_result(s,c))
       roots.append(s)
    plan=dict(roots=len(roots),scope='ALL valid fresh3x3 K+A custody/drop roots, asymmetric forward ray+diagonal leaps, maxply6; complete finite DP. No material input, no KRK/table hints.',max_nodes=4096,seconds=1.,max_depth=6,total_seconds=300,rule_fingerprint=c.ruleset_fingerprint,
              reference_key_justification='Board,hands,turn,ply suffice ONLY because repetition100>maxply6 and no other history rule/aux/pass/declaration exists.',
              solver_sha256=hashlib.sha256(Path('scripts/generic_win_proof.py').read_bytes()).hexdigest(),pn_sha256=hashlib.sha256(Path('scripts/generic_win_proof_pn.py').read_bytes()).hexdigest())
    (p/'plan.json').write_text(json.dumps(plan,indent=2));print('FROZEN_UNFAMILIAR',len(roots),flush=True)
    cache={};edges=0

    def exact(s):
     nonlocal edges
     key=(s.position.board,s.position.hands,s.position.side_to_move,s.ply_count)
     if key in cache:return cache[key]
     t=terminal_result(s,c)
     if t.is_terminal:v=0 if t.winner is None else 1 if t.winner==0 else -1
     else:
      children=[apply_action(s,a,c) for a in legal_actions(s,c)];edges+=len(children)
      values=[exact(child) for child in children];v=(max(values) if s.position.side_to_move==0 else min(values))
     cache[key]=v;return v
    labels=[exact(s) for s in roots];counts={};calls=0;failures=[];proofs=0
    with (p/'calls.jsonl').open('x') as log:
     for i,s in enumerate(roots):
      for name,fn in [('ANDOR',prove_win),('PN',prove_win_pn)]:
       if time.perf_counter()>=deadline:break
       r=fn(c,s,target=0,max_nodes=4096,seconds=1.,max_depth=6,cancel=lambda:time.perf_counter()>=deadline)
       v=verify_certificate(c,s,r.certificate,seconds=1.) if r.status==PROVEN_WIN else None
       if r.status==PROVEN_WIN:assert labels[i]==1 and v['verified'];proofs+=1
       calls+=1;key=str((name,labels[i],r.status));counts[key]=counts.get(key,0)+1
       log.write(json.dumps(dict(root=i,board=[None if x is None else [x.owner,x.current_type_id] for x in s.position.board],hands=[list(h.counts) for h in s.position.hands],turn=s.position.side_to_move,exact=labels[i],algorithm=name,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,verified=v))+'\n');log.flush()
      if time.perf_counter()>=deadline:break
    out=dict(status='COMPLETE_UNFAMILIAR_FINITE_GAME' if calls==len(roots)*2 else 'PARTIAL_CAP_PRESERVED',roots=len(roots),calls=calls,reference_states=len(cache),reference_edges=edges,counts=counts,verified_wins=proofs,seconds=time.perf_counter()-start)
    (p/'result.json').write_text(json.dumps(out,indent=2));print(out)


if __name__=='__main__':
    run()
