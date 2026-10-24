"""Data-only qualification of the support/history/entry packet.

Frozen source capsules are hashed strings. They are never imported, compiled,
executed or used as commands. Current maintained readers bind literal records.
"""
from pathlib import Path
from datetime import datetime,timedelta
import argparse,hashlib,gzip,json,time
from scripts.verify_leaper_delayed_capture import load
from scripts import leaper_design as L
from scripts.leaper_safe_support import rule,safe
from scripts.leaper_delayed_capture_witness import nodes
from scripts.leaper_delayed_win_certificate import qualify as q_existence
from scripts.leaper_safe_support import qualify as q_support
from scripts.leaper_support_interactions import qualify as q_interaction
from scripts.leaper_history_value_witness import qualify as q_history
from scripts.leaper_capture_epoch_conformance import qualify as q_epoch
from scripts.leaper_support_quantity_boundary import qualify as q_quantity
from scripts.leaper_entry_square import qualify as q_square
from scripts.leaper_history_order_key import qualify as q_key
from scripts.leaper_radius_admission import qualify as q_radius
from scripts.leaper_tempo_barrier import qualify as q_tempo
from tools.local_agent.common import write_json


def bound_deadline(reg,m,field):
    plan=reg['plan'];v=plan
    for k in field:v=v[k]
    expected=datetime.fromisoformat(plan['started_at'])+timedelta(seconds=v)
    reported=reg.get('original_deadline',reg.get('deadline',reg.get('original_phase_deadline')))
    assert reported is not None and datetime.fromisoformat(reported)==expected, 'original deadline changed'
    assert datetime.fromisoformat(m['started_at'])>=datetime.fromisoformat(plan['started_at'])
    assert datetime.fromisoformat(m['started_at'])<=datetime.fromisoformat(m['ended_at'])<=expected


def qualify(root,old):
    tick=time.perf_counter();mf=load(root/'manifest.json')
    assert mf['capsules_executable']is False
    for name,item in mf['files'].items():
        assert Path(name).name==name
        raw=(root/name).read_bytes();assert len(raw)==item['bytes']and hashlib.sha256(raw).hexdigest()==item['sha256']
        if name.endswith('.gz'):assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==item['private_original_sha256']
        obj=load(root/name)
        if isinstance(obj,dict)and 'source_utf8'in obj:
            assert hashlib.sha256(obj['source_utf8'].encode('utf-8')).hexdigest()==obj['sha256']
    # Bind base published inputs, without re-running the old completed study.
    oldmf=load(old/'manifest.json')
    for name in ('named-mu-registration.json.gz','named-mu-bridge.json.gz'):
        assert hashlib.sha256((old/name).read_bytes()).hexdigest()==oldmf['files'][name]['sha256']
    bindings=[('existence-registration.json.gz','producer_source_sha256','existence-first-source.json.gz'),
        ('support-registration.json','source_sha256','support-source.json.gz'),
        ('interaction-registration.json','source_sha256','interaction-source.json.gz'),
        ('history-positive-registration.json.gz','source_sha256','history-positive-source.json.gz'),
        ('capture-epoch-registration.json.gz','source_sha256','capture-epoch-source.json.gz'),
        ('support-general-registration.json','source_sha256','support-general-corrected-source.json.gz'),
        ('entry-square-registration.json','source_sha256','entry-square-source.json.gz'),
        ('history-order-key-registration.json.gz','source_sha256','history-order-key-source.json.gz'),
        ('radius-admission-registration.json','source_sha256','radius-admission-source.json.gz'),
        ('tempo-registration.json','source_sha256','tempo-source.json.gz')]
    for reg,field,source in bindings:assert load(root/reg)[field]==load(root/source)['sha256']
    phases=[('existence','existence-registration.json.gz','existence-completed.json.gz',q_existence,('absolute_preparation_and_validation_cap_seconds',),True),
      ('support','support-registration.json','support.json.gz',q_support,('cost','hard_preparation_analysis_cap_seconds'),False),
      ('history','history-positive-registration.json.gz','history-positive.json.gz',q_history,('cost','new_inclusive_cap_seconds'),True),
      ('capture_epoch','capture-epoch-registration.json.gz','capture-epoch.json.gz',q_epoch,('resources','inclusive_hard_cap_seconds'),True),
      ('entry_square','entry-square-registration.json','entry-square.json.gz',q_square,('resources','absolute_analysis_validation_cap_seconds'),False),
      ('history_key','history-order-key-registration.json.gz','history-order-key.json.gz',q_key,('cost','new_inclusive_hard_cap_seconds'),True),
      ('radius','radius-admission-registration.json','radius-admission.json.gz',q_radius,('resources','absolute_analysis_validation_cap_seconds'),False),
      ('tempo','tempo-registration.json','tempo.json.gz',q_tempo,('resources','absolute_analysis_validation_cap_seconds'),'packet')]
    results={};record_cache={};occurrences=0;planned_moves=0
    def inventory_records(m):
        nonlocal occurrences
        for node in nodes(m):
            occurrences+=1;k=json.dumps(node['record'],sort_keys=True)
            if k in record_cache:assert record_cache[k]==node, 'same full record has inconsistent retained node'
            else:record_cache[k]=node
    for label,rname,mname,fn,field,needs_old in phases:
        reg,m=load(root/rname),load(root/mname);bound_deadline(reg,m,field)
        result=fn(reg,m,root)if needs_old=='packet'else(fn(reg,m,old)if needs_old else fn(reg,m))
        assert result['status']=='PASS';results[label]=result;inventory_records(m)
        assert m.get('new_Player_queries',0)==m.get('new_graph_or_solver_calls',0)==0
        planned_moves+=m.get('new_Core_child_applications',0)
    interaction=load(root/'interaction.json.gz');ireg=load(root/'interaction-registration.json')
    assert datetime.fromisoformat(interaction['ended_at'])<=datetime.fromisoformat(ireg['plan']['parent_absolute_deadline'])
    results['interaction']=q_interaction(interaction);inventory_records(interaction)
    quantity=load(root/'support-general.json.gz');qreg=load(root/'support-general-registration.json')
    bound_deadline(qreg,quantity,('cost','absolute_analysis_validation_cap_seconds'))
    results['quantity_range']=q_quantity(quantity);inventory_records(quantity)
    reg=load(root/'existence-registration.json.gz');m=load(root/'existence-completed.json.gz')
    assert m['repair']['repair_source_sha256']==load(root/'existence-repair-source.json.gz')['sha256']
    assert m['repair']['original_measurement_sha256']==mf['files']['existence-partial-original.json.gz']['private_original_sha256']
    try:q_existence(reg,load(root/'existence-partial-original.json.gz'),old)
    except AssertionError as exc:assert 'finish prefix'in str(exc)
    else:raise AssertionError('original failed Enum branch must remain incomplete')
    # Source-derived public submission accounting, not total internal Core work.
    audit=load(root/'counter-scope-audit.json')['runtime_key_measure']
    assert audit['planned_new_prefix_moves']==16
    assert audit['derived_explicit_submission_plus_replay_actions']==sum(audit[k]for k in('planned_new_prefix_moves','follow_prefix_replay_actions','observe_final_state_replay_actions','observe_history_witness_replay_actions'))==160
    next_input=load(root/'next-b-tempo.json')
    assert next_input['status']=='PREPARED_NOT_COMPILED_OR_EXECUTED' and next_input['B_masks']==[5,1]
    assert next_input['new_Core_calls']==next_input['new_Player_queries']==next_input['new_graph_or_solver_calls']==0
    assert next_input['source_rule']==L.ruleset_to_dict(rule(4,22,5,[6,15,4,0]),include_metadata=True), 'prospective full rule source mismatch'
    assert next_input['proposed_rule']==L.ruleset_to_dict(rule(4,22,1,[6,15,4,0]),include_metadata=True), 'prospective full rule scope/clock mismatch'
    assert (next_input['H'],next_input['repeat'])==(6,2)and safe([6,15,4,0],4,22,1)
    return dict(status='PASS',hashed_files=len(mf['files']),record_occurrences=occurrences,unique_full_records=len(record_cache),planned_explicit_new_target_moves=planned_moves,
        source_capsule_executions=0,new_Player_queries=0,new_graph_or_solver_calls=0,results=results,qualification_seconds=time.perf_counter()-tick,
        scope='Ten scoped finite/analytic components; same-Core record binding plus independent combinatorial/local geometry. Counts are explicit target materializations, not all replays/internal legality cost. No all-domain or TTperformance inference.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--old-data',type=Path,default=Path(__file__).resolve().parents[1]/'docs/research/data/leaper_delayed_capture_20261024');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW qualification output required')
    r=qualify(a.directory,a.old_data);write_json(a.output,r);print(json.dumps({k:v for k,v in r.items()if k!='results'}))


if __name__=='__main__':main()
