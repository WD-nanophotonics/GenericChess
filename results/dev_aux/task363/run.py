import sys,json,time,random,re
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'results/dev_aux/task360'));import adapter as A
R=Path.cwd();O=R/'results/dev_aux/task363';O.mkdir(exist_ok=True);t0=time.monotonic();rows=[];queries=[];events=[]
weights=[[0]+[90]*7+[0]+[90]*6+[0],[0,90,137,211,307,419,503,601,0,719,823,929,1031,1151,1259,0]]
# Fixtures are algorithmic type coverage; values are arbitrary non-human qualification numbers.
cases=[];empty='k8/9/9/9/9/9/9/9/8K b - 1'
for pypt in range(1,15):
 if pypt==8:continue
 for color in (A.shogi.BLACK,A.shogi.WHITE):
  b=A.shogi.Board(empty);b.set_piece_at(A.shogi.SQUARE_NAMES.index('5e'),A.shogi.Piece(pypt,color));b.turn=1-color;cases.append({'name':f'board-{pypt}-{color}','initial':b.sfen(),'history':[]})
for pypt in range(1,8):
 for color in (0,1):
  b=A.shogi.Board(empty);b.pieces_in_hand[color][pypt]=2;b.turn=color;cases.append({'name':f'hand-{pypt}-{color}','initial':b.sfen(),'history':[]})
# Capturing every promoted type must demote into the capturer hand.
for pt in [9,10,11,12,13,14]:
 b=A.shogi.Board(empty);b.set_piece_at(A.shogi.SQUARE_NAMES.index('5e'),A.shogi.Piece(pt,1));b.set_piece_at(A.shogi.SQUARE_NAMES.index('5f'),A.shogi.Piece(A.shogi.ROOK,0));cases.append({'name':f'captureprom-{pt}','initial':b.sfen(),'history':['5f5e']})
for pt in [1,2,3,4,6,7]:
 b=A.shogi.Board(empty);b.set_piece_at(A.shogi.SQUARE_NAMES.index('5c'),A.shogi.Piece(pt,0));moves=sorted(m.usi() for m in b.legal_moves if m.promotion);assert moves;cases.append({'name':f'promote-{pt}','initial':b.sfen(),'history':[moves[0]]})
for pt in range(1,8):
 b=A.shogi.Board(empty);b.pieces_in_hand[0][pt]=1;moves=sorted(m.usi() for m in b.legal_moves if m.drop_piece_type==pt);cases.append({'name':f'drop-{pt}','initial':b.sfen(),'history':[moves[len(moves)//2]]})
# Full-history king cycle has a fourth occurrence; material equality alone cannot certify this state.
cycle=['1i2i','9a8a','2i1i','8a9a']*3;cases.append({'name':'fourfold-history','initial':empty,'history':cycle})
for seed in [2026102500,2026102501]:
 b=A.shogi.Board();initial=b.sfen();rng=random.Random(seed);h=[]
 for i in range(40):
  cases.append({'name':f'prefix-{seed}-{i}','initial':initial,'history':list(h)})
  moves=sorted(m.usi() for m in b.legal_moves);assert moves;u=rng.choice(moves);h.append(u);b.push_usi(u)
(O/'declaration.json').write_text(json.dumps({'weights':weights,'cases':cases,'search_indices':[0,40,63,80,100],'limit':1024,'scope':'board/hand/promotion/demotion/drop/cached/full eval/legal sets/full history plus finite search; not general generated rules or learning'},indent=2),encoding='utf-8')
with (O/'queries.jsonl').open('w',encoding='utf-8') as journal:
 for wi,w in enumerate(weights):
  e=A.Engine(w,journal)
  try:
   for line in e.prices:
    if not line.startswith('info string auxprice '):continue
    pc,v,signed,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if 9<=pt<=14 else pt
    assert v==w[pt] and signed==(1 if pc<16 else -1)*w[pt]
    assert cap==(0 if pt in (0,8,15) else w[pt]+w[base]);assert prom==(w[base+8]-w[base] if 1<=base<=6 else 0)
   for ci,c in enumerate(cases):
    b=A.replay(c['initial'],c['history']);line=e.state(c['initial'],c['history']);state=A.validate_state(line,b,w)
    e.send('moves');e.send('auxstate');lines=e.until(lambda x:x.startswith('info string auxstate '));move_lines=[x for x in lines[:-1] if not x.startswith('info ')];assert len(move_lines)==1,lines
    actual=set(move_lines[0].split());expected=set(m.usi() for m in b.legal_moves);assert actual==expected,(c['name'],actual-expected,expected-actual)
    if c['name']=='fourfold-history':assert state['repetition']=='rep_draw';assert b.is_fourfold_repetition()
    rows.append({'weight_index':wi,'case_index':ci,'case':c['name'],'state':state,'legal_count':len(actual)})
    if ci in [0,40,63,80,100] and state['repetition']=='rep_none':
     r=e.search(c['initial'],c['history']);A.validate_search(r);queries.append(r)
   events.append({'weight_index':wi,'prices':e.prices,'transcript':e.transcript})
  finally:e.close()
(O/'result.json').write_text(json.dumps({'status':'PASS','seconds':time.monotonic()-t0,'cases_per_price':len(cases),'state_checks':len(rows),'legal_sets':len(rows),'actual_go':len(queries),'rows':rows,'queries':queries,'events':events},indent=2),encoding='utf-8');print('PASS',len(rows),len(queries),time.monotonic()-t0)