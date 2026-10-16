"""One prospectively frozen 192-query qualification. Never rerun a started cap."""
from pathlib import Path
from copy import copy
from collections import Counter
from dataclasses import asdict
import json, hashlib, time, sys
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2088.provider import CompositeProvider
from results.dev_aux.task2048.portable_certificate import encode
OUT=Path('results/dev_aux/task2088')
def dump(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2),encoding='utf-8')
def main():
    if (OUT/'started.json').exists():raise RuntimeError('Original2088 cap already started: restart forbidden')
    # Pin implementation/input tree BEFORE any teacher access or proof query.
    files=set(Path('generic_chess').rglob('*.py'))|set(Path('scripts').glob('*.py'))
    for task in [2048,2056,2068,2072,2073,2074,2086,2087,2088]:
        files.update(x for x in Path(f'results/dev_aux/task{task}').glob('*') if x.suffix in('.py','.json','.jsonl'))
    pins={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files) if f.name not in('source-pin.json','started.json')}
    dump('source-pin.json',pins)
    begin=time.perf_counter();deadline=begin+600
    dump('started.json',dict(started_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),one_clock=True,cap_seconds=600,expected_seconds=180,restart_forbidden=True,expected_queries=192))
    cancelled=lambda:time.perf_counter()>=deadline
    ts=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2073','results/dev_aux/task2074');load=time.perf_counter()-ts
    provider=CompositeProvider(teacher);roots=json.loads(Path('results/dev_aux/task2087/inputs.json').read_text(encoding='utf-8'))['roots'];rows=[];certs=[];stopped=False
    with (OUT/'queries.jsonl').open('x',encoding='utf-8') as journal:
        for root in roots:
            if cancelled():stopped=True;break
            c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text(encoding='utf-8')));s=GameSession(c);snapshots=[copy(s)]
            for _ in range(2):
                if s.result.status is SessionStatus.ONGOING:s.submit(s.legal_actions()[0])
            snapshots.append(s)
            for prefix,current in enumerate(snapshots):
                for target in (0,1):
                    order=['reference','composite'] if (root['family']+prefix+target)%2==0 else ['composite','reference']
                    for name in order:
                        if cancelled():stopped=True;break
                        before=current.to_record();started=time.perf_counter()
                        row=dict(family=root['family'],composition=root['composition'],snapshot=prefix,actual_ply=current.state.ply_count,target=target,provider=name,root_record=json.loads(serialize_game_record(before)),actual_terminal=current.result.status.value)
                        if current.result.status is not SessionStatus.ONGOING:
                            row.update(status='ALREADY_TERMINAL',reason='actual_terminal_retained',nodes=0,seconds=0.,verified=None,winner=current.result.winner)
                        else:
                            f=prove_session_win_batch_pn if name=='reference' else provider
                            r=f(current,target=target,max_nodes=1024,seconds=min(1.5,max(0.,deadline-time.perf_counter())),max_depth=64,cancel=cancelled)
                            row.update(status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds,completed_depth=r.completed_depth,trace=[] if name=='reference' else list(provider.trace),verified=None)
                            if r.certificate is not None:
                                receipt=verify_session_certificate(current,r.certificate,max_nodes=16384,seconds=min(.5,max(0.,deadline-time.perf_counter())),cancel=cancelled);row['verified']=receipt
                                certs.append(dict(query=len(rows),rules=root['rules'],target=target,root_record=row['root_record'],tree=encode(r.certificate.tree)))
                                if not receipt['verified']:row['qualification_failure']='positive_certificate_not_verified'
                        row['total_seconds']=time.perf_counter()-started;assert current.to_record()==before
                        rows.append(row);journal.write(json.dumps(row)+'\n');journal.flush()
                    if stopped:break
                if stopped:break
            if stopped:break
    dump('certificates.json',certs)
    # Report changes including UNKNOWN. No draw reward is inferred.
    by={name:dict(status=dict(Counter(r['status']for r in rows if r['provider']==name)),reasons=dict(Counter(r['reason']for r in rows if r['provider']==name)),nodes=sum(r['nodes']for r in rows if r['provider']==name),query_seconds=sum(r['seconds']for r in rows if r['provider']==name),total_seconds=sum(r['total_seconds']for r in rows if r['provider']==name)) for name in('reference','composite')}
    unchanged=all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in pins.items())
    dump('result.json',dict(status='GLOBAL_CAP'if stopped else'COMPLETE_192_QUERY_QUALIFICATION',queries=len(rows),expected=192,unrun=192-len(rows),teacher_load_seconds=load,seconds=time.perf_counter()-begin,source_unchanged=unchanged,providers=by,certificates=len(certs),verified=sum(bool(r.get('verified',{}).get('verified')) for r in rows if r.get('verified')),qualification_failures=[i for i,r in enumerate(rows)if'qualification_failure'in r],scope='Freshstructuralqualification only. Exactteacherprepaidbuild/audit costs separatelyreported; noactualplayerWDLclaim orfullgenerateddomain support. Terminalprefixesretained.'))
    print((OUT/'result.json').read_text(encoding='utf-8'))
if __name__=='__main__':main()
