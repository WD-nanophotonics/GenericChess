"""Saved-state material clamp audit, no internal-tree claims."""
import json,hashlib,math,time
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task194';P=R/'results/dev_aux/task187';C=json.loads((P/'controller.json').read_bytes());assert C['completed'];limit=32000-2*246-1;rows=[];maximum=0;observed=0;clipped=0;promotions=0
for c in C['calls']:
 r=c['result'];w=c['weights'];b=chess.Board(r['root_fen'])
 for m in r['opening_history']:b.push_uci(m)
 vals=[];gross=[]
 for ix in range(len(r['actions'])+1):
  val=sum(w[k]*(len(b.pieces(i+1,True))-len(b.pieces(i+1,False))) for i,k in enumerate('PNBRQ'));vals.append(val);gross.append([sum(w[k]*len(b.pieces(i+1,col)) for i,k in enumerate('PNBRQ')) for col in (True,False)]);observed+=1;maximum=max(maximum,abs(val));clipped+=abs(val)>limit
  if ix<len(r['actions']):m=chess.Move.from_uci(r['actions'][ix]);promotions+=bool(m.promotion);b.push(m)
 rows.append(dict(name=c['context']['name'],absolute_max_observed_material=max(map(abs,vals)),clipped_observed=sum(abs(v)>limit for v in vals),max_gross_material=max(max(v) for v in gross),promotion_anywhere_bound=15*max(w[k] for k in 'PNBRQ'),bound_exceeds_clip=15*max(w[k] for k in 'PNBRQ')>limit))
out=dict(complete=True,actual_clip_limit=limit,MAX_PLY=246,VALUE_MATE=32000,observed_boards=observed,observed_clipped_boards=clipped,maximum_observed_abs_material=maximum,played_promotions=promotions,rows=rows,source_controller_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),scope='Everypostrootrecordedboard/currentprice checked. Initialtheoreticalall15promotedactorsworstcase bound isloose; internal/qsearchstatesunobserved. Evalclamp protectsmatepriority, mayflattenhighmaterial. No engine/product changes/reruns.')
(O/'analysis.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('rows',)},indent=2))
