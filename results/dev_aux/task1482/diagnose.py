from pathlib import Path
import json,collections,chess
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1516';O.mkdir(exist_ok=False);sel=json.loads((R/'results/dev_aux/task1485/selection.json').read_bytes());dev=json.loads((R/'results/dev_aux/task1491/result.json').read_bytes());rows=[]
for group,trainid,devid in [('early',1474,1486),('late',1475,1487)]:
 xx=[json.loads(x) for x in (R/f'results/dev_aux/task{trainid}/games.jsonl').read_text().splitlines()];ss=next(x for x in sel['groups'][group]['rows'] if x['weight']=='1/2');fd={int(p):{int(s):F(v) for s,v in vv.items()} for p,vv in ss['family_scores'].items()};seeds=sorted(fd[720]);loo=[]
 for seed in seeds:
  score={p:sum(v for s,v in dd.items() if s!=seed)/15 for p,dd in fd.items()};p=min(p for p in score if score[p]==max(score.values()));loo.append({'held_family':seed,'selected':p,'held_gain':str(fd[p][seed]-fd[720][seed])})
 train_gain=F(ss['scores']['360'])-F(ss['scores']['720']);dev_gain=F(next(x['mean'] for x in dev['groups'][group]['rows'] if x['comparison'].startswith('primary') and x['weight']=='1/2'));mechanism=[]
 for phase,tid in [('TRAIN',trainid),('DEV',devid)]:
  gs=[json.loads(x) for x in (R/f'results/dev_aux/task{tid}/games.jsonl').read_text().splitlines()]
  for price in sorted({g['leafP'] for g in gs}):
   cc=collections.Counter();pp=collections.Counter();duration=[]
   for g in gs:
    if g['leafP']!=price:continue
    b=chess.Board(g['root']['fen8']);seenP=False
    for a in g['actions']:
     m=chess.Move.from_uci(a['move']);p=b.piece_at(m.from_square);cc['pawn_moves']+=p.piece_type==1;cc['captures']+=b.is_capture(m);cc['promotions']+=bool(m.promotion);cc['EP']+=b.is_en_passant(m)
     if m.promotion:seenP=True;pp['promotion_'+str(m.promotion)]+=1
     b.push(m)
    cc['games_with_promotion']+=seenP;cc['games']+=1;cc['terminal_games']+=g['label']!='C';cc['wins']+=g['label']=='W';cc['losses']+=g['label']=='L';duration.append(len(g['actions']))
   mechanism.append({'phase':phase,'price':price,'events':dict(cc),'promotion_types':dict(pp),'mean_plies':sum(duration)/len(duration)})
 rows.append({'group':group,'TRAIN_selected360_gain':str(train_gain),'DEV_selected360_gain':str(dev_gain),'TRAIN_minusDEV_optimism':str(train_gain-dev_gain),'leave_one_TRAIN_family_out_selector_counts':dict(collections.Counter(x['selected'] for x in loo)),'leave_one_TRAIN_family_out_average_gain':str(sum(F(x['held_gain']) for x in loo)/16),'loo_rows':loo,'mechanisms':mechanism,'scope':'Descriptive/exposed diagnosis, not new independent validation. Same target trueW-L,C unresolved; promotion totals do not identify causal reward effect.'})
(O/'result.json').write_text(json.dumps({'status':'PAWN_TRAIN_SELECTION_OPTIMISM_AND_MECHANISM_DIAGNOSIS','rows':rows,'new_go':0},indent=2));print([{k:v for k,v in x.items() if k not in ['loo_rows','mechanisms']} for x in rows]);print([(x['group'],x['mechanisms']) for x in rows])
