"""Offline reader for the closed history consumer; never calls Player/prover.

Saved checker receipts provide proof authority; this reader independently binds
full public records/PVs and derives regret and cumulative failed-probe cost.
"""
from pathlib import Path
import hashlib,json
from math import isclose
from unittest.mock import patch
from generic_chess.core.actions import action_to_dict
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,SessionChoice,MATE
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import record_value

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'docs/research/data/aux_history_consumer_20261031'

def _check(condition,message):
    if not condition:raise ValueError(message)

def read_bound(folder=DEFAULT):
    folder=Path(folder)
    manifest=json.loads((folder/'manifest.json').read_bytes())
    for name,binding in manifest.items():
        raw=(folder/name).read_bytes()
        _check(len(raw)==binding['bytes']and hashlib.sha256(raw).hexdigest()==binding['sha256'],'member hash: '+name)
    packet={name:json.loads((folder/name).read_bytes())for name in (
        'observed.json','branch-observed.json','q0-observed.json',
        'q0-accounting-correction.json','q0-failed-dispatch-original.json','q0-protocol.json')}
    protocol=json.loads((folder/'protocol.json').read_bytes())
    binding=next(x for x in protocol['source_bindings']if x['path'].endswith('repeat4-counterexample.json'))
    raw=(ROOT/binding['path']).read_bytes()
    _check(hashlib.sha256(raw).hexdigest()==binding['sha256'],'source fixture binding')
    packet['fixture']=json.loads(raw)
    return packet

def audit(packet):
    root=packet['observed.json'];branch=packet['branch-observed.json']
    q=packet['q0-observed.json'];correction=packet['q0-accounting-correction.json']
    failed=packet['q0-failed-dispatch-original.json'];protocol=packet['q0-protocol.json'];fixture=packet['fixture']
    _check(root['root_summary']['actor']==1 and root['source_values_for0']==[0,1],'root perspective')
    _check(root['actual_WIN_verification']['verified']and root['actual_DRAW_verification']['verified'],'saved proof authority')
    safe=root['matched_root_policy']['common_certified_optimal_action']
    legal=root['matched_root_policy']['coverage'][0]['rows']
    key=lambda action:json.dumps(action,sort_keys=True,separators=(',',':'))
    legal_keys={key(x['action'])for x in legal}
    _check(len(legal)==len(legal_keys)==4,'root action set')
    losses=set()
    _check(len(branch['rows'])==4,'branch count')
    _check({key(x['action'])for x in branch['rows']}==legal_keys,'branch exact action coverage')
    for row in branch['rows']:
        valid=row['verified_check']['verified']
        _check(row['successor_terminal']=='ongoing','branch terminal claim')
        if valid:
            _check(row['child_value_for0_bounds']==[1,1]and row['root_actor1_regret_bounds']==[1,1],'loss bound')
            losses.add(key(row['action']))
        else:
            _check(row['classification']=='UNKNOWN'and row['child_value_for0_bounds']==[-1,1],'failed proof is UNKNOWN')
    _check(len(losses)==3 and key(safe)in legal_keys-losses,'safe versus strict loss partition')
    # Accounting is independent of the raw second-dispatch counter.
    actual=failed['actual_Player_calls']+q['actual_Player_calls']
    _check(actual==correction['actual_Player_calls']==5,'cumulative Player cost')
    _check(protocol['budget']['Player_calls']==correction['planned_calls']==4<actual,'exceeded frozen cap')
    _check(failed['rows']==[]and failed['actual_Player_calls']==1,'lost first return retained')
    _check(correction['status']=='CAP_EXCEEDED_CLOSED_NO_REFILL','closed failure scope')
    slots=[(row['history'],row['depth'])for row in q['rows']]
    expected=[(slot['history'],slot['depth'])for slot in protocol['slots']]
    _check(slots==expected and len(set(slots))==4,'second dispatch exact slots')
    _check(sum(row['receipt']['nodes']for row in q['rows'])==correction['second_dispatch_nodes']==136,'persisted node cost')
    compiled=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(fixture['rule']))
    source={('DRAW'if row['value']==0 else'WIN'):row for row in fixture['rows']}
    out=[];submits=0
    real_submit=GameSession.submit
    def counted(session,action):
        nonlocal submits
        submits+=1
        return real_submit(session,action)
    with patch.object(GameSession,'submit',counted):
        for row in q['rows']:
            name=row['history'];receipt=row['receipt'];raw=row['literal_leaf_record']
            _check(row['actual_root_actor']==1 and row['actual_root_value_for0']==source[name]['value'],'named root perspective/value')
            prefix=source[name]['record']['actions'];choices=receipt['pv_choices'];suffix=raw['actions'][len(prefix):]
            _check(raw['actions'][:len(prefix)]==prefix,'full history prefix')
            _check(receipt['complete']and receipt['completed_depth']==row['depth'],'completed literal depth')
            _check(len(choices)==len(suffix)==row['depth']and choices[0]==receipt['action'],'PV length/first choice')
            record=deserialize_game_record(json.dumps(raw))
            _check([record_value(SessionChoice('ACTION',action=a))for a in record.actions[len(prefix):]]==choices,'typed PV versus public record')
            _check(action_to_dict(record.actions[len(prefix)])==row['selected_action'],'selected exact semantic action')
            _check(key(row['selected_action'])in legal_keys,'selected action root membership')
            session=GameSession.replay(compiled,record)
            env=FixedScaleSessionEnv(session,unit_type='A');terminal=env.terminal();phi=env.features()
            model=Model([1.,0.],fixed=0,scale=10.)
            _check(terminal==row['literal_leaf_terminal']and list(phi)==row['literal_leaf_features'],'literal replay leaf')
            _check(row['model_weights_after']==[1.,0.],'no training')
            if terminal is None:
                _check(not receipt['pv_terminal']and receipt['pv_phi']==list(phi),'nonterminal features')
                _check(isclose(receipt['value'],model.raw(phi),rel_tol=0,abs_tol=1e-10),'literal material value')
            else:
                _check(receipt['pv_terminal']and receipt['pv_phi']is None and receipt['value']==MATE*terminal,'literal terminal value')
            _check(sum(x['nodes']for x in receipt['attempts'])==receipt['nodes'],'all paid attempt nodes')
            regret=0 if name=='WIN'or row['selected_action']==safe else 1
            _check(row['actor_regret_bounds']==[regret,regret],'actor regret sign/bounds')
            out.append(dict(history=name,depth=row['depth'],actor1_regret=regret,
                literal_leaf_terminal=terminal,terminal_status=session.result.status.value,
                pv_plies=len(suffix),paid_nodes=receipt['nodes']))
    _check(submits==52,'full replay cost52')
    return dict(rows=out,actual_Player_calls_all_dispatches=actual,planned_Player_calls=4,
        budget_compliant=False,claim_level='DESCRIPTIVE_PROTOCOL_FAILURE',
        total_paid_nodes='UNKNOWN_FIRST_RETURN_LOST',persisted_nodes_lower_bound=136,
        actual_offline_GameSession_submit_calls=submits,new_Player_calls=0,new_solver_calls=0,
        proof_scope='Joins already executed saved proof checks; does not independently re-prove WIN/DRAW.',
        quality_scope='Constructed exposed roots only; no training, strength, speed or general depth conclusion.')
