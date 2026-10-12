"""Freeze8new finitepin/xray/EP/promotion witnesses and color-mirrors."""
import chess,json,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task153';O.mkdir(exist_ok=True)
if (O/'declaration.json').exists():raise FileExistsError('frozen')
cases=[('pinned_defender','3k4/3n4/4Rp2/6P1/8/8/8/K2R4 w - - 0 1','e6f6',[0,1,111,112,207,208,209]),('xray_behind_bishop','k6q/3n2b1/4Rp2/6P1/8/8/8/K7 w - - 0 1','e6f6',[-189,-188,-187,0,207,208,209]),('en_passant','k7/8/8/3pP3/8/8/8/7K w - d6 0 1','e5d6',[0,1,111,112,207,208,209]),('promotion_capture','k6r/6P1/8/8/8/8/8/7K w - - 0 1','g7h8q',[0,1,208,209,697,698,699])]
rows=[]
for kind,fen,text,thresholds in cases:
 b=chess.Board(fen);m=chess.Move.from_uci(text);assert b.is_valid() and m in b.legal_moves
 for mirror in (False,True):
  board=b.mirror() if mirror else b;move=chess.Move(chess.square_mirror(m.from_square),chess.square_mirror(m.to_square),promotion=m.promotion) if mirror else m
  assert board.is_valid() and move in board.legal_moves
  rows.append(dict(id=kind+('-mirrored' if mirror else ''),kind=kind,mirror=mirror,fen=board.fen(),move=move.uci(),thresholds=thresholds,scope='Restrictedlegalcapture-on-target, declineonlywherelegalnontargetactionexists; notWDL/allmoveoracle. EP/promotion sourceSEEshortcut0explicitlyapproximate.'))
d=dict(task_id='153',question='Do price-routing repairs preservefinitepin/xray/color behavior, and whatspecialmoveapproximation remains?',weights=dict(P=208,K=0,N=2000,B=52,R=396,Q=510),modes=[0,3],fixtures=rows,queries=112,deadline_seconds=120,cost='8fixturesx2modesx7thresholds plus80leafqualificationprobes and32before/afterevaltraces; expected<5s,120sfuse. No newtraining orchangedoldfrozenrecords.',source_pin='9f778da667f6e07dae1e85d3e2ea204fc6dee94d',binary_sha256='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460',decision='Pinned/xray/color mismatches isolatefiniteunsupportedprice/SEEscope; EP/promotion0 differences areexplicitoldshortcut, notpricefixfailureorwholeenginelegalitybug. Leafpromotion/EPgain mustmatchcandidatecounts; no universalSEEclaim.')
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(json.dumps(dict(frozen=True,fixtures=len(rows),queries=112)))
