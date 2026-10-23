import gzip,json,hashlib
from scripts import leaper_design as L
from scripts.leaper_calibration_run import materialize


def test_materialization_registers_new_bytes_and_keeps_original_provenance(tmp_path):
    c=L.compile_rule(L.definition(1,2));s=L.GameSession(c)
    inputs={'worlds':[{'world':0,'status':'ready','rule':L.ruleset_to_dict(L.definition(1,2),include_metadata=True),'initial_record':L.record_value(s.to_record()),'initial_state':L.record_value(s.state)}]}
    original_hash=hashlib.sha256(json.dumps(inputs,indent=4).encode()).hexdigest()
    reg={'source_sha256':L.sha(__import__('pathlib').Path(L.__file__)),'input_sha256':original_hash,'preparer_sha256':'original-preparer','pairs':{'fixed':['STATIC_ADAPTER','STATIC_ADAPTER']},'whole_cap_seconds':300,'q':0,'TT':'freshactor/game'}
    packet=tmp_path/'input.json.gz';packet.write_bytes(gzip.compress(json.dumps({'runs':{'fixture':{'files':{'registration.json':reg,'inputs.json':inputs},'original_file_sha256':{'inputs.json':original_hash}}}},sort_keys=True).encode()))
    target=tmp_path/'new';materialize(packet,'fixture',target)
    new=L.load(target/'registration.json')
    assert new['input_sha256']==L.sha(target/'inputs.json')!=original_hash
    assert L.load(target/'inputs.json')==inputs
    assert L.load(target/'replication-original-registration.json')==reg
    for key in ('pairs','whole_cap_seconds','q','TT'):assert new[key]==reg[key]
    assert new['replication_provenance']['original_registered_input_sha256']==original_hash
    assert not(target/'preflight.json').exists() and not(target/'results.json').exists()
