from pathlib import Path
import json,sys,time,datetime,collections,hashlib
R=Path.cwd();P=R/".local_agent/matched-d2-20261016";O=R/".local_agent/playability-mu-20261016";sys.path[:0]=[str(R),str(O)]
import assessment as a
from generic_chess.learning.policy_v1 import action_v1_components
from scripts.research_record import record_value,write_record
p=a.p
def freeze():
 cases=[dict(seed=c["seed"],root=c["root"])for c in json.loads((P/"plan.json").read_bytes())["cases"]];cases.append(dict(seed="34101-causal-drop",root="first-action-cause/roots/34101.json"))
 write_record(P/"action-alias-plan.json",dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),question="Do existingV1base+typedcategories alias consequentiallegalactions on theactual9completeparents, or onlyredundantpatterns?",cases=cases,whole_seconds=120,expected_seconds=15,scope="Alllegalactionsperroot encoded; onlycollidinggroups requirefullCorechildcomparisons. Zero searches/games/training. Generated8familiesplusoneexistingstate, notaux/fullDSLcoverage. Partialcases/failuresretained. No modeldefault/newAPI." ))
def run():
 plan=json.loads((P/"action-alias-plan.json").read_bytes());start=time.perf_counter();rows=[]
 for case in plan["cases"]:
  p.stopped()
  if time.perf_counter()-start>=120:rows.append(dict(**case,kind="NOT_STARTED_UNKNOWN"));continue
  d,c,s,nr=a.load(P/case["root"]);legal=list(s.legal_actions());groups=collections.defaultdict(list)
  for ac in legal:
   if time.perf_counter()-start>=120:raise TimeoutError("Whole120scap duringencoding; rawpartialprocesskept")
   b,cat=action_v1_components(c,s.state.position,ac);groups[json.dumps([b.tolist(),list(cat)])].append(ac)
  coll=[]
  for key,acts in groups.items():
   if len(acts)<2:continue
   children=[]
   for ac in acts:
    child=p.apply_action(s.state,ac,c);children.append(dict(action=record_value(ac),child=record_value(child),child_sha256=hashlib.sha256(json.dumps(record_value(child),sort_keys=True).encode()).hexdigest()))
   coll.append(dict(feature=json.loads(key),actions=children,distinct_fullchildren=len({z["child_sha256"]for z in children})))
  row=dict(**case,kind="COMPLETE",legal_actions=len(legal),distinct_features=len(groups),colliding_groups=coll,consequential_groups=sum(x["distinct_fullchildren"]>1 for x in coll));rows.append(row);print("ALIAS_CENSUS",case["seed"],len(legal),len(groups),len(coll),row["consequential_groups"],flush=True)
 write_record(P/"action-alias-results.json",dict(complete=True,rows=rows,seconds=time.perf_counter()-start,queries=0,games=0,training=0,scope=plan["scope"]))
if __name__=="__main__":
 if sys.argv[-1]=="freeze":freeze()
 else:run()
