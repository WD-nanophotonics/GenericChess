"""Bounded exact finite-session model check, zero Native games/training.

The reference enumerates every session choice, including losing declarations,
using public GameSession replay. Solver copies and prunes AND/OR branches;
reference does neither. Complete records only are compared, partial cap retained.
"""
import collections,json,time,random
from dataclasses import replace
from pathlib import Path
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import RuleDeclaration,RuleDeclarationOutcomeBand,RuleWeightedMaterialMetric,RuleSpatialSelector,RuleStateGuard,RuleTypeRef
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_native_study import sha,mod
from scripts.generic_session_win_proof import prove_session_win,verify_session_certificate,SessionStrategyCursor


def freeze(folder):
    out=Path(folder);out.mkdir(exist_ok=False);rng=random.Random(20261015571);roots=[];actor=RoyalActor(4)
    while len(roots)<8:
        k,b,r=rng.sample(range(16),3);raw=['.']*16;raw[k]='K';raw[b]='k';raw[r]='R';state=tuple(raw)+(0,)
        if not actor.valid(state) or actor.attacked(state,actor.king(state,1),0) or len(actor.moves(state))<2:continue
        if dict(k=k,b=b,r=r) not in roots:roots.append(dict(k=k,b=b,r=r))
    sources=['scripts/generic_session_win_proof.py','scripts/generic_session_proof_validation.py']
    p=dict(roots=roots,profiles=['NONE','CONDITIONAL_WIN_RESTART','CONDITIONAL_RESTART_LOSS'],max_ply=8,targets=[0,1],max_reference_nodes=3000000,total_seconds=1500,proof_nodes=65536,proof_seconds=1.,verification_nodes=262144,verification_seconds=3.,expected_seconds=600,source_sha256={x:sha(x) for x in sources},question='Does typed session proof agree with actual complete finite WIN/RESTART/LOSS rule outcomes, and can public record replay bound its practical cost?',reason='Known real KRK defense needs6decisions with full history; maxply8 validates beyond trivial immediate declarations. No Native go, training, statistical games or product changes. If full enumeration caps, retain complete cases plus current partial, never extend or claim complete domain.')
    (out/'plan.json').write_text(json.dumps(p,indent=2),encoding='utf-8')


def make(root,profile,limit):
    rs=krk_ruleset(4);board=[None]*16
    for key,owner,kind in [('k',0,'K'),('b',1,'K'),('r',0,'R')]:board[root[key]]=Piece(owner,kind,kind)
    declarations=[]
    if profile!='NONE':
        for owner in (0,1):
            zone=RuleSpatialSelector('zone',zone_squares=tuple((x,3 if owner==0 else 0) for x in range(4)))
            guard=RuleStateGuard('exists','self',RuleTypeRef('explicit','K'),'base','any','board',zone,value=1)
            outcome=('WIN' if owner==0 else 'RESTART') if profile=='CONDITIONAL_WIN_RESTART' else 'RESTART'
            # Spatial guard and actual ply limit make availability history-dependent.
            declarations.append(RuleDeclaration('opaque_'+str(owner),owner,state_guards=(guard,),require_not_in_check=False,ply_limit=7,weighted_metric=RuleWeightedMaterialMetric(weights={'K':1,'R':1}),outcome_bands=(RuleDeclarationOutcomeBand(1,outcome),),failure_outcome='LOSS'))
    rs=replace(rs,initial_position=tuple(tuple(board[i:i+4]) for i in range(0,16,4)),max_ply=limit,declarations=tuple(declarations))
    return GameSession(compile_ruleset(rs))


def run(folder):
    out=Path(folder);p=json.loads((out/'plan.json').read_text(encoding='utf-8'));assert all(sha(x)==v for x,v in p['source_sha256'].items())
    stop=mod('SESSION57STOP','results/dev_aux/task166/run.py').stop;started=time.perf_counter();deadline=started+p['total_seconds'];nodes=edges=0;counts=collections.Counter();done=proved=0;error=None;active={}
    def guard():
        if time.perf_counter()>=deadline:raise RuntimeError('frozen_session_reference_wallcap')
        if nodes>=p['max_reference_nodes']:raise RuntimeError('frozen_session_reference_nodecap')
        if nodes%64==0:stop()
    def exact(session):
        nonlocal nodes,edges
        guard();nodes+=1;result=session.result
        if result.status is not SessionStatus.ONGOING:
            counts[result.status.value+':'+str(result.declaration_outcome)]+=1
            return 0 if result.winner is None else 1 if result.winner==0 else -1
        # Independent public enumeration: do not use prover choices/execute.
        children=[]
        for declaration in session.compiled.declarations:
            if declaration.owner!=session.state.position.side_to_move:continue
            guard();child=GameSession.replay(session.compiled,session.to_record());child.declare(declaration.declaration_id);edges+=1;children.append(exact(child))
        for action in session.legal_actions():
            guard();child=GameSession.replay(session.compiled,session.to_record());child.submit(action);edges+=1;children.append(exact(child))
        assert children,'unreported session terminal'
        return max(children) if session.state.position.side_to_move==0 else min(children)
    with (out/'calls.jsonl').open('x',encoding='utf-8') as log:
        try:
            for i,root in enumerate(p['roots']):
                for profile in p['profiles']:
                    stop();guard();session=make(root,profile,p['max_ply']);before=nodes;beg=time.perf_counter();active=dict(root=i,profile=profile,phase='REFERENCE')
                    label=exact(session);ref_seconds=time.perf_counter()-beg
                    for target in p['targets']:
                        stop();guard();active.update(phase='PROOF',target=target)
                        result=prove_session_win(session,target=target,max_nodes=p['proof_nodes'],seconds=p['proof_seconds'],max_depth=p['max_ply']+1,cancel=lambda:time.perf_counter()>=deadline)
                        receipt=None;path=[]
                        if result.status=='PROVEN_WIN':
                            assert label==(1 if target==0 else -1),'false session win'
                            receipt=verify_session_certificate(session,result.certificate,max_nodes=p['verification_nodes'],seconds=p['verification_seconds'],cancel=lambda:time.perf_counter()>=deadline);assert receipt['verified'],receipt
                            branch=GameSession.replay(session.compiled,session.to_record());cursor=SessionStrategyCursor(branch,result.certificate,max_nodes=p['verification_nodes'],seconds=p['verification_seconds'])
                            while cursor.node.edges:
                                choice=cursor.node.edges[0][0];path.append(dict(rank=cursor.node.rank,kind=choice.kind,declaration=choice.declaration_id));cursor.commit(branch,choice)
                            assert branch.result.winner==target;proved+=1
                        record=dict(root=i,profile=profile,target=target,exact_for_player0=label,reference_nodes=nodes-before,reference_seconds=ref_seconds,solver_status=result.status,solver_reason=result.reason,solver_nodes=result.nodes,solver_seconds=result.seconds,verification=receipt,actual_session_path=path)
                        log.write(json.dumps(record)+'\n');log.flush();done+=1
                    print('SESSION_REFERENCE',i,profile,label,'nodes',nodes,flush=True)
        except BaseException as exc:error=type(exc).__name__+':'+str(exc)
    result=dict(status='COMPLETE_FINITE_SESSION_REFERENCE_PASS' if error is None else 'PARTIAL_PRESERVED',error=error,complete_proof_calls=done,planned_calls=2*len(p['roots'])*len(p['profiles']),proved_verified_and_executed=proved,reference_nodes=nodes,reference_edges=edges,terminal_counts=dict(counts),active_if_interrupted=active if error else None,seconds=time.perf_counter()-started,native_go=0,training_games=0,scope='Complete declared maxply8 session rule outcomes for completed roots only. Independent proof algorithm/public session replay, not independent reimplementation of rules. Budget UNKNOWN never a draw or refutation. Exact labels are not fed to search or material learning.')
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':
    import sys;(freeze if sys.argv[1]=='freeze' else run)(sys.argv[2])
