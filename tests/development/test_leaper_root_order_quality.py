"""Scientific saved-evidence contracts; no new Player/solver/game execution."""
from pathlib import Path
from copy import deepcopy
import pytest
from scripts.verify_leaper_root_order_trials import load,run,verify_inputs,verify_rows,verify_source_capsule
from scripts.verify_leaper_population_games import run as verify_games,verify_game,outcome

DATA=Path(__file__).resolve().parents[2]/'docs/research/data/leaper_root_order_quality_20261026'

def test_frozen_trials_and_observer_contracts():
 r=run(DATA)
 assert r['inputs']==24 and r['full_rules']==12
 assert r['phases']['1']['queries']==96 and r['phases']['2']['queries']==144
 assert r['phases']['2']['observer_semantic_work_parity_pairs']==48
 assert r['new_Player']==r['new_solver']==r['new_games']==0

def test_missing_scheduled_trial_is_rejected():
 _,cache,acts=verify_inputs(DATA/'prepared-v2/inputs.json')
 rows=load(DATA/'phase1/queries.json');planned=[(r['case_id'],r['requested_depth'],r['arm'])for r in rows]
 with pytest.raises(AssertionError):verify_rows(rows[:-1],planned,cache,acts,[1,4],['baseline','scan_hint'])

def test_false_previous_work_cannot_be_promoted():
 _,cache,acts=verify_inputs(DATA/'prepared-v2/inputs.json')
 rows=deepcopy(load(DATA/'phase2/queries.json'));planned=[(r['case_id'],r['requested_depth'],r['arm'])for r in rows]
 row=next(r for r in rows if r['arm']=='work_order' and r['root_work']['orders'])
 event=row['root_work']['orders'][0];first=next(iter(event['previous_work']));event['previous_work'][first]+=1
 with pytest.raises(AssertionError,match='non-complete previous iteration promoted'):
  verify_rows(rows,planned,cache,acts,[4,6],['original','record_only','work_order'])

def test_changed_executed_source_is_rejected():
 caps=deepcopy(load(DATA/'phase2/executed-source.json'));plan=load(DATA/'phase2-frozen.json');caps['order_source']+='\n# changed\n'
 with pytest.raises(AssertionError,match='source capsule hash mismatch'):verify_source_capsule(caps,plan,2)

def test_actual_games_replay_literal_history_and_terminal():
 r=verify_games(DATA)
 assert r['mode']=='CLOSED_ALL_PLANNED_SLOTS'
 assert r['new_Player']==r['new_solver']==r['new_games']==0
 assert r['games_replayed']+len(r['not_started'])==24

def first_game():
 game=load(DATA/'population-games/games.json')[0]
 case=next(r for r in load(DATA/'prepared-v2/inputs.json')['rows']if r['id']==game['case_id'])
 return game,case,load(DATA/'population-budget-frozen.json')

def test_unfinished_is_unknown_not_draw_and_cannot_pass_as_terminal():
 game,case,plan=first_game();changed=deepcopy(game);changed['status']='UNFINISHED'
 assert outcome(changed)is None
 with pytest.raises(AssertionError):verify_game(changed,case,DATA/'population-games',plan)

def test_wrong_budget_role_and_changed_raw_return_rejected():
 game,case,plan=first_game()
 changed=deepcopy(game);changed['long_seat']=1-changed['long_seat']
 with pytest.raises(AssertionError):verify_game(changed,case,DATA/'population-games',plan)
 changed=deepcopy(game);changed['queries'][0]['decision']['score']+=1
 with pytest.raises(AssertionError,match='raw successful return was changed'):verify_game(changed,case,DATA/'population-games',plan)
