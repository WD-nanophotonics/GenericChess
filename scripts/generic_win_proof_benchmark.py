"""Frozen complete-KRK answer comparison; table values never enter proof search."""
import argparse,array,hashlib,json,random,time
from dataclasses import asdict
from pathlib import Path
from scripts.generic_win_proof import prove_win,verify_certificate,PROVEN_WIN,ALREADY_TERMINAL
from scripts.generic_proof_fixtures import compile_krk,krk_state
from generic_chess.core.actions import action_to_dict


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    w=Path('results/dev_aux/task1741/wdl4.bin').read_bytes()
    rank=array.array('H');rank.frombytes(Path('results/dev_aux/task1741/rank4.bin').read_bytes())
    rng=random.Random(2026101554);rows=[]
    for d in range(15):
        ids=[i for i,v in enumerate(w) if v in (1,2) and rank[i]==d]
        rng.shuffle(ids)
        for i in ids[:8]:rows.append(dict(id=i,rank=d,wdl=w[i]))
    ids=[i for i,v in enumerate(w) if v==0];rng.shuffle(ids)
    rows += [dict(id=i,rank=None,wdl=0) for i in ids[:16]]
    plan=dict(seed=2026101554,width=4,rows=rows,colors=[0,1],nodes=[4096,65536],
              seconds_per_call=1.,max_depth=32,total_seconds=600.,
              verification_nodes=65536,verification_seconds=1.,
              purpose='Correctness and coverage, not learning or WDL gain. Labels not passed to solver.',
              wdl_sha256=sha('results/dev_aux/task1741/wdl4.bin'),
              rank_sha256=sha('results/dev_aux/task1741/rank4.bin'),
              solver_sha256=sha('scripts/generic_win_proof.py'))
    (out/'plan.json').write_text(json.dumps(plan,indent=2))
    print(dict(frozen=len(rows),calls=len(rows)*4,plan_sha256=sha(out/'plan.json')))


def run(out):
    out=Path(out);p=json.loads((out/'plan.json').read_text())
    assert sha('scripts/generic_win_proof.py')==p['solver_sha256']
    start=time.perf_counter();deadline=start+p['total_seconds'];co=compile_krk()
    failures=[];counts={};done=0
    def stop():return time.perf_counter()>=deadline
    def tree(n):return dict(rank=n.rank,terminal_kind=n.terminal_kind,
                           edges=[dict(action=action_to_dict(a),child=tree(t)) for a,t in n.edges])
    with (out/'calls.jsonl').open('x') as log:
        for row in p['rows']:
            i=row['id'];k,b,r,t=i//512,(i//32)%16,(i//2)%16,i%2
            for color in p['colors']:
                state=krk_state(co,k,b,r,t^color,color)
                for nodes in p['nodes']:
                    if stop():break
                    result=prove_win(co,state,target=color,max_nodes=nodes,seconds=p['seconds_per_call'],
                                     max_depth=p['max_depth'],cancel=stop)
                    receipt=None
                    if result.status==PROVEN_WIN:
                        receipt=verify_certificate(co,state,result.certificate,max_nodes=p['verification_nodes'],
                                                   seconds=p['verification_seconds'],cancel=stop)
                        if row['wdl']==0 or not receipt['verified']:failures.append(dict(id=i,color=color,nodes=nodes,receipt=receipt))
                    record=dict(input=row,color=color,node_cap=nodes,status=result.status,reason=result.reason,
                                nodes=result.nodes,seconds=result.seconds,rank=result.certificate.tree.rank if result.certificate else None,
                                completed_depth=result.completed_depth,pushes=result.pushes,pops=result.pops,
                                terminal_kind=result.terminal_kind,winner=result.winner,verification=receipt,
                                certificate_tree=tree(result.certificate.tree) if result.certificate else None)
                    assert result.nodes<=nodes and result.pushes==result.pops
                    log.write(json.dumps(record)+'\n');log.flush();done+=1
                    key=str((row['rank'],nodes,result.status,result.reason));counts[key]=counts.get(key,0)+1
            if stop():break
    result=dict(status='PASS' if not failures and done==len(p['rows'])*4 else 'PARTIAL_OR_FAILED',
                calls=done,planned_calls=len(p['rows'])*4,failures=failures,counts=counts,
                seconds=time.perf_counter()-start,solver_sha256=p['solver_sha256'])
    (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='counts'}))


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['freeze','run']);a.add_argument('out');q=a.parse_args()
    (freeze if q.mode=='freeze' else run)(q.out)
