"""Exact complete syntactic/admissible inventory census coverage recheck."""
from pathlib import Path
from itertools import permutations
from collections import Counter
import hashlib,json
from scripts.generic_royal_actor import RoyalActor

def run():
 rows=[json.loads(x) for x in Path('results/dev_aux/task1895/states.jsonl').read_text().splitlines()];original=json.loads(Path('results/dev_aux/task1895/result.json').read_text());coverage=json.loads(Path('results/dev_aux/task1896/coverage.json').read_text());actor=RoyalActor(4);expected=set();syntactic=Counter()
 for mode in ('KK','KKN','KKR'):
  for squares in permutations(range(16),2 if mode=='KK' else 3):
   for owner in (range(1) if mode=='KK' else range(2)):
    for turn in (0,1):
     syntactic[mode]+=1;raw=['.']*16;raw[squares[0]]='K';raw[squares[1]]='k'
     if mode!='KK':raw[squares[2]]=mode[-1].lower() if owner else mode[-1]
     raw=tuple(raw)+(turn,)
     if actor.valid(raw):expected.add((mode,raw))
 actual={(r['inventory'],tuple(r['board'])) for r in rows};assert len(rows)==len(actual)==len(expected)==15240 and actual==expected
 digest=hashlib.sha256(b'\n'.join(json.dumps(r,separators=(',',':')).encode() for r in rows)+b'\n').hexdigest();assert digest==coverage['records_sha']==original['records_sha'];assert sum(len(r['actions']) for r in rows)==coverage['actual_legal_edges']==69360
 assert sum(syntactic.values())==coverage['correct_syntactic']==27360 and dict(syntactic)==coverage['syntactic_by_inventory'];wins=Counter()
 for r in rows:wins[r['inventory']]+=r['winner'] is not None
 assert wins['KK']==wins['KKN']==0 and wins['KKR']==80
 out=dict(status='PASS_EXACT_INPUTS_COUNTS_DIGEST_AND_TERMINALS',syntactic=27360,admissible=15240,edges=69360,winning_terminals=dict(wins),scope='No new Core/proof/Native calls; exact originalcensus typedrecord coverage and counts. Independentliteralactor defines admissibleinputset; originalcensus alreadychecked everyCorefrontier andedge.')
 with Path('results/dev_aux/task1896/recheck.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps(out))
if __name__=='__main__':run()
