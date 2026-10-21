import json
from pathlib import Path
from generic_chess.ai.budget import ThinkingConfig,ThinkingStrategy,allocate_search_limits
from generic_chess.clock import ClockState,SideTimeConfig,TimeControl,TimeControlMode
control=TimeControl(mode=TimeControlMode.FISCHER,owner0=SideTimeConfig(1,0),owner1=SideTimeConfig(1,0))
rows=[]
for move_number in (1,89):
    for remaining in (360,344):
        state=ClockState((remaining,1000),(0,0),0,True)
        for strategy in ThinkingStrategy:
            config=ThinkingConfig(strategy=strategy,max_nodes=50000,move_time_seconds=1.0,safety_margin_seconds=.3)
            limits=allocate_search_limits(state,control,0,move_number,config)
            rows.append({"move_number":move_number,"remaining_ms":remaining,"strategy":strategy.value,"allocated_ms":None if limits.max_time_seconds is None else limits.max_time_seconds*1000,"max_nodes":limits.max_nodes})
result={"question":"Which UI thinking strategies materially inherit the 16ms measured GetTickCount64 over-report near the 300ms reserve?","scope":"Deterministic allocator-only replay of the actual 360ms coarse and344ms QPC MatchClock states, 1s Fischer, 50000 fixed nodes, move1 and89; no search/game claims.","rows":rows}
out=Path('.local_agent/match-clock-strategy-sensitivity-20261021.json');out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
