import json,hashlib,importlib.util,time
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task285';D=json.loads((R/'results/dev_aux/task258/declaration.json').read_bytes());s=importlib.util.spec_from_file_location('codec',R/'results/dev_aux/task253/codec.py');C=importlib.util.module_from_spec(s);s.loader.exec_module(C);X=C.decode(json.loads((R/D['source_file']).read_bytes()));start=time.monotonic();selected=[];seen=set();examined=0
for game in X['calls']:
 if game['phase']!='train':continue
 for rec in game['result']['search_records']:
  hist=rec['full_history'];b=chess.Board(game['result']['root_fen'])
  for text in hist:assert chess.Move.from_uci(text) in b.legal_moves;b.push_uci(text)
  assert b.fen()==rec['root_fen'];key=tuple(hist)
  if key in seen:continue
  seen.add(key);examined+=1;captures=[]
  for m in sorted(b.legal_moves,key=lambda m:m.uci()):
   if b.is_capture(m):captures.append(dict(move=m.uci(),actor=chess.piece_symbol(b.piece_type_at(m.from_square)).upper(),victim='P' if b.is_en_passant(m) else chess.piece_symbol(b.piece_type_at(m.to_square)).upper()))
  if len({m['victim'] for m in captures})>=2:selected.append(dict(id=f'capture-{len(selected)}',initial_fen=game['result']['root_fen'],history=hist,fen=b.fen(),captures=captures,source_game=game['name'],phase='train' if len(selected)<2 else 'development'))
  if len(selected)==4:break
 if len(selected)==4:break
assert selected==D['roots'];assert hashlib.sha256((R/D['source_file']).read_bytes()).hexdigest()==D['source_file_sha256']
out=dict(complete=True,reconstructed_first_four_roots_exact=True,unique_source_states_examined=examined,selected=selected,seconds=time.monotonic()-start,source_sha256=D['source_file_sha256'],scope='Reproducibleindependentselectionfromfullrawsource236codec, nohumanlabel/rootgoal. Initial258selector was inadvertently self-overwrittenwithacomment AFTERfreeze byproducer; actualdeclaration/results remainedexact. Missingoriginalselectorbody isacknowledged, notclaimedfullypreserved. This285auditor reconstructscriterionandmatchesallroots, notretroactivefreshsample.',source_integrity='268/270allfullhistoryrecordsactualand260all235698treeleavesverified; sourceHashunchanged. First3White states shareonepriortrainingtrajectory, fourthBlacksameopening, not4IIDroots ornewholdout.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='selected'})
