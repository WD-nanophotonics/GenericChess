"""Portable replay of the bounded learner and history evidence, no Player."""
from pathlib import Path
from copy import copy
from collections import Counter
from dataclasses import replace
import argparse,gzip,hashlib,json,time
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from scripts.leaper_design import compile_rule,ruleset_from_dict,state_sha,match_action
from scripts.leaper_h6_later_price_exposure import analyze
from scripts.leaper_h6_later_records import ContextBinder
from scripts.verify_leaper_h6_later_exposure import verify as verify_panel
from scripts.verify_leaper_one_epoch import verify as verify_epoch
from scripts.verify_leaper_epoch_control import verify as verify_control
from scripts.leaper_clock_rebinding import verify_history_draw_safety
from scripts.verify_leaper_single_parity import literal_value
from scripts.leaper_frozen_pair_truth import read_frozen
from scripts.leaper_explorer_truth import load,digest
from scripts.research_record import record_value
from tools.local_agent.slack_transport import save_plugin_original


def replay_query(session,weights,receipt,action):
    if not receipt['complete']or not receipt['pv_choices']or receipt['pv_choices'][0]!=receipt['action']:raise ValueError('completed query/PV differs')
    leaf=copy(session)
    from generic_chess.core.actions import action_to_dict
    for index,choice in enumerate(receipt['pv_choices']):
        if choice['kind']!='ACTION':raise ValueError('unsupported declaration')
        a=match_action(leaf,choice['action'])
        if index==0 and action_to_dict(a)!=action:raise ValueError('retained chosen action differs')
        leaf.submit(a)
    env=FixedScaleSessionEnv(leaf,unit_type='A');model=Model(weights);actual=env.terminal();phi=None if actual is not None else list(env.features())
    if receipt['pv_phi']!=phi or receipt['pv_terminal']!=(actual is not None):raise ValueError('retained literal leaf differs')
    v=MATE*actual if actual is not None else model.raw(phi)
    if receipt['value']!=v:raise ValueError('retained literal score differs')
    return len(receipt['pv_choices'])


def verify(directory,output):
    directory=Path(directory);output=Path(output)
    if output.exists():raise ValueError('fresh ignored output required')
    output.mkdir(parents=True);tick=time.perf_counter();manifest=load(directory/'learning-manifest.json');raw=(directory/'learning-evidence.json.gz').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['compressed_sha256']:raise ValueError('compressed evidence digest differs')
    body=gzip.decompress(raw)
    if hashlib.sha256(body).hexdigest()!=manifest['decoded_sha256']:raise ValueError('decoded evidence digest differs')
    packet=json.loads(body);docs={}
    for key,text in packet['documents_utf8'].items():
        payload=text.encode()
        if hashlib.sha256(payload).hexdigest()!=manifest['document_sha256'][key]:raise ValueError('original scientific document differs')
        save_plugin_original(output/key,payload)
        docs[key]=[json.loads(s)for s in text.splitlines()]if key.endswith('jsonl')else json.loads(text)
    for key,text in packet['data_only_source_capsules_utf8'].items():
        if hashlib.sha256(text.encode()).hexdigest()!=manifest['capsule_sha256'][key]:raise ValueError('data-only source capsule differs')
    # Source capsules are never imported, executed or written as runnable code.
    base=Path('docs/research/data/leaper_h6_initial_truth_20261023')
    derived=analyze(base,output/'recomputed-exposure')
    if {k:v for k,v in derived.items()if k!='seconds'}!={k:v for k,v in docs['exposure.json'].items()if k!='seconds'}:raise ValueError('fixed incoming exposure differs')
    panel=verify_panel(docs['panel.json'],base,old=docs['initial-queries.json'])
    epoch=verify_epoch(docs['epoch-plan.json'],docs['epoch-result.json'],docs['epoch-episodes.jsonl'],base)
    if docs['control-result.json']['plan']['epoch_digest']!=digest(docs['epoch-result.json']):raise ValueError('paired source epoch digest differs')
    control=verify_control(docs['control-result.json'],docs['control-episodes.jsonl'],docs['epoch-episodes.jsonl'],base)
    binder=ContextBinder(base);initial=docs['initial-queries.json'];counts=Counter()
    witness_by={r['state_sha']:r for r in docs['literal-witness.json']['rows']}
    for row in initial['rows']:
        w=witness_by[row['state_sha']];c=compile_rule(ruleset_from_dict(w['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(w['record'])));env=FixedScaleSessionEnv(s,unit_type='A');weights=[row['B']if n==('board','B')else 1. for n in env.names]
        counts['initial_PV_Core_edges']+=replay_query(s,weights,row['receipt'],row['action'])
        if row['exact_WDL']!=next(b['exact_WDL_for0']for b in w['branches']if b['action']==row['action']):raise ValueError('initial diagnostic quality differs')
    for w in docs['literal-witness.json']['rows']:
        c=compile_rule(ruleset_from_dict(w['rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(w['record'])));actual=literal_value(s,Counter(),start=time.perf_counter())
        if actual!=w['root_WDL']:raise ValueError('literal diagnostic root differs')
        from generic_chess.core.actions import action_from_dict
        for b in w['branches']:
            ch=copy(s);ch.submit(action_from_dict(b['action']));v=-literal_value(ch,Counter(),start=time.perf_counter())
            if b['exact_WDL_for0']!=v:raise ValueError('literal diagnostic action differs')
    learned=docs['learned-decisions.json']
    for row in learned['rows']:
        candidate=docs['panel.json']['bound_contexts'][row['context']];s,_=binder.bind(candidate)
        expected=next(m['weights']for m in docs['epoch-result.json']['models']if m['family']==row['family'])
        if expected!=row['weights']:raise ValueError('queried learned epoch differs')
        counts['learned_PV_Core_edges']+=replay_query(s,row['weights'],row['receipt'],row['action'])
        vv={r['exact_WDL']for r in docs['panel.json']['rows']if r['context']==row['context']and r['action']==row['action']}
        if vv!={row['after_WDL']}or row['after_WDL']!=0:raise ValueError('learned diagnostic quality differs')
    safety=[]
    for name,recordkey in [('closed-draw-witness.json.gz','root_record'),('current-root-barrier.json.gz','record')]:
        r=load(directory/name);safety.append(verify_history_draw_safety(dict(target_rule=r['rule'],positions=r['positions']),r['rule'],r[recordkey],r['safety']))
    clocks=load(directory/'literal-clocks.json.gz');worlds,_,_=read_frozen('docs/research/data/leaper_forward_width_20261024/screen-evidence.json.gz');literal_nodes=0
    for row in clocks['rows']:
        w=next(w for w in worlds if w['n']==4 and w['mask']==row['mask']and w['rank']==row['source_rank'])
        rule=replace(ruleset_from_dict(w['rule']),max_ply=6)
        if record_value(rule)!=row['H6_rule']:raise ValueError('controlled H6 full rule differs')
        c=compile_rule(rule);s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
        if state_sha(s.state)!=row['state_sha']:raise ValueError('literal clock full history differs')
        cc=Counter();v=literal_value(s,cc,start=time.perf_counter())
        if v!=row['value']or dict(cc)!=row['literal_counts']:raise ValueError('complete literal clock tree differs')
        literal_nodes+=cc['nodes']
    result=dict(verified=True,panel=panel,epoch=epoch,control=control,diagnostic_counts=dict(counts),safety=safety,literal_clock_roots=len(clocks['rows']),literal_clock_nodes=literal_nodes,
        new_Player_queries=0,new_experimental_training_episodes=0,data_only_capsules=len(packet['data_only_source_capsules_utf8']),seconds=time.perf_counter()-tick,
        qualification='Exposure/records/PVs/libraryupdates replayed, notindependentengine orheldoututility. Abstractbarriercensus andlocalterminalcredit remain producerdiagnosticswithhashes,notclaimed repeatedhere.')
    (output/'verification.json').write_text(json.dumps(result,indent=2));print({k:v for k,v in result.items()if k not in('panel','epoch','control','safety')});return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.directory,a.output)
