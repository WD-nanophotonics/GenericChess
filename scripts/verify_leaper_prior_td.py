"""Replay a saved natural-prefix pilot without search or further training.

Checks real GameSession paths and literal candidate PV targets. TD arithmetic is
checked via the equivalent backward lambda-error sum, not the online trainer.
Uses shared Core: semantic consistency evidence, not an independent game oracle.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.leaper_design import compile_rule, ruleset_from_dict, GameSession, state_sha, record_value
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.actions import action_to_dict
from generic_chess.learning.incremental import FixedScaleSessionEnv, Model, SessionChoice, MATE
from generic_chess.session.serialization import deserialize_game_record

def canon(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'))

def replay(c,record):
    return GameSession.replay(c,deserialize_game_record(canon(record)))

def match(s,raw):
    # Candidate target exporter uses action_to_dict; source-style opponent
    # receipts use the dataclass record_value representation. Match complete
    # semantic actions in their actual saved representation, never coordinates
    # alone or a guessed mapping.
    choices=[a for a in s.legal_actions() if action_to_dict(a)==raw or record_value(a)==raw]
    assert len(choices)==1
    return choices[0]

def verify(packet):
    began=perf_counter(); counts=Counter()
    cfg=packet['config']; inputs=packet['inputs']; slots=packet['slots']
    worlds=inputs['worlds']; roots={(r['phase'],r['world'],r['index']):r for r in inputs['roots']}
    source=ROOT/cfg['source_file']
    source_raw=source.read_bytes()
    assert hashlib.sha256(source_raw).hexdigest()==cfg['source_sha256']
    source_worlds={str(w['world']):w for w in json.loads(gzip.decompress(source_raw))['runs']['strongfoe']['files']['inputs.json']['worlds']}
    assert worlds=={str(k):source_worlds[str(k)] for k in cfg['world_ids']}
    cs={int(k):compile_rule(ruleset_from_dict(w['rule'])) for k,w in worlds.items()}
    assert cfg['world_ids']==[0,30,12,42]
    assert cfg['train']['eta']==.05 and cfg['train']['lam']==.95 and cfg['train']['scale']==10.
    episodes=cfg['train']['episodes_per_world']
    assert episodes in (4,64)
    assert len(slots)==4*episodes+16*len(cfg['eval']['arms']) and len(roots)==4*episodes+8
    def guard():
        if role_stop_requested() or perf_counter()-began>600:
            raise RuntimeError('VERIFY_STOP_OR_CAP')
    for wi,world in enumerate(cfg['world_ids']):
        c=cs[world]; w=worlds[str(world)]
        assert (w['code_world'],w['layout_index'])==([0,6,12,18][wi],wi%2)
        assert w['board_size']==6
        for phase,index,prefix,seed in (
            [('train',k,8,cfg.get('seed_base',2026102300)+wi*cfg.get('seed_stride',100)+k) for k in range(episodes)]
            + [('eval',0,0,2026102300+wi*100+50),('eval',1,8,2026102300+wi*100+51)]
        ):
            guard(); root=roots[phase,world,index]; s=replay(c,w['initial_record']); rng=random.Random(seed)
            for _ in range(prefix):
                if s.state.terminal_status.is_terminal: break
                s.submit(rng.choice(tuple(s.legal_actions())))
            assert root['record']==record_value(s.to_record()) and root['id']==state_sha(s.state)
            assert root['seed']==seed and root['requested_prefix']==prefix and root['actual_prefix']==s.state.ply_count
            assert root['names']==[list(n) for n in FixedScaleSessionEnv(s,unit_type='A').names]
            counts['natural_roots']+=1
    models={}
    for world in cfg['world_ids']:
        values=worlds[str(world)]['price_profiles']['MOBILITY']['board_value_by_type']
        names=roots['train',world,0]['names']
        models[world]=[0. if kind=='hand' else values[t]/values['A'] for kind,t in names]
    rows={r['slot']:r for r in packet['games']}; paid=Counter()
    assert len(rows)==len(packet['games'])
    for slot in slots:
        guard()
        if slot['status']=='not_started':
            assert slot['slot'] not in rows and slot['utility']==[-1,1]
            continue
        row=rows[slot['slot']]
        for key in ['slot','phase','world','index','role','arm','utility']:
            assert row[key]==slot[key]
        root=roots[slot['phase'],slot['world'],slot['index']]; c=cs[slot['world']]; s=replay(c,root['record'])
        assert row['root']==state_sha(s.state)
        initial=models[slot['world']]
        if slot['arm']=='Unit': initial=[1. if k=='board' else 0. for k,t in root['names']]
        elif slot['arm']=='Mobility':
            v=worlds[str(slot['world'])]['price_profiles']['MOBILITY']['board_value_by_type']
            initial=[v[t]/v['A'] if k=='board' else 0. for k,t in root['names']]
        assert row['before']==initial and initial[0]==1.
        model=Model(initial); training_values=[]; gradients=[]; query_nodes=0; actual=0
        for qi,q in enumerate(row['queries']):
            guard(); assert q['id']==state_sha(s.state) and q['actor']==s.state.position.side_to_move
            if q['kind']=='candidate':
                assert q['actor']==slot['role'] and q['weights']==initial
                r=q['receipt']; query_nodes+=r['nodes']; paid[slot['phase']+'_candidate_queries']+=1; paid[slot['phase']+'_candidate_nodes']+=r['nodes']
                if not r['complete']:
                    assert r['action'] is None and r['value'] is None and qi==len(row['queries'])-1
                    continue
                leaf=copy(s)
                assert r['pv'] and r['pv'][0]==r['action']
                for a in r['pv']:
                    guard(); leaf.submit(match(leaf,a)); counts['literal_PV_edges']+=1
                env=FixedScaleSessionEnv(leaf,unit_type='A'); outcome=env.terminal()
                if outcome is None:
                    assert not r['pv_terminal'] and list(env.features())==r['pv_phi']
                    assert len(r['pv'])==r['completed_depth']
                    assert math.isclose(model.raw(env.features()),r['value'],abs_tol=1e-10,rel_tol=1e-12)
                    grad=model.gradient(env.features())
                    counts['nonterminal_targets']+=1
                else:
                    assert r['pv_terminal'] and r['value']==outcome*MATE
                    grad=[0.]*len(initial); counts['terminal_targets']+=1
                training_values.append(math.tanh(r['value']/10.)); gradients.append(grad)
                action=r['action']; counts['candidate_queries']+=1
            else:
                assert q['actor']!=slot['role']
                r=q['decision']; query_nodes+=r['nodes']+r['qnodes']; paid[slot['phase']+'_opponent_queries']+=1; paid[slot['phase']+'_opponent_nodes']+=r['nodes']+r['qnodes']
                leaf=copy(s)
                for a in r['principal_variation']:
                    guard(); leaf.submit(match(leaf,a)); counts['reference_PV_edges']+=1
                action=r['action']
                if action is None:
                    assert qi==len(row['queries'])-1
                    continue
                if r['principal_variation']: assert r['principal_variation'][0]==action
                counts['opponent_queries']+=1
            s.submit(match(s,action)); actual+=1
        outcome=FixedScaleSessionEnv(s,unit_type='A').terminal()
        assert record_value(s.to_record())==row['final_record'] and record_value(s.result)==row['terminal']
        assert outcome==row['outcome'] and query_nodes==row['nodes'] and actual==row['added']
        utility=[-1,1] if outcome is None else [outcome*(1 if slot['role']==0 else -1)]*2
        assert utility==row['utility']
        if slot['phase']=='train':
            values=training_values
            errors=[values[i+1]-values[i] for i in range(len(values)-1)]
            if values and outcome is not None: errors.append(outcome-values[-1])
            delta=[.05*sum(gradients[t][j]*sum(.95**(k-t)*errors[k] for k in range(t,len(errors))) for t in range(len(errors))) for j in range(len(initial))]
            expected=[w+d for w,d in zip(initial,delta)]; expected[0]=1.
            assert all(math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12) for a,b in zip(expected,row['after']))
            assert row['update']['samples']==len(errors) and row['update']['observed_searches']==len(values)
            assert row['update']['censored']==(outcome is None)
            loss=sum(e*e/2 for e in errors)/max(1,len(errors))
            assert math.isclose(loss,row['update']['loss'],abs_tol=1e-12,rel_tol=1e-12)
            models[slot['world']]=row['after']
            counts['TD_terms']+=len(errors); counts['actual_TD_updates']+=row['after']!=row['before']
        else:
            assert row['after']==row['before'] and row['update'] is None
        counts['actual_moves']+=actual; counts['games']+=1; counts['actual_terminal']+=outcome is not None
    assert packet['summary']['paid']==paid
    assert packet['summary']['attempted']==len(rows)
    assert packet['summary']['terminal']==counts['actual_terminal']
    assert packet['summary']['not_started']==[s['slot'] for s in slots if s['status']=='not_started']
    assert packet['models']=={str(k):v for k,v in models.items()}
    return dict(status='PASS',counts=counts,seconds=perf_counter()-began,scope='Saved legal histories/PVs and backward TD arithmetic via shared Core; no new search/training, no independent WDL or population inference.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('packet',type=Path); a=p.parse_args()
    packet=json.loads(gzip.decompress(a.packet.read_bytes()))
    print(json.dumps(verify(packet),ensure_ascii=True))
