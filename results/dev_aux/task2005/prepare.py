"""Instantiate predeclared continuation cells only after parent completes."""
from pathlib import Path
import json,hashlib,copy
OUT=Path('results/dev_aux/task2005');PARENT=Path('results/dev_aux/task1997')
def run():
 assert json.loads((PARENT/'campaign-completion.json').read_text())['status']=='COMPLETE'
 freeze=json.loads((OUT/'freeze.json').read_text());p=json.loads((PARENT/'run-plan.json').read_text());full=json.loads((PARENT/'FULL-lock-before-dev.json').read_text());prices=sorted({720,full['selected_R']})
 parent=[json.loads(x)for x in (PARENT/'games.jsonl').read_text().splitlines()];slots=[]
 for g in parent:
  if g['phase']!='DEV' or g['R']not in prices:continue
  slot={k:g[k]for k in ('family','candidate_side','R','N','ratio','scale','opponent_nodes','candidate_proof','candidate_cached','candidate_proof_nodes','opponent_R')};slot.update(slot=len(slots),parent_slot=g['slot'],phase='CONDITIONAL_H48');slots.append(slot)
 assert len(slots)==16*4*2*len(prices)<=256
 p.update(status='INSTANTIATED_FROM_PREDECLARED_H48_PROTOCOL',slots=slots,expected_games=len(slots),maximum_games=256,H=48,seconds_cap=1200,expected_seconds=freeze['cost']['expected_seconds'],parent_games=(PARENT/'games.jsonl').as_posix(),parent_moves=(PARENT/'moves.jsonl').as_posix(),selector='ALLfixed16DEVfamilies/fourfoes/bothroles/UNIT+TRAINonlyFULL; inheritactualterminalparents, continueALLUNKNOWN undernewH48policy; no prioranchor or outcome-selected subset.',scope=freeze['done'],conditional_continuation=True)
 p.update(prices=prices,train_games=0,parent_train_games=832,max_moves=256*88,new_perft_commands=0,reused_qualification_perfts=624,budget_declaration='NEWone1200s conditionalH48continuationclock, expected758s, original3300sparentcomplete/unchanged. Notoldcapextension/independentDEV.',cost_decision=freeze['cost'],tail='H48 newproofthrough47, thenverifiedrank<=64tail; actualmaxply96. Allterminalparentsinherited; UNKNOWNdistinct.')
 p['native_plan']['max_go']=256*88;p['native_plan']['seconds_cap']=1200
 p['source_sha']={k:v for k,v in p['source_sha'].items() if 'test_schedule.py'not in k}
 for f in ('results/dev_aux/task2005/freeze.json','results/dev_aux/task2005/continue.py','results/dev_aux/task2005/prepare.py','results/dev_aux/task1997/games.jsonl','results/dev_aux/task1997/moves.jsonl','results/dev_aux/task1997/FULL-lock-before-dev.json'):
  p['source_sha'][f]=hashlib.sha256(Path(f).read_bytes()).hexdigest()
 with (OUT/'run-plan.json').open('x')as f:json.dump(p,f,indent=2)
 print(json.dumps(dict(parent_cases=len(slots),prices=prices,continue_unknown=sum(parent[s['parent_slot']]['outcome']=='UNKNOWN'for s in slots),expected_seconds=p['expected_seconds'],one_cap_seconds=1200)))
if __name__=='__main__':run()
