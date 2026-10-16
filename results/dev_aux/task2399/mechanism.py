from pathlib import Path
from collections import defaultdict,Counter
import json,time
OUT=Path('results/dev_aux/task2399')
def run():
 tick=time.perf_counter();f=Path('results/dev_aux/task2385');rec=Path('results/dev_aux/task2394');assert(rec/'completion.json').exists();roots={r['index']:r for r in json.loads((f/'inputs.json').read_text())};slots=json.loads((f/'slots.json').read_text());games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())};by=defaultdict(list)
 for d in map(json.loads,(f/'decisions.jsonl').read_text().splitlines()):by[d['slot']].append(d)
 mapping={}
 for g in map(json.loads,(rec/'games.jsonl').read_text().splitlines()):mapping[g['slot']]=g['original_slot'];games[g['original_slot']]=dict(g,slot=g['original_slot'])
 for d in map(json.loads,(rec/'decisions.jsonl').read_text().splitlines()):
  if d['slot']in mapping:by[mapping[d['slot']]].append(d)
 rows=[];identical=0;incomplete=0;summary=Counter()
 for variant in('REMOVAL_NO_DROPS','HAND_NO_DROPS','HAND_WITH_DROPS'):
  for family in range(8):
   for role in(0,1):
    ss=[next(s for s in slots if roots[s['root']]['variant']==variant and roots[s['root']]['family']==family and s['candidate_color']==role and s['ratio']==price)for price in(1.,1.5)];pair=[games.get(s['slot'])for s in ss]
    if any(g is None or g['reward']is None for g in pair):incomplete+=1;continue
    a,b=pair;aa=a['record']['actions'];bb=b['record']['actions'];prefix=len(roots[a['root']]['record']['actions']);difference=next((i for i,(x,y)in enumerate(zip(aa,bb))if x!=y),None)
    if difference is None:assert aa==bb and a['reward']==b['reward'];identical+=1;continue
    ply=difference-prefix;d,e=[next(d for d in by[g['slot']]if d['ply']==ply)for g in pair];assert d['root_record']==e['root_record']and d['root_state_sha']==e['root_state_sha'];assert d['is_candidate']==e['is_candidate'];normal=all(x['source']=='FULL_SESSION_MATERIAL_SEARCH'and x['normal_receipt']is not None and x['normal_receipt']['completed_depth']==3 for x in(d,e));kind='CANDIDATE_FULL_D3'if normal and d['is_candidate']else'FOE_FIRST'if not d['is_candidate']else'OTHER_SOURCE_OR_PARTIAL';summary[(variant,kind)]+=1;rows.append(dict(variant=variant,family=family,role=role,first_difference_ply=ply,kind=kind,sources=[x['source']for x in(d,e)],normal_depths=[None if x['normal_receipt']is None else x['normal_receipt']['completed_depth']for x in(d,e)],proof_reasons=[x['proof_reason']for x in(d,e)],actual_rewards=[a['reward'],b['reward']],actual_gain=b['reward']-a['reward']))
 result=dict(status='PASS_FIRST_DIVERGENCE_SOURCE_ACCOUNTING_NO_FIT',complete_pairs=48-incomplete,incomplete_pairs=incomplete,identical_full_records=identical,first_differences=rows,summary=[dict(variant=v,kind=k,count=n)for(v,k),n in summary.items()],seconds=time.perf_counter()-tick,scope='Allcompleteactualpairs underfrozen1vs1.5; no outcomefilter/refit/newsearch. Firstdivergencewithsamefullrecord/state distinguishesownfullD3fromfoe-first/proof/partialtiming. Doesnotproveunboundedvalue/causalmediation/stableprice; missingpairnotdraw. Protocolstrata handledseparately2388.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
