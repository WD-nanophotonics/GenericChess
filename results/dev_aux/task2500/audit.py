"""Actual new-family replication replay and paired censored envelopes."""
from pathlib import Path
from collections import Counter
import json,random,chess
OUT=Path('results/dev_aux/task2500')
def run():
 rows=[json.loads(x)for x in(OUT/'games.jsonl').read_text().splitlines()];done=json.loads((OUT/'result.json').read_text());assert len(rows)==done['expected']==done['actual'];groups={};moves=0
 for g in rows:
  b=chess.Board(g['record']['initial'])
  for u in g['record']['moves']:
   m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);moves+=1
  assert b.fen()==g['record']['fen'];o=b.outcome(claim_draw=True);value=None if o is None else 0 if o.winner is None else 1 if o.winner else-1
  assert g['reward']==(None if value is None else value*(1 if g['color']==0 else-1));key=(g['seed'],g['method'],g['prefix_seed'],g['color']);groups.setdefault(key,{})[g['treatment']]=g
 summaries=[];contrasts=[]
 for key,pair in groups.items():
  assert set(pair)=={'initial','learned'};a,b=pair['initial'],pair['learned'];assert a['initial_record']==b['initial_record'];av,bv=a['reward'],b['reward'];al,au=(-1,1)if av is None else(av,av);bl,bu=(-1,1)if bv is None else(bv,bv)
  contrasts.append(dict(seed=key[0],family=key[2],color=key[3],lower=bl-au,upper=bu-al,difference=None if av is None or bv is None else bv-av,identical_record=a['record']==b['record']))
 for seed in sorted({x['seed']for x in contrasts}):
  rr=[x for x in contrasts if x['seed']==seed];families=sorted({x['family']for x in rr});blocks=[(sum(r['lower']for r in rr if r['family']==f)/2,sum(r['upper']for r in rr if r['family']==f)/2)for f in families];rng=random.Random(2500);boots=[]
  for _ in range(10000):
   sample=[rng.choice(blocks)for _ in blocks];boots.append((sum(x[0]for x in sample)/len(sample),sum(x[1]for x in sample)/len(sample)))
  summaries.append(dict(seed=seed,families=len(blocks),paired_games=len(rr),mean_reward_gain_bounds=[sum(r['lower']for r in rr)/len(rr),sum(r['upper']for r in rr)/len(rr)],family_bootstrap_descriptive_envelope=[sorted(x[0]for x in boots)[249],sorted(x[1]for x in boots)[9749]],identical_full_records=sum(r['identical_record']for r in rr),family_blocks=blocks))
 result=dict(status='PASS_ALL_NEW8_FAMILY_ACTUAL_REPLAY',games=len(rows),legal_plies=moves,contrasts=contrasts,summaries=summaries,scope='All2frozenlearned seeds retained, NEW8legalprefixfamilies/fixeduniformfoe. Lower/upper censored per-pair outcome bounds; bootstrap envelope descriptive8family resampling, NOT proof of robust/universal improvement. Twoinitializations reuse samefamilies, not16 independentfamilies. No holdout refit/selection.')
 (OUT/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='contrasts'}))
if __name__=='__main__':run()
