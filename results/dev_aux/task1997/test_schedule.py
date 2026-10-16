"""Observed-risk tests: fixed balanced opponent and immutable RACE/FULL locks."""
import json
from results.dev_aux.task1997.campaign import scheduled_slots,CampaignCap

def plan():
    return dict(prices=[180,360,540,720,900,1080,1260,1440,1800,2160,2520,2880,3600],train_opponent_R=[360,720,1440,2880]*8)

def test_balanced_training_and_crossed_validation(tmp_path):
    rows=[];p=plan()
    for slot in scheduled_slots(p,rows,tmp_path,lambda:False):
        assert slot['candidate_proof_nodes']==1024 and slot['opponent_nodes']==4096
        assert slot['candidate_cached'] and slot['candidate_proof']
        if slot['phase']!='DEV':assert slot['opponent_R']==p['train_opponent_R'][slot['family']]
        # Synthetic payoff deliberately creates different RACE and FULL optima.
        family=slot['family'];r=slot['R']
        value=(1 if r==360 else -1 if r==180 else 0) if family<4 else (1 if r==180 else -1 if r==360 else 0)
        rows.append(dict(slot,finite_event_score=value,seconds=.01))
    race=json.loads((tmp_path/'RACE-lock-before-control.json').read_text())
    full=json.loads((tmp_path/'FULL-lock-before-dev.json').read_text())
    assert race['selected_R']!=full['selected_R'] and full['selected_R']==180
    train=rows[:832];dev=rows[832:]
    assert len(train)==832 and len(dev)==512
    assert {tuple(g[k] for k in ('family','candidate_side','R','opponent_R')) for g in train}=={(f,side,r,p['train_opponent_R'][f]) for f in range(32) for side in (0,1) for r in p['prices']}
    assert {tuple(g[k] for k in ('family','candidate_side','R','opponent_R')) for g in dev}=={(f,side,r,opp) for f in range(32,48) for side in (0,1) for r in (180,720,1260,2160) for opp in (360,720,1440,2880)}
    assert len({(x['family'],x['candidate_side'],x['R'],x['opponent_R']) for x in rows})==len(rows)

def test_cancellation_never_creates_selector(tmp_path):
    gen=scheduled_slots(plan(),[],tmp_path,lambda:True)
    try:next(gen)
    except CampaignCap:pass
    else:raise AssertionError('cap ignored')
    assert not list(tmp_path.iterdir())
