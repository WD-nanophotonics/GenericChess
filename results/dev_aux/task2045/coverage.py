"""Independent exhaustive input coverage and inventory closure of new KRNB census."""
from pathlib import Path
from itertools import permutations
from collections import Counter
import json,hashlib
from scripts.generic_royal_actor import RoyalActor
OUT=Path('results/dev_aux/task2045');C=Path('results/dev_aux/task2044')
def main():
 plan=json.loads((C/'plan.json').read_text());original=json.loads((C/'result.json').read_text());raw=(C/'states.jsonl').read_bytes();rows=[json.loads(x) for x in raw.splitlines()];actor=RoyalActor(4);expected=set();syntactic=Counter()
 for mode in plan['inventories']:
  for squares in permutations(range(16),2 if mode=='KK' else 3):
   for owner in (range(1)if mode=='KK'else range(2)):
    for turn in (0,1):
     syntactic[mode]+=1;board=['.']*16;board[squares[0]]='K';board[squares[1]]='k'
     if mode!='KK':board[squares[2]]=mode[-1].lower()if owner else mode[-1]
     state=tuple(board)+(turn,)
     if actor.valid(state):expected.add((mode,state))
 actual={(r['inventory'],tuple(r['board']))for r in rows};assert len(rows)==len(actual)==len(expected) and actual==expected
 wins=Counter();edges=0
 for r in rows:
  mode=r['inventory'];state=tuple(r['board']);children=dict(actor.moves(state));assert sorted(children)==r['actions'];wins[mode]+=r['winner']is not None
  for child in children.values():
   material=[x.upper()for x in child[:-1]if x not in ('.','K','k')];nextmode='KK'+''.join(sorted(material));assert(nextmode,child)in expected;edges+=1
 assert sum(syntactic.values())==plan['syntactic_positions']==40800 and edges==original['actual_legal_edges']==104128 and wins['KKR']==80
 assert wins['KK']==wins['KKN']==wins['KKB']==0 and original['status']=='COMPLETE'and original['complete_inventory_and_all_edges']
 digest=hashlib.sha256(b'\n'.join(raw.splitlines())+b'\n').hexdigest();assert digest==original['records_sha']
 result=dict(status='PASS_COMPLETE_INPUT_COVERAGE_AND_ORIGINAL_CORE_EDGE_CENSUS',correct_syntactic=sum(syntactic.values()),syntactic_by_inventory=dict(syntactic),admissible_by_inventory=dict(Counter(r['inventory']for r in rows)),actual_legal_edges=edges,winning_terminals=dict(wins),records_sha=digest,no_win_inventories=['KK','KKN','KKB'],scope='Fresh actual KRNB4 Core census, complete literal-input coverage and every edge inventory closure independently checked. No old4KRN transfer, no6board evidence, no reward/game/policy change.')
 (OUT/'coverage.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
