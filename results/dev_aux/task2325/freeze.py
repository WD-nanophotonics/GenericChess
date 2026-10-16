"""New budget-only LOW60 experiment, all32 predetermined intervention slots."""
from pathlib import Path
import json,hashlib,datetime
OUT=Path('results/dev_aux/task2325')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 old=Path('results/dev_aux/task2307');p=json.loads((old/'plan.json').read_text());assert (old/'completion.json').exists()and Path('results/dev_aux/task2308/result.json').exists()
 for name in('inputs.json','slots.json'):
  with(OUT/name).open('xb')as f:f.write((old/name).read_bytes())
 p['input']='results/dev_aux/task2325/inputs.json';p['input_sha']=sha(OUT/'inputs.json');p['slots_sha']=sha(OUT/'slots.json');p['candidate_proof_caller_seconds']=12.;p['candidate']['proof_seconds']=8.4;p['candidate']['verification_seconds']=3.;p['one_cap_seconds']=1200;p['estimated_seconds']=600
 p['scope']='NEW80singleaxisLOWproofbudget8to60, SAMEonceLOWtrigger/noHIGH,ALLsame32slots/8exposedfamilies/roles/prices, samefoe/normal/H. ReuseoldLOW8andMAT32 afterfullcompatibilityaudit. Frozen2700cap/forecast1500s UNDER2hours, no splittingcircumvention oroldcapextension. ActualW-L/U only, no teacherreward/skip/refit/DEV/default/PRIMARY. Postfreezeoldcontext13referenceWIN/oldactualDRAW motivates budgetquestion; ALLslotskept, notWINselectedrewardpanel. Measurementclockcuts explicit, notguaranteedpairedtrajectories.'
 p['scope']='NEW80exposedTRAINengineeringbudgetcurveLOW12afterLOW60restoresmissedroot15wins. Caller12/proof8.4/sharedverify3/normal1, sameonceLOWtrigger/ALL32slots/8families/roles/prices/foe/H. BudgetchosenfromexposedLOW60receiptcost, NOTnewholdout orindependentreplication/presetoptimum. Forecast600/original1200cap, nooldcapextension/pricefit/DEV/defaultchange. ComparecompleteactualW-L/U/costandearliestdivergence, notguaranteedwin/speedup or stablepricebenefit.'
 p['pins']={n:sha(n)for n in p['pins']if not n.startswith('results/dev_aux/task2307/')};p['pins']['results/dev_aux/task2325/pilot.py']=sha(OUT/'pilot.py');p['pins']['results/dev_aux/task2325/freeze.py']=sha(OUT/'freeze.py')
 with(OUT/'plan.json').open('x')as f:json.dump(p,f,indent=2)
 print(json.dumps(dict(expected=p['expected_games'],forecast=p['estimated_seconds'],singlecap=p['one_cap_seconds'],caller=p['candidate_proof_caller_seconds'])))
if __name__=='__main__':run()
