"""Closed fixed-foe policy mechanisms; theta-blind proof noise is not price causality."""
from pathlib import Path
from collections import defaultdict,Counter
import json
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path("results/dev_aux/task2301")
def run():
 stop=EvidenceStopReader(Path.cwd());folder=Path("results/dev_aux/task2289");p=json.loads((folder/"plan.json").read_text());roots={r["index"]:r for r in json.loads(Path(p["input"]).read_text())};games=[json.loads(x)for x in(folder/"games.jsonl").read_text().splitlines()];ds=[json.loads(x)for x in(folder/"decisions.jsonl").read_text().splitlines()];moves=defaultdict(list)
 for d in ds:moves[d["slot"]].append(d)
 idx={(g["root"],g["arm"],g["ratio"],g["candidate_color"]):g for g in games};exposure=[];pairs=[]
 for g in games:
  own=[d for d in moves[g["slot"]]if d["is_candidate"]];proofs=[d for d in own if d["source"]in("VERIFIED_GRAPH_STRATEGY","VERIFIED_FULL_HISTORY_STRATEGY")];first=proofs[0]["ply"]if proofs else None
  exposure.append(dict(slot=g["slot"],root=g["root"],arm=g["arm"],ratio=g["ratio"],candidate_color=g["candidate_color"],actual_outcome=g["outcome"],new_attempts=sum(d["new_proof_attempt"]for d in own),verified_new_proofs=len(proofs),ordinary_before_firstproof=sum(d["source"]=="FULL_SESSION_MATERIAL_SEARCH"and(first is None or d["ply"]<first)for d in own),ordinary_total=sum(d["source"]=="FULL_SESSION_MATERIAL_SEARCH"for d in own),proof_before_any_material=bool(proofs)and not any(d["source"]=="FULL_SESSION_MATERIAL_SEARCH"and d["ply"]<first for d in own),candidate_measured_seconds=sum(d["measured_seconds"]for d in own),foe_measured_seconds=sum(d["measured_seconds"]for d in moves[g["slot"]]if not d["is_candidate"])))
 for root,r in roots.items():
  for arm in("MATERIAL_ONLY","TWO_REGIME_INCREMENTAL"):
   for role in(0,1):
    stop();a=idx.get((root,arm,1.,role));b=idx.get((root,arm,2.,role));row=dict(root=root,arm=arm,role=role,status="UNKNOWN_MISSING_OR_UNFINISHED")
    if a is not None and b is not None and a["reward"]is not None and b["reward"]is not None:
     la=deserialize_game_record(json.dumps(a["record"])).actions;ra=deserialize_game_record(json.dumps(b["record"])).actions;n=0
     while n<min(len(la),len(ra))and la[n]==ra[n]:n+=1
     row.update(status="IDENTICAL_RECORDS",reward_delta=b["reward"]-a["reward"])
     if n<len(la)or n<len(ra):
      assert n<len(la)and n<len(ra);offset=len(deserialize_game_record(json.dumps(r["record"])).actions);left=moves[a["slot"]][n-offset];right=moves[b["slot"]][n-offset];assert left["root_record"]==right["root_record"]and left["root_state_sha"]==right["root_state_sha"]and left["side"]==right["side"];source=[left["source"],right["source"]];normal=all(x=="FULL_SESSION_MATERIAL_SEARCH"for x in source)
      row.update(status="FIRST_ACTION_DIFFERENCE",first_sources=source,first_actor_is_candidate=left["is_candidate"],mechanism="MATERIAL_PARAMETER_CANDIDATE"if normal and left["is_candidate"]else"THETA_BLIND_PROOF_OR_FIXED_FOE_EXECUTION_VARIATION_NOT_PRICE_CAUSAL",both_normal_D3=normal and all(x["normal_receipt"]["completed_depth"]==3 for x in(left,right)),proof_attempts=[x["new_proof_attempt"]for x in(left,right)],measured_seconds=[x["measured_seconds"]for x in(left,right)])
    pairs.append(row)
 solver_pairs=[]
 price_pair_map={(r['root'],r['arm'],r['role']):r for r in pairs}
 for root,r in roots.items():
  for ratio in(1.,2.):
   for role in(0,1):
    stop();a=idx.get((root,'MATERIAL_ONLY',ratio,role));b=idx.get((root,'TWO_REGIME_INCREMENTAL',ratio,role));item=dict(root=root,ratio=ratio,role=role,status='UNKNOWN_MISSING_OR_UNFINISHED')
    if a is not None and b is not None:
     own=[d for d in moves[b['slot']]if d['is_candidate']];proofs=[d for d in own if d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY')];accepted=proofs[0]if proofs else None
     item.update(outcomes=[a['outcome'],b['outcome']],reward_difference_lower=(-1 if b['reward']is None else b['reward'])-(1 if a['reward']is None else a['reward']),reward_difference_upper=(1 if b['reward']is None else b['reward'])-(-1 if a['reward']is None else a['reward']),first_accepted_proof_ply=None if accepted is None else accepted['ply'],first_accepted_proof_regime=None if accepted is None else accepted['regime'],first_accepted_proof_actor=None if accepted is None else accepted['side'],candidate_proof_plus_admission_verification_seconds=sum(d['proof_seconds']+d['verification_seconds']for d in own),candidate_choose_measured_seconds=sum(d['measured_seconds']for d in own),whole_game_seconds=[a['seconds'],b['seconds']],configured_resource_note='currentcursor continuations/commit/replay cost also retained inchoose/game totals; proof+verification notwholecost')
     if a['reward']is not None and b['reward']is not None:
      item['status']='ACTUAL_TERMINAL_PAIR';la=deserialize_game_record(json.dumps(a['record'])).actions;ra=deserialize_game_record(json.dumps(b['record'])).actions;n=0
      while n<min(len(la),len(ra))and la[n]==ra[n]:n+=1
      item['identical_actual_records']=n==len(la)==len(ra)
      if not item['identical_actual_records']:
       assert n<len(la)and n<len(ra);offset=len(deserialize_game_record(json.dumps(r['record'])).actions);left=moves[a['slot']][n-offset];right=moves[b['slot']][n-offset];assert left['root_record']==right['root_record'];item.update(first_action_difference_ply=n-offset,first_difference_actor_is_candidate=right['is_candidate'],first_difference_sources=[left['source'],right['source']])
     theta=price_pair_map[(root,'TWO_REGIME_INCREMENTAL',role)];item['price_pair_status']=theta['status'];item['price_first_difference_mechanism']=theta.get('mechanism');item['proof_before_any_candidate_material']=next(x['proof_before_any_material']for x in exposure if x['slot']==b['slot'])
    solver_pairs.append(item)
 result=dict(status="CLOSED_TWO_REGIME_POLICY_EXPOSURE_AND_PRICE_FIRST_DIFFERENCE",actual_games=len(games),games=exposure,price_pairs=pairs,solver_on_off_pairs=solver_pairs,by_arm={arm:dict(games=sum(g["arm"]==arm for g in exposure),verified_firstproofs=sum(g["verified_new_proofs"]for g in exposure if g["arm"]==arm),proof_before_any_material=sum(g["proof_before_any_material"]for g in exposure if g["arm"]==arm),candidate_measured_seconds=sum(g["candidate_measured_seconds"]for g in exposure if g["arm"]==arm),foe_measured_seconds=sum(g["foe_measured_seconds"]for g in exposure if g["arm"]==arm),ordinary_calls=sum(g["ordinary_total"]for g in exposure if g["arm"]==arm))for arm in("MATERIAL_ONLY","TWO_REGIME_INCREMENTAL")},pair_statuses=dict(Counter(g["status"]for g in pairs)),scope="Candidateproofsearch is theta-blind with fixedroot/resource/interface; only ordinarymaterialleafusesratio. Record any firstproof/fixedfoedivergence as executionvariation, notpricecausality. Immediatecertification canremoveinitialmaterialdecisionopportunity. Posthocmechanism/finiteW-Ldifferent, no newfit/DEV/priceassignment/equalcomputeclaim.")
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps({k:v for k,v in result.items()if k not in("games","price_pairs","solver_on_off_pairs")}))
if __name__=="__main__":run()
