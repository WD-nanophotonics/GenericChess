"""Plan a NEW bounded learning-budget check; use the existing pilot runner.

The four-episode pilot stays closed at its original slots/caps. New TRAIN seed
stream, no warm continuation, no parameter/checkpoint selection. Existing EVAL
roots/baselines are explicitly exposed controls, not additional test samples.
"""
from copy import deepcopy
import argparse
import hashlib
from pathlib import Path
import random
from scripts.leaper_prior_td_pilot import (
    ROOT, WORLD_IDS, load, write, compile_rule, ruleset_from_dict, restore,
    record_value, state_sha, FixedScaleSessionEnv, role_stop_requested,
)

def plan(previous, output):
    old=load(previous/'config.json'); ins=load(previous/'inputs.json')
    output.mkdir(parents=True,exist_ok=False)
    roots=[deepcopy(r) for r in ins['roots'] if r['phase']=='eval']
    for wi,world in enumerate(WORLD_IDS):
        w=ins['worlds'][str(world)]; c=compile_rule(ruleset_from_dict(w['rule']))
        for k in range(64):
            if role_stop_requested(): raise RuntimeError('role_stop')
            seed=202610230000+wi*1000+k; rng=random.Random(seed); s=restore(c,w['initial_record'])
            for _ in range(8):
                if s.state.terminal_status.is_terminal: break
                s.submit(rng.choice(tuple(s.legal_actions())))
            env=FixedScaleSessionEnv(s,unit_type='A'); env.replay()
            roots.append(dict(world=world,phase='train',index=k,seed=seed,requested_prefix=8,
                              actual_prefix=s.state.ply_count,record=record_value(s.to_record()),
                              id=state_sha(s.state),names=env.names))
    slots=[]
    for k in range(64):
        for world in WORLD_IDS:
            slots.append(dict(slot=len(slots),phase='train',world=world,index=k,role=k%2,
                              arm='TD',status='not_started',utility=[-1,1]))
    for context in range(2):
        for world in WORLD_IDS:
            for role in (0,1):
                slots.append(dict(slot=len(slots),phase='eval',world=world,index=context,role=role,
                                  arm='TD',status='not_started',utility=[-1,1]))
    cfg=deepcopy(old)
    cfg.update(schema='leaper_prior_td_budget_v1',
               question='Does a predeclared NEW64-episode seed stream change conditional play beyond the free Mobility control, at a measured total learning cost?',
               whole_seconds=3600,expected_seconds=2900,
               budget_basis='First16 actual training games cost161.283s;256 games at that mean about2581s, plus16eval games. HARD whole3600s,train3000s,eval600s. Under120min including the preceding pilot; no long-run split or old-cap reset.',
               seed_base=202610230000,seed_stride=1000,
               selection=old['selection']+' NEW TRAIN seeds base202610230000+world-order*1000+episode. Reinitialize Mobility, no pilot-model continuation. EVAL roots already exposed; paired free controls reused from the separately closed pilot, not additional independent tests.',
               decision='Measure one fixed final budget, all256 TRAIN slots and16 TD EVAL slots. No checkpoint selection, hyperparameter adjustment, missing-slot refill or outcome-driven rule/root selection. Contrast against the prior exposed EVAL cohort only; cannot generalize to new rules.',
               planner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    cfg['train'].update(episodes_per_world=64,role_order=[0,1]*32,seconds=3000)
    cfg['eval'].update(arms=['TD'],seconds=600)
    write(output/'config.json',cfg); write(output/'inputs.json',dict(worlds=ins['worlds'],roots=roots)); write(output/'slots.json',slots)
    (output/'source.py').write_bytes((ROOT/'scripts/leaper_prior_td_pilot.py').read_bytes())
    (output/'planner.py').write_bytes(Path(__file__).read_bytes())
    print('NEW_BUDGET_PLANNED:256 train+16 eval;hard3600s;original pilot unchanged')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--previous',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); plan(a.previous,a.output)
