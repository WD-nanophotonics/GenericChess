"""All shared-case transition accounting; exact common-policy symmetry control."""
from pathlib import Path
from collections import Counter
import json
OUT=Path('results/dev_aux/task1995')
def run():
 def lines(p):return[json.loads(x) for x in Path(p).read_text().splitlines()]
 def key(g):return g['family'],g['candidate_side'],g['R'],g['opponent_R']
 old={key(g):g for g in lines('results/dev_aux/task1987/games.jsonl')};new={key(g):g for g in lines('results/dev_aux/task1994/games.jsonl')}
 panels=[]
 for r in (720,1260):
  keys=[k for k in new if k[2]==r];trans=Counter((old[k]['outcome'],new[k]['outcome']) for k in keys)
  panels.append(dict(R=r,cases=len(keys),transitions={a+'->'+b:n for (a,b),n in trans.items()},identical_full_records=sum(old[k]['record']==new[k]['record'] for k in keys)))
 symmetry=[]
 for f in range(32):
  a=new[f,0,720,720];b=new[f,1,720,720]
  symmetry.append(dict(family=f,same_full_record=a['record']==b['record'],role_score_sum=a['finite_event_score']+b['finite_event_score']))
 result=dict(status='PASS_ALL_CASE_ACCOUNTING',by_price=panels,UNITvsUNIT_commonpolicy_control=dict(families=32,identical_full_records=sum(x['same_full_record'] for x in symmetry),nonzero_role_sums=sum(x['role_score_sum']!=0 for x in symmetry),per_family=symmetry),scope='Shared alreadyfrozen cases, no extraGame/Core/PN/Native calls or rejectedcases. EqualUNIT actors have identical requestedpolicy; retain any realclock/pathvariation. CrossconditionchangesopponentPN+cache, notisolatedPNcause, and is notnewtraining replication.')
 with (OUT/'mechanism.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='UNITvsUNIT_commonpolicy_control'}|{'symmetry_summary':{k:v for k,v in result['UNITvsUNIT_commonpolicy_control'].items() if k!='per_family'}}))
if __name__=='__main__':run()
