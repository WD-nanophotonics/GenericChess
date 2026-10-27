"""One bounded actual-consumer check; no learner update, games or new rules."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter, process_time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from generic_chess.core.actions import action_to_dict
from generic_chess.learning.incremental import BudgetEnd, FixedScaleSessionEnv, unchanged_model
from generic_chess.learning.mainline_search import search
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession

def choice(c):
    return dict(kind=c.kind,action=None if c.action is None else action_to_dict(c.action),declaration_id=c.declaration_id)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    began, cpu=perf_counter(),process_time()
    plan=json.loads(a.plan.read_bytes())
    b=Path(plan['input']).read_bytes()
    if sha256(b).hexdigest()!=plan['input_sha256']:
        raise ValueError('frozen selected input hash mismatch')
    worlds=json.loads(b)
    elapsed=(datetime.now().astimezone()-datetime.fromisoformat(plan['logical_origin'])).total_seconds()
    allowance=min(plan['whole_execution_seconds'],plan['whole_logical_check_minutes']*60-elapsed-180)
    if allowance<=0:
        raise ValueError('no execution allowance remains before reserved analysis')
    deadline=began+allowance
    def guard():
        for name in ('rollout','advisor','slack'):
            f=json.loads((ROOT/'.local_agent'/(name+'.json')).read_bytes())
            if f.get('user_paused') or f.get('stopped'):
                raise BudgetEnd('STOPPED_USER')
        if perf_counter()>=deadline:
            raise BudgetEnd('GLOBAL_TIME_CAP')
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    (a.output/'driver.py').write_bytes(Path(__file__).read_bytes())
    rows=[]; admissions=[]; failure=None
    with (a.output/'queries.jsonl').open('x',encoding='utf-8') as out:
        try:
            for index in plan['world_order']:
                guard()
                w=worlds[index]
                setup_wall,setup_cpu=perf_counter(),process_time()
                compiled=compile_ruleset_for_execution(ruleset_from_dict(w['rule']))
                session=GameSession.replay(compiled,deserialize_game_record(json.dumps(w['initial_record'])))
                env=FixedScaleSessionEnv(session,unit_type=plan['unit'])
                if compiled.ruleset_fingerprint!=w['fingerprint'] or session.to_record().actions:
                    raise ValueError('source fingerprint or empty initial-record changed')
                before=env.record()
                state=session.state
                admissions.append(dict(world=index,fingerprint=w['fingerprint'],compiled_type=type(compiled).__name__,has_ir=hasattr(compiled,'ir'),names=env.names,initial_record=before,initial_phi=env.features(),setup_wall=perf_counter()-setup_wall,setup_cpu=process_time()-setup_cpu))
                for depth in plan['depths']:
                    # Fixed alternation changes call order without changing paired inputs.
                    weights=plan['B_weights'] if (index+depth)%2 else list(reversed(plan['B_weights']))
                    for weight in weights:
                        guard()
                        if len(rows)>=plan['max_queries']:
                            raise BudgetEnd('FROZEN_QUERY_CAP')
                        model=unchanged_model([1.,weight,1.,1.])
                        frozen=list(model.weights)
                        own_wall,own_cpu=perf_counter(),process_time()
                        receipt=search(env,model,depth=depth,nodes=plan['query_nodes'],seconds=min(plan['query_seconds'],max(1e-9,deadline-perf_counter())),seed=plan['seed']+index,cancel=guard)
                        unchanged=(env.record()==before and env.session.state==state and not env.stack and model.weights==frozen)
                        row=dict(world=index,depth=depth,B=weight,wall=perf_counter()-own_wall,cpu=process_time()-own_cpu,state_and_model_unchanged=unchanged,complete=receipt.complete,completed_depth=receipt.completed_depth,attempted_depth=receipt.attempted_depth,reason=receipt.reason,nodes=receipt.nodes,value=receipt.value,pv_phi=receipt.pv_phi,pv_terminal=receipt.pv_terminal,choice=None if receipt.action is None else choice(receipt.action),pv=[choice(c) for c in receipt.pv_choices],attempts=[asdict(t) for t in receipt.attempts])
                        out.write(json.dumps(row,allow_nan=False)+'\n');out.flush()
                        rows.append(row)
                        if not unchanged:
                            raise ValueError('query mutated root/model')
                print(json.dumps(dict(world=index,returns=len(rows),wall=perf_counter()-began)),flush=True)
        except Exception as error:
            failure=dict(type=type(error).__name__,message=str(error))
    result=dict(scope='Actual modern learner search feasibility; no training update/full game/solver/rule generation/old-game analysis',source_input_sha256=sha256(b).hexdigest(),driver_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),actual_queries=len(rows),expected_queries=plan['max_queries'],missing_queries=plan['max_queries']-len(rows),wall=perf_counter()-began,cpu=process_time()-cpu,failure=failure,admissions=admissions)
    (a.output/'execution.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='admissions'}),flush=True)
if __name__=='__main__':
    main()
