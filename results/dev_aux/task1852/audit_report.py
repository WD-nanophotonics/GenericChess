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
    folder=Path(folder);plan=read(folder/'plan.json');completion=read(folder/'completion.json')
    rows=lines(folder/'games.jsonl');moves=lines(folder/'moves.jsonl');by_slot=defaultdict(list)
    for row in moves:by_slot[row['slot']].append(row)
    assert completion['status']=='COMPLETE' and len(rows)==len(plan['slots'])==completion['completed']==384
    assert len(moves)==completion['moves'] and len({x['slot'] for x in rows})==384
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
            budget=plan['candidate_nodes'] if step['side']==game['candidate_side'] else plan['opponent_nodes']
            assert step['budget']==budget
            requested_proof=game['candidate_proof'] if step['side']==game['candidate_side'] else True
            if step['source']=='PROOF':
                assert requested_proof and ply<plan['H'];owners.add(step['side']);proof_steps+=1
            if not requested_proof:assert step['proof_nodes']==step['verification_nodes']==0 and step['source'] not in ('PROOF','PROOF_CONTINUATION')
            proof_cap=plan['candidate_proof_nodes'] if step['side']==game['candidate_side'] else plan['opponent_proof_nodes']
            assert step['proof_nodes']<=proof_cap and step['verification_nodes']<=plan['verification_nodes']
            expected_limits=dict(normal_nodes=budget,proof_nodes=proof_cap,verification_nodes=plan['verification_nodes'],total_seconds=plan['step_seconds'],proof_seconds=plan['proof_seconds'],verification_seconds=plan['verification_seconds'],normal_seconds=plan['normal_seconds'])
            assert step['phase_limits']==expected_limits
            for phase_name in ('admission_seconds','proof_seconds','verification_seconds','normal_seconds'):
                assert step[phase_name]>=0;phase_seconds[phase_name]+=step[phase_name]
            assert sum(step[k] for k in ('admission_seconds','proof_seconds','verification_seconds','normal_seconds'))<=step['seconds']+.000001
            proof_work.update(step['proof_stats'])
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
            game=rows[step['slot']];r=game['R'] if step['side']==game['candidate_side'] else 720
            assert a['R']==ch['R']==r and ch['reported_nodes']==step['search_nodes']
            assert ch['requested_nodes']==step['budget']
            assert (a['position'],a['root_record'])==native_bindings[ordinal]
            assert f"go nodes {ch['requested_nodes']} " in a['command']
            assert uci(deserialize_game_record(json.dumps({'schema_version':1,'ruleset_fingerprint':c.ruleset_fingerprint,'actions':[step['choice']],'resigned_by':None})).actions[0])==ch['move']
        actual_native=len(chosen)
    return dict(status='PASS_ALL_PHYSICAL_SLOTS',folder=str(folder),games=len(rows),moves=len(moves),actual_native=actual_native,proof_games=proof_games,proof_steps=proof_steps,
        all_adopted_proof_games_physically_won=True,tail_games=tail_games,tail_moves=tail_moves,terminal=dict(terminal),exit_causes=dict(causes),node_overruns=node_overruns,
        phase_seconds=dict(phase_seconds),proof_work=dict(proof_work),full_native_history_bindings=len(native_bindings),selection_scope='fullTRAIN-only deterministic selector; current rows not altered',source='No proving/search/Native calls; public record replay+literal actor transition+exact state/result/rank/receipt checks')

def report(folder):
    folder=Path(folder);rows=lines(folder/'games.jsonl');prices=(360,720,1440);out={'folder':str(folder),'cells':[],'selections':{},'contrasts':[]}
    index={(x['phase'],x['family'],x['candidate_side'],x['candidate_proof'],x['R']):x for x in rows}
    def scores(phase,mode,r):return [x for x in rows if x['phase']==phase and x['candidate_proof']==mode and x['R']==r]
    for phase in ('TRAIN','DEV'):
        for mode in (False,True):
            for r in prices:
                cells=scores(phase,mode,r);out['cells'].append(dict(phase=phase,proof=mode,R=r,games=len(cells),outcomes=dict(Counter(x['outcome'] for x in cells)),net=sum(x['finite_event_score'] for x in cells),seconds=sum(x['seconds'] for x in cells)))
    for mode in (False,True):
        cells={r:scores('TRAIN',mode,r) for r in prices};assert all(len(x)==32 for x in cells.values())
        net={r:sum(x['finite_event_score'] for x in v) for r,v in cells.items()};selected=min(prices,key=lambda r:(-net[r],r));paths=[]
        for initial in prices:
            current=initial;path=[current]
            while True:
                neighbors=[r for r in prices if abs(prices.index(r)-prices.index(current))==1 and net[r]>net[current]]
                if not neighbors:break
                current=min(neighbors,key=lambda r:(-net[r],r));path.append(current)
            paths.append(dict(initial=initial,path=path,endpoint=current))
        vectors=[]
        for family in range(16):vectors.append([sum(index[('TRAIN',family,side,mode,r)]['finite_event_score'] for side in (0,1)) for r in prices])
        out['selections'][str(mode)]=dict(scores=net,selected=selected,paths=paths,nonflat_families=sum(len(set(v))>1 for v in vectors),family_vectors=vectors)
    selected=out['selections']['True']['selected']
    # Common hybrid-TRAIN selected theta for valid 2x2 contrasts; keep fixed opponent.
    definitions=[('A_to_B',(False,720),(True,720)),('A_to_C',(False,720),(False,selected)),('B_to_D',(True,720),(True,selected)),('C_to_D',(False,selected),(True,selected))]
    family_arrays={}
    for name,left,right in definitions:
        deltas=[];transitions=Counter();role=defaultdict(list);time_pair=[];bounds=[]
        for family in range(16,32):
            values=[]
            for side in (0,1):
                a=index[('DEV',family,side,*left)];b=index[('DEV',family,side,*right)]
                value=b['finite_event_score']-a['finite_event_score'];values.append(value);role[side].append(value);transitions[a['outcome']+'->'+b['outcome']]+=1;time_pair.append((a['seconds'],b['seconds']))
                lower=(b['finite_event_score'] if b['outcome']!='UNKNOWN' else -1)-(a['finite_event_score'] if a['outcome']!='UNKNOWN' else 1)
                upper=(b['finite_event_score'] if b['outcome']!='UNKNOWN' else 1)-(a['finite_event_score'] if a['outcome']!='UNKNOWN' else -1)
                if a['slot']==b['slot']:lower=upper=0
                bounds.append((lower,upper))
            deltas.append(sum(values)/2)
        family_arrays[name]=deltas;rng=random.Random(2026101559);bs=sorted(sum(rng.choices(deltas,k=16))/16 for _ in range(20000))
        out['contrasts'].append(dict(name=name,left=left,right=right,identical_cell=left==right,mean=sum(deltas)/16,family95=[bs[500],bs[19499]],family_deltas=deltas,role_means={k:sum(v)/len(v) for k,v in role.items()},transitions=dict(transitions),seconds=[sum(p[i] for p in time_pair) for i in (0,1)],unknown_worst_case_bounds=[sum(p[i] for p in bounds)/32 for i in (0,1)]))
    interaction=[x-y for x,y in zip(family_arrays['C_to_D'],family_arrays['A_to_B'])];rng=random.Random(2026101559);bs=sorted(sum(rng.choices(interaction,k=16))/16 for _ in range(20000));out['interaction']=dict(mean=sum(interaction)/16,family95=[bs[500],bs[19499]],family_deltas=interaction)
    out['interpretation']='Self-comparisons when selected theta equals baseline are algebraic zero, not precision evidence or learning improvement. Exploratory finite-event W-L on declared new initialside0 mu, fixedUNIT64 opponent; UNKNOWN contributes no event but remains censored, worstcase bounds explicit. CI resamples16families, not moves/roles as independent. No unique/human price or infinite WDL claim.'
    return out

if __name__=='__main__':
    folder=sys.argv[1];prefix=Path('results/dev_aux/task1852')/Path(folder).name
    for suffix,fun in [('audit',audit),('report',report)]:
        value=fun(folder)
        with Path(str(prefix)+'-'+suffix+'.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
        print(json.dumps(value if suffix=='audit' else dict(selections=value['selections'],contrasts=[{k:x[k] for k in ('name','mean','family95')} for x in value['contrasts']],interaction=value['interaction'])),flush=True)
