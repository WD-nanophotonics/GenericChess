import sys,json,time,hashlib
from pathlib import Path
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));sys.path.insert(0,str(R/'results/dev_aux/task390'));import adapter as A;import run as G;from analyze import features
O=R/'results/dev_aux/task391';d=json.loads((O/'declaration.json').read_text(encoding='utf-8'));t0=time.monotonic();rows=[];states=[]
def state(e,sfen,h):
 b=C.Board(sfen)
 for u in h:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 line=e.state(sfen,h);fields=line.split(' ',7);literal=sum(v*w for v,w in zip(features(b.sfen())[0],e.w));assert int(fields[3])==int(fields[4])==literal and int(fields[5])==(literal if b.turn==0 else -literal);assert fields[7].split()[:3]==b.sfen().split()[:3];states.append(dict(initial_sfen=sfen,history=h,state=line,literal_material=literal));return b
for name,c in [('real_recorded_capture',d['real_first_undefended_capture']),('local_exchange',d['local_exchange'])]:
 G.stop();w=c['weights'];e=A.Engine(w)
 try:
  if name=='real_recorded_capture':
   b=state(e,c['initial_sfen'],c['history']);assert b.sfen().split()[:3]==c['before_sfen'].split()[:3];move=c['move'];captured=c['captured'];letter=captured[-1].upper();pt={'P':1,'L':2,'N':3,'S':4,'B':5,'R':6,'G':7,'K':8}[letter]+(8 if '+' in captured else 0);expected=w[pt];thresholds=[expected-1,expected,expected+1];increment=c['material_increment']
  else:
   b=state(e,c['sfen'],[]);move=c['first'];expected=c['board_see'];thresholds=[-74,-73,-32,-31,-30];increment=c['board_hand_actual_two_capture_material']
  m=b.move_from_usi(move);assert b.is_legal(m)
  for threshold in thresholds:
   e.send(f'auxsee {move} {threshold}');lines=e.until(lambda x:x.startswith('info string auxsee '));value=int(lines[-1].split()[-1]);assert bool(value)==(expected>=threshold),(name,threshold,lines);rows.append(dict(case=name,move=move,threshold=threshold,actual_board_SEE_pass=bool(value),expected_board_see=expected,exact_local_material_value=increment,local_material_pass=increment>=threshold,lines=lines,scope='localmaterialvalue notall-defense/minimax orstrength certificate'))
  if name=='local_exchange':state(e,c['sfen'],[c['first'],c['reply']])
 finally:e.close()
result=dict(status='PASS',auxsee_calls=len(rows),new_go=0,seconds=time.monotonic()-t0,rows=rows,states=states,source_sha=d['source_sha'],executable_sha256=hashlib.sha256(A.EXE.read_bytes()).hexdigest(),scope='actualexperimentalbinary board-onlySEE threshold mismatch with board+hand evaluation; observedscope limit, no defaultpatch orwrongmoveclaim');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','states']}))