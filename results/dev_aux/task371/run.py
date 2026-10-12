import sys,json,time
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));import adapter as A
O=R/'results/dev_aux/task371';O.mkdir(exist_ok=True);weights=[[0]+[90]*7+[0]+[90]*6+[0],[0,90,137,211,307,419,503,601,0,719,823,929,1031,1151,1259,0]];empty='k8/9/9/9/9/9/9/9/8K b - 1';cases=[]
for pt in range(1,15):
 if pt==8:continue
 b=A.shogi.Board(empty);b.set_piece_at(A.shogi.SQUARE_NAMES.index('5e'),A.shogi.Piece(pt,1));b.set_piece_at(A.shogi.SQUARE_NAMES.index('5f'),A.shogi.Piece(A.shogi.ROOK,0));assert A.shogi.Move.from_usi('5f5e') in b.legal_moves;cases.append({'type':'undefended_capture','captured_type':pt,'sfen':b.sfen(),'move':'5f5e'})
b=A.shogi.Board(empty);b.set_piece_at(A.shogi.SQUARE_NAMES.index('5e'),A.shogi.Piece(A.shogi.PAWN,1));b.set_piece_at(A.shogi.SQUARE_NAMES.index('5f'),A.shogi.Piece(A.shogi.ROOK,0));b.set_piece_at(A.shogi.SQUARE_NAMES.index('5d'),A.shogi.Piece(A.shogi.PAWN,1));assert A.shogi.Move.from_usi('5f5e') in b.legal_moves;cases.append({'type':'one_recapture','captured_type':1,'sfen':b.sfen(),'move':'5f5e','reply':'5d5e'})
(O/'declaration.json').write_text(json.dumps({'weights':weights,'cases':cases,'thresholds':'expectedboard-onlyexchangevalue minus1,exact,plus1','scope':'finite no-recapture orone-unpromoted-recapture literalboardSEE; alsoindependent actualboard+hand captureincrement. Not all-defense/promotion exchange proof.'},indent=2),encoding='utf-8');rows=[];t0=time.monotonic()
for wi,w in enumerate(weights):
 e=A.Engine(w)
 try:
  for ci,c in enumerate(cases):
   pt=A.MAP[c['captured_type']];expected=w[pt] if c['type']=='undefended_capture' else w[pt]-w[6];b=A.shogi.Board(c['sfen']);before=A.material(b,w);b.push_usi(c['move']);after=A.material(b,w);basept=pt-8 if pt>=9 else pt;assert after-before==w[pt]+w[basept];e.state(c['sfen'],[])
   for threshold in [expected-1,expected,expected+1]:
    e.send(f"auxsee {c['move']} {threshold}");lines=e.until(lambda x:x.startswith('info string auxsee '));value=int(lines[-1].split()[-1]);assert bool(value)==(expected>=threshold),(wi,c,threshold,lines);rows.append({'weight_index':wi,'case_index':ci,'threshold':threshold,'expected_board_see':expected,'actual':bool(value),'actual_material_capture_delta':after-before})
 finally:e.close()
(O/'result.json').write_text(json.dumps({'status':'PASS','seconds':time.monotonic()-t0,'see_calls':len(rows),'rows':rows},indent=2),encoding='utf-8');print('PASS',len(rows),time.monotonic()-t0)