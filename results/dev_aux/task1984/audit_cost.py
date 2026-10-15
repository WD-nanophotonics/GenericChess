"""All exposed-cost cases physical replay; compare frozen historical controls."""
from pathlib import Path
from collections import Counter
import json,hashlib
from results.dev_aux.task1969.physical_audit import audit,read,lines
OUT=Path('results/dev_aux/task1984')
def key(x):return x['family'],x['candidate_side'],x['R'],x['opponent_R']
def check(task,output,oldR):
 root=Path('results/dev_aux')/task;physical=audit(root);p=read(root/'run-plan.json');rows=lines(root/'games.jsonl');moves=lines(root/'moves.jsonl')
 assert physical['full_study_complete'] and all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 baseline={key(x):x for x in lines('results/dev_aux/task1968/games.jsonl') if x['candidate_proof'] and x['R']==oldR}
 old=[baseline[key(g)] for g in rows];assert len(old)==len(rows)
 # Physical paths, not material regrading or proof labels.
 transitions=Counter((a['outcome'],b['outcome']) for a,b in zip(old,rows))
 samepaths=sum(a['record']==b['record'] for a,b in zip(old,rows))
 actualcost=sum(x['seconds'] for x in rows);oldcost=sum(x['seconds'] for x in old)
 result=dict(status='PASS',physical=physical,actual_game_seconds=actualcost,old_game_seconds=oldcost,cost_ratio=actualcost/oldcost,identical_full_records=samepaths,total_games=len(rows),outcome_transitions={a+'->'+b:n for (a,b),n in transitions.items()},bank_hits=sum(m.get('bank_hit',False) for m in moves),filter_skips=sum(m.get('logical_reason')=='certified_inventory_no_win' or m['proof_reason']=='certified_inventory_no_win' for m in moves),source_unchanged=True,scope='EXPOSED fixedcases, old chronological recordedtiming reference; ordinary concurrent load allowed. Newresource/filter condition may change timed policy. Equality here is measured, not universal. No newpricelearning/DEVvalidation or unlimitedWDL.')
 with (OUT/output).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='physical'}))
def main():
 import sys
 OUT.mkdir(exist_ok=True)
 if sys.argv[1]=='probe':check('task1977','probe.json',720)
 else:check('task1983','filter.json',1440)
if __name__=='__main__':main()
