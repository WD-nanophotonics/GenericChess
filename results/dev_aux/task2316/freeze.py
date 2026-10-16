"""New budget-only TWO8 experiment, all32 predetermined intervention slots."""
from pathlib import Path
import json,hashlib,datetime
OUT=Path('results/dev_aux/task2316')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 old=Path('results/dev_aux/task2307');p=json.loads((old/'plan.json').read_text());assert (old/'completion.json').exists()and Path('results/dev_aux/task2308/result.json').exists()
 for name in('inputs.json','slots.json'):
  with(OUT/name).open('xb')as f:f.write((old/name).read_bytes())
 if True:
  slots=json.loads((OUT/'slots.json').read_text())
  for x in slots:x['arm']='TWO_REGIME_INCREMENTAL'
  (OUT/'slots.json').write_text(json.dumps(slots,indent=2))
 p['input']='results/dev_aux/task2316/inputs.json';p['input_sha']=sha(OUT/'inputs.json');p['slots_sha']=sha(OUT/'slots.json');p['candidate_proof_caller_seconds']=8.;p['candidate']['proof_seconds']=5.6;p['candidate']['verification_seconds']=2.;p['one_cap_seconds']=1200;p['estimated_seconds']=600
 p['scope']='NEW80factorialcompletionHIGHplusLOW8versusLOW8, SAMEonceLOWtrigger/noHIGH,ALLsame32slots/8exposedfamilies/roles/prices, samefoe/normal/H. ReuseoldLOW8andMAT32 afterfullcompatibilityaudit. Frozen2700cap/forecast1500s UNDER2hours, no splittingcircumvention oroldcapextension. ActualW-L/U only, no teacherreward/skip/refit/DEV/default/PRIMARY. Postfreezeoldcontext13referenceWIN/oldactualDRAW motivates budgetquestion; ALLslotskept, notWINselectedrewardpanel. Measurementclockcuts explicit, notguaranteedpairedtrajectories.'
 p['scope']='NEW80predeclared2x2completion:LOW8/LOW60/TWO8/TWO60, onlyNEWtwo32slotarms, oldLOW8/TWO60reused aftercontractaudit. TWO8changesHIGHtrigger versusoldLOW8withSAME8budget; LOW60versusoldTWO60isolatestriggerat60. FreezeBEFORE2313outcomes; nofit/rootselection/DEV/default/newworker. Original1200cap forecast600s, no oldcapextension/2hreviewcircumvention. ActualW-L/U/cost, family8scopedinteractionnotstablepriceclaim.'
 p['pins']={n:sha(n)for n in p['pins']if not n.startswith('results/dev_aux/task2307/')};p['pins']['results/dev_aux/task2316/pilot.py']=sha(OUT/'pilot.py');p['pins']['results/dev_aux/task2316/freeze.py']=sha(OUT/'freeze.py')
 with(OUT/'plan.json').open('x')as f:json.dump(p,f,indent=2)
 print(json.dumps(dict(expected=p['expected_games'],forecast=p['estimated_seconds'],singlecap=p['one_cap_seconds'],caller=p['candidate_proof_caller_seconds'])))
if __name__=='__main__':run()
