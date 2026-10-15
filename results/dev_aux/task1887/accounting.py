"""Paid outcome/role cancellation/proof-cost accounting, no new game."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time
OUT=Path('results/dev_aux/task1887')
def run():
 start=time.perf_counter();folder=Path('results/dev_aux/task1881');games=[json.loads(x) for x in (folder/'games.jsonl').read_text().splitlines()];moves=[json.loads(x) for x in (folder/'moves.jsonl').read_text().splitlines()];assert len(games)==192;index={(g['family'],g['candidate_side'],g['ratio']):g for g in games};by=defaultdict(list)
 for move in moves:by[move['slot']].append(move)
 phases={};proof=Counter();cost=defaultdict(Counter)
 for phase in ('TRAIN','DEV'):
  rows=[]
  for family in range(0,16) if phase=='TRAIN' else range(16,32):
   role_vectors=[[index[family,role,r]['finite_event_score'] for r in (.5,1.,2.)] for role in (0,1)]
   totals=[sum(v[i] for v in role_vectors) for i in range(3)]
   rows.append(dict(family=family,role_vectors=role_vectors,totals=totals,any_role_nonflat=any(len(set(v))>1 for v in role_vectors),net_nonflat=len(set(totals))>1))
  phases[phase]=dict(families=rows,any_role_nonflat=sum(r['any_role_nonflat'] for r in rows),net_nonflat=sum(r['net_nonflat'] for r in rows),role_effect_cancelled=sum(r['any_role_nonflat'] and not r['net_nonflat'] for r in rows))
 for g in games:
  ms=by[g['slot']];owners={m['side'] for m in ms if m['source']=='PROOF'}
  key=g['phase']+':'+g['outcome']
  proof[key+(':candidate_proof' if g['candidate_side'] in owners else ':opponent_proof' if owners else ':no_proof')]+=1
  for m in ms:
   cell=cost[key];cell['moves']+=1
   for field in ('proof_nodes','search_nodes','verification_nodes','proof_seconds','normal_seconds','verification_seconds','admission_seconds','fill_verification_nodes','fill_verification_seconds'):cell[field]+=m.get(field,0)
 out=dict(status='COMPLETE_PAID_ROLE_AND_PROOF_ACCOUNTING',phases=phases,proof_categories=dict(proof),cost_by_actual_outcome={k:dict(v) for k,v in cost.items()},seconds=time.perf_counter()-start,new_games=0,new_native_go=0,new_proof_calls=0,scope='Posthocmechanismaccounting on all frozen data, not new validation or selection. Anyrole effects and balancedfamily effects are separate. Proof adoption is actual verifiedphysical execution, not theoretical WIN reward; UNKNOWN stays censored.')
 with (OUT/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({**out,'phases':{k:{a:b for a,b in v.items() if a!='families'} for k,v in phases.items()},'cost_by_actual_outcome':'saved in result.json'}))
if __name__=='__main__':run()
