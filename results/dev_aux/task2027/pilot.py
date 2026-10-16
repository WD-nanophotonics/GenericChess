"""Prospective balanced-opponent TRAIN, full opponent-crossed DEV, true rule W-L."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,time,sys
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_phase_player import SessionPhasePlayer,PhaseLimits
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_proof_player import commit_session_decision
from scripts.generic_win_proof import _same_state

OUT=Path('results/dev_aux/task2027');ROOT=Path('results/dev_aux/task1941')
SOURCES=['results/dev_aux/task1866/unit_panel.py','scripts/generic_session_cached_phase_player.py','scripts/generic_session_proof_bank.py','scripts/generic_session_phase_player.py','scripts/generic_session_win_proof_batch_pn.py','scripts/generic_session_proof_player.py','scripts/generic_session_win_proof.py',
 'scripts/generic_session_win_proof_pn.py','scripts/generic_proof_player.py','scripts/generic_win_proof.py',
 'scripts/generic_session_native_material.py','results/dev_aux/task109/adapter.py',
 'generic_chess/session/session.py','generic_chess/core/search_runtime.py',str(Path(__file__).relative_to(Path.cwd()))]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
def eval_for(b,n=720):
    def evaluate(position,target):
        return sum((1 if p.owner==target else -1)*({'R':1260,'N':n,'B':b}.get(p.current_type_id,0)) for p in position.board if p is not None)
    return evaluate

def _run(cohort,global_start):
    global OUT
    OUT=Path('results/dev_aux/task2027')
    plan=json.loads((OUT/'run-plan.json').read_text(encoding='utf-8'))
    assert all(sha(p)==v for p,v in plan['source_sha'].items())
    c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')))
    roots=json.loads(Path(plan['roots']).read_text(encoding='utf-8'))['roots']
    q=json.loads(Path(plan['qualification']).read_text(encoding='utf-8'));assert q['status']=='PASS_SCOPED_KRNB_NATIVE_FEASIBILITY' and q['source_unchanged']
    start=global_start;done=0;total_moves=0;rows=[];actual_slots=[];status='COMPLETE'
    from scripts.generic_session_native_material import _load_transport
    from results.dev_aux.task2025.provider import KRNB6UnitProvider as UnitProvider
    native_plan={**plan['native_plan'],'seconds_cap':max(.01,plan['seconds_cap']-(time.perf_counter()-start)),'max_go':plan['maximum_games']*96}
    transport=_load_transport();globals()['_active_provider']=provider=UnitProvider(native_plan,OUT/'run',stop=lambda:transport.stop_check(Path.cwd()))
    provider.start()
    def cancelled():return time.perf_counter()-start>=plan['seconds_cap']
    with (OUT/'games.jsonl').open('x',encoding='utf-8') as games,(OUT/'moves.jsonl').open('x',encoding='utf-8') as moves:
        for slot in bounded_slots(plan,rows,OUT,cancelled):
            if cancelled():status='GLOBAL_CAP';break
            actual_slots.append(slot)
            with (OUT/'planned-slots.jsonl').open('a',encoding='utf-8') as planned:planned.write(json.dumps(slot)+'\n')
            current=GameSession(c,roots[slot['family']]['setup']);players=[];banks=[SessionLogicalProofBank(prove_session_win_batch_pn,capacity=256) for _ in (0,1)]
            for side in (0,1):
                candidate=side==slot['candidate_side']
                price=slot['B'] if candidate else slot['opponent_B']
                nprice=slot['N'] if candidate else 720
                values=(1260,nprice,price,nprice)
                def normal(state,n,seconds,cancel,values=values):return provider.choose(current,state,values,n,seconds,cancel)
                player_class=SessionCachedPhasePlayer
                extra={'bank':banks[side]}
                players.append(player_class(c,eval_for(price,nprice),**extra,normal_search=normal,limits=PhaseLimits(proof_nodes=slot['candidate_proof_nodes'] if candidate else plan['opponent_proof_nodes'],verification_nodes=plan['verification_nodes'],proof_seconds=plan['proof_seconds'],verification_seconds=plan['verification_seconds'],normal_seconds=plan['normal_seconds']),
                    proof_enabled=slot['candidate_proof'] if candidate else True,max_depth=plan['normal_depth'],proof_depth=plan['proof_depth']))
            game_start=time.perf_counter();tail=False;reason='H_UNKNOWN';history=[];before=0
            for ply in range(plan['H']):
                if current.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
                if cancelled():reason='GLOBAL_CAP';status='GLOBAL_CAP';break
                side=current.state.position.side_to_move;p=players[side]
                n=plan['candidate_nodes'] if side==slot['candidate_side'] else slot['opponent_nodes']
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
                    seconds=decision.seconds,commit_seconds=commit_seconds,tail=ply>=plan['H'],phase_limits=dict(decision.phase_limits),proof_stats=dict(decision.proof_stats),admission_seconds=decision.admission_seconds,proof_seconds=decision.proof_seconds,verification_seconds=decision.verification_seconds,normal_seconds=decision.normal_seconds,
                    before_state_sha=old_sha,after_state_sha=sha_state(current.state),before_ranks=old_ranks,
                    after_ranks=[None if q.cursor is None else q.cursor.node.rank for q in players],
                    result=asdict(result))
                if isinstance(decision, __import__('scripts.generic_session_cached_phase_player',fromlist=['CachedPhaseDecision']).CachedPhaseDecision):
                    for key in ('bank_hit','bank_stored','bank_verification_scope','bank_query_seconds','fill_verification_nodes','fill_verification_seconds','logical_proof_nodes','logical_proof_seconds','logical_proof_stats','logical_status','logical_reason'):row[key]=getattr(decision,key)
                    row['bank_overhead_seconds']=decision.bank_overhead_seconds
                row['result']['status']=result.status.value
                moves.write(json.dumps(row)+'\n');moves.flush();history.append(row);total_moves+=1
                if current.result.status is not SessionStatus.ONGOING:reason='ACTUAL_TERMINAL';break
            result=current.result
            outcome='UNKNOWN' if result.status is SessionStatus.ONGOING else ('DRAW' if result.winner is None else ('WIN' if result.winner==slot['candidate_side'] else 'LOSS'))
            score=1 if outcome=='WIN' else -1 if outcome=='LOSS' else 0 if outcome=='DRAW' else None
            record=json.loads(serialize_game_record(current.to_record()))
            row=dict(**slot,outcome=outcome,finite_event_score=score,result=asdict(result),reason=reason,
                moves=len(history),tail=tail,seconds=time.perf_counter()-game_start,record=record,final_state_sha=sha_state(current.state),
                proof_moves=sum(x['source'] in ('PROOF','PROOF_CONTINUATION') for x in history),
                normal_node_overruns=sum(x['search_nodes']>x['budget'] for x in history))
            row['result']['status']=result.status.value;games.write(json.dumps(row)+'\n');games.flush();rows.append(row);done+=1
            if done%24==0:print(json.dumps(dict(done=done,moves=total_moves,seconds=round(time.perf_counter()-start,3))),flush=True)
            if outcome=='UNKNOWN':status='INCOMPLETE_OUTCOME';break
            if status=='GLOBAL_CAP':break
    if cancelled():status='GLOBAL_CAP'
    provider.close()
    audit_plan={**plan,'slots':actual_slots,'expected_games':len(actual_slots),'selector':plan['selector']}
    write('audit-plan.json',audit_plan)
    write('completion.json',dict(status=status,completed=done,expected=len(actual_slots),moves=total_moves,seconds=time.perf_counter()-start,
        source_sha=plan['source_sha'],native_go=provider.queries,native_nodes=provider.reported_nodes,source_unchanged=all(sha(p)==v for p,v in plan['source_sha'].items())))
def sha_state(state):return hashlib.sha256(repr(state).encode()).hexdigest()
def qualify():
    plan=json.loads((OUT/'run-plan.json').read_text(encoding='utf-8'));assert all(sha(p)==v for p,v in plan['source_sha'].items())
    from results.dev_aux.task2025.provider import KRNB6UnitProvider as UnitProvider
    from scripts.generic_session_native_material import _load_transport
    t=_load_transport();provider=UnitProvider({**plan['native_plan'],'seconds_cap':60,'max_go':plan['expected_perft']},OUT/'qualification-run',stop=lambda:t.stop_check(Path.cwd()));start=time.perf_counter();perfts=[];c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')));roots=json.loads(Path(plan['roots']).read_text(encoding='utf-8'))['roots']
    try:
        provider.start()
        for root in roots:
            current=GameSession(c,root['setup'])
            for r in plan['R_values']:
                count=provider.perft_one(current,(1260,720,r,720));perfts.append(dict(family=root['family'],B=r,moves=count))
    finally:provider.close()
    assert len(perfts)==plan['expected_perft'] and time.perf_counter()-start<60
    write('qualification.json',dict(status='PASS',perfts=perfts,native_perft_commands=plan['expected_perft'],native_search_go=0,seconds=time.perf_counter()-start,source_unchanged=all(sha(p)==v for p,v in plan['source_sha'].items())))
    print(json.dumps(dict(qualified=plan['expected_perft'],seconds=time.perf_counter()-start)),flush=True)

class CampaignCap(RuntimeError):pass

def scheduled_slots(plan,rows,out,cancelled):
    for slot in plan['slots']:
        if cancelled():raise CampaignCap('Original cap; no extension')
        yield slot

def bounded_slots(plan,rows,out,cancelled):
    try:yield from scheduled_slots(plan,rows,out,cancelled)
    except CampaignCap:return

def campaign():
    global OUT
    import datetime
    OUT=Path('results/dev_aux/task2027');plan=json.loads((OUT/'run-plan.json').read_text(encoding='utf-8'))
    assert all(sha(p)==v for p,v in plan['source_sha'].items())
    start=time.perf_counter();status='COMPLETE'
    write('start.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),one_clock=True,cap_seconds=plan['seconds_cap'],restart_forbidden=True))
    try:
        assert json.loads(Path('results/dev_aux/task2026/result.json').read_text(encoding='utf-8'))['status']=='PASS_ALL_KRNB_NATIVE_FEASIBILITY_RECEIPTS'
        if time.perf_counter()-start>=plan['seconds_cap']:raise CampaignCap('Qualification consumed original clock')
        _run(0,start)
        status=json.loads((OUT/'completion.json').read_text(encoding='utf-8'))['status']
    except CampaignCap:status='GLOBAL_CAP'
    except BaseException as exc:
        status='ERROR';write('campaign-error.json',dict(error=type(exc).__name__+':'+str(exc)))
        raise
    finally:
        provider=globals().pop('_active_provider',None)
        if provider is not None:
            if provider.e is not None and not provider.e.closed:provider.e.close()
            if not provider.journal.closed:provider.journal.close()
        write('campaign-completion.json',dict(status=status,seconds=time.perf_counter()-start,global_cap_seconds=plan['seconds_cap'],source_unchanged=all(sha(p)==v for p,v in plan['source_sha'].items())))
    print(json.dumps(dict(campaign=status,seconds=time.perf_counter()-start)),flush=True)
if __name__=='__main__':campaign()
