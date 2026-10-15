from pathlib import Path
import json
from results.dev_aux.task1965.campaign import scheduled_slots,bounded_slots
GRID=[180,360,540,720,900,1080,1260,1440,1800,2160,2520,2880,3600]
def test_actual_call_schedule_and_lock_boundaries(tmp_path):
    rows=[];keys=set();gen=scheduled_slots({'prices':GRID},rows,tmp_path,lambda:False)
    for item in gen:
        key=tuple(item[k] for k in ('family','candidate_side','R','opponent_nodes'))
        assert key not in keys;keys.add(key)
        if item['phase']=='CONTROL':assert (tmp_path/'RACE-lock-before-control.json').exists()
        if item['phase']=='DEV':assert (tmp_path/'FULL-lock-before-dev.json').exists()
        rows.append(dict(item,finite_event_score=0,seconds=1.))
    assert len(rows)==544
    assert sum(x['phase']=='RACE' for x in rows)==208
    assert sum(x['phase']=='CONTROL' for x in rows)==208
    race=json.loads((tmp_path/'RACE-lock-before-control.json').read_text())
    full=json.loads((tmp_path/'FULL-lock-before-dev.json').read_text())
    assert race['selected_R']==full['selected_R']==180 and race['physical_games']==208
    assert len([x for x in rows if x['phase']=='DEV' and x['R']==180])==64
    assert len([x for x in rows if x['phase']=='DEV' and x['R']==720])==64

def test_control_cannot_replace_racing_lock(tmp_path):
    rows=[];gen=scheduled_slots({'prices':GRID},rows,tmp_path,lambda:False)
    for item in gen:
        if item['phase']=='DEV':break
        # Stress incorrect accidental replacement: full table can differ from race.
        score=1 if item['phase']=='CONTROL' and item['R']==3600 else 0
        rows.append(dict(item,finite_event_score=score,seconds=0.))
    race=json.loads((tmp_path/'RACE-lock-before-control.json').read_text())
    full=json.loads((tmp_path/'FULL-lock-before-dev.json').read_text())
    assert race['selected_R']==180 and full['RACE_R']==180
    assert full['selected_R']!=race['selected_R']
    assert (tmp_path/'RACE-lock-before-control.json').read_text()==json.dumps(race,indent=2)

def test_cap_never_creates_selector_or_fabricated_remaining_games(tmp_path):
    rows=[];gen=bounded_slots({'prices':GRID},rows,tmp_path,lambda:len(rows)>=3)
    for item in gen:rows.append(dict(item,finite_event_score=0,seconds=0.))
    assert len(rows)==3 and not (tmp_path/'RACE-lock-before-control.json').exists()
