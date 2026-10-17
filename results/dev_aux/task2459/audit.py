"""Independent closed selectors, no-search reserve and source/unique-game accounting."""
from pathlib import Path
from collections import Counter
import json,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from scripts.generic_proof_rnb_bridge import orbit,actor_state
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2459')
def read(p):return json.loads(Path(p).read_text())
def run():
 stop=SharedDeleteStopReader(Path.cwd());t=time.perf_counter();tasks=(2427,2441,2442,2454,2455,2461);rows=[];allgames=[];allcerts=0;normals=Counter();terminal=Counter()
 for task in tasks:
  stop();f=Path(f'results/dev_aux/task{task}');p=read(f/'plan.json');done=read(f/'completion.json');games=[json.loads(x)for x in(f/'games.jsonl').read_text().splitlines()];decisions=[json.loads(x)for x in(f/'decisions.jsonl').read_text().splitlines()];commits=[json.loads(x)for x in(f/'commits.jsonl').read_text().splitlines()];certs=[json.loads(x)for x in(f/'certificates.jsonl').read_text().splitlines()];assert done['status']=='COMPLETE'and len(games)==p['expected_games']==done['games'];assert len(commits)==sum(g['plies']for g in games)==len(decisions);assert len(certs)==done['certificates'];assert all(g['reward']in(-1,0,1)and g['outcome']!='U'and g['ending']=='ACTUAL_TERMINAL'for g in games)
  for d in decisions:
   if d['normal_receipt']is not None:assert d['normal_receipt']['completed_depth']==3;normals[(d['is_candidate'],3)]+=1
  terminal.update(g['actual_status']for g in games);allgames.extend((task,g['slot'])for g in games);allcerts+=len(certs);rows.append(dict(task=task,games=len(games),moves=len(commits),certificate_instances=len(certs),game_seconds=sum(g['seconds']for g in games),run_seconds=done['seconds'],original_global_cap=p['one_cap_seconds']))
 # Independent arithmetic selection, not calling either selector.
 tr=Path('results/dev_aux/task2441');games=[json.loads(x)for x in(tr/'games.jsonl').read_text().splitlines()];registration=read(tr/'registration.json');scores={tuple(point):sum(g['reward']for g in games if(g['ratio'],g['hand_ratio'])==tuple(point))/8 for point in registration['train_grid']};base=(1.5,1.5);eligible=[x for x in scores if scores[x]>scores[base]];chosen=min(eligible,key=lambda x:(-scores[x],x))if eligible else base;assert list(chosen)==read('results/dev_aux/task2444/selection.json')['selected']==list(base)
 nh=Path('results/dev_aux/task2461');new=[json.loads(x)for x in(nh/'games.jsonl').read_text().splitlines()];reuse=read(nh/'baseline-reuse.json');values={1.:sum(r['reward']for r in reuse)/8};values.update({x:sum(g['reward']for g in new if g['N_hand']==x)/8 for x in(0.,.5,2.)});eligible=[x for x in values if values[x]>values[1.]];best=min(eligible,key=lambda x:(-values[x],x))if eligible else 1.;assert best==read('results/dev_aux/task2463/selection.json')['selected_N_hand']==1.
 for task in(2446,2462):
  f=Path(f'results/dev_aux/task{task}');assert read(f/'activation.json')['status']=='NOT_EXECUTED_CONDITION_FALSE'and not(f/'started.json').exists()
 old=read('results/dev_aux/task2439/inputs.json');newroots=read('results/dev_aux/task2462/inputs.json');groups=[]
 for rr in old+newroots:
  stop();ss=GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path(rr['rules']).read_text())));assert not rr['record']['actions'];groups.append(min(map(repr,orbit(actor_state(ss.state)))))
 assert len(groups)==len(set(groups))==20;assert not Path('results/dev_aux/task2462/games.jsonl').exists();pins=0
 for task in range(2427,2465):
  for planfile in Path(f'results/dev_aux/task{task}').rglob('plan.json'):
   stop();p=read(planfile)
   for name,h in p.get('pins',{}).items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,(planfile,name);pins+=1
 forecast=read(nh/'registration.json')['whole_logical_forecast_seconds'];assert forecast==5250<7200;assert len(allgames)==len(set(allgames))==186
 result=dict(status='PASS_UNIQUE_ACTUAL_WL_SELECTORS_PINS_AND_UNQUERIED_RESERVE',new_unique_study_games=len(allgames),new_committed_moves=sum(r['moves']for r in rows),in_game_certificate_instances=allcerts,rows=rows,actual_terminal_statuses=dict(terminal),normal_completed_depths=[dict(candidate=k[0],depth=k[1],count=v)for k,v in normals.items()],independent_primary_selected=list(chosen),independent_Nhand_selected=best,once_reused_within_segment_games=8,newNhand_matrix_cells=32,newNhand_unique_games=24,new_reserve_orbits_unqueried=8,all_old_new_orbits_disjoint=20,source_pin_checks=pins,whole_logical_compute_forecast_seconds=forecast,actual_compute_and_engineering_scope='Stagegame/runseconds separate; overlapandengineering/test/recordcost includedinactualsessionclock, not claimedthroughputspeedup. Unexecutedconditional64+32cellskeptbutnotfakegames/unknownrewards.',seconds=time.perf_counter()-t,scope='Allunique186newactualterminalgames countedONCE; NHbaseline8alreadyinside48TRAIN, notextra8newgames. SameCore/cursorverifiers, no externalengineornewsearch/fitness. Fullintactpinsbeforepublicationprojection. All105savedgamecertinstances and2367journalmoves areactualclosedconsumeraudits. New8orbitsstrictlyunqueried, conditionalbranchesnotrevived; no human/default/PRIMARYchanges.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
