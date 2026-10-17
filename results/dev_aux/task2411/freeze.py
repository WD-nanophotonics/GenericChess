from pathlib import Path
from dataclasses import replace
import json,hashlib,datetime
from generic_chess.core.pieces import Piece
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleActionEffect,RuleSquareRef
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.session.result import SessionStatus
out=Path('results/dev_aux/task2411');base=deserialize_ruleset(Path('results/dev_aux/task2315/rules.json').read_text());cases=[]
for count in(0,5):
 if count==0:
  rs=replace(base,initial_setup_options=());prefix=[((0,1),(0,2),'sem_01'),((3,0),(3,1),'legacy_')]
 else:
  rows=[list(row)for row in base.initial_position];rows[1][0]=Piece(0,'P','R',True)
  for x,y in[(0,3),(2,1),(2,2),(3,2),(3,3)]:assert rows[y][x]is None;rows[y][x]=Piece(1,'R','R')
  old=base.semantic_actions[1];actions=[]
  for name,squares in[('harvest_first',[(2,1),(2,2)]),('harvest_second',[(3,2),(3,3)])]:
   effects=tuple(RuleActionEffect('remove',square_ref=RuleSquareRef('fixed',square=xy),disposition='capture_to_hand',piece_owner='opponent')for xy in squares)+(old.effects[0],old.effects[1])
   actions.append(replace(old,name=name,type_ids=('R',),effects=effects,aux_state=()))
  rs=replace(base,initial_position=tuple(tuple(row)for row in rows),initial_setup_options=(),semantic_actions=(base.semantic_actions[0],)+tuple(actions));prefix=[((0,1),(0,2),'sem_01'),((3,0),(3,1),'legacy_'),((0,2),(0,3),'sem_02'),((3,1),(3,0),'legacy_')]
 path=out/f'rules-{count}.json';path.write_text(serialize_ruleset(rs));c=compile_ruleset_for_execution(rs);s=GameSession(c)
 for src,dst,pattern in prefix:
  a,=[a for a in s.legal_actions()if hasattr(a,'from_square')and(a.from_square.file,a.from_square.rank)==src and(a.to_square.file,a.to_square.rank)==dst and a.pattern_id.startswith(pattern)];s.submit(a)
 assert s.result.status is SessionStatus.ONGOING;board=sum(p is not None for p in s.state.position.board);hands=sum(h.total()for h in s.state.position.hands);assert board==4 and hands==count+1
 cases.append(dict(extra=count,rules=path.as_posix(),record=json.loads(serialize_game_record(s.to_record())),board=board,hands=hands,total=board+hands,gate_current=board<=4 and board+hands<=8,board_only_heuristic=board<=4,legal_choices=len(s.legal_actions())))
(out/'inputs.json').write_text(json.dumps(cases,indent=2));(out/'plan.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),question='Does total8 gate exclude a tiny actual executable WIN because hand multiplicity is overcounted?',cases=2,query_nodes=64,query_seconds=3.,verification_seconds=3.,max_depth=8,cap_seconds=30,forecast_seconds=10,scope='Two constructed actualhistories, NOTmatchedruntimecausalpanel. Sparsecaseoldcapture/promotion/aux;richcaseinitialP-currentR plusTWOlegal3-victimcaptureactions/2kingmoves,4effects each obeycompilerlimit. SixREALRcapturedstock/noinjectedhistory. Gate diagnostic only; fixedTRAIN/reservepolicy unchanged. UNKNOWNpreserved/no oldcapextension/replacementgateadoption.',pins={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest()for p in[out/'inputs.json']+[Path(r['rules'])for r in cases]}),indent=2));print(json.dumps([dict(extra=r['extra'],board=r['board'],hands=r['hands'],total=r['total'],gate=r['gate_current'],legal=r['legal_choices'])for r in cases]))
