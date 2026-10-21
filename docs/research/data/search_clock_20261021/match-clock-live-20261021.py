import json, time
from pathlib import Path
from generic_chess.clock import MatchClock, SideTimeConfig, TimeControl, TimeControlMode
from generic_chess.ai.budget import ThinkingConfig, ThinkingStrategy, allocate_search_limits

control=TimeControl(mode=TimeControlMode.FISCHER,
    owner0=SideTimeConfig(main_seconds=1,overtime_seconds=0),
    owner1=SideTimeConfig(main_seconds=1,overtime_seconds=0),time_forfeit=True)
qpc=time.perf_counter
coarse=time.monotonic
expiry=[]
budgets=[]
for rep in range(4):
    order=("coarse","qpc") if rep%2==0 else ("qpc","coarse")
    for arm in order:
        now=coarse if arm=="coarse" else qpc
        start=qpc()
        clock=MatchClock(control,active_owner=0,now=now)
        polls=0
        while True:
            polls+=1
            state=clock.state()
            if state.expired_owner==0: break
            elapsed=qpc()-start
            if elapsed>1.3: raise RuntimeError(f"expiry timeout {arm} {rep}")
        expiry.append({"rep":rep,"arm":arm,"qpc_elapsed_ms":(qpc()-start)*1000,
                       "polls":polls,"reported_remaining_ms":state.remaining_ms[0],
                       "expired_owner":state.expired_owner})

for rep in range(4):
    order=("coarse","qpc") if rep%2==0 else ("qpc","coarse")
    for arm in order:
        now=coarse if arm=="coarse" else qpc
        start=qpc()
        clock=MatchClock(control,active_owner=0,now=now)
        target=start+0.656
        while qpc()<target: pass
        state=clock.state()
        config=ThinkingConfig(strategy=ThinkingStrategy.FIXED_NODES,max_nodes=50000,safety_margin_seconds=.3)
        limits=allocate_search_limits(state,control,0,1,config)
        end=qpc()
        budgets.append({"rep":rep,"arm":arm,"qpc_elapsed_ms":(end-start)*1000,
            "actual_remaining_ms":max(0,1000-(end-start)*1000),
            "reported_remaining_ms":state.remaining_ms[0],
            "allocated_budget_ms":limits.max_time_seconds*1000,
            "expired_owner":state.expired_owner})

result={"question":"On this Windows runtime, does the actual default MatchClock source differ materially from perf_counter at 1s expiry or at 344ms remaining near the UI AI safety margin?",
 "scope":"Four alternating coarse/QPC repetitions each for 1s Fischer expiry and a QPC-targeted 656ms elapsed budget sample. Busy-loop sampling, no search or training; actual host clock sources, not simulated phases.",
 "clock_info":{"monotonic_implementation":time.get_clock_info("monotonic").implementation,
               "monotonic_resolution":time.get_clock_info("monotonic").resolution,
               "perf_counter_implementation":time.get_clock_info("perf_counter").implementation,
               "perf_counter_resolution":time.get_clock_info("perf_counter").resolution},
 "expiry":expiry,"budget_samples":budgets}
out=Path(".local_agent/match-clock-live-20261021.json")
out.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({"file":str(out),"bytes":out.stat().st_size,"clock_info":result["clock_info"],
 "expiry":expiry,"budget_samples":budgets},indent=2))
