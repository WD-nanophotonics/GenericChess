import json,hashlib
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task382';O.mkdir(exist_ok=True);families={};total=0
for task in [370,373]:
 for line_no,line in enumerate((R/'results/dev_aux'/f'task{task}'/'games.jsonl').read_text(encoding='utf-8').splitlines(),1):
  g=json.loads(line)
  if g['termination']['kind']!='checkmate':continue
  h=g['root']['history']+[a['move'] for a in g['actions']];b=C.Board(g['root']['initial_sfen'])
  for u in h:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
  assert b.is_check() and not list(b.legal_moves);family='curated_seed_family0' if task==373 else 'standard_prefix_'+str(g['root']['seed']);entry={'family':family,'source_file':f'results/dev_aux/task{task}/games.jsonl','source_line':line_no,'initial_sfen':g['root']['initial_sfen'],'history':h,'mate_sfen':b.sfen(),'generator_prices':g['weights'],'winner':g['termination']['winner']};families.setdefault(family,[]).append(entry);total+=1
selected=[];roots=[]
for family,gs in sorted(families.items()):
 seed=min(gs,key=lambda x:tuple(x['history']));selected.append(seed)
 for distance in [2,6,10]:
  if len(seed['history'])<distance:continue
  h=seed['history'][:-distance];b=C.Board(seed['initial_sfen'])
  for u in h:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
  assert list(b.legal_moves);roots.append({'phase':'exposed_seed_diagnostic','family':family,'distance':distance,'initial_sfen':seed['initial_sfen'],'history':h,'expected_sfen':b.sfen(),'seed_source':{'file':seed['source_file'],'line':seed['source_line']}})
d={'status':'PREPARED_NOT_EXECUTED','source_true_mates':total,'families':len(families),'selected_seeds':selected,'roots':roots,'selection':'allactualcheckmatefamilies from370/373; firstlexicographiccompletehistory perfamily; ALL2/6/10 legalrollback. No arbitraryreverseboard, price/human/resultmagnitude selection','next_action':'qualifyallknowninitial/endpointprices BOTHcolors,cold1024/cap24 fixedunit; no training/reselection orhumanfit; unknowntrue-enddensity andwhether near allsolved M1 removes price discrimination','question':'Do independent sourcefamilies andlegalrollback distance change meaningfultrue-win signal percost versus onecuratedfamily andordinary40plyprefix?','scope':'Allsources alreadyexposed, diagnosticnotindependentvalidation. Entirefamily remainsonegroup; sourceconditioningon generatorprices recorded. Curated initialunknown pre-SFENhistory exclusion persists. Distance isheuristic notall-defense matecertificate.'};(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print('PREPARED',total,len(families),len(roots))