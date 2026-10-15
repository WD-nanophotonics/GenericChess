"""Actual existing quarter-budget planning control on exposed18targets."""
import json,time,hashlib,dataclasses,collections
from pathlib import Path
from scripts.generic_session_proof_validation import make
from scripts.generic_session_win_proof import prove_session_win,SessionStrategyCursor
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_win_proof import CertificateVerificationError
from generic_chess.session.result import SessionStatus

FOLDER=Path(__file__).parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def freeze():
    old=json.loads(Path('results/dev_aux/task1816/plan.json').read_text(encoding='utf-8'))
    assay_path=Path('results/dev_aux/task1804/plan.json');assay=json.loads(assay_path.read_text(encoding='utf-8'))
    assert assay['candidate_nodes']==4096 and assay['opponents'][0]['nodes']==64 and assay['step_seconds']==.25
    settings=[dict(id='CANDIDATE_QUARTER',nodes=4096//4,seconds=.25/4),dict(id='UNIT64_QUARTER',nodes=64//4,seconds=.25/4)]
    sources=['scripts/generic_session_win_proof.py','scripts/generic_session_win_proof_pn.py','results/dev_aux/task1819/allocation.py']
    plan=dict(cases=old['cases'],roots=old['roots'],max_ply=old['max_ply'],max_depth=old['max_depth'],settings=settings,repetitions=2,algorithms=['ANDOR','SESSION_PN'],global_seconds=120,expected_seconds=10,planned_calls=144,source_sha256={p:sha(p) for p in sources},allocation_source=str(assay_path),allocation_source_sha256=sha(assay_path),scope='prospective SAME nominal proof+verification quarter allocations, each algorithm visit units still different; no Session policy integrated or new game/learning claim',decision='Does the exposed1s PN coverage improvement actually survive the existing.25s-step proof/verification allocations? no tuning of allocations, roots, prices or old caps')
    with (FOLDER/'plan.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)

def run():
    p=json.loads((FOLDER/'plan.json').read_text(encoding='utf-8'));assert all(sha(k)==v for k,v in p['source_sha256'].items())
    beg=time.perf_counter();deadline=beg+p['global_seconds'];rows=[];active={};error=None
    import importlib.util
    spec=importlib.util.spec_from_file_location('stops58allocation','results/dev_aux/task166/run.py');stop=importlib.util.module_from_spec(spec);spec.loader.exec_module(stop)
    with (FOLDER/'calls.jsonl').open('x',encoding='utf-8') as log:
      try:
       for repeat in range(p['repetitions']):
        for index,case in enumerate(p['cases']):
         for setting in (p['settings'] if (repeat+index)%2==0 else list(reversed(p['settings']))):
          for name in (p['algorithms'] if (repeat+index)%2==0 else list(reversed(p['algorithms']))):
            stop.stop();assert time.perf_counter()<deadline,'frozen_allocation_wallcap'
            active=dict(repeat=repeat,**case,allocation=setting['id'],algorithm=name)
            current=make(p['roots'][case['root']],case['profile'],p['max_ply'])
            solver=prove_session_win if name=='ANDOR' else prove_session_win_pn
            result=solver(current,target=case['target'],max_nodes=setting['nodes'],seconds=setting['seconds'],max_depth=p['max_depth'],cancel=lambda:time.perf_counter()>=deadline)
            row={**active,'status':result.status,'reason':result.reason,'nodes':result.nodes,'seconds':result.seconds,'verification':None,'physical_moves':0}
            if result.status=='PROVEN_WIN':
                assert case['exact_for_player0']==(1 if case['target']==0 else -1)
                try:cursor=SessionStrategyCursor(current,result.certificate,max_nodes=setting['nodes'],seconds=setting['seconds'])
                except CertificateVerificationError as e:row['verification']=e.receipt
                else:
                    row['verification']=cursor.receipt
                    while current.result.status is SessionStatus.ONGOING:
                        choice=cursor.choose(current) if current.state.position.side_to_move==case['target'] else cursor.node.edges[0][0]
                        cursor.commit(current,choice);row['physical_moves']+=1
                    assert current.result.winner==case['target']
            rows.append(row);log.write(json.dumps(row)+'\n');log.flush();active={}
      except Exception as e:error=type(e).__name__+':'+str(e)
    summary=[]
    for setting in p['settings']:
     for name in p['algorithms']:
      rr=[r for r in rows if r['allocation']==setting['id'] and r['algorithm']==name]
      summary.append(dict(allocation=setting['id'],algorithm=name,calls=len(rr),proved=sum(r['status']=='PROVEN_WIN' for r in rr),verified=sum(bool(r['verification'] and r['verification']['verified']) for r in rr),physical_wins=sum(r['physical_moves']>0 for r in rr),proof_seconds=sum(r['seconds'] for r in rr),verification_seconds=sum(r['verification']['seconds'] if r['verification'] else 0 for r in rr),reasons=dict(collections.Counter(r['reason'] for r in rr))))
    output=dict(status='PARTIAL' if error else 'COMPLETE',error=error,active=active,planned_calls=p['planned_calls'],complete_calls=len(rows),elapsed_seconds=time.perf_counter()-beg,summary=summary,new_native_go=0,training_games=0,new_exact_reference_nodes=0)
    (FOLDER/'result.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(output,indent=2))
if __name__=='__main__':
 import sys
 freeze() if sys.argv[1]=='freeze' else run()
