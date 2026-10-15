"""Frozen cost curve on already-complete1808 references, no new exact oracle."""
import hashlib,json,time,dataclasses,collections
from pathlib import Path
from scripts.generic_session_proof_validation import make
from scripts.generic_session_win_proof import prove_session_win,SessionStrategyCursor
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_win_proof import CertificateVerificationError
from generic_chess.session.result import SessionStatus

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def freeze():
    source=Path('results/dev_aux/task1808/calls.jsonl');old=json.loads(Path('results/dev_aux/task1808/plan.json').read_text(encoding='utf-8'))
    cases=[json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
    assert len(cases)==18
    modules=['scripts/generic_session_win_proof.py','scripts/generic_session_win_proof_pn.py','scripts/generic_session_proof_validation.py','results/dev_aux/task1816/compare.py']
    plan=dict(cases=[{k:r[k] for k in ['root','profile','target','exact_for_player0']} for r in cases],roots=old['roots'],max_ply=old['max_ply'],max_depth=9,proof_nodes=65536,seconds=[.1,1.,5.],repetitions=2,algorithms=['ANDOR','SESSION_PN'],global_seconds=600,verification_nodes=262144,verification_seconds=3.,expected_seconds=180,source_sha256={p:sha(p) for p in modules},old_call_file=str(source),old_call_sha256=sha(source),new_native_go=0,training_games=0,reference_nodes_generated=0,scope='exposed completed9root/profile references only, method/cost engineering comparison, not new independent holdout or price learning; original1808partial/cap untouched',decision='Would same public-session certificate PN change useful proof coverage/cost enough to retain it as an optional future assay, or defer it? all18case targets, budgets and2counterbalanced repeats fixed; no extension on result')
    Path(__file__).with_name('plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')

def run():
    folder=Path(__file__).parent;p=json.loads((folder/'plan.json').read_text(encoding='utf-8'))
    assert all(sha(path)==value for path,value in p['source_sha256'].items())
    started=time.perf_counter();deadline=started+p['global_seconds'];rows=[];active={};error=None
    def cancel():return time.perf_counter()>=deadline
    # Existing own stop function checks effective user resume/stop records.
    import importlib.util
    spec=importlib.util.spec_from_file_location('stop58','results/dev_aux/task166/run.py');stop=importlib.util.module_from_spec(spec);spec.loader.exec_module(stop)
    with (folder/'calls.jsonl').open('x',encoding='utf-8') as log:
      try:
        for repeat in range(p['repetitions']):
          for case_index,case in enumerate(p['cases']):
            for seconds in (p['seconds'] if (repeat+case_index)%2==0 else list(reversed(p['seconds']))):
              names=p['algorithms'] if (repeat+case_index)%2==0 else list(reversed(p['algorithms']))
              for name in names:
                stop.stop()
                if cancel():raise RuntimeError('frozen_cost_curve_wallcap')
                current=make(p['roots'][case['root']],case['profile'],p['max_ply']);before=current.to_record()
                active=dict(repeat=repeat,case_index=case_index,**case,seconds_budget=seconds,algorithm=name)
                solver=prove_session_win if name=='ANDOR' else prove_session_win_pn
                result=solver(current,target=case['target'],max_nodes=p['proof_nodes'],seconds=min(seconds,deadline-time.perf_counter()),max_depth=p['max_depth'],cancel=cancel)
                assert current.to_record()==before
                record={**active,**{k:v for k,v in dataclasses.asdict(result).items() if k!='certificate'},'verification':None,'physical_path':[]}
                if result.status=='PROVEN_WIN':
                    expected=1 if case['target']==0 else -1
                    assert case['exact_for_player0']==expected,'FALSE_PROVEN_WIN_AGAINST_COMPLETE_REFERENCE'
                    try:
                        cursor=SessionStrategyCursor(current,result.certificate,max_nodes=p['verification_nodes'],seconds=min(p['verification_seconds'],max(0.,deadline-time.perf_counter())),cancel=cancel)
                    except CertificateVerificationError as e:record['verification']=e.receipt
                    else:
                        record['verification']=cursor.receipt
                        while current.result.status is SessionStatus.ONGOING:
                            stop.stop()
                            if cancel():raise RuntimeError('frozen_cost_curve_wallcap')
                            choice=cursor.choose(current) if current.state.position.side_to_move==case['target'] else cursor.node.edges[0][0]
                            rank=cursor.node.rank;cursor.commit(current,choice)
                            assert cursor.node.rank<rank
                            record['physical_path'].append(choice.kind)
                        assert current.result.winner==case['target']
                rows.append(record);log.write(json.dumps(record)+'\n');log.flush();active={}
      except Exception as e:error=type(e).__name__+':'+str(e)
    summary=[]
    for seconds in p['seconds']:
      for name in p['algorithms']:
        group=[r for r in rows if r['algorithm']==name and r['seconds_budget']==seconds]
        summary.append(dict(algorithm=name,seconds_budget=seconds,calls=len(group),proved=sum(r['status']=='PROVEN_WIN' for r in group),independently_verified=sum(bool(r['verification'] and r['verification']['verified']) for r in group),physical_wins=sum(bool(r['physical_path']) for r in group),proof_seconds=sum(r['seconds'] for r in group),verification_seconds=sum(r['verification']['seconds'] if r['verification'] else 0 for r in group),nodes=sum(r['nodes'] for r in group),reasons=dict(collections.Counter(r['reason'] for r in group))))
    output=dict(status='PARTIAL' if error else 'COMPLETE',error=error,active=active,planned_calls=216,complete_calls=len(rows),elapsed_seconds=time.perf_counter()-started,summary=summary,new_native_go=0,training_games=0,new_reference_nodes=0)
    (folder/'result.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(output,indent=2),flush=True)
if __name__=='__main__':
 import sys
 freeze() if sys.argv[1]=='freeze' else run()
