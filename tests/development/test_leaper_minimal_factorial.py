"""Data-integrity regression controls for actual four-actor evidence."""
import copy
from pathlib import Path
import pytest
from scripts.leaper_minimal_factorial_packet import metadata,contrast
from scripts import leaper_design as L

def _documents():
    from scripts.leaper_two_type_packet import read_packet
    directory=Path('docs/research/data/leaper_minimal_prices_and_role_capacity_20261024')
    if (directory/'manifest.json').exists():return read_packet(directory/'packet.json.gz',directory/'manifest.json')
    mapping_path=Path('.local_agent/ad-main-export-map.json')
    if not mapping_path.exists():pytest.skip('Scientific data not installed; no Player execution')
    mapping=L.load(mapping_path)
    mapping.update({'analysis/role-mate.json':'.local_agent/ad-role-mate-results.json','analysis/role-target.json':'.local_agent/ad-role-mate-target-qualification.json','analysis/role-witness.json':'.local_agent/ad-role-mate-witness.json','adjacent/inputs.json':'.local_agent/ad-adjacent-inputs.json','analysis/role-registration.json':'.local_agent/ad-role-mate-registration.json','analysis/role-witness-provenance.json':'.local_agent/ad-role-witness-provenance.json','source/role_mate.py':'.local_agent/ad-role-mate.py','source/role_target.py':'.local_agent/ad-role-mate-target.py','source/role_witness.py':'.local_agent/ad-role-mate-witness.py'})
    return {k:Path(v).read_bytes().decode('utf-8')for k,v in mapping.items()}

def _local():
    import json
    docs=_documents();return [json.loads(docs[k])for k in ('inputs.json','game-001.json','case-001.json')]

def test_future_controller_requires_exact_leaf_and_order_contract():
    world,row,reg=_local();metadata(world,row,reg)
    for field in ('actual_leaf_profile','ordering_profile'):
        bad=copy.deepcopy(row);bad[field]['board_value_by_type']['B']+=1
        with pytest.raises(AssertionError):metadata(world,bad,reg)
    bad=copy.deepcopy(row);bad['slot']['policy']='DEFAULT'
    with pytest.raises(AssertionError):metadata(world,bad,reg)
    bad=copy.deepcopy(row);bad['queries'][0]['controller']='DEFAULT'
    with pytest.raises(AssertionError):metadata(world,bad,reg)

def test_missing_factorial_cell_keeps_signed_completion_bounds():
    rows=[dict(root=0,controller='UNIT',value=0),dict(root=0,controller='STATIC_FIXED',value=0),dict(root=0,controller='DYNAMIC_FIXED',value=1)]
    r=contrast(rows);e=r['roots'][0]['effects'];assert e['material_OFF']==dict(value=0,lower=0,upper=0)
    assert e['material_ON']==dict(value=None,lower=-2,upper=0)
    assert e['interaction']==dict(value=None,lower=-2,upper=0)
    assert r['equalweight_mean_bounds']['material_ON']==[-2,1.75]

def test_complete_factorial_separates_material_dynamic_interaction():
    rows=[dict(root=i,controller=m,value=v)for i in range(8)for m,v in [('UNIT',0),('STATIC_FIXED',0),('DYNAMIC_FIXED',1),('FULL_FIXED',1)]]
    mean=contrast(rows)['equalweight_mean_bounds'];assert mean['material_OFF']==mean['material_ON']==mean['interaction']==[0,0]
    assert mean['dynamic_UNIT']==mean['dynamic_DEFAULT']==[1,1]


@pytest.mark.parametrize('corruption',['remove_actual_defense','change_complete_rule'])
def test_role_capacity_reader_rejects_false_mate_or_wrong_rule(corruption):
    import json
    from scripts.leaper_role_mate_packet import qualify_role_documents
    docs=dict(_documents());raw=json.loads(docs['analysis/role-mate.json'])
    if corruption=='remove_actual_defense':
        case=next(case for row in raw['rows']for case in row['candidates']if case.get('actions'));case['actions']=[]
    else:raw['rows'][0]['rule']['max_ply']+=1
    docs['analysis/role-mate.json']=json.dumps(raw)
    with pytest.raises(AssertionError):qualify_role_documents(docs)

def test_whole_caller_cost_includes_setup_without_claiming_module_imports(tmp_path,monkeypatch):
    from scripts import leaper_default_contact as writer
    world,_,_=_local();clock=[0.0];original_compile=L.compile_rule
    def paid_setup(rule):
        result=original_compile(rule);clock[0]+=5.0;return result
    source=tmp_path/'input.json';L.write_record(source,world)
    reg=dict(input_sha256=L.sha(source),source_sha256=L.sha(Path(writer.__file__)),expected_total_seconds=60,controller='UNIT',root=0,profile=world['profile'],nodes=64,cap_seconds=0)
    rp=tmp_path/'reg.json';L.write_record(rp,reg)
    monkeypatch.setattr(L,'compile_rule',paid_setup);monkeypatch.setattr(writer.time,'perf_counter',lambda:clock[0])
    def no_queries(*args,**kwargs):raise AssertionError('cost metadata control must not search')
    monkeypatch.setattr(L.AlphaBetaPlayer,'choose_action',no_queries)
    row=writer.run(source,rp,tmp_path/'closed.json')
    assert row['queries']==[] and row['seconds']==0
    assert row['setup_seconds']==5 and row['caller_seconds_before_final_write']==5
    assert row['cost_scope']=='seconds=game_loop; caller includes setup before final serialization; module imports excluded'
