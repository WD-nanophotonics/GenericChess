"""Frozen choice-only phase attribution, not a new price/WDL game experiment."""
from pathlib import Path
from dataclasses import asdict
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_session_native_material import SessionKRNMaterialProvider,_load_transport
from scripts.generic_session_proof_player import SessionProofMaterialPlayer
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
OUT=Path('results/dev_aux/task1836');base=json.loads(Path('results/dev_aux/task1824/plan.json').read_text());base.update(seconds_cap=120,max_go=15)
c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1822/rules.json').read_text()));cases=[dict(slot='fresh0',record=None)]+json.loads(Path('results/dev_aux/task1827/plan.json').read_text())['cases']
plan=dict(question='For qualified current actual-session choice, does proof, Native normal search or full root admission dominate? One fixed exposed fresh root plus four saved long-history endpoints, baselineR720 only, no commitments/price optimization.',cases=cases,methods=['PLAIN','SESSION','BATCH'],nodes=4096,seconds=.25,seconds_cap=120,source_sha={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in ['scripts/generic_session_proof_player.py','scripts/generic_session_native_material.py','scripts/generic_session_win_proof_pn.py','scripts/generic_session_win_proof_batch_pn.py']},scope='15choice calls, no physical games or WDLlabels, same phase allocation. Existing game sources/rewards immutable; Native remainder visits differ by spentproof, report actual receipts not equal primitive work.')
with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
A=_load_transport();provider=SessionKRNMaterialProvider(base,OUT/'run',stop=lambda:A.stop_check(Path.cwd()));rows=[];start=time.perf_counter()
try:
    provider.start()
    for i,case in enumerate(cases):
        methods=plan['methods'][::(-1 if i%2 else 1)]
        for method in methods:
            current=GameSession(c) if case['record'] is None else GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])))
            def normal(state,n,seconds,cancel):return provider.choose(current,state,720,n,seconds,cancel)
            p=SessionProofMaterialPlayer(c,lambda position,target:0,proof_enabled=method!='PLAIN',proof_search=prove_session_win_batch_pn if method=='BATCH' else prove_session_win_pn,normal_search=normal)
            d=p.choose(current,max_nodes=4096,seconds=.25)
            assert d.choice is not None
            parts=dict(admission=d.admission_seconds,proof=d.proof_seconds,verification=d.verification_seconds,normal=d.normal_seconds)
            assert sum(parts.values())<=d.seconds+.000001
            rows.append(dict(slot=case['slot'],method=method,source=d.source,total_seconds=d.seconds,phase_seconds=parts,nodes=d.nodes,proof_nodes=d.proof_nodes,verification_nodes=d.verification_nodes,search_nodes=d.search_nodes,exit_cause=d.exit_cause))
finally:provider.close()
summary={method:{phase:sum(x['phase_seconds'][phase] for x in rows if x['method']==method) for phase in ('admission','proof','verification','normal')} for method in plan['methods']}
out=dict(status='COMPLETE',calls=len(rows),new_native_go=provider.queries,new_physical_games=0,seconds=time.perf_counter()-start,summary=summary,rows=rows)
with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
