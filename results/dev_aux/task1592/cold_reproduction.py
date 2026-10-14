from pathlib import Path
import json,collections,re
R=Path.cwd();O=R/'results/dev_aux/task1598';O.mkdir(exist_ok=False);old={};new={};count=collections.Counter();diff=[]
for line in (R/'results/dev_aux/task1550/choices.jsonl').open():
 x=json.loads(line)
 if x['node_budget']==64:old[x['leafR'],x['state_id']]=x
for line in (R/'results/dev_aux/task1576/new_choices.jsonl').open():
 x=json.loads(line);key=x['leafR'],x['state_id']
 if key in old:new[key]=x
assert len(old)==len(new)==512
for k,a in old.items():
 b=new[k];assert [a[x] for x in ['move','child_id','position','command']]==[b[x] for x in ['move','child_id','position','command']]
 def normalize(lines):return [re.sub(r' time \d+',' time VARIABLE',re.sub(r' nps \d+',' nps VARIABLE',l)) for l in lines]
 assert normalize(a['uci_info'])==normalize(b['uci_info']);count['actual_cold_query_replayed_matches']+=1
out={'status':'PASS_512_SAMEBUDGET_SAMEPRICE_ACTUAL_COLD_ROOT_REPRODUCTIONS','counts':dict(count),'new_go':0,'scope':'48task1550 versus49task1576 existingactualqueries; compare chosenaction,child,input,command,depth/PV/score/nodes modulo time/nps. Ordinaryconcurrencytimingnotexclusive, no extra rerun; supportsdeterministiccold policy only.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
