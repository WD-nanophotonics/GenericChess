"""Register task2583 TRAIN and task2584 common EVAL BEFORE any new fitness.

Writes plan.json, replay-plan.json, audit-plan.json (task2583), eval-plan.json (task2584)
and registration.json with pins. Refuses to overwrite.
"""
from pathlib import Path
import json,random,hashlib,datetime,itertools
D=Path('results/dev_aux/task2583');E=Path('results/dev_aux/task2584')
SEEDS=[1977,8173,27182,31415];METHODS=('Fixednu','SelfCandidate');BOUNDARIES=[1250000,2500000]
CODE=['results/dev_aux/task2492/learning.py','results/dev_aux/task2492/episode.py','results/dev_aux/task2492/adapters.py','results/dev_aux/task2504/search.py','results/dev_aux/task2565/train.py','results/dev_aux/task2565/audit.py','results/dev_aux/task2580/train.py','results/dev_aux/task2580/replay.py','results/dev_aux/task2392/reader.py','results/dev_aux/task2153/stop_evidence.py','results/dev_aux/task2131/stop_reader.py','results/dev_aux/task109/adapter.py','results/dev_aux/task2581/evaluate.py','results/dev_aux/task2581/verify.py','results/dev_aux/task2568/summary.py','results/dev_aux/task2583/train.py','results/dev_aux/task2583/audit.py','results/dev_aux/task2583/register.py','results/dev_aux/task2584/bind.py','results/dev_aux/task2584/analyze.py']
def sha(n):return hashlib.sha256(Path(n).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def write(path,obj):
 assert not path.exists(),path;path.write_text(json.dumps(obj,indent=2))
def run():
 s=json.loads(Path('.local_agent/session.json').read_text());assert s['state']=='active'
 arms=[[seed,m]for seed in SEEDS for m in METHODS];random.Random(2583).shuffle(arms)
 plan=dict(session_id=s['id'],registered_at=now(),domain='chess',arms_order=arms,dimension=5,eta=.05,**{'lambda':.95},nodes_per_arm=2500000,nodes_per_game=25000,nodes_per_query=8192,seconds_per_query=2.0,depth=2,H=1024,training_family_offset=581000,ordering_seed_offset=1002583000,snapshot_nodes=BOUNDARIES,max_games=20000,cap_seconds=3600,
  pins={n:sha(n)for n in CODE if n!='results/dev_aux/task2584/analyze.py'},
  scope='NEW SAME plain TD Fixednu (candidate vs fixed uniform foe) versus SelfCandidate (episode-frozen candidate theta plays BOTH actors), both observe ONLY designated candidate-colour searches; mixed8,8,64,64 paired-role resets, all4initials, all paid nodes incl failed/opponent. No filter/bestseed/human prior. All existing caps CLOSED; new caps independent. Selfplay removes coefficient-foe mismatch only, not finite horizon/replanning mismatch.',
  foes=dict(uniform=[1.]*5),foe_cycle=['uniform'],seeds=SEEDS,mixed_prefix_cycle=[8,8,64,64])
 write(D/'plan.json',plan)
 write(D/'replay-plan.json',dict(total_wall_seconds=120,nodes_per_query=8192,seconds_per_query=2,scope='First AND last complete observed query per ALL8 arms, actual search replay, no update/fitness choice.'))
 write(D/'audit-plan.json',dict(prepared_at=now(),unpruned_node_cap=200000,unpruned_seconds_cap=120,selection='First AND last complete observed query for each of ALL8 arms, identical stream choice to actual search replay, no EVAL fitness selection.',scope='Unpruned reference recursion of D2 witness semantics; all counts/cap failures retained.'))
 recipes={}
 for k in range(1,5):
  recipes[str(591000+k)]=dict(family=591000+k,plies=8);recipes[str(592000+k)]=dict(family=591000+k,plies=64)
 treatments=['initial|plain']+[f'{m}@{b/1e6:g}M|plain'for m in METHODS for b in BOUNDARIES]
 foes=dict(uniform=[1.]*5,random48821=[1,1.4583547904631338,0.9552467972775168,0.9937802786854406,0.98710237340455])
 slots=[[0,seed,int(code),color,t,o]for seed,code,color,t,o in itertools.product(SEEDS,sorted(recipes,key=int),(0,1),treatments,foes)];random.Random(2584).shuffle(slots);assert len(slots)==640
 write(E/'eval-plan.json',dict(domain='chess',rules=[0],slots=slots,root_recipes=recipes,foes=foes,depth=2,prefix_plies=8,H=1024,nodes_per_query=8192,seconds_per_query=2.0,ordering_seed_offset=1002584000,cap_seconds=2400,
  scope='ALL4initials x(initial+Fixednu1.25/2.5M+SelfCandidate1.25/2.5M) x4 NEW underlying families x prefix8/64 xBOTHroles xSAME2fixedplainfoes (task2581 foes), full history actual WLD, no root/outcome/material filter. TRAIN581k disjoint from EVAL591k; old541k/551k/552k/531k untouched. Every snapshot retained, no best checkpoint.'))
 pins={n:sha(n)for n in CODE}
 for n in('task2583/plan.json','task2583/replay-plan.json','task2583/audit-plan.json','task2584/eval-plan.json'):pins['results/dev_aux/'+n]=sha('results/dev_aux/'+n)
 write(D/'registration.json',dict(registered_at=now(),session_id=s['id'],executor='Claude Code substitute for DEV_AUX (user-directed 2026-10-19)',question='At a larger same paid dose (2.5M/arm, snapshots 1.25M/2.5M), does SelfCandidate TD improve actual WLD utility and cross-initial price consistency over competitive Fixednu TD under SAME mixed legal resets?',
  registered_contrasts=['SelfCandidate@B - Fixednu@B for B in 1.25M,2.5M','X@B - initial for X in methods','X@2.5M - X@1.25M within method','each: all/by prefix 8,64/by foe/by seed/by role; paired finite bounds, U=[-1,1]'],
  expected_minutes='TRAIN est 47-55 (hard cap 60) + EVAL est 23-28 (hard cap 40) + audits/replay ~10; total under 120. Caps raised from proposal 3300/1800 BEFORE registration after 2026-10-19 smoke (7.1k nodes/s TRAIN, 2.19 s/EVAL game) under concurrent alphasho load, to avoid a partial last arm; no extension after start.',
  estimate_basis='task2580: 12M TRAIN nodes 1533.6s; task2581: 768 EVAL games 1484.0s. Scaled: 20M -> ~2556s, 640 -> ~1237s.',
  cheaper_alternative='Old96 100k/5-9 episodes inconclusive; smaller dose cannot address dose/learning-curve question with all4initials.',
  pins=pins,scientific_status='OPEN',no_new_fitness_yet=True))
 print(json.dumps(dict(arms=arms,slots=len(slots),pins=len(pins))))
if __name__=='__main__':run()
