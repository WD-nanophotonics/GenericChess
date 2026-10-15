"""Predeclared absolute-unit sensitivity of actualW-L price ranking, exposed roots."""
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

OUT=Path('results/dev_aux/task1881');ROOT=Path('results/dev_aux/task1872')
SOURCES=['results/dev_aux/task1866/unit_panel.py','scripts/generic_session_cached_phase_player.py','scripts/generic_session_proof_bank.py','scripts/generic_session_phase_player.py','scripts/generic_session_win_proof_batch_pn.py','scripts/generic_session_proof_player.py','scripts/generic_session_win_proof.py',
 'scripts/generic_session_win_proof_pn.py','scripts/generic_proof_player.py','scripts/generic_win_proof.py',
 'scripts/generic_session_native_material.py','results/dev_aux/task109/adapter.py',
 'generic_chess/session/session.py','generic_chess/core/search_runtime.py',str(Path(__file__).relative_to(Path.cwd()))]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
def freeze():
    roots=json.loads((ROOT/'feasibility.json').read_text(encoding='utf-8'))['roots'];slots=[]
    for root in roots:
        for role in (0,1):
            profiles=[(n,int(n*ratio),ratio) for ratio in (.5,1.,2.) for n in (720,)]
            if (root['family']+role)%2:profiles.reverse()
            for n,r,ratio in profiles:slots.append(dict(slot=len(slots),family=root['family'],phase=root['phase'],candidate_side=role,candidate_proof=True,candidate_cached=True,R=r,N=n,ratio=ratio,scale=n/720))
    native_plan=json.loads(Path('results/dev_aux/task1866/plan.json').read_text(encoding='utf-8'))['native']
    c=compile_ruleset_for_execution(deserialize_ruleset((ROOT/'rules.json').read_text()));native_plan['fingerprint']=c.ruleset_fingerprint
    native_plan['files']={k:v for k,v in native_plan['files'].items() if Path(k).as_posix()!='results/dev_aux/task1846/rules.json'}
    native_plan['files'][str(ROOT/'rules.json')]=sha(ROOT/'rules.json')
    plan=dict(status='FROZEN_BEFORE_GAMES',question='Does a frozen contact-rich input-only law support actualW-L ratiolearning under a fixed H24 completeplayer on independentactualDEV families? All32roots/3ratios/bothroles, N720fixed/cachedcandidate/fixedcoldUNIT64opponent. TRAIN96beforeDEV96, no unitchoice or oldsource relabel.',
        roots=str(ROOT/'feasibility.json'),roots_sha=sha(ROOT/'feasibility.json'),rules=str(ROOT/'rules.json'),rules_sha=sha(ROOT/'rules.json'),
        native_plan=native_plan,
        qualification='results/dev_aux/task1862/qualification.json',
        source_sha={str(Path(p).relative_to(Path.cwd())) if Path(p).is_absolute() else p:sha(p) for p in SOURCES},slots=slots,expected_games=192,
        candidate_nodes=4096,opponent_nodes=64,candidate_proof_nodes=16384,opponent_proof_nodes=16,proof_seconds=1.5,verification_nodes=16384,verification_seconds=.5,normal_seconds=.1,step_seconds=2.75,normal_depth=3,proof_depth=64,H=24,
        opponent=dict(R=720,N=720,proof=True),prices=[.5,1.,2.],N_units=[720],
        tail='At H16 only already verified rank<=64 strategies authorize up to64extra physical moves; no new proof after H. UNKNOWN not draw, no quantity reward.',
        seconds_cap=1200,expected_seconds=360,max_moves=192*88,
        selector='All96TRAIN actualW-L only, maxratio/smallestratiotie, strictadjacentpathsfromall3initials; write after96TRAIN beforefirst96DEV. DEVneverchoosesratios/units/roots/horizon/weights. ContactTRAIN exploratorypilot/proxies exposed; actualDEV/proxy outcomes unread. No baseline selfcomparison precisionclaim.',
        bank=dict(capacity=256,start='EMPTY',owner='candidate only across chronological price/role counterfactuals',solver='batchPN',time_cancel_depth_unsupported_failedverification='NOT_STORED'),
        cost_decision='Preparednext study only, NOTEXECUTED in61. Inputonly32contactlaw froze beforeproxy/W-L. First4TRAINpilot2/4nonflat provides limitedbasis for a single192game conditionaltest. H8 savescost butmisses1lateWIN/changestie versusH24; chooseH24conservativelybeforeANYcontactDEVdata, notbycontrast/min. FixedN720 avoidsDEVunitchoice. Expected360s/hard1200s, no extension/fees/extra workers or newcalibration. If no holdoutgain retainnegative, notautomaticallyscaleup.',
        load='Ordinary concurrent projects allowed; real elapsed and visit units reported, not equal primitive engine work.',backend='MODIFIED_FAIRY_MATERIAL_ONLY_SESSION',previous_python_control='results/dev_aux/task1823',
        native_scope='ExactNEW1846fingerprint, full rootFEN+record actions, native repetition/nmove disabled; actualSession remains authority. Leaf/native/capture tables aligned jointly, not unmodified Stockfish/NNUE.')
    write('run-plan.json',plan);print(json.dumps(dict(frozen=len(slots),seconds_cap=1200)))
def eval_for(r,n=720):
    def evaluate(position,target):
        return sum((1 if p.owner==target else -1)*({'R':r,'N':n}.get(p.current_type_id,0)) for p in position.board if p is not None)
    return evaluate

def _run():
    plan=json.loads((OUT/'run-plan.json').read_text(encoding='utf-8'))
    assert all(sha(p)==v for p,v in plan['source_sha'].items())
    c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')))
    roots=json.loads(Path(plan['roots']).read_text(encoding='utf-8'))['roots']
    q=json.loads(Path(plan['qualification']).read_text());assert q['status']=='PASS' and q['source_unchanged']
    start=time.perf_counter();done=0;total_moves=0;rows=[];status='COMPLETE'
    from scripts.generic_session_native_material import _load_transport
    from results.dev_aux.task1866.unit_panel import UnitProvider
    native_plan={**plan['native_plan'],'seconds_cap':plan['seconds_cap'],'max_go':192*88}
    transport=_load_transport();globals()['_active_provider']=provider=UnitProvider(native_plan,OUT/'run',stop=lambda:transport.stop_check(Path.cwd()))
    provider.start()
    bank=SessionLogicalProofBank(prove_session_win_batch_pn,capacity=plan['bank']['capacity'])
    def cancelled():return time.perf_counter()-start>=plan['seconds_cap']
    with (OUT/'games.jsonl').open('x',encoding='utf-8') as games,(OUT/'moves.jsonl').open('x',encoding='utf-8') as moves:
        for slot in plan['slots']:
            if cancelled():status='GLOBAL_CAP';break
            current=GameSession(c,roots[slot['family']]['setup']);players=[]
            for side in (0,1):
                candidate=side==slot['candidate_side']
                price=slot['R'] if candidate else 720
                nprice=slot['N'] if candidate else 720
                values=(price,nprice,nprice,nprice)
                def normal(state,n,seconds,cancel,values=values):return provider.choose(current,state,values,n,seconds,cancel)
                player_class=SessionCachedPhasePlayer if candidate and slot['candidate_cached'] else SessionPhasePlayer
                extra={'bank':bank} if player_class is SessionCachedPhasePlayer else {}
                players.append(player_class(c,eval_for(price,nprice),**extra,normal_search=normal,limits=PhaseLimits(proof_nodes=plan['candidate_proof_nodes'] if candidate else plan['opponent_proof_nodes'],verification_nodes=plan['verification_nodes'],proof_seconds=plan['proof_seconds'],verification_seconds=plan['verification_seconds'],normal_seconds=plan['normal_seconds']),
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
            score=1 if outcome=='WIN' else -1 if outcome=='LOSS' else 0
            record=json.loads(serialize_game_record(current.to_record()))
            row=dict(**slot,outcome=outcome,finite_event_score=score,result=asdict(result),reason=reason,
                moves=len(history),tail=tail,seconds=time.perf_counter()-game_start,record=record,final_state_sha=sha_state(current.state),
                proof_moves=sum(x['source'] in ('PROOF','PROOF_CONTINUATION') for x in history),
                normal_node_overruns=sum(x['search_nodes']>x['budget'] for x in history))
            row['result']['status']=result.status.value;games.write(json.dumps(row)+'\n');games.flush();rows.append(row);done+=1
            if done==96:
                scores={ratio:sum(x['finite_event_score'] for x in rows if x['ratio']==ratio) for ratio in (.5,1.,2.)}
                write('selection-before-dev.json',dict(scope='96completeTRAIN only before96DEV; N720fixed, no unit/horizon/DEVselection.',scores=scores,selected=min(scores,key=lambda r:(-scores[r],r))))
            if done%24==0:print(json.dumps(dict(done=done,moves=total_moves,seconds=round(time.perf_counter()-start,3))),flush=True)
            if status=='GLOBAL_CAP':break
    provider.close()
    write('completion.json',dict(status=status,completed=done,expected=192,moves=total_moves,seconds=time.perf_counter()-start,
        source_sha=plan['source_sha'],native_go=provider.queries,native_nodes=provider.reported_nodes,source_unchanged=all(sha(p)==v for p,v in plan['source_sha'].items())))
def sha_state(state):return hashlib.sha256(repr(state).encode()).hexdigest()
def run():
    try:_run()
    except BaseException as error:
        write('error.json',dict(error=type(error).__name__+':'+str(error)))
        raise
    finally:
        provider=globals().pop('_active_provider',None)
        if provider is not None:
            if provider.e is not None and not provider.e.closed:provider.e.close()
            if not provider.journal.closed:provider.journal.close()

if __name__=='__main__':
    {'freeze':freeze,'run':run}[sys.argv[1]]()
