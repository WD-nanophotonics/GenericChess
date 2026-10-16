"""Zero-new-search audit of treatment reaching shared candidate decisions."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time
OUT=Path('results/dev_aux/task2178')
def run():
 start=time.perf_counter();root=Path('results/dev_aux/task2167');games=list(map(json.loads,(root/'games.jsonl').read_text(encoding='utf-8').splitlines()));ds=defaultdict(list)
 for r in map(json.loads,(root/'decisions.jsonl').read_text(encoding='utf-8').splitlines()):ds[r['physical_id']].append(r)
 audit=json.loads(Path('results/dev_aux/task2173/result.json').read_text(encoding='utf-8'));rows=[];counts=Counter()
 def cell(d,g):
  n=d['normal_receipt'];return dict(price=g['ratio'],requested_depth=g['candidate_depth'],physical_id=g['physical_id'],source=d['source'],retained_depth=None if n is None else n['completed_depth'],choice=d['choice'],normal_exit=None if n is None else n['exit_cause'],proof_reason=d['proof_reason'])
 for family in range(32):
  for foe in(.5,2.):
   for role in(0,1):
    group=[g for g in games if(g['family'],g['opponent_ratio'],g['candidate_side'])==(family,foe,role)];assert len(group)==4;seq=[ds[g['physical_id']]for g in group];common=[];firstcand=None;firstdiv=None
    for steps in zip(*seq):
     if len({d['root_state_sha']for d in steps})!=1 or len({json.dumps(d['root_record'],sort_keys=True)for d in steps})!=1:break
     values=[cell(d,g)for d,g in zip(steps,group)];candidate=steps[0]['is_candidate'];identical=len({json.dumps(d['choice'],sort_keys=True)for d in steps})==1
     row=dict(ply=steps[0]['ply'],is_candidate=candidate,root_state_sha=steps[0]['root_state_sha'],cells=values,all_choices_same=identical)
     if candidate:
      common.append(row)
      if firstcand is None:firstcand=row
     if not identical:firstdiv=row;break
    counts['groups']+=1;counts['firstcandidate_in_commonprefix']+=firstcand is not None
    if firstcand:
     counts['firstcandidate_four_choices_identical']+=firstcand['all_choices_same'];counts['firstcandidate_allnormal']+=all(c['source']in('MATERIAL_SEARCH','FULL_SESSION_MATERIAL_SEARCH')for c in firstcand['cells']);counts['firstcandidate_anyproof']+=any(c['source']in('PROOF','PROOF_CONTINUATION')for c in firstcand['cells']);counts['firstcandidate_anyfallback']+=any(c['source']=='PRECOMPUTED_LEGAL_FALLBACK'for c in firstcand['cells'])
     for c in firstcand['cells']:counts['first_depth_'+str(c['requested_depth'])+'_retained_'+str(c['retained_depth'])]+=1
    counts['fourcell_firstdivergence_candidate']+=firstdiv is not None and firstdiv['is_candidate'];counts['fourcell_firstdivergence_foe']+=firstdiv is not None and not firstdiv['is_candidate'];counts['no_divergence_in_fourcell_sharedprefix']+=firstdiv is None
    rows.append(dict(family=family,foe=foe,role=role,first_candidate=firstcand,common_candidate_decisions=common,first_divergence=firstdiv,outcomes=[dict(price=g['ratio'],depth=g['candidate_depth'],score=g['score'],outcome=g['outcome'])for g in group]))
 out=dict(status='PASS_ALL128_FOURCELL_GROUPS_ALL32_FAMILIES',groups=len(rows),counts=dict(counts),rows=rows,family_interactions=audit['family_effects'],new_search_or_game_or_teacher=0,seconds=time.perf_counter()-start,scope='All32families retained; no conditioning causal-effect estimate on posttreatment completion/actionchange. Commonprefix requires exactfullrecord andstateSHA. Fourcell paths afterfirstdivergence notsamecontext; reportedasdifferent, not aligned byply. Positionalteacher notqueried.');(OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items()if k not in('rows','family_interactions')}),flush=True)
if __name__=='__main__':run()
