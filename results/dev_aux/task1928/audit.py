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
    folder=Path(folder);plan=read(folder/'run-plan.json');completion=read(folder/'completion.json')
    rows=lines(folder/'games.jsonl');moves=lines(folder/'moves.jsonl');by_slot=defaultdict(list)
    for row in moves:by_slot[row['slot']].append(row)
    assert completion['status']=='COMPLETE' and len(rows)==len(plan['slots'])==completion['completed']==plan['expected_games']
    assert len(moves)==completion['moves'] and len({x['slot'] for x in rows})==plan['expected_games']
    c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text(encoding='utf-8')))
    roots=read(plan['roots'])['roots'];actor=RoyalActor(4);proof_games=tail_games=tail_moves=proof_steps=0;causes=Counter();terminal=Counter()
    node_overruns=0;cert_owners=Counter();native_bindings=[];phase_seconds=Counter();proof_work=Counter()
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
            proof_cap=plan['candidate_proof_nodes'] if step['side']==game['candidate_side'] else plan['opponent_proof_nodes']
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
        if outcome=='UNKNOWN':assert len(trajectory)>=plan['H'] and not tail_admitted
        if owners:
            assert len(owners)==1 and s.result.winner==next(iter(owners))
            proof_games+=1;cert_owners[next(iter(owners))]+=1
        if tail_admitted:assert s.result.status is not SessionStatus.ONGOING;tail_games+=1
        assert tail_admitted==game['tail'];terminal[s.result.status.value]+=1
    actual_native=0
    if (folder/'run/transport.jsonl').exists():
        events=lines(folder/'run/transport.jsonl');intent=[x for x in events if x['event']=='INTENT'];sent=[x for x in events if x['event']=='SENT'];chosen=[x for x in events if x['event']=='CHOICE'];external=[x for x in moves if x['source']=='EXTERNAL_SEARCH']
        assert len(intent)==len(sent)==len(chosen)==len(external)==completion['native_go']
        for ordinal,(a,b,ch,step) in enumerate(zip(intent,sent,chosen,external)):
            assert a['query']==b['query']==ch['query']==ordinal
            game=rows[step['slot']];r=[game['R'],game['N'],game['N'],game['N']] if step['side']==game['candidate_side'] else [720]*4
            assert a['R']==ch['R']==r and ch['reported_nodes']==step['search_nodes']
            assert ch['requested_nodes']==step['budget']
            assert (a['position'],a['root_record'])==native_bindings[ordinal]
            assert f"go nodes {ch['requested_nodes']} " in a['command']
            assert uci(deserialize_game_record(json.dumps({'schema_version':1,'ruleset_fingerprint':c.ruleset_fingerprint,'actions':[step['choice']],'resigned_by':None})).actions[0])==ch['move']
        actual_native=len(chosen)
    return dict(status='PASS_ALL_PHYSICAL_SLOTS',folder=str(folder),games=len(rows),moves=len(moves),actual_native=actual_native,proof_games=proof_games,proof_steps=proof_steps,
        all_adopted_proof_games_physically_won=True,tail_games=tail_games,tail_moves=tail_moves,terminal=dict(terminal),exit_causes=dict(causes),node_overruns=node_overruns,
        phase_seconds=dict(phase_seconds),proof_work=dict(proof_work),full_native_history_bindings=len(native_bindings),selection_scope=plan['selector'],actual_max_proof_depth=max((m['proof_stats'].get('peak_depth',0) for m in moves),default=0),source='No proving/search/Native calls; public record replay+literal actor transition+exact state/result/rank/receipt checks')



def main():
    folder=Path('results/dev_aux/task1920');out=audit(folder)
    games=lines(folder/'games.jsonl');moves=lines(folder/'moves.jsonl');p=read(folder/'run-plan.json');sel=read(folder/'selection-before-dev.json');index={(g['phase'],g['family'],g['candidate_side'],g['N'],g['ratio']):g for g in games};cells=[];selections={};comparisons=[]
    for unit in p['N_units']:
        scores={ratio:sum(g['finite_event_score'] for g in games if g['phase']=='TRAIN' and g['N']==unit and g['ratio']==ratio) for ratio in (1.,2.,3.,4.)};selected=min(scores,key=lambda r:(-scores[r],r))
        assert sel['selected']==selected and {float(k):v for k,v in sel['scores'].items()}==scores
        vectors=[[sum(index['TRAIN',family,role,unit,ratio]['finite_event_score'] for role in (0,1)) for ratio in (1.,2.,3.,4.)] for family in range(16)]
        paths=[]
        for initial in (1.,2.,3.,4.):
            current=initial;path=[current]
            while True:
                adjacent=[r for r in (1.,2.,3.,4.) if abs((1.,2.,3.,4.).index(r)-(1.,2.,3.,4.).index(current))==1 and scores[r]>scores[current]]
                if not adjacent:break
                current=min(adjacent,key=lambda r:(-scores[r],r));path.append(current)
            paths.append(dict(initial=initial,path=path,endpoint=current))
        selections[unit]=dict(scores=scores,selected=selected,paths=paths,nonflat_train_families=sum(len(set(v))>1 for v in vectors),family_vectors=vectors)
        for phase in ('TRAIN','DEV'):
            for ratio in (1.,2.,3.,4.):
                gs=[g for g in games if g['phase']==phase and g['N']==unit and g['ratio']==ratio];assert len(gs)==32
                cells.append(dict(phase=phase,N=unit,ratio=ratio,games=32,outcomes=dict(Counter(g['outcome'] for g in gs)),net=sum(g['finite_event_score'] for g in gs),seconds=sum(g['seconds'] for g in gs)))
        for initial in (1.,2.,3.,4.):
            delta=[];bounds=[];transitions=Counter();role_sums=Counter()
            for family in range(16,32):
                ds=[]
                for role in (0,1):
                    a=index['DEV',family,role,unit,initial];b=index['DEV',family,role,unit,selected];value=b['finite_event_score']-a['finite_event_score'];ds.append(value);role_sums[role]+=value;transitions[a['outcome']+'->'+b['outcome']]+=1
                    if a['slot']==b['slot']:bounds.append((0,0))
                    else:bounds.append(((b['finite_event_score'] if b['outcome']!='UNKNOWN' else -1)-(a['finite_event_score'] if a['outcome']!='UNKNOWN' else 1),(b['finite_event_score'] if b['outcome']!='UNKNOWN' else 1)-(a['finite_event_score'] if a['outcome']!='UNKNOWN' else -1)))
                delta.append(sum(ds)/2)
            rng=random.Random(20261016631928);boot=sorted(sum(rng.choices(delta,k=16))/16 for _ in range(20000));comparisons.append(dict(N=unit,initial=initial,selected=selected,identical_cell=initial==selected,mean=sum(delta)/16,family95=[boot[500],boot[19499]],family_deltas=delta,role_means={k:v/16 for k,v in role_sums.items()},transitions=dict(transitions),unknown_worst_case_bounds=[sum(b[i] for b in bounds)/32 for i in (0,1)]))
    candidate=[m for m in moves if m['side']==games[m['slot']]['candidate_side']];q=[m for m in candidate if m.get('logical_status')!='NOT_QUERIED'];physical=dict(queries=len(q),hits=sum(m['bank_hit'] for m in q),misses=sum(not m['bank_hit'] for m in q),actual_proof_nodes=sum(m['proof_nodes'] for m in candidate),logical_proof_nodes=sum(m['logical_proof_nodes'] for m in candidate),fill_verification_nodes=sum(m['fill_verification_nodes'] for m in candidate),fill_verification_seconds=sum(m['fill_verification_seconds'] for m in candidate),current_verification_nodes=sum(m['verification_nodes'] for m in candidate),max_proof_depth=max((dict(m['proof_stats']).get('peak_depth',0) for m in candidate),default=0))
    out.update(cells=cells,selections=selections,comparisons=comparisons,candidate_bank=physical,scope='32NEWinput-only oneRtwoNfamilies, fixedN720/4ratios/roles/H24/fixedcoldUNIT64proofopponent. All128TRAIN before128DEV. NoDEVroot/price/H/weightselection. TRAIN-onlycomplete-depthdiagnosticwasfrozenAFTERactualW-Lproducerstart, notaretroactiveinputgate. ConditionalfiniteeventW-L/UNKNOWN only, not infinitehorizonWDL or universalhumanprices. CIclusters16families, selfcomparisonzeroalgebraicnotprecision.')
    with (Path('results/dev_aux/task1928')/'audit_report.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
    print(json.dumps({k:v for k,v in out.items() if k not in ('proof_work','cells','comparisons')}))
if __name__=='__main__':main()
