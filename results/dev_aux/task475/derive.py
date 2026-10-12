import json,sys,hashlib
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task475';sys.path.insert(0,str(R/'results/dev_aux/task390'));from analyze import features
source=R/'results/dev_aux/task471/result.json';r=json.loads(source.read_text(encoding='utf-8'));MAP={'P':1,'L':2,'N':3,'S':4,'B':5,'R':6,'G':7,'K':8};rows=[]
def boardtypes(sfen):
 cells={}
 for rank,row in enumerate(sfen.split()[0].split('/')):
  col=0;prom=False
  for ch in row:
   if ch=='+':prom=True;continue
   if ch.isdigit():col+=int(ch);continue
   cells[str(9-col)+chr(97+rank)]=MAP[ch.upper()]+(8 if prom else 0);col+=1;prom=False
  assert col==9
 return cells
for arm,groups in r['source_rows'].items():
 for group in groups:
  q=group['queries'][0];w=q['weights'];b=C.Board(q['initial_sfen'])
  for u in q['history']:b.push_usi(u)
  for li,line in enumerate(q['lines']):
   if ' pv ' not in line:continue
   p=b.copy()
   for ply,u in enumerate(line.split(' pv ',1)[1].split()):
    before=p.sfen();cells=boardtypes(before);m=p.move_from_usi(u);assert p.is_legal(m);side=p.turn;target=cells.get(u[2:4],0);drop='*' in u;actor=0 if drop else cells[u[:2]];base=target-8 if target in range(9,15) else target;promotion_delta=(w[actor+8]-w[actor]) if not drop and u.endswith('+') else 0;expected=(0 if target==0 else w[target]+w[base])+promotion_delta;p.push(m);after=p.sfen();v0,_=features(before);v1,_=features(after);actual=(1 if side==0 else -1)*sum(w[i]*(v1[i]-v0[i]) for i in range(16));assert actual==expected,(u,actual,expected)
    if target!=0:rows.append(dict(arm=arm,family=group['family'],root_seed=group['root_seed'],info_index=li,PV_ply=ply,move=u,captured_type=target,captured_board_price=w[target],demoted_hand_price=w[base],first_move_promotion_delta=promotion_delta,actual_immediate_material_gain=actual,board_capture_component_underestimate=actual-w[target]))
out=dict(status='PASS_LITERAL_NATIVE_MATERIAL',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),captures=len(rows),nonzero_missing_hand_promotion_component=sum(x['board_capture_component_underestimate']!=0 for x in rows),range_missing_component=[min(x['board_capture_component_underestimate'] for x in rows),max(x['board_capture_component_underestimate'] for x in rows)],rows=rows,new_go=0,scope='ALLreturnedPV physicalcaptures from firstcoldquery of ALL16root/price groups/BOTHengines. Independentnativelegal push +literalboard/handweightedmaterial verifies immediatecapture+hand+promotion increment. RepeatedPVprefixes notindependent samples; sourcefutility captured-board term alone differs from actualincrement, but fixed/history margin/alpha/branch authority unobserved: NOactual harmfulpruning orlearningcause claim. No exchange all-defense solver orparameterfit.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='rows'})
