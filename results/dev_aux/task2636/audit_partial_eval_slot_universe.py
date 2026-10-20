from __future__ import annotations
import hashlib,json,random
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
PLAN=ROOT/'results/dev_aux/task2636/one-init-study-plan.json'
OUT=ROOT/'results/dev_aux/task2636/partial-eval-slot-universe-audit.json'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def main()->dict:
 plan=json.loads(PLAN.read_text(encoding='utf8')); lineage=plan['source_lineage']
 pool_path=ROOT/lineage['root_pool']; audit_path=ROOT/lineage['root_audit']
 if sha(pool_path)!=lineage['root_pool_sha256'] or sha(audit_path)!=lineage['root_audit_sha256']:
  raise ValueError('frozen root pool/audit hash mismatch')
 pool=json.loads(pool_path.read_text(encoding='utf8'))
 if pool.get('root_pool_registered') or pool.get('learner_or_search_started'):
  raise ValueError('slot-universe audit requires unregistered/unexecuted pool')
 ev=plan['evaluation']; roots=pool['evaluation_roots']; candidate_count=plan['training']['arms']
 endpoints=tuple(ev['endpoints']); colors=tuple(ev['learner_colors']); per_candidate=ev['roots_per_rule']
 if len(endpoints)!=2 or len(colors)!=2:raise ValueError('expected two endpoints and two learner colors')
 assignment=ev['node_cap_assignment']
 if '20000' not in assignment or '40000' not in assignment or 'first eight' not in assignment or 'remaining eight' not in assignment:raise ValueError('frozen paired cap assignment differs from expected 8/8 split')
 seed_by_candidate={}
 rows_by_candidate={}
 for row in roots:
  c=row['candidate_index']; seed=row['candidate_seed']
  if c in seed_by_candidate and seed_by_candidate[c]!=seed:raise ValueError('candidate seed changed within roots')
  seed_by_candidate[c]=seed; rows_by_candidate.setdefault(c,[]).append(row)
 if set(rows_by_candidate)!=set(range(candidate_count)):raise ValueError('evaluation candidate universe mismatch')
 all_slots=set(); all_pairs=set(); cap_counts={}
 for c in range(candidate_count):
  rows=rows_by_candidate[c]
  if len(rows)!=per_candidate:raise ValueError(f'candidate {c} root count mismatch')
  families=[r['family'] for r in rows]
  if len(set(families))!=per_candidate:raise ValueError(f'candidate {c} duplicate family')
  seed=seed_by_candidate[c]
  shuffled=families.copy();random.Random(977422+seed).shuffle(shuffled)
  cap_by_family={family:(20000 if j<8 else 40000) for j,family in enumerate(shuffled)}
  cap_counts[str(c)]={'candidate_seed':seed,'20000':sum(v==20000 for v in cap_by_family.values()),'40000':sum(v==40000 for v in cap_by_family.values())}
  for family in families:
   for color in colors:
    pair=(c,family,color);all_pairs.add(pair)
    for endpoint in endpoints:
     slot=(c,family,color,endpoint);all_slots.add(slot)
     # Same cap is identified by candidate family, independent of endpoint/color.
     assert cap_by_family[family] in (20000,40000)
 if len(all_slots)!=ev['slots'] or len(all_pairs)!=ev['paired_root_color_contrasts']:
  raise ValueError(f'planned universe mismatch: {len(all_slots)} slots, {len(all_pairs)} pairs')
 if len(all_pairs)*len(endpoints)!=len(all_slots):raise ValueError('pair-to-slot mapping is not bijective')
 result={'status':'PASS_FROZEN_EVALUATION_SLOT_UNIVERSE','plan_sha256':sha(PLAN),'auditor_sha256':sha(Path(__file__)),'root_pool_sha256':sha(pool_path),'root_audit_sha256':sha(audit_path),'candidate_count':candidate_count,'roots_per_candidate':per_candidate,'candidate_seed_by_index':{str(k):seed_by_candidate[k] for k in sorted(seed_by_candidate)},'endpoints':list(endpoints),'learner_colors':list(colors),'slots':len(all_slots),'pairs':len(all_pairs),'cap_counts_by_candidate':cap_counts,'cap_assignment_shared_across_endpoints_and_colors':True,'outcomes_or_search_values_read':False,'registration_or_evaluation_started':False,'scope':'Frozen planned key universe only; no result rows, outcome labels, learner or search execution.'}
 OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf8');return result
if __name__=='__main__':print(json.dumps(main(),indent=2,sort_keys=True))
