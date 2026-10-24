"""Prospective fresh-safe layout robustness for a fixed two-type rule family."""
from __future__ import annotations
from pathlib import Path
from dataclasses import replace
from collections import Counter
import argparse,json,random,time,traceback
from scripts import leaper_design as L
from scripts import leaper_default_contact as D
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.rules.validation import RuleValidationError
from generic_chess.core.attacks import anchor_square,pseudo_attacks
from tools.local_agent.common import write_json
from tools.local_agent import session

def prepare(source,output,registration,count=12,seed=202610240951):
    assert not output.exists() and not registration.exists()
    old=L.load(source);base=L.ruleset_from_dict(old['rule']);rng=random.Random(seed)
    boards=[];placements=[];rejected=Counter();attempts=0
    while len(boards)<count:
        attempts+=1;squares=tuple(rng.sample(range(25),6))
        if squares in placements:rejected['duplicate']+=1;continue
        cells=[None]*25
        for ix,owner,tid in zip(squares,(0,0,0,1,1,1),('K','A','B','K','A','B')):cells[ix]=L.Piece(owner,tid,tid)
        board=tuple(tuple(cells[5*r:5*r+5])for r in range(5))
        rule=replace(base,initial_position=board,initial_setup_options=())
        try:c=L.compile_rule(rule)
        except RuleValidationError as exc:
            if all(x.code in ('INITIAL_ANCHOR_ATTACKED','INITIAL_NO_LEGAL_MOVE') for x in exc.issues):
                rejected['compiler:'+','.join(sorted({x.code for x in exc.issues}))]+=1;continue
            raise
        s=L.GameSession(c)
        if any(anchor_square(s.state.position,side,c) in pseudo_attacks(s.state.position,1-side,c)for side in (0,1)):
            rejected['initial_check']+=1;continue
        if s.state.terminal_status.is_terminal:rejected['initial_terminal']+=1;continue
        boards.append(board);placements.append(squares)
    rule=replace(base,initial_position=boards[0],initial_setup_options=tuple(RuleInitialSetupOption('fresh'+str(i),b)for i,b in enumerate(boards[1:],1)))
    c=L.compile_rule(rule);roots=[]
    for i in range(count):
        s=L.GameSession(c,None if i==0 else 'fresh'+str(i));assert not s.state.terminal_status.is_terminal
        assert L.GameSession.replay(c,s.to_record()).state==s.state
        roots.append(dict(index=i,record=L.record_value(s.to_record()),state=L.record_value(s.state),state_sha256=L.state_sha(s.state),legal_count=len(s.legal_actions()),placement=placements[i]))
    profile=L.record_value(L.AlphaBetaPlayer(c,use_disk_cache=False).evaluation_profile)
    world=dict(rule=L.ruleset_to_dict(rule),fingerprint=L.compute_fingerprint(rule),roots=roots,profile=profile,sampler=dict(seed=seed,attempts=attempts,rejected=dict(rejected),law='Uniform ordered six distinct labelled squares via fixed PRNG; reject initial check of either king, terminal root and duplicate placement only. All accepted roots retained; no WDL, price, path or payoff filter.',scope=f'{count} finite fresh-safe contexts, fixed side0, not independent generated-rule samples; initial setup law/fingerprint changes from previous contact input.'))
    write_json(output,world)
    slots=[]
    order=list(range(count));rng.shuffle(order)
    for root in order:
        policies=['UNIT','DEFAULT'];rng.shuffle(policies)
        slots.extend(dict(root=root,controller=x)for x in policies)
    reg=dict(at=D.now(),question='Does the complete default-versus-unit finite payoff difference survive a prospective fresh-safe mu rather than one constructed contact root?',hypothesis='Dynamic conversion can help some natural contexts yet not improve the finite paired mean. Keep all losses/draws and any missing values; no truth eligibility, tuning or learner gate.',input_sha256=L.sha(output),source_sha256=L.sha(Path(__file__)),driver_sha256=L.sha(Path(D.__file__)),nodes=8192,slots=slots,cap_seconds=4200,per_game_cap=240,expected_total_seconds=202*2*count*1.15+900,cost_basis=dict(point_per_game_seconds=202,point_games=202*2*count,reserve_fraction=.15,prepare_validate_analyze_seconds=900,basis='Conservative full64*3s search allowance plus10s setup/record forecast. This is an estimate, not a measured upper bound; prior fullcontact maximum176.12s. Cooperative wholecap4200 may leave UNKNOWN. No extension/refill.'),services='Native legality ONLY, availability/check FALSE; D64/N8192/3s/Q0/check-onlyFALSE/hard8',tt='Fresh players per game, TT retained within, diskOFF',opponent='fixedUNIT8192 for both arms',profile=profile,scope=f'{2*count} newly frozen configurations, {count} prospective complete roots x2controllers. No seed replication, existing game replay, default activation, truth/learner or AUX checkout access.')
    write_json(registration,reg);return reg

def run(inputs,registration,directory):
    assert not directory.exists();directory.mkdir(parents=True)
    reg=L.load(registration);assert L.sha(inputs)==reg['input_sha256'] and L.sha(Path(__file__))==reg['source_sha256'] and L.sha(Path(D.__file__))==reg['driver_sha256'];assert reg['expected_total_seconds']<7200
    tick=time.perf_counter();result=dict(status='RUNNING',started_at=D.now(),slots=[dict(x,status='not_started')for x in reg['slots']]);write_json(directory/'results.json',result)
    try:
        for i,slot in enumerate(result['slots']):
            remaining=reg['cap_seconds']-(time.perf_counter()-tick)
            if session.stopped() or remaining<=0:break
            case=dict(reg,source_sha256=reg['driver_sha256'],controller=slot['controller'],root=slot['root'],cap_seconds=min(reg['per_game_cap'],remaining),parent_registration_sha256=L.sha(registration))
            casepath=directory/f'case-{i:03d}.json';write_json(casepath,case)
            try:
                row=D.run(inputs,casepath,directory/f'game-{i:03d}.json');slot.update(status='finished',value=row['value'],censor=row['censor'],seconds=row['seconds'])
                print('SLOT',i,slot,flush=True)
            except Exception as exc:
                slot.update(status='failed',error=repr(exc));write_json(directory/f'error-{i:03d}.json',dict(error=repr(exc),traceback=traceback.format_exc()))
            write_json(directory/'results.json',result)
    finally:
        result.update(status='CLOSED',ended_at=D.now(),seconds=time.perf_counter()-tick,missing=[i for i,x in enumerate(result['slots'])if x['status']!='finished' or x['value'] is None]);write_json(directory/'results.json',result);print('PANEL_CLOSED',result['seconds'],result['missing'],flush=True)
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','run']);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--registration',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.mode=='prepare':prepare(a.input,a.output,a.registration)
    else:run(a.input,a.registration,a.output)
