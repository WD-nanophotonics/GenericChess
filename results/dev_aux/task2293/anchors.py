"""Closed boundary panel: protocol/anchor reproduction and original1 reference."""
from pathlib import Path
from collections import Counter
import json,hashlib,numpy as np
OUT=Path("results/dev_aux/task2293")
def run():
 read=lambda p:json.loads(Path(p).read_text());old=Path("results/dev_aux/task2282");new=Path("results/dev_aux/task2287");p=read(old/"plan.json");q=read(new/"plan.json");keys=("seeds","candidate","opponent","opponent_prices","candidate_colors","H");assert all(p[k]==q[k]for k in keys);assert (old/"inputs.json").read_bytes()==(new/"inputs.json").read_bytes()
 # Both producers invoke the SAME unmodified seeded GuidedPlayer/Guide module.
 a=(old/"transfer.py").read_text();b=(new/"transfer.py").read_text();assert "import_module('results.dev_aux.task2282.study')"in a and "import_module('results.dev_aux.task2282.study')"in b
 older=[json.loads(x)for x in(old/"games.jsonl").read_text().splitlines()];fresh=[json.loads(x)for x in(new/"games.jsonl").read_text().splitlines()];key=lambda g:(g["context"],g["family"],g["opponent_ratio"],g["candidate_color"]);oi={(key(g),g["ratio"]):g for g in older};ni={(key(g),g["ratio"]):g for g in fresh};anchors=[(g,oi[(key(g),2.)])for g in fresh if g["ratio"]==2.];assert all(x["record"]==y["record"]and x["reward"]==y["reward"]for x,y in anchors)
 depth={}
 for folder,label in[(old,"old78"),(new,"new79")]:
  rows=[json.loads(x)for x in(folder/"moves.jsonl").read_text().splitlines()];normal=[m for m in rows if m["source"]=="FULL_SESSION_MATERIAL_SEARCH"];assert all(m["normal_depth"]==3 and m["normal_visits"]<=8192 for m in normal);depth[label]=dict(normal_calls=len(normal),actual_depths=dict(Counter(str(m["normal_depth"])for m in normal)))
 rng=np.random.default_rng(20261017792293);families=sorted({g["family"]for g in older});summary={}
 for seed in p["seeds"]:
  contrasts={}
  for ratio in(1.5,2.,3.):
   lo=[];hi=[];missing=0;perfoe={}
   for fam in families:
    bounds=[]
    for foe in p["opponent_prices"]:
     for role in p["candidate_colors"]:
      k=(seed,fam,foe,role);x=oi[(k,1.)];y=ni.get((k,ratio))
      if y is None or y["reward"]is None or x["reward"]is None:bounds.append((-2.,2.));missing+=1
      else:bounds.append((y["reward"]-x["reward"],)*2)
    lo.append(sum(v[0]for v in bounds)/4);hi.append(sum(v[1]for v in bounds)/4)
   for foe in p["opponent_prices"]:
    bounds=[]
    for fam in families:
     for role in p["candidate_colors"]:
      k=(seed,fam,foe,role);x=oi[(k,1.)];y=ni.get((k,ratio));bounds.append((-2.,2.)if y is None or y["reward"]is None else(y["reward"]-x["reward"],)*2)
    perfoe[str(foe)]=dict(net_lower=sum(z[0]for z in bounds)/64,net_upper=sum(z[1]for z in bounds)/64)
   lo=np.array(lo);hi=np.array(hi);indices=rng.integers(0,32,size=(10000,32));contrasts[str(ratio)+"-vs-old1"]=dict(net_lower=float(lo.mean()),net_upper=float(hi.mean()),unknown_or_missing_pairs=missing,family_blocks=32,descriptive95_envelope=[float(np.quantile(lo[indices].mean(axis=1),.025)),float(np.quantile(hi[indices].mean(axis=1),.975))],by_foe=perfoe)
  summary[str(seed)]=contrasts
 result=dict(status="PASS_CLOSED_PROTOCOL_AND_EXACT_PRICE2_ANCHOR_REPRODUCTION",same_input_bytes=True,matched_configuration_keys=list(keys),same_GuidedPlayer_source="results/dev_aux/task2282/study.py",price2_anchors=len(anchors),all_anchor_actual_records_rewards_identical=True,new_anchor_measured_game_seconds=sum(g["seconds"]for g,_ in anchors),normal_depths=depth,summary=summary,scope="Descriptiveold1referenceonly after SAMEinput/startrecords/guide/priority/foe/role/resource contract and ALLcompleteD3/price2anchoridentitychecked. Crossbatchwallmeasurementnotcontrolledspeedclaim; notpoolanchorsasnewindependentfamilies. 32familiesperseed, missingfullbounds; no selection/DEV/fit/wholesignalartifactclaim.")
 (OUT/"result.json").write_bytes(json.dumps(result,indent=2).encode());print(json.dumps(result))
if __name__=="__main__":run()
