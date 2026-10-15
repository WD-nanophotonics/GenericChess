"""Independent public replay / fixed-slot / actual outcome and rank audit.

No prover, engine, search or reward recomputation by material. Each physical
move is replayed from public GameRecord actions and compared with literal actor
children, exact full-state hashes and actual SessionResult.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,random,statistics,sys
from dataclasses import asdict
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def lines(path):return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines()]
def state_sha(state):return hashlib.sha256(repr(state).encode()).hexdigest()
def result_dict(s):
    result=asdict(s.result);result['status']=s.result.status.value;return result

def audit(folder):
    folder=Path(folder);plan=read(folder/('audit-plan.json' if (folder/'audit-plan.json').exists() else 'run-plan.json'));completion=read(folder/'completion.json')
    rows=lines(folder/'games.jsonl');moves=lines(folder/'moves.jsonl');by_slot=defaultdict(list)
    for row in moves:by_slot[row['slot']].append(row)
    assert completion['status'] in ('COMPLETE','GLOBAL_CAP') and len(rows)==completion['completed']<=len(plan['slots'])==plan['expected_games'];assert completion['status']!='COMPLETE' or len(rows)==plan['expected_games']
    assert len(moves)==completion['moves'] and len({x['slot'] for x in rows})==plan['expected_games']
    c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')))
    roots=read(plan['roots'])['roots'];actor=RoyalActor(4);proof_games=tail_games=tail_moves=proof_steps=0;causes=Counter();terminal=Counter()
    node_overruns=0;cert_owners=Counter();native_bindings=[];phase_seconds=Counter();proof_work=Counter();incomplete_slots=[];pending_proof_slots=[]
    for expected,game in zip(plan['slots'],rows):
        assert all(game[k]==v for k,v in expected.items())
        s=GameSession(c,roots[game['family']]['setup']);trajectory=by_slot[game['slot']];owners=set();tail_admitted=False
        assert len(trajectory)==game['moves']
        for ply,step in enumerate(trajectory):
            assert step['ply']==ply and s.result.status is SessionStatus.ONGOING
            assert s.state.position.side_to_move==step['side'] and state_sha(s.state)==step['before_state_sha']
            budget=plan['candidate_nodes'] if step['side']==game['candidate_side'] else game.get('opponent_nodes',plan['opponent_nodes'])
            assert step['budget']==budget
            requested_proof=game['candidate_proof'] if step['side']==game['candidate_side'] else True
            if step['source']=='PROOF':
                assert requested_proof and ply<plan['H'];owners.add(step['side']);proof_steps+=1
            if not requested_proof:assert step['proof_nodes']==step['verification_nodes']==0 and step['source'] not in ('PROOF','PROOF_CONTINUATION')
            proof_cap=game.get('candidate_proof_nodes',plan['candidate_proof_nodes']) if step['side']==game['candidate_side'] else plan['opponent_proof_nodes']
            assert step['proof_nodes']<=proof_cap and step['verification_nodes']<=plan['verification_nodes']
            expected_limits=dict(normal_nodes=budget,proof_nodes=proof_cap,verification_nodes=plan['verification_nodes'],total_seconds=plan['step_seconds'],proof_seconds=plan['proof_seconds'],verification_seconds=plan['verification_seconds'],normal_seconds=plan['normal_seconds'])
            cached=game['candidate_cached'] and step['side']==game['candidate_side']
            if cached:
                expected_limits.update(bank_fill_verification_nodes=plan['verification_nodes'],bank_fill_verification_seconds=plan['verification_seconds'])
                assert step['fill_verification_nodes']<=plan['verification_nodes']
                if step['bank_hit']:
                    assert step['proof_nodes']==step['fill_verification_nodes']==0
                    assert all(v==0 for v in step['proof_stats'].values())
                    assert step['logical_reason'] in ('proven_rule_win','node_budget','no_forced_win_in_exhausted_tree') or step['logical_status']=='PROVEN_WIN'
                if step['source']=='PROOF':assert step['verification_nodes']>0
            assert step['phase_limits']==expected_limits
            for phase_name in ('admission_seconds','proof_seconds','verification_seconds','normal_seconds'):
                assert step[phase_name]>=0;phase_seconds[phase_name]+=step[phase_name]
            assert sum(step[k] for k in ('admission_seconds','proof_seconds','verification_seconds','normal_seconds'))<=step['seconds']+.000001
            proof_work.update({k:v for k,v in step['proof_stats'].items() if k!='peak_depth'})
            if step['source']=='EXTERNAL_SEARCH':
                root=GameSession(c,roots[game['family']]['setup']);record=s.to_record()
                command='position fen '+actor.fen(actor_state(root.state))+(' moves '+' '.join(uci(a) for a in record.actions) if record.actions else '')
                native_bindings.append((command,repr(record)))
            if ply>=plan['H']:
                assert step['tail'] and step['proof_nodes']==step['verification_nodes']==0 and step['source']!='PROOF'
                assert any(rank is not None and 0<rank<=64 for rank in step['before_ranks'])
                tail_admitted=True;tail_moves+=1
            else:assert not step['tail']
            expected_actor=dict(actor.moves(actor_state(s.state)))
            actual={uci(a):a for a in s.legal_actions()};assert set(actual)==set(expected_actor)
            # This scoped frozen law has only physical board moves.
            encoded=step['choice'];record=s.to_record()
            raw=json.loads(serialize_game_record(record));raw['actions'].append(encoded)
            child_record=deserialize_game_record(json.dumps(raw))
            action=child_record.actions[-1];text=uci(action);assert text in expected_actor
            s.submit(action)
            assert actor_state(s.state)==expected_actor[text]
            assert state_sha(s.state)==step['after_state_sha'] and result_dict(s)==step['result']
            for before,after in zip(step['before_ranks'],step['after_ranks']):
                if before is not None and before>0:assert after is not None and 0<=after<before
            causes[step['exit_cause']]+=1
            node_overruns+=step['search_nodes']>budget
        replayed=GameSession.replay(c,deserialize_game_record(json.dumps(game['record'])))
        assert _same_state(s.state,replayed.state) and _same_state(s.result,replayed.result)
        assert state_sha(s.state)==game['final_state_sha'] and result_dict(s)==game['result']
        outcome='UNKNOWN' if s.result.status is SessionStatus.ONGOING else ('DRAW' if s.result.winner is None else ('WIN' if s.result.winner==game['candidate_side'] else 'LOSS'))
        assert game['outcome']==outcome and game['finite_event_score']==(1 if outcome=='WIN' else -1 if outcome=='LOSS' else 0)
        if outcome=='UNKNOWN':
            if game['reason']=='H_UNKNOWN':assert len(trajectory)>=plan['H'] and not tail_admitted
            else:assert completion['status']!='COMPLETE';incomplete_slots.append(game['slot'])
        if owners:
            assert len(owners)==1
            if s.result.status is SessionStatus.ONGOING:
                assert completion['status']!='COMPLETE' and game['slot'] in incomplete_slots;pending_proof_slots.append(game['slot'])
            else:
                assert s.result.winner==next(iter(owners));proof_games+=1;cert_owners[next(iter(owners))]+=1
        if tail_admitted:
            assert s.result.status is not SessionStatus.ONGOING or game['slot'] in incomplete_slots
            tail_games+=1
        assert tail_admitted==game['tail'];terminal[s.result.status.value]+=1
    actual_native=0
    if (folder/'run/transport.jsonl').exists():
        events=lines(folder/'run/transport.jsonl');intent=[x for x in events if x['event']=='INTENT'];sent=[x for x in events if x['event']=='SENT'];chosen=[x for x in events if x['event']=='CHOICE'];external=[x for x in moves if x['source']=='EXTERNAL_SEARCH']
        assert len(external)<=len(chosen)<=len(sent)<=len(intent)==completion['native_go']
        assert completion['status']!='COMPLETE' or len(intent)==len(sent)==len(chosen)==len(external)
        for ordinal,(a,b,ch,step) in enumerate(zip(intent,sent,chosen,external)):
            assert a['query']==b['query']==ch['query']==ordinal
            game=rows[step['slot']];r=[game['R'],game['N'],game['N'],game['N']] if step['side']==game['candidate_side'] else [game['opponent_R'],720,720,720]
            assert a['R']==ch['R']==r and ch['reported_nodes']==step['search_nodes']
            assert ch['requested_nodes']==step['budget']
            assert (a['position'],a['root_record'])==native_bindings[ordinal]
            assert f"go nodes {ch['requested_nodes']} " in a['command']
            assert uci(deserialize_game_record(json.dumps({'schema_version':1,'ruleset_fingerprint':c.ruleset_fingerprint,'actions':[step['choice']],'resigned_by':None})).actions[0])==ch['move']
        actual_native=len(external)
    return dict(status='PASS_ALL_PHYSICAL_SLOTS',folder=str(folder),games=len(rows),moves=len(moves),actual_native=actual_native,proof_games=proof_games,proof_steps=proof_steps,
        all_adopted_proof_games_physically_won=not pending_proof_slots,incomplete_game_slots=incomplete_slots,pending_proof_slots=pending_proof_slots,full_study_complete=completion['status']=='COMPLETE',expected_games=plan['expected_games'],missing_game_slots=[s['slot'] for s in plan['slots'][len(rows):]],tail_games=tail_games,tail_moves=tail_moves,terminal=dict(terminal),exit_causes=dict(causes),node_overruns=node_overruns,
        phase_seconds=dict(phase_seconds),proof_work=dict(proof_work),full_native_history_bindings=len(native_bindings),selection_scope=plan['selector'],actual_max_proof_depth=max((m['proof_stats'].get('peak_depth',0) for m in moves),default=0),source='No proving/search/Native calls; public record replay+literal actor transition+exact state/result/rank/receipt checks')
