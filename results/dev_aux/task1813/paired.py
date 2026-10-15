"""Counterbalanced old/new optional-session proof cost on fixed real fixtures."""
import importlib.util,sys,json,time,statistics,hashlib
from pathlib import Path
from unittest.mock import patch
from generic_chess.session.session import GameSession
from results.dev_aux.task1813.measure import fixtures
import scripts.generic_session_win_proof as current
spec=importlib.util.spec_from_file_location('session58_previous',Path(__file__).with_name('previous_session_proof.py'))
previous=importlib.util.module_from_spec(spec);sys.modules[spec.name]=previous;spec.loader.exec_module(previous)

def run():
    rows=[];original=GameSession.legal_actions
    cases=list(fixtures())
    for repeat in range(24):
        for name,s in cases[::(-1 if repeat%2 else 1)]:
            reference=None
            for version,m in ([('previous',previous),('current',current)] if repeat%2==0 else [('current',current),('previous',previous)]):
                calls=[0]
                def frontier(session):calls[0]+=1;return original(session)
                before=s.to_record()
                with patch.object(GameSession,'legal_actions',frontier):
                    t=time.perf_counter();p=m.prove_session_win(s,max_depth=1,seconds=3.);ps=time.perf_counter()-t;pc=calls[0];calls[0]=0
                    assert p.status=='PROVEN_WIN'
                    t=time.perf_counter();v=m.verify_session_certificate(s,p.certificate,seconds=3.);vs=time.perf_counter()-t
                    assert v['verified'] and s.to_record()==before
                    key=repr(p.certificate)
                    if reference is None:reference=key
                    else:assert key==reference,'changed certificate'
                rows.append(dict(repeat=repeat,fixture=name,version=version,proof_seconds=ps,verify_seconds=vs,proof_frontiers=pc,verify_frontiers=calls[0],proof_nodes=p.nodes,verify_nodes=v['nodes']))
    summary={}
    for name,s in cases:
        summary[name]={}
        for version in ['previous','current']:
            rr=[r for r in rows if r['fixture']==name and r['version']==version]
            summary[name][version]={k:statistics.median(r[k] for r in rr) for k in ['proof_seconds','verify_seconds','proof_frontiers','verify_frontiers','proof_nodes','verify_nodes']}
        # Physically execute the actual public claim after independent verification.
        p=current.prove_session_win(s,max_depth=1,seconds=3.);cursor=current.SessionStrategyCursor(s,p.certificate,seconds=3.)
        end=cursor.commit(s,cursor.choose(s));assert end.winner==0 and end.declaration_outcome=='WIN'
    output=dict(order='AB/BA each fixture/repeat, reversed fixture order each repeat',repetitions=24,rows=rows,summary=summary,new_native_go=0,training_games=0,certificate_identity='repr of complete old/new trees and root records/states identical for all72paired fixtures',limitation='small immediate declaration costs under ordinary concurrent load; not general search or end-to-end learning speedup',source_hashes={m.__name__:hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in [previous,current]})
    Path(__file__).with_name('paired.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
