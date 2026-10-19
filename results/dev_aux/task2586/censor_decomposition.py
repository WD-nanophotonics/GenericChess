"""Full 512-pair 100k/400k terminal-status decomposition (Dot reply 1792402091.889509).
Existing records only; denominator fixed at all registered pairs; one-sided known outcomes kept."""
from pathlib import Path
import json,collections
E=Path('results/dev_aux/task2586/eval')
def run(a='Fixed@400k',b='Fixed@100k',threshold=.0625):
 rows={tuple(g['slot']):g for g in map(json.loads,(E/'eval-games.jsonl').open())};pairs=collections.defaultdict(dict)
 for s,g in rows.items():pairs[(s[0],s[1],s[2],s[3],s[5])][s[4]]=g
 cat=collections.Counter();known=collections.Counter();lo=collections.Counter();hi=collections.Counter();endings=collections.Counter()
 for k,v in pairs.items():
  x,y=v[a],v[b];c=('T'if x['reward']is not None else'U')+('T'if y['reward']is not None else'U');cat[c]+=1
  xs=(x['reward'],x['reward'])if x['reward']is not None else(-1,1);ys=(y['reward'],y['reward'])if y['reward']is not None else(-1,1)
  if c=='TT':known[c]+=x['reward']-y['reward']
  lo[c]+=xs[0]-ys[1];hi[c]+=xs[1]-ys[0]
  for m,g in((a,x),(b,y)):
   if g['reward']is None:endings[m+':'+g['ending']]+=1
 n=len(pairs);L=sum(lo.values());H=sum(hi.values())
 out=dict(status='COMPLETE_EXISTING_RECORDS',contrast=f'{a} - {b}',denominator=n,categories=dict(cat),known_TT_sum=known['TT'],per_category_bounds={c:[lo[c],hi[c]]for c in cat},total_bounds=[L/n,H/n],unknown_causes=dict(endings),
  decision_rule=f'Prefer {a} over the 4x cheaper {b} only if the full paired gain >= {threshold}. Threshold fixed here before any new evaluation.',
  threshold_reachable=H/n>=threshold,required_unresolved_contribution=threshold*n-known['TT'],max_unresolved_contribution=sum(hi[c] for c in cat if c!='TT'),
  scope='Descriptive existing-record decomposition; both-terminal subset is outcome-selected and only describes itself. No new games.')
 (E/'censor-decomposition.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=1))
if __name__=='__main__':run()
