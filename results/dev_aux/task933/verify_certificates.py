from pathlib import Path
import json,sys,time
R=Path.cwd();O=R/'results/dev_aux/task935';O.mkdir(exist_ok=False);start=time.monotonic()
for n in [360,364,925]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G
from stock_guard import assert_supported
z=json.loads((R/'results/dev_aux/task934/certificates.json').read_bytes());count=0;terminal=0;branches=0;rows=[]
for case in z['cases']:
 b=A.shogi.Board(case['root']['initial_sfen']);states=[G.key(b)];movers=[];checks=[];attacker=case['attacker']
 def verify(tree,depth):
  global count,terminal,branches
  count+=1;assert b.sfen()==tree['sfen'];assert_supported(b.sfen());t=G.terminal(b,states,checks,movers)
  if 'terminal' in tree:assert t==tree['terminal'] and t['winner']==attacker;terminal+=1;return
  assert t is None and depth>0 and tree['actor']==b.turn;legal=sorted(m.usi() for m in b.legal_moves);cc=tree['children'];assert [c['move'] for c in cc]==legal if b.turn!=attacker else len(cc)==1 and cc[0]['move'] in legal
  branches+=len(cc)
  for c in cc:
   actor=b.turn;m=A.shogi.Move.from_usi(c['move']);assert m in b.legal_moves;movers.append(actor);b.push(m);checks.append(b.is_check());states.append(G.key(b))
   try:verify(c['proof'],depth-1)
   finally:states.pop();checks.pop();b.pop();movers.pop()
 verify(case['proof'],6);assert b.sfen()==case['root']['initial_sfen'];rows.append(dict(seed=case['root']['seed'],attacker=attacker,verified=True))
r=dict(status='PASS_ALL_THREE_FORCE_CERTIFICATES_INDEPENDENT_PYTHON_RULES',rows=rows,certificate_nodes=count,terminal_wins=terminal,branches=branches,seconds=time.monotonic()-start,new_go=0,scope='All legal defender replies verified, one legal winning attacker action per node, exacthistory/terminal andstockclosed. Force within6 only, no fullWDL; selectedpositiveverification isdiagnostic notnewtrainingrootselection.');(O/'result.json').write_text(json.dumps(r,indent=2));print(r)
