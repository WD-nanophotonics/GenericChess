"""Bounded attribution of actual public Session transition work, not speedup."""
import json,hashlib,cProfile,pstats,time,collections
from pathlib import Path
from unittest.mock import patch
from generic_chess.session.session import GameSession
from generic_chess.core import transition,terminal
from scripts.generic_session_proof_validation import make
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_win_proof import verify_session_certificate

FOLDER=Path(__file__).parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def freeze():
    old=json.loads(Path('results/dev_aux/task1808/plan.json').read_text(encoding='utf-8'))
    p=dict(cases=[dict(root=0,profile='NONE'),dict(root=0,profile='CONDITIONAL_WIN_RESTART'),dict(root=1,profile='NONE')],roots=old['roots'],max_ply=8,max_depth=9,proof_nodes=65536,proof_seconds=1.,global_seconds=10,scope='three already-exposed complete references; instrumented function counts only, timings include profiler overhead and are not speedup or production comparisons',decision='Is public Session transition cost dominated by repeated parent legality or the optional wrapper? Measure before any API/fast-path change; no Core/default patch or primary attribution takeover.',sources={p:sha(p) for p in ['scripts/generic_session_win_proof_pn.py','scripts/generic_session_win_proof.py','generic_chess/session/session.py','generic_chess/core/transition.py','generic_chess/core/terminal.py','results/dev_aux/task1820/profile.py']})
    with (FOLDER/'plan.json').open('x',encoding='utf-8') as f:json.dump(p,f,indent=2)

def run():
    p=json.loads((FOLDER/'plan.json').read_text(encoding='utf-8'));assert all(sha(k)==v for k,v in p['sources'].items())
    root=Path.cwd().resolve();rows=[];started=time.perf_counter();deadline=started+p['global_seconds']
    for case in p['cases']:
        current=make(p['roots'][case['root']],case['profile'],p['max_ply']);before=current.to_record()
        counts=collections.Counter();parents=collections.Counter();frontier_parents=set();profile=cProfile.Profile()
        old_frontier=GameSession.legal_actions;old_validation=transition.legal_actions;old_submit=GameSession.submit;old_declare=GameSession.declare
        def frontier(session):counts['session_frontiers']+=1;frontier_parents.add(id(session.state));return old_frontier(session)
        def validation(state,compiled):counts['parent_legality_reenumerations']+=1;parents[id(state)]+=1;return old_validation(state,compiled)
        def submit(session,action):counts['public_submit']+=1;return old_submit(session,action)
        def declare(session,claim):counts['public_declare']+=1;return old_declare(session,claim)
        with patch.object(GameSession,'legal_actions',frontier),patch.object(transition,'legal_actions',validation),patch.object(GameSession,'submit',submit),patch.object(GameSession,'declare',declare):
            profile.enable();result=prove_session_win_pn(current,target=0,max_nodes=p['proof_nodes'],seconds=p['proof_seconds'],max_depth=p['max_depth'],cancel=lambda:time.perf_counter()>=deadline);profile.disable()
        assert current.to_record()==before
        receipt=verify_session_certificate(current,result.certificate,max_nodes=262144,seconds=3.) if result.certificate else None
        if receipt:assert receipt['verified']
        functions=[]
        for (filename,line,function),(primitive,calls,self_time,cumulative,callers) in pstats.Stats(profile).stats.items():
            path=Path(filename)
            public=path.relative_to(root).as_posix() if path.is_absolute() and path.is_relative_to(root) else path.name
            functions.append(dict(file=public,line=line,function=function,primitive_calls=primitive,calls=calls,self_seconds=self_time,cumulative_seconds=cumulative))
        functions.sort(key=lambda r:r['cumulative_seconds'],reverse=True)
        rows.append(dict(**case,status=result.status,reason=result.reason,proof_nodes=result.nodes,frontiers=result.frontiers,transitions=result.transitions,instrumented_seconds=result.seconds,verification=receipt,counts=dict(counts),distinct_validation_parents=len(parents),validation_parent_multiplicities=dict(collections.Counter(parents.values())),validation_calls_on_already_frontier_enumerated_parents=sum(n for key,n in parents.items() if key in frontier_parents),top_functions=functions[:35]))
    result=dict(cases=rows,elapsed_seconds=time.perf_counter()-started,new_native_go=0,training_games=0,new_exact_reference_nodes=0,interpretation='source-only research scope; counts show repeated checked parent generation after session frontier, but no fast-path safety/benefit or primary-current-source claim. Root admission/public independent verification remain mandatory.')
    (FOLDER/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps([{k:r[k] for k in ['root','profile','status','proof_nodes','frontiers','transitions','counts','distinct_validation_parents','validation_calls_on_already_frontier_enumerated_parents']} for r in rows],indent=2))
if __name__=='__main__':
 import sys
 freeze() if sys.argv[1]=='freeze' else run()
