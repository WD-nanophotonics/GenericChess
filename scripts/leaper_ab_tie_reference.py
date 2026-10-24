"""Bounded complete root frontiers using the existing reference AlphaBeta.

Sixteen systematic actual training histories; no oracle-selected starts. Each
forced child is searched with a fresh infinite root window, so completed child
values are exact for this q0 finite tree. Partial frontiers remain UNKNOWN.
"""
from pathlib import Path
import argparse,json,time
from copy import copy
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,write,SOURCE
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,AlphaBeta,BudgetEnd,MATE


def run(pilot,output):
    output.mkdir(parents=True,exist_ok=False);cfg=json.loads((pilot/'plan.json').read_bytes());world=cfg['worlds']['contact'];c=L.compile_rule(L.ruleset_from_dict(world['rule']));cases=[]
    for gi in range(4,8):
        row=json.loads((pilot/f'game-{gi:03d}.json').read_bytes());s=restore(c,row['initial_record']);own=0
        for q in row['queries']:
            if q['actor']==row['slot']['role']:
                if own in(0,8,16,24):cases.append(dict(game=gi,own_index=own,state_sha256=L.state_sha(s.state),record=L.record_value(s.to_record()),baseline=q['receipt']))
                own+=1
            if q['receipt']['complete']:s.submit(L.match_action(s,q['receipt']['action']['action']))
    spec=dict(source=SOURCE,producer_sha256=L.sha(Path(__file__)),cases=cases,depth=8,
        question='Can an exact q0 root tie supply an active free-B target, or does selected-action starvation persist when each real alternative is searched with an independent full window?',
        selection='Unit pilot contact training games4..7, own-query indices0/8/16/24. Systematic actual histories, not chosen from WDL or gradient. Explicitly posthoc mechanism sample, never training starts.',
        backend='Unchanged incremental.AlphaBeta(depth7,qdepth0) for each real root action. Complete full-history environment, no Position quotient, priceB1. Independent reference ordering seed0; no production change.',
        caps=dict(whole_seconds=1800,query_seconds=30,query_nodes=500000),
        cost='Previously closed pilot132.6s/suffix51.2s; initcontrol~220s, depth diagnostic<=1800s; this<=1800s plus verification/analysis expected<=1200s, total<120min. One bounded incomplete frontier experiment, no future cap refill.',
        scope='Exact finite-tree values only for complete child searches. Root optimum/tie classification needs all actual legal children. Selected PV phi is one witness per child, not all tied deep leaves or a WDL/benefit label.')
    write(output/'spec.json',spec);began=time.perf_counter();rows=[];stop=None
    for case in cases:
        env=FixedScaleSessionEnv(restore(c,case['record']),unit_type='A');actions=env.actions();branches=[]
        for ac in actions:
            if role_stop_requested()or time.perf_counter()-began>=1800:stop='WHOLE_CAP_UNKNOWN';break
            child=copy(env);child.stack=[];child.push(ac);actual=child.terminal()
            if actual is not None:value=MATE*actual;phi=None;terminal=True;receipt=None
            else:
                def cancel():
                    if role_stop_requested():raise BudgetEnd('USER_STOP')
                    if time.perf_counter()-began>=1800:raise BudgetEnd('WHOLE_CAP_UNKNOWN')
                r=AlphaBeta(7,0).search(child,Model((1,1,0,0)),nodes=500000,seconds=min(30,1800-(time.perf_counter()-began)),seed=0,cancel=cancel)
                receipt=dict(complete=r.complete,reason=r.reason,nodes=r.nodes,seconds=r.seconds,depth=r.completed_depth)
                value=r.value if r.complete else None;phi=r.pv_phi if r.complete else None;terminal=r.pv_terminal
            branches.append(dict(action=L.record_value(ac),value=value,phi=phi,terminal=terminal,receipt=receipt))
            write(output/'partial.json',dict(rows=rows,current=dict(game=case['game'],own_index=case['own_index'],branches=branches),seconds=time.perf_counter()-began))
        complete=len(branches)==len(actions)and all(b['value']is not None for b in branches)
        optimum=(max if env.player()==0 else min)(b['value']for b in branches)if complete else None
        ties=[b for b in branches if b['value']==optimum]if complete else[]
        row=dict(game=case['game'],own_index=case['own_index'],state_sha256=case['state_sha256'],complete=complete,
            legal_count=len(actions),branches=branches,optimum=optimum,
            optimal_actions=[b['action']for b in ties],active_B_optimal_witnesses=[b['action']for b in ties if not b['terminal']and b['phi'][1]!=0],
            baseline_action_optimal=None if not complete else case['baseline']['action']in[b['action']for b in ties])
        rows.append(row);write(output/f"root-{len(rows)-1:03d}.json",row)
        print('root',case['game'],case['own_index'],complete,'opt',optimum,'ties',len(ties),'active',len(row['active_B_optimal_witnesses']),flush=True)
        if stop:break
    result=dict(source=SOURCE,status=stop or'COMPLETE',rows=rows,unstarted=cases[len(rows):],seconds=time.perf_counter()-began)
    write(output/'result.json',result);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();run(a.pilot,a.output)
