from pathlib import Path
import json,collections,cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task945';O.mkdir(exist_ok=False);rows=[]
for n in [923,929,938]:
 counts=collections.Counter();examples=[]
 for line in (R/f'results/dev_aux/task{n}/games.jsonl').open():
  g=json.loads(line)
  if g['root']['variant']!='edge8':continue
  counts['games']+=1
  for a in g['actions']:
   if a['promotion']:counts['actual_promotions']+=1;counts['actual_'+str(a['moving']).lower()+'_promotion']+=1
  for q in g['queries']:
   if q['player']!='candidate':continue
   counts['candidate_queries']+=1;b=C.Board(q['initial_sfen'])
   for u in q['history']:b.push_usi(u)
   counts['root_has_horse']+=any(pc and pc%16==13 for pc in b.pieces);counts['root_has_promoted_knight']+=any(pc and pc%16==11 for pc in b.pieces);lines=[l for l in q['lines'] if ' pv ' in l]
   if not lines:continue
   horse=any(pc and pc%16==13 for pc in b.pieces);promN=any(pc and pc%16==11 for pc in b.pieces)
   for u in lines[-1].split(' pv ',1)[1].split():
    b.push_usi(u);horse|=any(pc and pc%16==13 for pc in b.pieces);promN|=any(pc and pc%16==11 for pc in b.pieces)
   counts['printed_final_PV_horse_exposure']+=horse;counts['printed_final_PV_promN_exposure']+=promN
   if horse and len(examples)<3:examples.append(dict(seed=g['root']['seed'],profile=g.get('profile'),history=q['history'],pv=lines[-1]))
 rows.append(dict(task=n,counts=dict(counts),examples=examples));print(n,dict(counts))
(O/'result.json').write_text(json.dumps(dict(status='QUALIFIED_ZERO_GO_PROMOTION_EXPOSURE_REVIEW',rows=rows,new_go=0,scope='ValidstockedgeNBG only; positiveactualroot/printedPVexposure confirmsB/Horse family andpromN coupling. AbsenceinprintedPVdoesnotproveabsenceinsearchtree; PVnotexactscoreleafgradient. No baseB-onlyclaim.'),indent=2))
