import copy,datetime,hashlib,json
from pathlib import Path
import chess,pytest
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2620 import evaluate as e, protocol as p


def dump(path,obj):
    path.write_text(json.dumps(obj),encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_actual_search_execution_exercises_model_import_and_unknown(tmp_path,monkeypatch):
    run=tmp_path/'run';run.mkdir();(tmp_path/'.local_agent').mkdir()
    monkeypatch.setattr(e,'ROOT',tmp_path);monkeypatch.setattr(e,'RUN',run)
    monkeypatch.setattr(e,'require_identity',lambda:None)
    monkeypatch.setattr(e,'SharedDeleteStopReader',lambda root:lambda:None)
    dump(tmp_path/'.local_agent/session.json',dict(state='active',id='new-active-segment'))
    original=dict(seeds=[7],methods=['TreeStrap','TDLeaf','WDL'],nodes_per_seed_method_arm=100)
    original_sha=dump(tmp_path/'original-plan.json',original)
    arms=[dict(seed=7,seed_index=0,method=m,status='NODE_BUDGET_REACHED',nodes_total=100,
               initial_weights=[1.]*5,final_weights=[1.]*5) for m in original['methods']]
    training=dict(status='COMPLETE_TRAINING',eligible_for_evaluation=True,plan_sha256=original_sha,arms=arms)
    training_sha=dump(run/'training-result.json',training)
    roots_sha=dump(run/'evaluation-root-manifest.json',dict(roots=[dict(family=1,record=ChessEnv().record())]))
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    plan=dict(task='unit-only',source_sha256={},python_chess_version=chess.__version__,
        registered_at=stamp,preparation_started_at=stamp,session_id='registration-segment',
        training_plan_path='original-plan.json',training_plan_sha256=original_sha,
        training_result_sha256=training_sha,evaluation_root_manifest_sha256=roots_sha,
        all_in_hard_cap_seconds=60,fixed_foe_weights=[1.]*5,
        evaluation=dict(root_count=1,expected_slots=1,ordered_slots=[[0,7,1,0,'initial']],
        caps_by_family={'1':512},cap_values_nodes_both_sides=[512],hard_cap_seconds=30,
        max_plies_per_game=1,nodes_per_search=512,seconds_per_search=5,ordering_seed_base=123,depth=1,q_limit=1))
    plan_sha=dump(run/'plan.json',plan)
    dump(run/'registration.json',dict(status='REGISTERED_PRE_EVALUATION',plan_sha256=plan_sha))
    result=e.evaluate()
    assert result['status']=='COMPLETE' and result['actual_slots']==1
    assert result['actual_terminal']==0 and result['unknown']==1
    row=json.loads((run/'evaluation-games.jsonl').read_text().splitlines()[0])
    assert row['learner_reward'] is None and row['reward_bounds']==[-1,1]
    query=json.loads((run/'evaluation-queries.jsonl').read_text().splitlines()[0])
    assert query['complete'] and query['record_before']!=query['record_after']
    started=json.loads((run/'evaluation-started.json').read_text())
    assert started['registration_session_id']!='new-active-segment'
    assert started['launch_session_id']=='new-active-segment'
    with pytest.raises(FileExistsError):e.evaluate()


def test_root_selection_skips_exact_exposure_without_outcomes():
    first=p.select_roots(set(),3)
    excluded={p.canonical(first[0]['record'])}
    selected=p.select_roots(excluded,3)
    assert not excluded & {p.canonical(x['record']) for x in selected}
    assert len({p.canonical(x['record']) for x in selected})==3
    assert [x['family'] for x in p.select_roots(excluded,3)]==[x['family'] for x in selected]


def test_plan_rejects_inconsistent_original_provenance_and_missing_pairs():
    slots=[[0,7,1,c,e] for c in (0,1) for e in ('initial','TreeStrap','TDLeaf','WDL')]
    plan=dict(seeds=[7],evaluation=dict(root_count=1,caps_by_family={'1':20000},ordered_slots=slots,expected_slots=8))
    p.validate_plan(plan)
    ambiguous=copy.deepcopy(plan);ambiguous['evaluation_root_selection']={'root_count':32}
    with pytest.raises(ValueError,match='metadata'):p.validate_plan(ambiguous)
    incomplete=copy.deepcopy(plan);incomplete['evaluation']['ordered_slots'].pop()
    with pytest.raises(ValueError,match='cross product'):p.validate_plan(incomplete)
