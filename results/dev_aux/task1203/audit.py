
from pathlib import Path
import json,collections,chess
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1204';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task1203/plan.json').read_bytes());out=[];exceptions=[]
for source in D['sources']:
 gs=[json.loads(s) for s in (R/f'results/dev_aux/task{source}/games.jsonl').read_text().splitlines()]
 for arm in ['J','L']:
  key=lambda g:(g['root']['seed'],g['color'],g['opponent'])
  baseline={key(g):g for g in gs if g['arm']==arm and g['price']==720}
  for price in D['pairs']:
   ss=[g for g in gs if g['arm']==arm and g['price']==price];rows=[];counts=collections.Counter()
   for g in ss:
    b=baseline[key(g)];pairs=list(zip(g['actions'],b['actions']));offset=next((i for i,(a,c) in enumerate(pairs) if a['move']!=c['move']),None)
    if offset is None:
     assert len(g['actions'])==len(b['actions']) and g['label']==b['label'] and g['final_fen']==b['final_fen'];counts['same_whole_trajectory']+=1;continue
    a=g['actions'][offset];c=b['actions'][offset];assert a['before']==c['before'] and a['actor']==c['actor'];assert a['actor']==g['color'],'Opponentfirst divergence suggestsleak'
    board=chess.Board(a['before'])
    desc=[]
    for act in [c,a]:
     m=chess.Move.from_uci(act['move']);victim=board.piece_at(m.to_square);actor=board.piece_at(m.from_square);v=board.copy(stack=True);v.push(m);desc.append(dict(move=act['move'],actor=actor.symbol(),victim=victim.symbol() if victim else None,check=v.is_check(),mate=v.is_checkmate()))
    dy=F((g['label']=='W')-(g['label']=='L')-(b['label']=='W')+(b['label']=='L'))
    counts['candidate_first_divergence']+=1;counts['first_divergence_atroot']+=offset==0;counts['finite_improved']+=dy>0;counts['finite_worse']+=dy<0;counts['finite_same']+=dy==0;counts['capturechoice']+=bool(desc[0]['victim'] or desc[1]['victim']);counts['quietquiet']+=not(desc[0]['victim'] or desc[1]['victim'])
    rows.append(dict(seed=g['root']['seed'],color=g['color'],opponent=g['opponent'],ply=offset,fen=a['before'],baseline=desc[0],candidate=desc[1],baseline_label=b['label'],candidate_label=g['label'],finite_delta=str(dy)))
   out.append(dict(source=source,arm=arm,price=price,cases=len(ss),counts=dict(counts),rows=rows))
(O/'result.json').write_text(json.dumps(dict(status='PASS_ALL_FIRST_DIVERGENCES_ARE_CANDIDATE',groups=out,new_go=0,scope=D['scope']),indent=2))
for v in out:print(v['source'],v['arm'],v['price'],v['counts'])
