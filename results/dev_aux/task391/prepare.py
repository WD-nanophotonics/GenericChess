import sys,json,time,hashlib
from pathlib import Path
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task390'));from analyze import features
O=R/'results/dev_aux/task391';O.mkdir(exist_ok=True);w=[0,90,151,78,68,284,109,716,0,80,171,200,345,121,55,0];selected=[]
for line,text in enumerate((R/'results/dev_aux/task370/games.jsonl').open(encoding='utf-8'),1):
 g=json.loads(text)
 for ply,a in enumerate(g['actions']):
  if not a['captured']:continue
  b=C.Board(a['before_sfen']);m=b.move_from_usi(a['move']);assert b.is_legal(m);after=b.copy();after.push(m);assert after.sfen().split()[:3]==a['after_sfen'].split()[:3];v0,t0=features(b.sfen());v1,t1=features(after.sfen());actual=sum((y-x)*p for x,y,p in zip(v0,v1,g['weights']))*(1 if a['actor']==0 else -1);recaps=[C.move_to_usi(n) for n in after.legal_moves if C.move_to(n)==C.move_to(m)]
  if not recaps and actual>0:
   selected.append(dict(file='results/dev_aux/task370/games.jsonl',line=line,ply=ply,weights=g['weights'],initial_sfen=g['root']['initial_sfen'],history=g['root']['history']+[x['move'] for x in g['actions'][:ply]],before_sfen=a['before_sfen'],move=a['move'],captured=a['captured'],promotion=a['promotion'],material_increment=actual,legal_same_square_recaptures=recaps))
   break
 if selected:break
assert len(selected)==1
# Three actors plus distant kings; finite local-exchange counterexample, not game/WDL proof.
sfen='k8/9/9/4p4/4p4/4+B4/9/9/8K b - 1';b=C.Board(sfen);first='5f5e';reply='5d5e';assert b.is_legal(b.move_from_usi(first));b.push_usi(first);assert b.is_legal(b.move_from_usi(reply));b.push_usi(reply)
start=features(sfen)[0];finish=features(b.sfen())[0];material=sum((y-x)*p for x,y,p in zip(start,finish,w));expected_board=w[1]-w[13];assert expected_board==-31 and material==-225
source=R/'.local_agent/yaneura25/source/position.cpp';search=R/'.local_agent/yaneura25/source/engine/yaneuraou-engine/yaneuraou-search.cpp';d=dict(real_first_undefended_capture=selected[0],local_exchange=dict(sfen=sfen,weights=w,first=first,reply=reply,board_see=expected_board,board_hand_actual_two_capture_material=material,threshold=-73,expected_board_see_pass=True,actual_two_capture_material_pass=False,scope='fixedlegal two-capture sequence; SEE board-onlyapprox vs exactsequence value. Does not establish optimaldefense, movechoice orpruning bug; remainingboardempty intentionallyprobe'),source_sha='c1b80eaa09fe13d5f12b1599d1ae4d53c224de30',patched_position_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),search_sha256=hashlib.sha256(search.read_bytes()).hexdigest(),source_uses=dict(initial_capture_board_only='position.cpp2591',moving_actor_pre_move_type='position.cpp2603..2604',candidate_LVA_board_price='position.cpp2650..2662',actual_qsearch_threshold='engine/yaneuraou-engine/yaneuraou-search.cpp4993'),planned_actual='auxsee only, no go; aftersole387producerfinished; test-74/-73/-32/-31/-30 andexactstatecache before/after',new_go=0)
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(json.dumps(d))