"""Finite depth/cost/gradient diagnostic on all original contact roots.

Calls the existing learner's public search. Requested depth, completed depth,
literal chosen PV and free gradient stay separate; no strength or WDL label.
"""
from pathlib import Path
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,SOURCE,restore,write
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,BudgetEnd
from generic_chess.learning.mainline_search import search


def run(output):
    output.mkdir(parents=True,exist_ok=False);docs=source_documents();world=json.loads(docs['contact/inputs.json'])
    slots=[dict(id=i,depth=d,root=r,B=b)for i,(d,r,b)in enumerate((d,r,b)for d in(6,8,10,12)for r in range(4)for b in(1.,2.))]
    spec=dict(source=SOURCE,world=world,slots=slots,producer_sha256=L.sha(Path(__file__)),
        question='Does deeper actual completed search expose a B-sensitive chosen PV or a literal terminal continuation missed by the shallow unit pilot?',
        selection='All original4contactroots, both fixed B1/B2; no WDL/outcome filtering. Original D4 pilot supplies shallow reference; no retraining, default change or extra game campaign.',
        nodes_per_query=1000000,seconds_per_query=60,whole_seconds=1800,expected_seconds=1500,
        search='Unchanged mainline learner adapter, q0, same terminal authority, fresh Player, TT/order enabled with equal capture priority;10percent of same time reserved for literal PV replay.',
        stop='One cumulative cap, missing/incomplete retainUNKNOWN, no retry or old-cap refill. Larger work and actual completed depths are explicit; no equal-cost or speed claim.',
        logical_cost='Together with<=200s unitpilot,<=900s initcontrol,<=900s suffix and<=1800s verification/analysis, still<120min. These are distinct interventions, not splitting a >=120min run.')
    write(output/'spec.json',spec);c=L.compile_rule(L.ruleset_from_dict(world['rule']));began=time.perf_counter();rows=[]
    for slot in slots:
        if role_stop_requested()or time.perf_counter()-began>=spec['whole_seconds']:break
        env=FixedScaleSessionEnv(restore(c,world['roots'][slot['root']]['record']),unit_type='A');model=Model((1,slot['B'],0,0))
        def cancel():
            if role_stop_requested():raise BudgetEnd('USER_STOP')
            if time.perf_counter()-began>=spec['whole_seconds']:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
        receipt=search(env,model,depth=slot['depth'],nodes=spec['nodes_per_query'],
            seconds=min(spec['seconds_per_query'],spec['whole_seconds']-(time.perf_counter()-began)),pv_reserve_fraction=.1,cancel=cancel)
        gradient=None if not receipt.complete or receipt.pv_terminal else model.gradient(receipt.pv_phi)
        row=dict(slot=slot,state_sha256=L.state_sha(env.session.state),receipt=L.record_value(receipt),gradient=gradient)
        rows.append(row);write(output/f"query-{slot['id']:03d}.json",row);write(output/'partial.json',dict(rows=rows,seconds=time.perf_counter()-began))
        print(slot,'completed',receipt.completed_depth,'nodes',receipt.nodes,'seconds',receipt.seconds,'phi',receipt.pv_phi,'terminal',receipt.pv_terminal,flush=True)
    result=dict(status='CLOSED',source=SOURCE,rows=rows,unstarted=slots[len(rows):],seconds=time.perf_counter()-began)
    write(output/'result.json',result);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();run(a.output)
