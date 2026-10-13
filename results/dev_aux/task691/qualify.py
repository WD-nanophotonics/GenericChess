import json,time,cshogi as C
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task691';start=time.perf_counter();prefix=json.loads((R/'results/dev_aux/task678/result.json').read_bytes())['prefixes'];lookup={(x['source_line'],x['cap']):x for x in prefix};rows=[];absorbing=0
HAND=[1,2,3,4,7,5,6]
def qty(b,c):
 counts=[0,0]
 for pc in b.pieces:
  if pc and pc%16!=8:counts[0 if pc<16 else 1]+=1
 for i,h in enumerate(b.pieces_in_hand):counts[i]+=sum(h)
 assert sum(counts)==38;return counts[c]-counts[1-c]
for i,t in enumerate((R/'results/dev_aux/task676/games.jsonl').open(encoding='utf-8'),1):
 g=json.loads(t);b=C.Board(g['root']['initial_sfen'])
 for u in g['root']['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 for a in g['actions'][:min(12,len(g['actions']))]:assert b.sfen()==a['before_sfen'];m=b.move_from_usi(a['move']);assert b.is_legal(m);b.push(m)
 q12=qty(b,g['color']);q24=g['raw_quantity'];assert q12==lookup[(i,12)]['quantity'] and q24==lookup[(i,24)]['quantity'];assert F(q12+q24,38)==(F(q12,19)+F(q24,19))/2
 if len(g['actions'])<=12:assert q12==q24;absorbing+=1
 rows.append(dict(source_line=i,quantity12=q12,quantity24=q24,mean_fitness=str(F(q12+q24,38))))
out=dict(status='ALL384_MULTI_HORIZON_FITNESS_PREFIX_PASS',rows=rows,actual_prior_paths=384,absorbing_terminal_before_or_at12=absorbing,new_go=0,seconds=time.perf_counter()-start,scope='Independentcshogi12prefixquantity against678independentPythonroot/history/terminal/quantity and677fullphysicalaudit. Literalmean quantity12/24 verified, terminalbefore12 absorbingfinalquantity notcontinued. This isonlygoalimplementationqualification onoldfrozenpaths, notnewfit/pricequality/holdout. No source-reference use.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out['status'],absorbing)
