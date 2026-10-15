"""Frozen equal-wall/visit cost diagnostic; no current-policy replacement."""
from pathlib import Path
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.generic_session_win_proof_check_first import prove_session_win_check_first
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
OUT=Path('results/dev_aux/task1843')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def freeze():
    prior=json.loads(Path('results/dev_aux/task1827/plan.json').read_text());files=['scripts/generic_session_win_proof_batch_pn.py','scripts/generic_session_win_proof_check_first.py',__file__]
    plan=dict(question='Does price-independent rule-history checking-move ordering WITHOUT pruning quiet moves reduce visited work on four EXPOSED saved full-history censored endpoints? Different valid witnesses allowed, actual Session verification mandatory; no old outcome or cap change.',cases=prior['cases'],budgets=prior['budgets'],targets=prior['targets'],rules=prior['rules'],max_depth=64,seconds_cap=180,source_sha={str(p):sha(p) for p in files},schedule='case,budget,target; reversemethod order on oddcase+target+budget to reduce ordinary load bias; one paired run, exposed diagnostic not fresh scientific validation.',expected_calls=48)
    with (OUT/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
def run():
    p=json.loads((OUT/'plan.json').read_text());assert all(sha(f)==h for f,h in p['source_sha'].items());c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));rows=[];start=time.perf_counter()
    with (OUT/'calls.jsonl').open('x',encoding='utf-8') as log:
        for ci,case in enumerate(p['cases']):
            for bi,budget in enumerate(p['budgets']):
                for target in p['targets']:
                    methods=[('CHECK_FIRST',prove_session_win_check_first),('BATCH',prove_session_win_batch_pn)]
                    if (ci+bi+target)%2:methods.reverse()
                    pair=[]
                    for method,solver in methods:
                        assert time.perf_counter()-start<p['seconds_cap']
                        s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])))
                        r=solver(s,target=target,max_nodes=budget['nodes'],seconds=budget['seconds'],max_depth=64)
                        v=verify_session_certificate(s,r.certificate,max_nodes=262144,seconds=3.) if r.certificate is not None else None
                        if v is not None:assert v['verified']
                        row=dict(slot=case['slot'],target=target,budget=budget,method=method,status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,transitions=r.transitions,frontiers=r.frontiers,eager_board_successors=getattr(r,'eager_board_successors',None),verification=v,rank=r.certificate.tree.rank if r.certificate is not None else None,certificate_repr_sha=hashlib.sha256(repr(r.certificate).encode()).hexdigest() if r.certificate is not None else None)
                        rows.append(row);pair.append(row);log.write(json.dumps(row)+'\n');log.flush()
                    if all(x['status']=='PROVEN_WIN' for x in pair):pass # Different ordering can produce different valid certificates and work; each independently verified above.
                    print(json.dumps([dict(method=x['method'],slot=x['slot'],target=x['target'],budget=x['budget'],status=x['status'],nodes=x['nodes'],seconds=x['seconds']) for x in pair]),flush=True)
    out=dict(status='COMPLETE',calls=len(rows),seconds=time.perf_counter()-start,groups=[dict(method=m,budget=b,calls=sum(x['method']==m and x['budget']==b for x in rows),proven=sum(x['method']==m and x['budget']==b and x['status']=='PROVEN_WIN' for x in rows),seconds=sum(x['seconds'] for x in rows if x['method']==m and x['budget']==b)) for m in ('CHECK_FIRST','BATCH') for b in p['budgets']],no_new_native_or_games=True,current_policy_unchanged=True)
    with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
if __name__=='__main__':
    import sys
    {'freeze':freeze,'run':run}[sys.argv[1]]()
