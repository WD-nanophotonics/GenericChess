from pathlib import Path
import json,ast,chess,random
R=Path.cwd();O=R/'results/dev_aux/task1039';(O/'failure.json').write_text(json.dumps(dict(error='Literalcomparisononinvalidroots includes royalcaptures inPython invalidpositionlegalarray; rejectedrootsnotrun, no actualgameaffected',actual_go=0,correction='Checkvalidrootliteralfrontier only; independentlyreconstructandpreserveall invalidfailure attempts'),indent=2),encoding='utf-8');g=dict(chess=chess)
for file,names in [('task1016/qualify.py',['inside','legal5','fen5','term5']),('task1016/audit_pilot.py',['reachable','attacked','literal'])]:
 tree=ast.parse((R/'results/dev_aux'/file).read_text(encoding='utf-8-sig'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'independent_filter','exec'),g)
checks=[]
for task in [1017,1029]:
 d=json.loads((R/f'results/dev_aux/task{task}/roots.json').read_bytes());accepted=[];counts=[0]*4
 for r in d['trace']:
  types=r.get('types',[6,4,2,6,4,2]);colors=r.get('colors',[1,1,1,0,0,0]);sq=random.Random(r['seed']).sample([chess.square(f,t) for t in range(5) for f in range(5)],len(types));assert sq==r['squares'];b=chess.Board(None)
  for s,t,c in zip(sq,types,colors):b.set_piece_at(s,chess.Piece(t,bool(c)))
  b.turn=not((r['index']//4)%2) if task==1029 else not(r['index']%2);assert b.fen()==r['fen8'] and g['fen5'](b)==r['fen5'];legal=g['literal'](b);failure=None
  if not b.is_valid():failure='invalid'
  else:
   assert legal==r['legal']
   if g['term5'](b):failure='terminal'
   elif len(legal)<2:failure='too_few_legal'
   elif not any(b.is_capture(chess.Move.from_uci(m)) for m in legal):failure='no_capture'
   else:
    for m in legal:
     actor=b.turn;b.push_uci(m);t=g['term5'](b);b.pop()
     if t and t['winner']==actor:failure='immediate_win';break
  assert failure==r['failure']
  if failure is None:
   if task==1017 and len(accepted)<32:accepted.append(r['seed'])
   elif task==1029 and counts[r['index']%4]<8:accepted.append(r['seed']);counts[r['index']%4]+=1
 assert accepted==[r['seed'] for r in d['roots']];checks.append(dict(task=task,attempts=len(d['trace']),filters=True))
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL640_MINI_GENERATOR_FILTERS_AND_FROZEN_ORDER',checks=checks,new_go=0),indent=2),encoding='utf-8');print(checks)
