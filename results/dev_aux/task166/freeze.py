"""Freeze reachable balanced full-army roots before any engine result."""
import json,random,hashlib,chess
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task166';O.mkdir(exist_ok=True)
def make(seed,plies=20):
 b=chess.Board();rng=random.Random(seed);actions=[]
 for _ in range(plies):
  legal=sorted((m for m in b.legal_moves if not b.is_capture(m) and not m.promotion),key=lambda m:m.uci())
  if not legal or b.is_game_over(claim_draw=False):return dict(seed=seed,excluded=True,reason='no legal noncapture continuation or terminal',ply=len(actions),initial_fen=chess.Board().fen(),history=actions,expected_fen=b.fen(),legal_moves=[m.uci() for m in sorted(b.legal_moves,key=lambda m:m.uci())])
  move=rng.choice(legal);b.push(move);actions.append(move.uci())
 if not b.is_valid() or b.is_game_over(claim_draw=False):return dict(seed=seed,excluded=True,reason='invalid or terminal at fixed20ply',ply=len(actions),initial_fen=chess.Board().fen(),history=actions,expected_fen=b.fen())
 counts={str(t):[len(b.pieces(t,c)) for c in (True,False)] for t in range(1,7)}
 assert counts=={'1':[8,8],'2':[2,2],'3':[2,2],'4':[2,2],'5':[1,1],'6':[1,1]}
 return dict(seed=seed,initial_fen=chess.Board().fen(),history=actions,expected_fen=b.fen(),counts=counts)
if __name__=='__main__':
 if (O/'declaration.json').exists():raise FileExistsError('frozen')
 profiles=json.loads((R/'results/dev_aux/task127/declaration.json').read_bytes())['profiles']
 all_roots=[make(2026102600+i) for i in range(8)]
 roots=[r for r in all_roots if not r.get('excluded')];excluded=[r for r in all_roots if r.get('excluded')]
 profiles['reversed']={**profiles['learned'],**dict(zip('NBRQ',[profiles['learned'][k] for k in 'QRBN']))}
 D=dict(task_id='166',question='Do reachable full-army 20ply noncapture roots provide short-game price feedback with less mate saturation?',roots=roots,excluded_roots=excluded,planned_games=96,excluded_slots=len(excluded)*12,profiles=profiles,opponents=['random','unit2ply'],random_seeds=[2026202600+i for i in range(8)],cap=16,games=len(roots)*12,deadline_seconds=300,binary_sha256='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460',agent='mode3 one thread16MiB/go nodes1024; fivepriceprobes/exactMG/EGack/reset pergame; one engine only',root_rule='Exactly20uniform legal noncapture/nonpromotion actions from orthodox initial position; impossible construction slots excluded symmetrically across all profile/opponent/color arms before engine results and preserved without resampling, no engine/outcome/human-price selection. Complete preludehistory stays in every engine/opponent query.',profiles_scope='Unit and exposed Task126 predictor, plus fixed reversal of its NBRQ weights as diagnostic intervention; no human reference input, no new training.',reward='Unchanged Task104 terminal100+speed elseunitcountdiff/15; bounded andcomponent measures separate',decision='Paired action/reward differences and lower terminal saturation can support further feedback-learning check, not humanpriceidentification. Retain zero/negative profile/opponent findings.',cost='96fixed16plygames estimated<60s with extraPython completeunit2ply work;300s fuse, noextraengine/worker or fees. This is distribution intervention not equal-compute strength.',scope='Reachable standardChess/fullarmy/count-preserving preludes; fullcastling/EP/history afterroots, notfullgeneric orShogi. No longer games or seedresampling.')
 (O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');print(json.dumps(dict(frozen=True,games=D['games'],excluded_slots=D['excluded_slots'],roots=len(D['roots']))))
