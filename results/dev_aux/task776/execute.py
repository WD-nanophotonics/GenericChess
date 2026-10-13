import json,hashlib,time,sys,os,math,cshogi as C
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task776';plan=json.loads((O/'declaration.json').read_bytes());d=json.loads((R/'results/dev_aux/task769/execution_inputs.json').read_bytes());assert json.loads((R/'results/dev_aux/task775/result.json').read_bytes())['status']=='PASS_ORIGINAL_PARTIAL198_GAMES_PLUS12_UNCLOSED_QUERIES';start=time.monotonic();deadline=start+90
for n in [360,364,381,509]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(R/'results/dev_aux/task583'));from controller_curriculum import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];save=lambda p,x:p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def qty12(g):
 b=C.Board(g['root']['initial_sfen'])
 for u in g['root']['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 for a in g['actions'][:12]:assert b.sfen()==a['before_sfen'];m=b.move_from_usi(a['move']);assert b.is_legal(m);b.push(m)
 n=[0,0]
 for pc in b.pieces:
  if pc and pc%16!=8:n[0 if pc<16 else 1]+=1
 for i,h in enumerate(b.pieces_in_hand):n[i]+=sum(h)
 assert sum(n)==38;return n[g['color']]-n[1-g['color']]


P=R/'results/dev_aux/task777';assert not(P/'games.jsonl').exists();games=go=0;acks=[];refs=[];current=None;e=eu=None
try:
 with (P/'queries.jsonl').open('w') as qj,(P/'games.jsonl').open('w') as gj:
  for cell in plan['remaining']:
   group=(cell['opponent'],tuple(cell['weights']))
   if group!=current:
    if e:e.close();eu.close()
    current=group;e=ControlledEngine(cell['weights'],qj,'warm_game');eu=ControlledEngine(d['opponents'][cell['opponent']],qj,'warm_game');acks.extend([dict(role='candidate',opponent=cell['opponent'],weights=e.w,prices=e.prices),dict(role='unit',opponent=cell['opponent'],weights=eu.w,prices=eu.prices)]);save(P/'price_acks.json',acks)
   e.begin_game();eu.begin_game();g=native_game(e,eu,e.w,cell['root'],cell['color'],None,d,deadline);q12=qty12(g);q24=g['raw_quantity'];g.update(pool='independent_validation',opponent=cell['opponent'],cap=24,quantity12=q12,quantity24=q24,fitness=str(F(q12+q24,38)));gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());games+=1;go+=len(g['queries']);refs.append(dict(file=P.relative_to(R).as_posix()+'/games.jsonl',line=games));
   if games%32==0:print('MISSING_COMPLETE',games,go,round(time.monotonic()-start,1),flush=True)
finally:
 if e:e.close();eu.close()
assert games==250;save(P/'result.json',dict(status='COMPLETE_ALL250_ORIGINAL_MISSING_CASES',actual_games=games,actual_go=go,refs=refs,seconds=time.monotonic()-start,original769_complete=False,original769_fuse_failure_retained=True,scope=plan['scope']));print('TECHNICAL_COMPLETION',games,go,round(time.monotonic()-start,3),flush=True)
