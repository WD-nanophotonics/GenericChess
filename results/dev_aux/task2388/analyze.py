from pathlib import Path
from collections import Counter,defaultdict
import json,time,hashlib
import numpy as np
OUT=Path('results/dev_aux/task2388')
def run():
 tick=time.perf_counter();base=Path('results/dev_aux/task2385');recovery=Path('results/dev_aux/task2394');assert(recovery/'completion.json').exists();p=json.loads((base/'plan.json').read_text());slots=json.loads((base/'slots.json').read_text());roots={r['index']:r for r in json.loads(Path(p['input']).read_text())};old=list(map(json.loads,(base/'games.jsonl').read_text().splitlines()));new=list(map(json.loads,(recovery/'games.jsonl').read_text().splitlines()));games={g['slot']:dict(g,protocol='OLD_FILEIO')for g in old}
 for g in new:
  original=g['original_slot'];assert original>=20 and original not in games;assert all(g[k]==slots[original][k]for k in('root','ratio','opponent','candidate_color','arm'));games[original]=dict(g,slot=original,protocol='NEW_SHAREDREAD')
 failure=json.loads((base/'failure.json').read_text());assert failure['partial']['slot']['slot']==19 and failure['partial_reward']is None;assert 19 not in games
 rng=np.random.default_rng(830088);panels=[];delta_by={}
 for variant in p['variants']:
  byprice={};familybounds=[];same=0;pairprotocols=[]
  for price in(1.,1.5):
   selected=[s for s in slots if roots[s['root']]['variant']==variant and s['ratio']==price];counts=Counter('U'if s['slot']not in games else games[s['slot']]['outcome']for s in selected);byprice[str(price)]={x:counts[x]for x in'WLDU'}
  for family in range(8):
   lower=upper=0.
   for color in(0,1):
    pair=[];protocol=[]
    for price in(1.,1.5):
     slot=next(s for s in slots if roots[s['root']]['variant']==variant and roots[s['root']]['family']==family and s['candidate_color']==color and s['ratio']==price);g=games.get(slot['slot']);pair.append(g);protocol.append(None if g is None else g['protocol'])
    b,l=pair;lb,ub=(-1.,1.)if b is None or b['reward']is None else(b['reward'],b['reward']);ll,ul=(-1.,1.)if l is None or l['reward']is None else(l['reward'],l['reward']);lower+=ll-ub;upper+=ul-lb
    if b is not None and l is not None:same+=b['record']==l['record']
    pairprotocols.append(dict(family=family,color=color,protocol=protocol,complete_actual_pair=all(g is not None and g['reward']is not None for g in pair)))
   familybounds.append((lower/2,upper/2))
  arr=np.array(familybounds,dtype=float);indices=rng.integers(0,8,size=(10000,8));lo=arr[:,0][indices].mean(axis=1);hi=arr[:,1][indices].mean(axis=1);delta_by[variant]=arr;panels.append(dict(variant=variant,by_price=byprice,paired_slots=16,family_bounds=familybounds,empirical_gain_bounds=[float(arr[:,0].mean()),float(arr[:,1].mean())],descriptive_family_bootstrap_envelope=[float(np.quantile(lo,.025)),float(np.quantile(hi,.975))],identical_returned_record_pairs=same,pair_protocols=pairprotocols))
 interactions=[]
 for variant in p['variants'][1:]:
  a=delta_by[variant];b=delta_by[p['variants'][0]];low=a[:,0]-b[:,1];high=a[:,1]-b[:,0];interactions.append(dict(variant_vs_removal=variant,all8_price_gain_interaction_bounds=[float(low.mean()),float(high.mean())],protocol_homogeneous_families=[0,2,3,4,5,6,7],homogeneous_price_gain_interaction_bounds=[float(low[[0,2,3,4,5,6,7]].mean()),float(high[[0,2,3,4,5,6,7]].mean())],scope='Family1excludedfromhomogeneousprotocolcontrastbecauseknowninterruption/readertypeboundary, NOToutcomeselection. All8boundskept. No inferentialcausality/populationclaim.'))
 returned=list(games.values());result=dict(status='CLOSED_FIXED_PRICE_MECHANISM_RESPONSE_WITH_CENSORING_AND_PROTOCOL_STRATA',original_returned=len(old),recovery_returned=len(new),actual_terminal=sum(g['reward']is not None for g in returned),returned_UNKNOWN=sum(g['reward']is None for g in returned),unreturned=96-len(returned),old_interrupted_UNKNOWN=1,known_old_unknown_prefix_plies=2,actual_returned_moves=sum(g['plies']for g in returned),all_committed_moves=sum(g['plies']for g in returned)+2,panels=panels,interactions=interactions,seconds=time.perf_counter()-tick,scope='No price fit/selection;1vspriorfrozen1.5 across3rulevariants/8exposedTRAINfamilies/roles/foe2. Partialprotocoldata: original19beforestopIOerror +boundedsharedreaderonlyunstarted underSAMEabsoluteoriginaldeadline; nevercompleteoldslot19/relabelU. Allplanned96includedinbounds, missing[-1,1] andpaired[-2,2], notdraw. Bootstrapdescriptive8familyclusters, no independent-gamecount. HAND_NO_DROPSisadversarialdormant-handcreditcontrol: currentcallbackgivesuselessnondeployablehandpiecesnonzeroweight, NOTvalidatedgenericpriceaxiom. Conditionalrulemechanismexploration, notcleanconfirmatorysingleprotocolmatrix/newinitialholdout/old82replication; nohumanfit/default/PRIMARYadoption.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k not in('panels','interactions')}));print(json.dumps([dict(variant=r['variant'],by_price=r['by_price'],bounds=r['empirical_gain_bounds'])for r in panels]))
if __name__=='__main__':run()
