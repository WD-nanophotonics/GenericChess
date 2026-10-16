from pathlib import Path
import json,hashlib
OUT=Path('results/dev_aux/task2331')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 source=Path('results/dev_aux/task2330');data=json.loads((source/'inputs.json').read_text());result=json.loads((source/'result.json').read_text());assert result['status']=='FROZEN_PRICE_UNQUERIED_PREFIX_MU'and len(data['roots'])==16
 roots=[]
 for r in data['roots']:
  roots.append(dict(index=r['family'],rules=r['rules'],record=r['record'],state_sha=r['state_sha'],group=r['group'],canonical_reference_label=r['target_label'],order_sha=r['order_sha'],original_split='NEW_VALIDATION_PRICE_UNQUERIED'))
 with(OUT/'inputs.json').open('x')as f:json.dump(roots,f,indent=2)
 slots=[]
 for root in range(16):
  for opponent in range(2):
   for color in(0,1):
    prices=(1.,2.)if(root+opponent+color)%2==0 else(2.,1.)
    for ratio in prices:slots.append(dict(slot=len(slots),root=root,opponent=opponent,candidate_color=color,ratio=ratio,arm='LOW_ONLY_INCREMENTAL'))
 with(OUT/'slots.json').open('x')as f:json.dump(slots,f,indent=2)
 p=json.loads(Path('results/dev_aux/task2325/plan.json').read_text());p.update(input=str(OUT/'inputs.json'),input_sha=sha(OUT/'inputs.json'),slots_sha=sha(OUT/'slots.json'),expected_games=128,one_cap_seconds=3300,estimated_seconds=2300)
 p['opponents']=[dict(p['opponents'][0],ratio=x)for x in(1.5,4.)]
 p['selection']='ALL16new2330familyorbits x2fixedfoeprices1.5/4 x2candidatecolors x2candidateprices1/2; adjacentpricepairs paritybalancedbeforeANYfitness. ActualW-L+1/-1/0only; U/None and missing preserved; nofit/DEVadaptation/rootchange. Canonicalreference isselectiondescriptoronly; notonlineguide/reward.'
 p['scope']='NEW81price-unqueriedfamilyvalidation ofalreadyfixed1/2andLOW12. SAMEcandidateproof/normal/H, fixedfoeconfigurationwithinpricepair. 16familyclusters,128gamesnotindependentfamilies. CanonicalmuWIN/DRAWexposedlabels andcompleteoldreferenceprepayment explicit; notunseenrule/WDLholdout. Foe1.5/4notnewtoallproject(oldtableguideusedthem), newtogenericLOW12panel. Forecast2300s/original3300cap<2h, nooldcapextension/splitting/worker/default/PRIMARY/UI/humanfit.'
 p['pins']={}
 for name in('results/dev_aux/task2331/pilot.py','results/dev_aux/task2331/freeze.py','results/dev_aux/task2330/distribution.py','results/dev_aux/task2330/inputs.json','results/dev_aux/task2330/plan.json','results/dev_aux/task2210/player.py','results/dev_aux/task2273/incremental_adapted.py','generic_chess/core/semantic_executor.py','generic_chess/session/session.py'):
  p['pins'][name]=sha(name)
 with(OUT/'plan.json').open('x')as f:json.dump(p,f,indent=2)
 print(json.dumps(dict(expected=128,forecasts=2300,onecap=3300,price_queries=0,roots=16)))
if __name__=='__main__':run()
