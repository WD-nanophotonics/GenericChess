"""Frozen three-price actual-TRAIN selector; never reads validation outcomes."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time,hashlib
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2342')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 stop=EvidenceStopReader(Path.cwd());stop();f=Path('results/dev_aux/task2340');read=lambda p:json.loads(Path(p).read_text());p=read(f/'plan.json');audit=read('results/dev_aux/task2343/task2340-audit.json');assert audit['status']=='PASS_FULL_ACTUAL_RECORDS_PHASES_CERTIFICATES_SINGLEAXIS_CONTRACT';games=list(map(json.loads,(f/'games.jsonl').read_text().splitlines()));done=read(f/'completion.json');assert len(games)==done['games']==audit['games'];by=defaultdict(list)
 for g in games:by[g['ratio']].append(g)
 complete=len(games)==96 and all(g['reward']is not None for g in games);scores={str(x):None if not complete else sum(g['reward']for g in by[x])/32 for x in(1.,1.5,3.)};selected=None
 if complete:
  assert all(len(by[x])==32 for x in(1.,1.5,3.));best=max(scores.values());selected=1. if best<=scores['1.0'] else min(x for x in(1.5,3.)if scores[str(x)]==best)
 validation_needed=selected is not None and selected!=1.;reserve_sha=sha('results/dev_aux/task2341/inputs.json');assert reserve_sha==p['pins']['results/dev_aux/task2341/inputs.json']
 result=dict(status='TRAIN_SELECTION_COMPLETE'if complete else'NO_SELECTION_INCOMPLETE_TRAIN',candidate_grid=[1.,1.5,3.],objective='MeanactualterminalWminusLoverALL8oldTRAINfamilies/twofixedfoes/bothroles',scores=scores,outcomes={str(x):dict(Counter(g['outcome']for g in by[x]))for x in(1.,1.5,3.)},selected_price=selected,strict_improvement_accepted=validation_needed,validation_needed=validation_needed,train_games=len(games),actual_terminals=sum(g['reward']is not None for g in games),UNKNOWN=sum(g['reward']is None for g in games),never_executed=96-len(games),train_input_sha=sha(p['input']),train_record_sha=sha(f/'games.jsonl'),reserved_validation_input_sha=reserve_sha,scope='ActualgenericLOW12policy-matchedsmallgridTRAINfit; oldexposedTRAINonly, no83/81validationoutcomesreadbylearner. ThreepricesfrompriorordinalcellsnotnewDEVoptimization/humanfit; no unique/universalmetricclaim. U/missingrequiresNOSELECTION, neverzero. Strictgainoverbaseline1required,tieprefersbaseline1thenlowerprice. Reserve16neworbits BEFOREfit; no identicalpolicyvalidationifnoacceptedupdate. No default/UI/PRIMARYadoption.')
 with(OUT/'selection.json').open('x')as f:json.dump(result,f,indent=2)
 if validation_needed:
  future=dict(status='RESERVED_NOT_EXECUTED',question='DoesTRAIN-selectedprice improveactualW-L ontheprefitreserved16familyorbits/foes1.5and4 withSAMELOW12?',candidate_price=selected,baseline_price=1.,source_train_selection_sha=sha(OUT/'selection.json'),reserved_inputs='results/dev_aux/task2341/inputs.json',reserved_inputs_sha=reserve_sha,families=16,roles=[0,1],foe_prices=[1.5,4.],planned_games=128,estimated_seconds=2300,original_cap_seconds=3300,scope='Price-unqueriedconditionalfamilyvalidation, notnewrule/WDLholdout. No fit/newpricechoice/replacementoradaptationfrom81validation. Freezeactualplayer/resources/source beforefutureexecution; thisreservationdoesnotstartanexperimentclock.')
  with(OUT/'reserved-validation.json').open('x')as f:json.dump(future,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
