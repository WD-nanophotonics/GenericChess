"""Bounded frozen actual-session policy feasibility; no Native or WDL surrogate."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,time,sys
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_proof_player import SessionProofMaterialPlayer,commit_session_decision
from scripts.generic_win_proof import _same_state

OUT=Path('results/dev_aux/task1823');ROOT=Path('results/dev_aux/task1822')
SOURCES=['scripts/generic_session_proof_player.py','scripts/generic_session_win_proof.py',
 'scripts/generic_session_win_proof_pn.py','scripts/generic_proof_player.py','scripts/generic_win_proof.py',
 'generic_chess/session/session.py','generic_chess/core/search_runtime.py',str(Path(__file__).relative_to(Path.cwd()))]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
def freeze():
    roots=json.loads((ROOT/'qualification.json').read_text(encoding='utf-8'))['roots'];slots=[]
    for root in roots:
        for role in (0,1):
            pairs=[(mode,r) for mode in (False,True) for r in (360,720,1440)]
            if (root['family']+role)%2:pairs.reverse()
            for mode,r in pairs:slots.append(dict(slot=len(slots),family=root['family'],phase=root['phase'],candidate_side=role,candidate_proof=mode,R=r))
    plan=dict(status='FROZEN_BEFORE_GAMES',question='Can the new actual-session chooser safely execute bounded price/proof controls, and is finite-event price signal present under a fixed opponent? Not mature-engine replication or human-price recovery.',
        roots=str(ROOT/'qualification.json'),roots_sha=sha(ROOT/'qualification.json'),rules=str(ROOT/'rules.json'),rules_sha=sha(ROOT/'rules.json'),
        source_sha={p:sha(p) for p in SOURCES},slots=slots,expected_games=384,
        candidate_nodes=4096,opponent_nodes=64,step_seconds=.25,normal_depth=3,proof_depth=64,H=16,
        opponent=dict(R=720,N=720,proof=True),prices=[360,720,1440],N=720,
        tail='At H16 only already verified rank<=64 strategies authorize up to64extra physical moves; no new proof after H. UNKNOWN not draw, no quantity reward.',
        seconds_cap=1800,expected_seconds=600,max_moves=384*80,
        selector='TRAIN actual W-L averaged equally over16families and bothroles separately for each candidate proof mode; maximum, smallestR tie. Adjacent strict-improvement grid paths reported from all3initials. DEV never selects price/mu/weight/budget.',
        cost_decision='One bounded384game three-price/two-role/two-policy control can expose integration failures and whether real outcomes distinguish prices. Existing GameState/mature engine study remains unchanged; do not enlarge/extend if partial or flat.',
        load='Ordinary concurrent projects allowed; real elapsed and visit units reported, not equal primitive engine work.',native_go=0)
    write('plan.json',plan);print(json.dumps(dict(frozen=len(slots),seconds_cap=1800)))
def eval_for(r):
    def evaluate(position,target):
        return sum((1 if p.owner==target else -1)*({'R':r,'N':720}.get(p.current_type_id,0)) for p in position.board if p is not None)
    return evaluate

def run():
    plan=json.loads((OUT/'plan.json').read_text(encoding='utf-8'))
    assert all(sha(p)==v for p,v in plan['source_sha'].items())
    c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')))
    roots=json.loads(Path(plan['roots']).read_text(encoding='utf-8'))['roots']
    start=time.perf_counter();done=0;total_moves=0;rows=[];status='COMPLETE'
    def cancelled():return time.perf_counter()-start>=plan['seconds_cap']
    with (OUT/'games.jsonl').open('x',encoding='utf-8') as games,(OUT/'moves.jsonl').open('x',encoding='utf-8') as moves:
        for slot in plan['slots']:
            if cancelled():status='GLOBAL_CAP';break
            current=GameSession(c,roots[slot['family']]['setup']);players=[]
            for side in (0,1):
                candidate=side==slot['candidate_side']
                players.append(SessionProofMaterialPlayer(c,eval_for(slot['R'] if candidate else 720),
                    proof_enabled=slot['candidate_proof'] if candidate else True,max_depth=plan['normal_depth'],proof_depth=plan['proof_depth']))
            game_start=time.perf_counter();tail=False;reason='H_UNKNOWN';history=[];before=0
            for ply in range(plan['H']+64):
                if current.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
                if cancelled():reason='GLOBAL_CAP';status='GLOBAL_CAP';break
                if ply>=plan['H']:
                    live=[p.cursor for p in players if p.cursor is not None and p.cursor.node.rank>0]
                    if not live or min(cur.node.rank for cur in live)>64:break
                    tail=True
                side=current.state.position.side_to_move;p=players[side]
                n=plan['candidate_nodes'] if side==slot['candidate_side'] else plan['opponent_nodes']
                decision=p.choose(current,max_nodes=n,seconds=plan['step_seconds'],cancel=cancelled,allow_new_proof=ply<plan['H'])
                if decision.choice is None:reason=decision.exit_cause;break
                old_record=current.to_record();old_sha=sha_state(current.state)
                old_ranks=[None if q.cursor is None else q.cursor.node.rank for q in players]
                committed=time.perf_counter();result=commit_session_decision(current,decision,players,cancel=cancelled)
                commit_seconds=time.perf_counter()-committed
                # Every committed public record is independently replayed.
                rebuilt=GameSession.replay(c,current.to_record())
                assert _same_state(rebuilt.state,current.state) and _same_state(rebuilt.result,current.result)
                row=dict(slot=slot['slot'],ply=ply,side=side,budget=n,choice=action_to_dict(decision.choice.action) if decision.choice.kind=='ACTION' else {'declaration':decision.choice.declaration_id},
                    source=decision.source,proof_reason=decision.proof_reason,exit_cause=decision.exit_cause,
                    proof_nodes=decision.proof_nodes,verification_nodes=decision.verification_nodes,search_nodes=decision.search_nodes,
                    seconds=decision.seconds,commit_seconds=commit_seconds,tail=ply>=plan['H'],
                    before_state_sha=old_sha,after_state_sha=sha_state(current.state),before_ranks=old_ranks,
                    after_ranks=[None if q.cursor is None else q.cursor.node.rank for q in players],
                    result=asdict(result))
                row['result']['status']=result.status.value
                moves.write(json.dumps(row)+'\n');moves.flush();history.append(row);total_moves+=1
                if current.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
            result=current.result
            outcome='UNKNOWN' if result.status is SessionStatus.ONGOING else ('DRAW' if result.winner is None else ('WIN' if result.winner==slot['candidate_side'] else 'LOSS'))
            score=1 if outcome=='WIN' else -1 if outcome=='LOSS' else 0
            record=json.loads(serialize_game_record(current.to_record()))
            row=dict(**slot,outcome=outcome,finite_event_score=score,result=asdict(result),reason=reason,
                moves=len(history),tail=tail,seconds=time.perf_counter()-game_start,record=record,final_state_sha=sha_state(current.state),
                proof_moves=sum(x['source'] in ('PROOF','PROOF_CONTINUATION') for x in history),
                node_overruns=sum(x['proof_nodes']+x['verification_nodes']+x['search_nodes']>x['budget'] for x in history))
            row['result']['status']=result.status.value;games.write(json.dumps(row)+'\n');games.flush();rows.append(row);done+=1
            if done%12==0:print(json.dumps(dict(done=done,moves=total_moves,seconds=round(time.perf_counter()-start,3))),flush=True)
            if status=='GLOBAL_CAP':break
    write('completion.json',dict(status=status,completed=done,expected=384,moves=total_moves,seconds=time.perf_counter()-start,
        source_sha=plan['source_sha'],native_go=0,source_unchanged=all(sha(p)==v for p,v in plan['source_sha'].items())))
def sha_state(state):return hashlib.sha256(repr(state).encode()).hexdigest()
if __name__=='__main__':
    {'freeze':freeze,'run':run}[sys.argv[1]]()
