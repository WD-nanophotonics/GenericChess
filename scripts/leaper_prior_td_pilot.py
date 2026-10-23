"""Bounded AUX control: free priors and the SAME episode learner on natural starts.

Consumes committed PRIMARY inputs; does not generate/select/screen rules. Plan
before run. Existing GameSession, public search and TDLeafEpisode own semantics.
This small exposed-rule study is not a held-out population or price estimator.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.leaper_design import compile_rule, ruleset_from_dict, GameSession, state_sha, record_value, make_player
from scripts.leaper_microgames import role_stop_requested
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.incremental import FixedScaleSessionEnv, Model, TDLeafEpisode, BudgetEnd
from generic_chess.learning.mainline_search import search

SOURCE_SHA = '1ac1f97a74b26015ffb73dcb612333923a6d61d0'
WORLD_IDS = (0, 30, 12, 42)  # code indices 0,6,12,18; alternating existing layouts.

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')

def load(path):
    return json.loads(path.read_bytes())

def restore(compiled, record):
    return GameSession.replay(compiled, deserialize_game_record(json.dumps(record)))

def prior(world, names, arm):
    values = world['price_profiles']['MOBILITY']['board_value_by_type']
    return [0. if kind == 'hand' else 1. if arm == 'Unit' else values[t] / values['A'] for kind, t in names]

def plan(output, source):
    output.mkdir(parents=True, exist_ok=False)
    raw = source.read_bytes()
    worlds = {w['world']: w for w in json.loads(gzip.decompress(raw))['runs']['strongfoe']['files']['inputs.json']['worlds']}
    selected = {str(i): worlds[i] for i in WORLD_IDS}
    roots = []
    for wi, world in enumerate(selected.values()):
        compiled = compile_rule(ruleset_from_dict(world['rule']))
        for phase, index, prefix, seed in (
            [('train', k, 8, 2026102300 + wi * 100 + k) for k in range(4)]
            + [('eval', 0, 0, 2026102300 + wi * 100 + 50), ('eval', 1, 8, 2026102300 + wi * 100 + 51)]
        ):
            s = restore(compiled, world['initial_record'])
            rng = random.Random(seed)
            for _ in range(prefix):
                if role_stop_requested():
                    raise RuntimeError('role stop during plan')
                if s.state.terminal_status.is_terminal:
                    break  # Retain early terminals; no replacement or outcome filtering.
                s.submit(rng.choice(tuple(s.legal_actions())))
            env = FixedScaleSessionEnv(s, unit_type='A')
            env.replay()
            roots.append(dict(world=world['world'], phase=phase, index=index, seed=seed,
                              requested_prefix=prefix, actual_prefix=s.state.ply_count,
                              record=record_value(s.to_record()), id=state_sha(s.state), names=env.names))
    slots = []
    for k in range(4):
        for world in WORLD_IDS:
            slots.append(dict(slot=len(slots), phase='train', world=world, index=k,
                              role=k % 2, arm='TD', status='not_started', utility=[-1, 1]))
    for context in range(2):
        for wi, world in enumerate(WORLD_IDS):
            for role in (0, 1):
                arms = ['Unit', 'Mobility', 'TD']
                shift = (wi + role + context) % 3
                arms = arms[shift:] + arms[:shift]
                if (wi + role + context) % 2:
                    arms.reverse()
                for arm in arms:
                    slots.append(dict(slot=len(slots), phase='eval', world=world, index=context,
                                      role=role, arm=arm, status='not_started', utility=[-1, 1]))
    config = dict(schema='leaper_prior_td_pilot_v1', source_commit=SOURCE_SHA,
                  source_file=str(source.relative_to(ROOT)), source_sha256=hashlib.sha256(raw).hexdigest(),
                  world_ids=WORLD_IDS, selection='Four metadata-spaced code indices 0,6,12,18 with alternating SOURCE layout0/1. No outcome, WDL, first-divergence, material imbalance or search-based selection. Exposed rules, prospectively frozen NEW prefix seeds; no independent-rule holdout claim.',
                  question='Does zero-trained Mobility transfer to initial/uniform8 starts, and does four-episode SAME-learner TD add conditional play utility beyond that prior?',
                  train=dict(episodes_per_world=4, prefixes=8, role_order=[0,1,0,1], eta=.05, lam=.95, scale=10., seconds=600),
                  eval=dict(contexts=['INITIAL', 'uniform8'], roles=[0,1], arms=['Unit','Mobility','TD'], seconds=1200),
                  candidate=dict(backend='generic_chess.learning.mainline_search.search', depth=4, nodes=8192, seconds=2., pv_reserve_fraction=.1, qmax=0, qhard=0, equal_capture_order_values=True, fresh_player=True),
                  opponent=dict(policy='STATIC_ADAPTER', depth=3, nodes=8192, seconds=2., qmax=0, qhard=8, persistent_within_game=True),
                  game_seconds=90, game_nodes=250000, horizon=128, whole_seconds=1800, expected_seconds=1000,
                  decision='Finite feasibility, actual target/update exposure and paired utility/cost. No hyperparameter/model selection; all post-training models freeze, including partial/no-update models. UNKNOWN and missing slots stay in denominator. No old cohort cap refill, no WDL gate or oracle TRAIN inputs.',
                  cheaper_alternative='Old eight posthoc divergence histories show free-prior utility but cannot answer natural-prefix transfer or incremental TD. Reuse source worlds instead of a new rule screen.',
                  producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write(output / 'config.json', config)
    write(output / 'inputs.json', dict(worlds=selected, roots=roots))
    write(output / 'slots.json', slots)
    (output / 'source.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(status='PLANNED', slots=len(slots), train=16, eval=48, roots=len(roots), terminal_roots=sum(r['actual_prefix'] < r['requested_prefix'] for r in roots))), flush=True)

def run(output):
    cfg = load(output / 'config.json')
    assert cfg['producer_sha256'] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    # Exclusive marker prevents a second writer or a cap reset on resume.
    with (output / 'execution.json').open('x', encoding='utf-8') as f:
        json.dump(dict(status='RUNNING', producer_sha256=cfg['producer_sha256']), f)
    inputs = load(output / 'inputs.json'); slots = load(output / 'slots.json')
    assert all(s['status'] == 'not_started' for s in slots)
    worlds = inputs['worlds']
    compiled = {int(k): compile_rule(ruleset_from_dict(w['rule'])) for k,w in worlds.items()}
    roots = {(r['phase'],r['world'],r['index']):r for r in inputs['roots']}
    models = {}
    for world in WORLD_IDS:
        r = roots['train',world,0]
        models[world] = Model(prior(worlds[str(world)], r['names'], 'Mobility'))
    began = perf_counter(); phase_start = began; phase = 'train'; paid = Counter()
    for slot in slots:
        if slot['phase'] != phase:
            phase = slot['phase']; phase_start = perf_counter()
            write(output / 'frozen-models.json', {str(k): v.weights for k,v in models.items()})
        phase_allowance = cfg[phase]['seconds']
        if role_stop_requested() or perf_counter()-began >= cfg['whole_seconds']:
            break
        if perf_counter()-phase_start >= phase_allowance:
            continue
        root = roots[phase,slot['world'],slot['index']]; w=worlds[str(slot['world'])]; c=compiled[slot['world']]
        s=restore(c,root['record']); env=FixedScaleSessionEnv(s,unit_type='A')
        assert state_sha(s.state)==root['id']
        model=models[slot['world']] if slot['arm']=='TD' and phase=='train' else Model(models[slot['world']].weights if slot['arm']=='TD' else prior(w,env.names,slot['arm']))
        before=list(model.weights); learner=TDLeafEpisode(eta=.05,lam=.95) if phase=='train' else None
        foe=make_player(c,'STATIC_ADAPTER',w); gamebeg=perf_counter(); queries=[]; nodes=0; added=0; censor=None
        def cancel():
            if role_stop_requested(): raise BudgetEnd('role_stop')
            if perf_counter()-began >= cfg['whole_seconds']: raise BudgetEnd('whole_cap')
            if perf_counter()-phase_start >= phase_allowance: raise BudgetEnd('phase_cap')
            if perf_counter()-gamebeg >= cfg['game_seconds']: raise BudgetEnd('game_cap')
        class Token:
            last=0.; stopped=False
            def is_cancelled(self):
                if perf_counter()-self.last >= .05:
                    self.last=perf_counter()
                    try: cancel()
                    except BudgetEnd: self.stopped=True
                return self.stopped
        while not s.state.terminal_status.is_terminal:
            try: cancel()
            except BudgetEnd as e: censor=str(e); break
            if added>=cfg['horizon'] or nodes>=cfg['game_nodes']:
                censor='caller_cap'; break
            actor=s.state.position.side_to_move; qid=state_sha(s.state)
            remaining=min(2.,cfg['whole_seconds']-(perf_counter()-began),phase_allowance-(perf_counter()-phase_start),cfg['game_seconds']-(perf_counter()-gamebeg))
            if remaining<=0: censor='time_cap'; break
            if actor==slot['role']:
                receipt=search(FixedScaleSessionEnv(s,unit_type='A'),model,depth=4,nodes=min(8192,cfg['game_nodes']-nodes),seconds=remaining,pv_reserve_fraction=.1,cancel=cancel)
                raw={k:v for k,v in asdict(receipt).items() if k not in ('action','pv_choices')}
                raw.update(action=None if receipt.action is None else action_to_dict(receipt.action.action),pv=[action_to_dict(x.action) for x in receipt.pv_choices])
                queries.append(dict(id=qid,actor=actor,kind='candidate',weights=before,receipt=raw))
                nodes+=receipt.nodes; paid[phase+'_candidate_queries']+=1; paid[phase+'_candidate_nodes']+=receipt.nodes
                if not receipt.complete or receipt.action is None: censor='candidate:'+receipt.reason; break
                if learner is not None: learner.observe(model,receipt)
                action=receipt.action.action
            else:
                receipt=foe.choose_action(s,SearchLimits(max_depth=3,max_nodes=min(8192,cfg['game_nodes']-nodes),max_time_seconds=remaining,quiescence_max_depth=0,quiescence_hard_max_depth=8),cancel_token=Token())
                queries.append(dict(id=qid,actor=actor,kind='opponent',decision=record_value(receipt)))
                nodes+=receipt.nodes+receipt.qnodes; paid[phase+'_opponent_queries']+=1; paid[phase+'_opponent_nodes']+=receipt.nodes+receipt.qnodes
                if receipt.action is None: censor='opponent:'+receipt.termination_reason; break
                action=receipt.action
            s.submit(action); added+=1
        env=FixedScaleSessionEnv(s,unit_type='A'); outcome=env.terminal(); update=learner.finish(model,outcome) if learner is not None else None
        utility=[-1,1] if outcome is None else [outcome*(1 if slot['role']==0 else -1)]*2
        result=dict(slot=slot['slot'],phase=phase,world=slot['world'],index=slot['index'],role=slot['role'],arm=slot['arm'],root=root['id'],before=before,after=list(model.weights),queries=queries,final_record=record_value(s.to_record()),terminal=record_value(s.result),outcome=outcome,utility=utility,censor=censor if outcome is None else None,update=update,seconds=perf_counter()-gamebeg,added=added,nodes=nodes)
        write(output / f"game-{slot['slot']}.json",result)
        slot.update(status='finished' if outcome is not None else 'censored',utility=utility,censor=result['censor'])
        write(output / 'slots.json',slots)
        write(output / 'models.json',{str(k):v.weights for k,v in models.items()})
        print(json.dumps({k:result[k] for k in ['slot','phase','world','arm','utility','added','seconds','update']},ensure_ascii=True),flush=True)
    write(output / 'summary.json',dict(status='CLOSED',seconds=perf_counter()-began,paid=paid,planned=len(slots),attempted=sum(s['status']!='not_started' for s in slots),terminal=sum(s['status']=='finished' for s in slots),not_started=[s['slot'] for s in slots if s['status']=='not_started']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['plan','run']); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source',type=Path,default=ROOT/'docs/research/data/leaper_tie_truth_20261023/strongfoe-source.json.gz')
    a=p.parse_args()
    if a.mode=='plan': plan(a.output,a.source.resolve())
    else: run(a.output)
