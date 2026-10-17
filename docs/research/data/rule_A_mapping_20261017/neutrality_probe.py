from pathlib import Path
import json,sys,time,dataclasses
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.ai.evaluation.analyzer import build_movement_capability
from generic_chess.ai.evaluation.profile import _raw_capability_score
from generic_chess.ai.evaluation.config import EvaluationConfig
D=R/'.local_agent/rule-aware-map-20261017';write_json(D/'next-neutrality-plan.json',dict(question='Is the raw-capability ratio neutral when a finiteboard ray can have only one step, before calling that a safe equivalent-rule mapping?',changed_premise='NewactualA-onlyrawcapabilitymapping has15strictdecisionsandone finitepositiveutilitystratum. Needneutralityofitsactualfeatureinput, not a new formal/provergate.',immediate='Source-only numericfixturecheck on4x4: ray(max1) versusleap andunlimitedlongraysthatfitonlyonestep; compareallnumericcapabilityfields/rawscore, notsyntaxsignature. Thenoneexistinglegacyrule/fullstate action/effect/history check beforeclaimingsemanticequivalence.',limits='4numericpairs/<10seconds, no gameplay/training/AUXwrites.',done='Difference => diagnose semanticversusheuristiccontractbeforedeclaringbug/adoptingmapping. Equality => onlyscopedfeatureevidence, noall-domainproof. No newpolicy/default/automaticfitness.'))
inputs=[((RayAtom((0,1),max_steps=1),),(LeapAtom((0,1)),)),((RayAtom((-1,2)),RayAtom((1,2))),(LeapAtom((-1,2)),LeapAtom((1,2)))),((RayAtom((-3,1)),RayAtom((3,1))),(LeapAtom((-3,1)),LeapAtom((3,1)))),((RayAtom((-2,1)),RayAtom((2,1))),(LeapAtom((-2,1)),LeapAtom((2,1))))]
rows=[];start=time.perf_counter()
for rays,leaps in inputs:
 a=build_movement_capability(4,rays,EvaluationConfig());b=build_movement_capability(4,leaps,EvaluationConfig());aa=dataclasses.asdict(a);bb=dataclasses.asdict(b);diff={k:[aa[k],bb[k]]for k in aa if k!='movement_signature'and aa[k]!=bb[k]};ra=_raw_capability_score(a,EvaluationConfig());rb=_raw_capability_score(b,EvaluationConfig());rows.append(dict(rays=[repr(x)for x in rays],leaps=[repr(x)for x in leaps],numeric_differences=diff,ray_raw=ra,leap_raw=rb,ratio=ra/rb if rb else None))
write_json(D/'next-neutrality-observation.json',dict(status='FOUR_SCOPED_NUMERIC_PAIRS_EXECUTED_RULE_EQUIVALENCE_NOT_YET_CHECKED',rows=rows,seconds=time.perf_counter()-start,scope='Actualrawfeatureconsumernumerics only; movement_signature intentionallysyntactic. No rule/action/historyequivalence or bugclaim yet, no modeladjustment/fitness/newframework.'))
print('NEXT begun: numericpairdifferences',[(len(r['numeric_differences']),r['ratio'])for r in rows])
