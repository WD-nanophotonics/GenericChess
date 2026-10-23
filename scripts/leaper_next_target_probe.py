"""Consume committed PRIMARY typed5x5 inputs through AUX's literal learner path.

No rule generation, fitness game, model update, oracle sampler or default change.
One source-order pass; this target-portability/exposure result is not strength.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import gzip,hashlib,json,sys
from pathlib import Path
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.leaper_prior_td_pilot import *

def run(source,output):
    output.mkdir(parents=True,exist_ok=False); raw=source.read_bytes(); d=json.loads(gzip.decompress(raw)); worlds=d['next_proposal']['inputs.json']['worlds']
    cfg=dict(question='Do complete committed5x5 INITIAL/uniform8 inputs expose literal learner targets and trainable material gradients?',source_commit=SOURCE_SHA,source_sha256=hashlib.sha256(raw).hexdigest(),selection='ALL96typedinputs in source order;no WDL/price/deadzone filtering;zero games/updates',whole_seconds=180,depth=4,nodes=8192,query_seconds=2,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    write(output/'config.json',cfg); write(output/'worlds.json',worlds); slots=[dict(slot=i,world=w['world'],status='not_started') for i,w in enumerate(worlds)];write(output/'slots.json',slots)
    began=perf_counter(); cs={}; counts=Counter()
    def cancel():
        if role_stop_requested():raise BudgetEnd('role_stop')
        if perf_counter()-began>=180:raise BudgetEnd('whole_cap')
    for slot,w in zip(slots,worlds):
        try:cancel()
        except BudgetEnd:break
        fp=w['fingerprint']
        if fp not in cs:cs[fp]=compile_rule(ruleset_from_dict(w['rule']))
        s=restore(cs[fp],w['initial_record']); env=FixedScaleSessionEnv(s,unit_type='A'); env.replay(); weights=prior(w,env.names,'Mobility')
        r=search(env,Model(weights),depth=4,nodes=8192,seconds=min(2.,max(.001,180-(perf_counter()-began))),pv_reserve_fraction=.1,cancel=cancel)
        receipt={k:v for k,v in asdict(r).items() if k not in ('action','pv_choices')};receipt.update(action=None if r.action is None else action_to_dict(r.action.action),pv=[action_to_dict(x.action) for x in r.pv_choices])
        row=dict(slot=slot['slot'],world=w['world'],context=w['context'],id=state_sha(s.state),weights=weights,receipt=receipt)
        write(output/f"query-{slot['slot']}.json",row);slot['status']='complete' if r.complete else 'UNKNOWN';write(output/'slots.json',slots)
        counts['queries']+=1;counts['nodes']+=r.nodes;counts['complete']+=r.complete;counts['nonterminal_targets']+=r.complete and not r.pv_terminal;counts['terminal_returns']+=r.complete and r.pv_terminal;counts['nonzero_trainable_PV_features']+=r.complete and r.pv_phi is not None and any(r.pv_phi[1:3]);counts['D'+str(r.completed_depth)]+=1
    write(output/'summary.json',dict(status='CLOSED',seconds=perf_counter()-began,planned=len(slots),paid=counts,not_started=[s['slot'] for s in slots if s['status']=='not_started'],games=0,updates=0));print(json.dumps(load(output/'summary.json')),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.source,a.output)
