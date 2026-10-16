from pathlib import Path
import json,hashlib
OUT=Path('results/dev_aux/task2340')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 assert json.loads(Path('results/dev_aux/task2341/result.json').read_text())['status']=='FROZEN_PRICE_UNQUERIED_PREFIX_MU'
 old=Path('results/dev_aux/task2325');roots=json.loads((old/'inputs.json').read_text());assert len(roots)==8 and all(r['original_split']=='TRAIN'for r in roots)
 with(OUT/'inputs.json').open('x')as f:json.dump(roots,f,indent=2)
 slots=[]
 for root in sorted(r['index']for r in roots):
  for opponent in range(2):
   for color in(0,1):
    prices=[1.,1.5,3.];shift=(root+opponent+color)%3;prices=prices[shift:]+prices[:shift]
    for ratio in prices:slots.append(dict(slot=len(slots),root=root,opponent=opponent,candidate_color=color,ratio=ratio,arm='LOW_ONLY_INCREMENTAL'))
 assert len(slots)==96
 with(OUT/'slots.json').open('x')as f:json.dump(slots,f,indent=2)
 p=json.loads(Path('results/dev_aux/task2325/plan.json').read_text());p.update(input=str(OUT/'inputs.json'),input_sha=sha(OUT/'inputs.json'),slots_sha=sha(OUT/'slots.json'),expected_games=96,one_cap_seconds=2100,estimated_seconds=1500)
 p['opponents']=[dict(p['opponents'][0],ratio=x)for x in(.5,2.)]
 p['selection']='ALL8OLDexposedTRAINfamiliesfrom2325/2307, prices1/1.5/3fromPRIOR79ordercells (baseline1andopenintervalrepresentatives), fixedfoe.5/2,bothroles, Latinrotatedpriceorder. Objective actualmeanWminusL; chooseonlystrictimprovementover1, equalbestpreferslowestprice. No use of81validationoutcomestoselectprice/grid/roots; no humanfit.'
 p['scope']='NEW81small3candidateTRAINoptimizationunderSAMEgenericLOW12completepolicy, notoldprepaidACTIONguide. SourceTRAINoldexposed/fixed8, notnewholdout. NEW2341reserve16orbitscreatedBEFOREfit/no validationpricequeries. Gridfromoldstructuralpartition, notnewDEVperformance; no claimedunique/globalratio. Forecast1500/original2100cap<2h; onlylaunchiforiginalcap+safeclosingworkfitsremainingsegment. U/missingcannotbezero; selectorrequiresALL96actualterminals, otherwisenoacceptedselection. No newworkers/default/UI/PRIMARY/oldcapchange.'
 names=['results/dev_aux/task2340/pilot.py','results/dev_aux/task2340/freeze.py','results/dev_aux/task2341/inputs.json','results/dev_aux/task2341/plan.json','results/dev_aux/task2334/deferred.json','results/dev_aux/task2342/select.py','results/dev_aux/task2342/selection-contract.json','results/dev_aux/task2210/player.py','results/dev_aux/task2273/incremental_adapted.py','generic_chess/core/semantic_executor.py','generic_chess/session/session.py'];p['pins']={n:sha(n)for n in names}
 with(OUT/'plan.json').open('x')as f:json.dump(p,f,indent=2)
 print(json.dumps(dict(expected=96,forecast=1500,onecap=2100,trainfamilies=8,reserved_validation=16,fitness_queries=0)))
if __name__=='__main__':run()
