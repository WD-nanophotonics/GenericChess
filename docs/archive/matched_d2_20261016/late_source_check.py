from pathlib import Path
import json,sys,hashlib,subprocess
B=Path(sys.argv[1]).resolve();D=Path(sys.argv[2]).resolve()
prefix=(B/"consumer.py").read_text().split("start=time.perf_counter()",1)[0];exec(compile(prefix,str(B/"consumer.py"),"exec"),globals())
d=json.loads((D/"action-representation.json").read_bytes());s,nr=root(read("first-action-cause/roots/34101.json"));ts=tuple(sorted(s.compiled.support.type_metadata));ix={v:i for i,v in enumerate(ts)}
for row in d["rows"]:
 ac=action(row["action"]);assert ac in s.legal_actions();packed=pack_semantic_action(nr,s.state.position,ac)
 assert int(packed)==row["native_packed"]and record_value(sem.public_action(nr,packed))==row["action"]
 cats=[ix[ac.base_type_id],len(ts),ix[ac.base_type_id],2];assert cats==row["v1_categories"]
assert d["same_destination"]and d["packed_distinct"]and d["v1_category_distinct"]
r=subprocess.run([sys.executable,"-S",str(D/"unknown_sensitivity.py"),str(B)],capture_output=True,timeout=60);assert r.returncode==0,(r.stdout,r.stderr)
actual=json.loads((B/"unknown-sensitivity.json").read_bytes());reference=json.loads((D/"unknown-sensitivity.json").read_bytes());assert actual["panels"]==reference["panels"]
out=dict(complete=True,normal_native_source_package_origins_asserted=True,action_native_identity_and_categorical_binding=True,action_v0_float_original_execution_not_independently_recomputed=True,unknown_sensitivity_all_fields_equal_except_computation_clock=True,extra_searches=0,extra_games=0,source_hashes={f:hashlib.sha256((D/f).read_bytes()).hexdigest()for f in["unknown_sensitivity.py","unknown-sensitivity.json","action_representation.py","action-representation.json"]},scope="Actualpostsealed-sourcedirectorylateanalysisverification; no whole6consumerrepeat/no newstudyquery/proof, nolearning ortransferclaim.")
(D/"late-analysis-replay.json").write_bytes((json.dumps(out,indent=2)+"\n").encode());print("LATE_ANALYSIS_SOURCE_PASS",flush=True)
