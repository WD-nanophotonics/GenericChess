"""NEW finite max-ply4 Session reference qualification, not old oracle continuation.

Independent literal enumeration of public board actions and every owned claim;
no prover frontier/execute helper, no TT, no price or label selection. Exact
actual max-ply4 rule draws differ explicitly from the old H16 censored game.
"""
from copy import copy
from dataclasses import replace
from pathlib import Path
import hashlib,json,time
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import RuleDeclaration
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
OUT=Path('results/dev_aux/task1830')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,data):
    with (OUT/name).open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
def freeze():
    plan=dict(question='Does the new batched public-Core model agree with complete actual Session WDL on a separately declared small finite rule domain, including actual declaration choices?',parent_rules='results/dev_aux/task1822/rules.json',parent_sha=sha('results/dev_aux/task1822/rules.json'),families=list(range(4)),profiles=['NONE','DEFENDER_RESTART','DEFENDER_LOSS','ACTOR_WIN'],max_ply=4,per_case_seconds=30,per_case_nodes=250000,whole_seconds=300,proof_nodes=65536,proof_seconds=2.,proof_depth=5,
        source_sha={str(p):sha(p) for p in [__file__,'scripts/generic_session_win_proof_batch_pn.py','scripts/generic_session_win_proof_pn.py','scripts/generic_session_win_proof.py']},
        scope='NEW maxply4 rules, first4frozen input families and4predeclared claim profiles,16complete games/32target labels if all completed. Does not resume old1808partialcap, label actualH16 outcomes, train prices or claim full generic completeness.')
    write('plan.json',plan)
def run():
    p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items());base=deserialize_ruleset(Path(p['parent_rules']).read_text());roots=json.loads(Path('results/dev_aux/task1822/qualification.json').read_text())['roots'];rows=[];start=time.perf_counter();error=None
    profiles={'NONE':(), 'DEFENDER_RESTART':(RuleDeclaration('restart',1,require_not_in_check=False,failure_outcome='RESTART'),), 'DEFENDER_LOSS':(RuleDeclaration('loss',1,require_not_in_check=False,failure_outcome='LOSS'),), 'ACTOR_WIN':(RuleDeclaration('win',0,require_not_in_check=False,failure_outcome='WIN'),)}
    with (OUT/'cases.jsonl').open('x',encoding='utf-8') as log:
        try:
            for family in p['families']:
                for profile in p['profiles']:
                    assert time.perf_counter()-start<p['whole_seconds'];rules=replace(base,max_ply=p['max_ply'],declarations=profiles[profile]);c=compile_ruleset_for_execution(rules);s=GameSession(c,roots[family]['setup']);nodes=0;beg=time.perf_counter();digest=hashlib.sha256()
                    def solve(current):
                        nonlocal nodes
                        nodes+=1
                        if nodes>p['per_case_nodes'] or time.perf_counter()-beg>p['per_case_seconds'] or time.perf_counter()-start>p['whole_seconds']:raise TimeoutError('new finite reference cap; no partial label')
                        result=current.result;digest.update(repr((current.to_record(),result)).encode())
                        if result.status is not SessionStatus.ONGOING:return 0 if result.winner is None else 1 if result.winner==0 else -1
                        values=[]
                        for declaration in current.compiled.declarations:
                            if declaration.owner==current.state.position.side_to_move:
                                child=copy(current);child.declare(declaration.declaration_id);values.append(solve(child))
                        for action in current.legal_actions():
                            child=copy(current);child.submit(action);values.append(solve(child))
                        assert values
                        return (max if current.state.position.side_to_move==0 else min)(values)
                    value=solve(s);oracle_seconds=time.perf_counter()-beg;proofs=[]
                    for target in (0,1):
                        for name,solver in [('SESSION',prove_session_win_pn),('BATCH',prove_session_win_batch_pn)]:
                            result=solver(s,target=target,max_nodes=p['proof_nodes'],seconds=p['proof_seconds'],max_depth=p['proof_depth']);v=None
                            if result.certificate is not None:
                                assert value==(1 if target==0 else -1),'false forced win versus complete actual reference'
                                v=verify_session_certificate(s,result.certificate,max_nodes=262144,seconds=3.);assert v['verified']
                            proofs.append(dict(target=target,method=name,status=result.status,reason=result.reason,nodes=result.nodes,seconds=result.seconds,verification=v))
                    row=dict(family=family,profile=profile,setup=roots[family]['setup'],fingerprint=c.ruleset_fingerprint,target0_wdl=value,oracle_nodes=nodes,oracle_seconds=oracle_seconds,trace_sha=digest.hexdigest(),proofs=proofs)
                    rows.append(row);log.write(json.dumps(row)+'\n');log.flush();print(json.dumps(dict(family=family,profile=profile,value=value,oracle_nodes=nodes,seconds=oracle_seconds)),flush=True)
        except BaseException as ex:error=type(ex).__name__+':'+str(ex)
    write('result.json',dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED_NO_LABEL_FOR_ACTIVE_CASE',error=error,completed_cases=len(rows),expected=16,oracle_nodes=sum(x['oracle_nodes'] for x in rows),seconds=time.perf_counter()-start,false_proven_wins=0 if error is None else 'see error',new_native_or_training=0))
if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
