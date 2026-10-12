"""Freeze geometry/side/clock material-trace fixtures before engine calls."""
import json,random,hashlib
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task130';OUT.mkdir(exist_ok=True)
profiles=[dict(P=208,K=0,N=208,B=208,R=208,Q=208),dict(P=208,K=0,N=232,B=328,R=396,Q=510)]
profiles += [r['final_weights'] for r in json.loads((ROOT/'results/dev_aux/task121/controller.json').read_bytes())['runs']]
packs=[('PPNBBRQ','PPNNBRQ'),('PPPNRQ','PPBQQ'),('PNBRQQ','PPNNBR'),('PPNNB','PBRQ')]
rng=random.Random(130);fixtures=[];attempts=0
for pack,strings in enumerate(packs):
 for layout in range(2):
  for trial in range(1000):
   attempts+=1;b=chess.Board(None);b.set_piece_at(chess.A1,chess.Piece(chess.KING,chess.WHITE));b.set_piece_at(chess.H8,chess.Piece(chess.KING,chess.BLACK))
   available=[s for s in chess.SQUARES if s not in (chess.A1,chess.H8)];good=True
   for color,text in zip((chess.WHITE,chess.BLACK),strings):
    for kind in text:
     eligible=[s for s in available if kind!='P' or chess.square_rank(s) not in (0,7)]
     if not eligible:good=False;break
     sq=rng.choice(eligible);available.remove(sq);b.set_piece_at(sq,chess.Piece.from_symbol(kind if color else kind.lower()))
   if not good:continue
   if not all((setattr(b,'turn',color) is None and b.is_valid() and not b.is_check() and not b.is_game_over(claim_draw=False)) for color in (chess.WHITE,chess.BLACK)):continue
   break
  else:raise RuntimeError('Fixedfixture construction failed; do not expand')
  for color in (chess.WHITE,chess.BLACK):
   for clock in (0,80):
    b.turn=color;b.halfmove_clock=clock;b.fullmove_number=1
    fixtures.append(dict(pack=pack,layout=layout,side='w' if color else 'b',clock=clock,fen=b.fen(),count_differences={chess.piece_symbol(t).upper():len(b.pieces(t,chess.WHITE))-len(b.pieces(t,chess.BLACK)) for t in (chess.PAWN,chess.KNIGHT,chess.BISHOP,chess.ROOK,chess.QUEEN)}))
decl=dict(task_id='130',question='Is the actual configurable eval a linear PNBRQ leaf across geometry, side and clock, rather than only singlepiece calibration?',profiles=profiles,fixtures=fixtures,planned_actual_trace_rows=len(profiles)*len(fixtures),singlepiece_config_probes=5*len(profiles),engine_calls='eval/ready only, no go or games; one owned process at a time afterTask129finishes',budget_seconds=60,source_scope='Sameoriginalbinary477628ae, disclosedsourcepin9f778da6 andpatch; actual finite evidence is not independent source-to-binary proof',fixture_scope='Synthetic freshFENeval fixtures only, no game-history or strength claim. Bothsides valid/notcheck/nonterminal beforefreeze; no resampling after engine results',construction_attempts=attempts,price_scope='All3frozenTask121ends plusunit/returnpredictor, no bestendpoint selection or humanvalue labels')
(OUT/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8');print(dict(fixtures=len(fixtures),profiles=len(profiles),actual_trace_rows=decl['planned_actual_trace_rows'],construction_attempts=attempts))