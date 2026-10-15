"""Actual existing material binary / full public Session entry qualification."""
from pathlib import Path
import json,hashlib,time
from dataclasses import asdict
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_session_native_material import SessionKRNMaterialProvider,_load_transport
from scripts.generic_session_proof_player import SessionProofMaterialPlayer,commit_session_decision
from scripts.generic_session_win_proof import execute,SessionChoice
from scripts.generic_win_proof import _same_state
from results.dev_aux.task1823.study import eval_for
OUT=Path('results/dev_aux/task1824')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def freeze():
    old=json.loads(Path('results/dev_aux/task1803/plan.json').read_text(encoding='utf-8'))
    qual=json.loads(Path('results/dev_aux/task1822/qualification.json').read_text(encoding='utf-8'))
    ini=Path(old['variant_ini']).read_bytes();(OUT/'variant.ini').write_bytes(ini)
    files=['scripts/generic_session_native_material.py','results/dev_aux/task109/adapter.py',old['binary'],str(OUT/'variant.ini'),'results/dev_aux/task1822/rules.json']
    plan=dict(binary=old['binary'],variant_ini=str(OUT/'variant.ini'),variant_names=old['variant_names'],fingerprint=qual['fingerprint'],
        files={p:sha(p) for p in files},seconds_cap=300,max_go=64,
        declaration='32allroot public/native one-ply frontiers plus every child of first2roots, before gameplay. Then2fixedrole actualSession pilots withR720, fixedopponent64 andcandidate4096, H16+existingstrategy tail64. PriceACK everyprofile; full rootFEN/actionhistory sent. No WDLprice conclusions, 0traininggames.',
        native_scope='Exact new1822KRNrules fingerprint only; modified material-only Fairy, full public authority; rollout nfold/nmove disabled, not unmodified Stockfish or general declarations.')
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    print('FROZEN_QUALIFICATION')
def run():
    p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));A=_load_transport();start=time.perf_counter();provider=SessionKRNMaterialProvider(p,OUT/'run',stop=lambda:A.stop_check(Path.cwd()));error=None;frontiers=actions=0;games=[]
    c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1822/rules.json').read_text(encoding='utf-8')))
    roots=json.loads(Path('results/dev_aux/task1822/qualification.json').read_text(encoding='utf-8'))['roots']
    try:
        provider.start()
        for root in roots:
            s=GameSession(c,root['setup']);actions+=provider.perft_one(s);frontiers+=1
            if root['family']<2:
                for action in s.legal_actions():
                    child=GameSession.replay(c,s.to_record());child.submit(action)
                    if child.result.status is SessionStatus.ONGOING:actions+=provider.perft_one(child);frontiers+=1
        for r in (360,720,1440):provider.profile(r)
        for role in (0,1):
            s=GameSession(c,roots[0]['setup']);players=[];moves=[]
            for side in (0,1):
                def normal(state,n,seconds,cancel):return provider.choose(s,state,720,n,seconds,cancel)
                players.append(SessionProofMaterialPlayer(c,eval_for(720),normal_search=normal))
            for ply in range(80):
                if s.result.status is not SessionStatus.ONGOING:break
                if ply>=16 and not any(x.cursor is not None and x.cursor.node.rank>0 for x in players):break
                side=s.state.position.side_to_move;d=players[side].choose(s,max_nodes=4096 if side==role else 64,seconds=.25,allow_new_proof=ply<16)
                assert d.choice is not None
                result=commit_session_decision(s,d,players)
                rebuilt=GameSession.replay(c,s.to_record());assert _same_state(rebuilt.state,s.state) and _same_state(rebuilt.result,s.result)
                moves.append(dict(ply=ply,side=side,source=d.source,nodes=d.nodes,proof_nodes=d.proof_nodes,verification_nodes=d.verification_nodes,search_nodes=d.search_nodes,seconds=d.seconds,cause=d.exit_cause))
            result=asdict(s.result);result['status']=s.result.status.value
            games.append(dict(role=role,moves=moves,result=result,record=json.loads(serialize_game_record(s.to_record()))))
    except BaseException as ex:error=type(ex).__name__+':'+str(ex)
    finally:provider.close()
    out=dict(status='PASS' if error is None else 'FAILED_PRESERVED',error=error,frontiers=frontiers,legal_actions=actions,games=games,native_go=provider.queries,native_nodes=provider.reported_nodes,seconds=time.perf_counter()-start)
    with (OUT/'qualification.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
    print(json.dumps({k:v for k,v in out.items() if k!='games'}))
if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
