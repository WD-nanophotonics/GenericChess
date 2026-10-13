import json,hashlib,time,collections
from pathlib import Path
from fractions import Fraction as F
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task609';O.mkdir(exist_ok=True);start=time.perf_counter();r=json.loads((R/'results/dev_aux/task607/result.json').read_bytes());d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());rows=[];counts=collections.Counter();groups={}
for task,stage in [(597,'terminal_train'),(598,'mixed_train'),(599,'development')]:
 for line,text in enumerate((R/f'results/dev_aux/task{task}/games.jsonl').open(encoding='utf-8'),1):
  g=json.loads(text);w=g['weights'];color=g['color']
  for ply,a in enumerate(g['actions']):
   before=C.Board(a['before_sfen']);after=C.Board(a['after_sfen']);actor=a['actor'];m=before.move_from_usi(a['move']);assert before.is_legal(m);cap=before.piece(C.move_to(m));pt=before.piece(C.move_from(m))%16 if not C.move_is_drop(m) else 0;ct=cap%16 if cap else 0;base=ct-8 if 9<=ct<=14 else ct;board_projection=w[ct] if ct else 0;hand_capture=(w[ct]+w[base]) if ct else 0;promotion=(w[pt+8]-w[pt]) if a['promotion'] else 0;gain=hand_capture+promotion
   def material(b):
    v=sum((1 if pc<16 else -1)*w[pc%16] for pc in b.pieces if pc)
    for owner,hand in enumerate(b.pieces_in_hand):
     for t,n in zip([1,2,3,4,7,5,6],hand):v+=(1 if owner==0 else -1)*w[t]*n
    return v
   actual=(material(after)-material(before))*(1 if actor==0 else -1);assert actual==gain
   if not ct and not a['promotion']:continue
   role='candidate' if actor==color else 'random';row=dict(stage=stage,source=dict(file=f'results/dev_aux/task{task}/games.jsonl',line=line,ply=ply),family=g['root']['source_family'],root=g['root']['index'],color=color,role=role,captured_type=ct,moving_type=pt,promotion=a['promotion'],gives_check=after.is_check(),board_only_projection=board_projection,actual_immediate_material_gain=actual,omitted_hand_and_promotion=actual-board_projection);rows.append(row);counts[stage+':events']+=1;counts[stage+':candidate' if role=='candidate' else stage+':random']+=1;key=(stage,role,ct);x=groups.setdefault(key,dict(events=0,under_projection=0,over_projection=0,equal_projection=0,checks=0,delta_min=10**9,delta_max=-10**9));x['events']+=1;x['under_projection']+=actual>board_projection;x['over_projection']+=actual<board_projection;x['equal_projection']+=actual==board_projection;x['checks']+=after.is_check();x['delta_min']=min(x['delta_min'],actual-board_projection);x['delta_max']=max(x['delta_max'],actual-board_projection)
out=dict(status='PASS_ALL_ACTUAL_IMMEDIATE_GAINS',all_saved_actions=102939,events=len(rows),counts=dict(counts),groups=[dict(stage=s,role=r,captured_type=t,**x) for (s,r,t),x in groups.items()],rows=rows,new_go=0,seconds=time.perf_counter()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task607/result.json').read_bytes()).hexdigest(),scope='ALLactualphysicalactions exactShogi hand+board+promotion immediateleafmaterialdelta, notexchangevalue/forcedgain or proofprunedcapturedmoves. Baselinecapturefutility usesboardPieceValue, plusotherhistory/depth/static terms; projectedgap alone doesNOTassertsearchbias/cutoffunsafety/generalbestrepair. Negativepromotiongain retained. No source/humanpricefitting orselectedaxis.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],events=len(rows),counts=out['counts'],seconds=out['seconds'],new_go=0)))