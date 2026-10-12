import sys,json,time,collections
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task388';O.mkdir(exist_ok=True);t0=time.monotonic();rows=[]
for task in [377,380]:
 for line,text in enumerate((R/f'results/dev_aux/task{task}/games.jsonl').read_text(encoding='utf-8').splitlines(),1):
  g=json.loads(text);w=g['weights'];color=g['color']
  for horizon in [12,24]:
   n=min(horizon,len(g['actions']));sfen=g['actions'][n-1]['after_sfen'] if n else g['root']['expected_sfen'];b=C.Board(sfen);score,owned=V.literal(sfen,w);quantity=owned[color]-owned[1-color];last=g['actions'][n-1] if n else None;recaps=[]
   if last and last['captured']:
    target=b.move_from_usi(last['move'])
    # Destination survives USI decode even when current side cannot execute last move.
    square=C.move_to(target)
    recaps=[C.move_to_usi(m) for m in b.legal_moves if C.move_to(m)==square]
   rows.append(dict(task=task,line=line,horizon=horizon,actual_plies=n,weights=w,seed=g['root']['seed'],color=color,quantity=quantity,material=(score if color==0 else -score),sfen=sfen,last_move=last['move'] if last else None,last_capture=last['captured'] if last else None,last_promotion=last['promotion'] if last else False,legal_immediate_recaptures=recaps,final_termination=g['termination'] if n==len(g['actions']) else None,scope='same frozen path prefix; legal recapture opportunity not profitability/all-defense certificate'))
summary=[]
for task in [377,380]:
 for h in [12,24]:
  rs=[r for r in rows if r['task']==task and r['horizon']==h];summary.append(dict(task=task,horizon=h,cells=len(rs),last_capture=sum(bool(r['last_capture']) for r in rs),last_capture_with_legal_recapture=sum(bool(r['legal_immediate_recaptures']) for r in rs),end_terminal=sum(r['final_termination'] is not None and r['final_termination']['winner'] is not None for r in rs),quantity_mean=str(sum(Fraction(r['quantity']) for r in rs)/len(rs))))
result=dict(rows=rows,summary=summary,seconds=time.monotonic()-t0,new_go=0,new_games=0,scope='H12/H24 descriptive only; no horizon/model reselect, no trajectory reuse for fitting');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='rows'}))