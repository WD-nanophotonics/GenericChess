"""Sixteen preplanned public queries; compare finite local critic slopes.

Mechanism diagnostic on exposed TRAIN histories, not a new training sampler or
strength test. The plan must already bind exact saved roots/weights/receipts.
"""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.leaper_prior_td_pilot import restore,compile_rule,ruleset_from_dict,state_sha,write,role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,BudgetEnd
from generic_chess.learning.mainline_search import search
from generic_chess.core.actions import action_to_dict

def run(planfile,pilotfile,output):
    output.mkdir(parents=True,exist_ok=False)
    plan=json.loads(planfile.read_bytes()); source=pilotfile.read_bytes(); pilot=json.loads(gzip.decompress(source))
    write(output/'plan.json',plan)
    write(output/'source.json',dict(pilot_sha256=hashlib.sha256(source).hexdigest(),producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    slots=[dict(slot=i,case=ci,world=case['world'],dimension=dim,sign=sign,status='not_started')
           for i,(ci,case,dim,sign) in enumerate((ci,case,dim,sign) for ci,case in enumerate(plan['cases']) for dim in (1,2) for sign in (-1,1))]
    write(output/'slots.json',slots); rows=[]; began=perf_counter()
    compiled={case['world']:compile_rule(ruleset_from_dict(pilot['inputs']['worlds'][str(case['world'])]['rule'])) for case in plan['cases']}
    def cancel():
        if role_stop_requested(): raise BudgetEnd('role_stop')
        if perf_counter()-began>=plan['whole_seconds']: raise BudgetEnd('whole_cap')
    for slot in slots:
        try: cancel()
        except BudgetEnd: break
        case=plan['cases'][slot['case']]; s=restore(compiled[case['world']],case['root_record']); assert state_sha(s.state)==case['id']
        weights=list(case['weights']); weights[slot['dimension']]+=slot['sign']*plan['epsilon']
        r=search(FixedScaleSessionEnv(s,unit_type='A'),Model(weights),depth=plan['depth'],nodes=plan['nodes'],seconds=min(plan['per_query_seconds'],max(.001,plan['whole_seconds']-(perf_counter()-began))),pv_reserve_fraction=.1,cancel=cancel)
        raw={k:v for k,v in asdict(r).items() if k not in ('action','pv_choices')}
        raw.update(action=None if r.action is None else action_to_dict(r.action.action),pv=[action_to_dict(x.action) for x in r.pv_choices])
        known=r.complete and r.completed_depth==case['baseline']['completed_depth']==4 and not r.pv_terminal
        slope=(r.value-case['baseline']['value'])/(slot['sign']*plan['epsilon']) if known else None
        expected=case['baseline']['pv_phi'][slot['dimension']]
        row=dict(slot)
        row.update(root=case['id'],weights=weights,receipt=raw,slope=slope,saved_leaf_coefficient=expected,matches=None if slope is None else abs(slope-expected)<1e-7,status='COMPLETE' if known else 'UNKNOWN')
        rows.append(row); write(output/f"query-{slot['slot']}.json",row)
        slot['status']=row['status']; write(output/'slots.json',slots)
    summary=dict(status='CLOSED',seconds=perf_counter()-began,planned=16,attempted=len(rows),known=sum(r['slope'] is not None for r in rows),mismatched=sum(r['matches'] is False for r in rows),nodes=sum(r['receipt']['nodes'] for r in rows),not_started=[s['slot'] for s in slots if s['status']=='not_started'])
    write(output/'summary.json',summary); print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('plan',type=Path); p.add_argument('pilot',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
    run(a.plan,a.pilot,a.output)
