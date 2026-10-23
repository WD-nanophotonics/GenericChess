"""Small all-defense proofs for the observed one-orbit defensive escape."""
from copy import copy
from pathlib import Path
import json,time
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import admit,history_solver
from scripts.leaper_cooperative_certificate import decode_position
from scripts.generic_session_win_proof import SessionChoice,SessionProofNode,SessionWinCertificate,verify_session_certificate
from scripts.generic_session_certificate_json import export_session_certificate
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record


def extract(directory,adjacency,*,seconds=120):
    start=time.perf_counter();directory=Path(directory);source=load(directory/'inputs.json.gz');output=[]
    for pair in adjacency['pairs']:
        selected=[r for r in pair['rows']if r['left_WDL']==-1 and r['right_WDL']==0]
        family=next(f for f in source['families']if f['family']==pair['left_family'])
        first=next(r for r in source['rows']if r['family']==family['family']);c=admit(family,first)
        domain=load(directory/f"domain{family['family']}.json.gz");positions=[decode_position(p,c.initial_position)for p in domain['positions']];indices={p:i for i,p in enumerate(positions)}
        edges=domain['edges'];terms={int(k):v for k,v in domain['terminals'].items()};solve,work=history_solver(edges,terms,[p.side_to_move for p in positions],lambda n:None)
        for row in selected:
            root=GameSession.replay(c,deserialize_game_record(json.dumps(row['left_record'])));charged=0;target=1
            def node(session,remaining,prior):
                nonlocal charged
                if time.perf_counter()-start>=seconds or charged>=8192:raise RuntimeError('EXTRACT_CAP_UNKNOWN')
                charged+=1
                if session.result.status.value!='ongoing':
                    if session.result.winner!=target:raise ValueError('strategy did not reach actual target win')
                    return SessionProofNode(0,terminal=session.result)
                if remaining<=0:raise ValueError('unclosed strategy at H6')
                i=indices[session.state.position];visited=tuple(sorted((*prior,i)));branches=[]
                own=session.state.position.side_to_move==target
                for action in session.legal_actions():
                    child=copy(session);child.submit(action);j=indices[child.state.position]
                    if own and solve(j,remaining-1,visited)[0]!=-1:continue
                    sub=node(child,remaining-1,visited);branches.append((SessionChoice('ACTION',action=action),sub))
                    if own:break
                if not branches:raise ValueError('no rank-consistent strategy edge')
                return SessionProofNode(1+max(n.rank for a,n in branches),tuple(branches))
            certificate=SessionWinCertificate(c.ruleset_fingerprint,root.to_record(),root.state,target,node(root,6,()))
            receipt=verify_session_certificate(root,certificate,max_nodes=8192,seconds=30)
            if not receipt['verified']:raise ValueError('independent literal certificate failed')
            output.append(dict(left_id=row['left_id'],right_id=row['right_id'],placement=row['placement'],
                left_forced_loss_certificate=export_session_certificate(root,certificate,max_nodes=8192),
                independent_verification=receipt,right_draw_escapes=row['new_best_escapes']))
    return dict(format='leaper-H6-onebit-literal-certificates-v1',adjacency_digest=digest(adjacency),rows=output,
        verified_nodes=sum(r['independent_verification']['nodes']for r in output),
        verified_transitions=sum(r['independent_verification']['session_transitions']for r in output),
        seconds=time.perf_counter()-start,scope='All16observed LOSS-to-DRAW roots: actual oldrule full-history all-defense mate certificates forseat1; newrule literal capture reaches independently closed no-mate subdomain. Proof extraction from already solved labels,not a newsearch/Player campaign.')


if __name__=='__main__':
    import argparse
    cli=argparse.ArgumentParser();cli.add_argument('--directory',required=True);cli.add_argument('--adjacency',required=True);cli.add_argument('--output',required=True);a=cli.parse_args();r=extract(a.directory,load(a.adjacency));save(a.output,r);print(json.dumps({k:v for k,v in r.items()if k!='rows'}))
