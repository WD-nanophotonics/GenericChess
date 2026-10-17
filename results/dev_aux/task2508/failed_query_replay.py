"""Diagnose all CLOSED curve SEARCH_LIMIT roots, keeping original U unchanged."""
from pathlib import Path
import json,chess,time
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2504.search import TrainingSearch
OUT=Path('results/dev_aux/task2508')
def run():
 base=Path('results/dev_aux/task2510');p=json.loads((base/'plan.json').read_text());rows=[json.loads(x)for x in(base/'games.jsonl').read_text().splitlines()];reports=[]
 for row in rows:
  if row['ending']!='SEARCH_LIMIT_UNKNOWN':continue
  b=chess.Board(row['record']['initial'])
  for u in row['record']['moves']:b.push_uci(u)
  env=ChessEnv(b);before=env.record();ply=len(row['record']['moves'])-len(row['initial_record']['moves']);m=Model(row['weights']if env.player()==row['color']else p['foe_weights']);r=TrainingSearch(p['depth'],quiet=False).search(env,m,nodes=p['nodes_per_query'],seconds=p['seconds_per_query'],seed=row['family']*10000+ply);assert env.record()==before
  reports.append(dict(seed=row['seed'],family=row['family'],color=row['color'],treatment=row['treatment'],ply=ply,complete=r.complete,nodes=r.nodes,seconds=r.seconds,reason=r.reason,usable_target=r.value,original_ending=row['ending'],original_reward=row['reward']))
 result=dict(status='CLOSED_FAILURE_ROOT_DIAGNOSED_ORIGINAL_UNKNOWN_RETAINED',roots=reports,scope='All1originalSEARCH_LIMITroot replayedonce atoriginal8192nodes/5s/commonplainD2/actualfullhistory/frozenweights+seed. No newgame/fitnesslabel orcapextension. Originalperquerylimitreason wasnotjournaled, so replayidentifiesasufficientcurrentresourceboundary, notproof ofhistoricalwallcause. OriginalU unchanged evenifcurrentenvironmentdiffers.')
 (OUT/'failed-query-replay.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
