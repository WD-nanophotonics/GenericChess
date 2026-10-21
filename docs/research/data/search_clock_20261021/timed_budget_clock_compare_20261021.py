import json, random, statistics, time
from pathlib import Path
from generic_chess import build_western_chess_ruleset, compile_ruleset_for_execution
from generic_chess.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits

ROOTS=(101,102,103)
BUDGETS=(0.005,0.010,0.020)
REPEATS=4
compiled=compile_ruleset_for_execution(build_western_chess_ruleset())
roots=[]
for seed in ROOTS:
    rng=random.Random(seed); session=GameSession(compiled)
    for _ in range(12):
        actions=sorted(session.legal_actions(),key=str)
        if session.result.status.value!='ongoing' or not actions: raise RuntimeError('unexpected early terminal')
        session.submit(actions[rng.randrange(len(actions))])
    roots.append((seed,session))
clock_module=time
low_clock=time.monotonic
high_clock=time.perf_counter
rows=[]
for seed,session in roots:
    player=AlphaBetaPlayer(compiled,use_disk_cache=False)
    initial=(session.state,session._search_witnesses)
    for budget in BUDGETS:
        for rep in range(REPEATS):
            order=('low','high') if rep%2==0 else ('high','low')
            pair={}
            for arm in order:
                player.reset()
                clock_module.monotonic=low_clock if arm=='low' else high_clock
                t0=time.perf_counter()
                d=player.choose_action(session,SearchLimits(max_depth=8,max_nodes=None,max_time_seconds=budget,quiescence_max_depth=0))
                wall=time.perf_counter()-t0
                pair[arm]={'wall_seconds':wall,'reported_elapsed_seconds':d.elapsed_seconds,'first_legal_seconds':d.time_to_first_legal_action,'first_iteration_seconds':d.time_to_first_completed_iteration,'nodes':d.nodes,'qnodes':d.qnodes,'completed_depth':d.completed_depth,'reason':d.termination_reason,'result_source':d.result_source,'action':str(d.action) if d.action is not None else None}
            rows.append({'seed':seed,'budget_seconds':budget,'rep':rep,'order':order,'arms':pair,'state_unchanged':(session.state,session._search_witnesses)==initial})
clock_module.monotonic=low_clock
summary=[]
for budget in BUDGETS:
    grp=[r for r in rows if r['budget_seconds']==budget]
    for arm in ('low','high'):
        summary.append({'budget_seconds':budget,'arm':arm,'n':len(grp),'actual_wall_median':statistics.median(r['arms'][arm]['wall_seconds'] for r in grp),'reported_elapsed_median':statistics.median(r['arms'][arm]['reported_elapsed_seconds'] for r in grp),'median_nodes':statistics.median(r['arms'][arm]['nodes']+r['arms'][arm]['qnodes'] for r in grp),'depth_counts':{str(d):sum(r['arms'][arm]['completed_depth']==d for r in grp) for d in sorted({r['arms'][arm]['completed_depth'] for r in grp})},'exact_action_agreement_with_other_arm':sum(r['arms']['low']['action']==r['arms']['high']['action'] for r in grp)})
result={'question':'On identical standard-chess public-player roots, does replacing the 15.625ms GetTickCount64 deadline clock with the 100ns QPC perf_counter change finite-budget completed work or accuracy of cost telemetry?','scope':'Three fixed 12-ply seeded legal roots; same Player instance/TT reset; 4 paired repetitions alternating order at 5/10/20ms per-call time caps; no training. This is a local timer-resolution calibration, not engine-strength evidence.','clock_sources':{'low':{'implementation':time.get_clock_info('monotonic').implementation,'resolution':time.get_clock_info('monotonic').resolution},'high':{'implementation':time.get_clock_info('perf_counter').implementation,'resolution':time.get_clock_info('perf_counter').resolution}},'rows':rows,'summary':summary,'all_states_unchanged':all(r['state_unchanged'] for r in rows)}
p=Path('.local_agent/timed_budget_clock_compare_20261021.json');p.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'file':str(p),'bytes':p.stat().st_size,'clock_sources':result['clock_sources'],'summary':summary,'all_states_unchanged':result['all_states_unchanged']},indent=2))
