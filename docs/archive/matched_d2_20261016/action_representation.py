from pathlib import Path
import sys,json
R=Path.cwd();P=R/".local_agent/matched-d2-20261016";O=R/".local_agent/playability-mu-20261016";sys.path[:0]=[str(R),str(O)]
import assessment as a
from generic_chess.learning.policy import semantic_action_features
from generic_chess.learning.policy_v1 import action_v1_components
from generic_chess.native.mirror import pack_semantic_action
from scripts.research_record import record_value
d,c,s,nr=a.load(P/"first-action-cause/roots/34101.json");plan=json.loads((P/"first-action-cause/plan.json").read_bytes());rows=[]
for label,ad in plan["cases"][0]["forced_actions"].items():
 ac=next(x for x in s.legal_actions()if record_value(x)==ad);v=semantic_action_features(c,s.state.position,ac);base,cat=action_v1_components(c,s.state.position,ac);raw=pack_semantic_action(nr,s.state.position,ac)
 assert record_value(a.p.sem.public_action(nr,raw))==ad
 rows.append(dict(local_label=label,action=ad,native_packed=int(raw),v0_features=v.tolist(),v1_base=base.tolist(),v1_categories=list(cat)))
out=dict(complete=True,rows=rows,same_destination=rows[0]["action"]["to_square"]==rows[1]["action"]["to_square"],packed_distinct=rows[0]["native_packed"]!=rows[1]["native_packed"],v0_features_distinct=rows[0]["v0_features"]!=rows[1]["v0_features"],v1_category_distinct=rows[0]["v1_categories"]!=rows[1]["v1_categories"],queries=0,games=0,training=0,scope="Actual2legalP/Xdropcurrentpolicyfeature/Nativeidentitycontrol, no modelinference/quality/transfer/all-domainclaim. Samefrom/toalonewouldalias, existingidentity/v1categoriesdoNOT. Reuseexistinginterfaces, no newpolicyheadframework.")
(P/"action-representation.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print(out)
