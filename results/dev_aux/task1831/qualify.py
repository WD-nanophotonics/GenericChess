"""Actual old-versus-all-source-rebuilt engine controls, not new game learning."""
from pathlib import Path
import json,time,hashlib,copy
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from scripts.generic_session_native_material import SessionKRNMaterialProvider,_load_transport
OUT=Path('results/dev_aux/task1831')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
    old=json.loads(Path('results/dev_aux/task1824/plan.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1822/rules.json').read_text()));roots=json.loads(Path('results/dev_aux/task1822/qualification.json').read_text())['roots']
    profiles=[(r,n) for r in (360,720,1440) for n in (64,4096)];arms=[('ORIGINAL',old['binary']),('REBUILT','.local_agent/rebuilt59-material/fairy-material-rebuilt.exe')]
    declaration=dict(question='Can all-source reconstruction reproduce actual public legal frontiers and fixed-node material queries, despite binary build-date/id differences?',roots=list(range(8)),prefix='fresh plus first public legal action',profiles=profiles,arms=[dict(name=n,sha256=sha(p)) for n,p in arms],seconds_cap=300,expected_searches=192,expected_perft=32,scope='16exposed physical states, one-thread cold profile, fixed nodes. Does not rerun training or establish full-binary equivalence; actual complete source and compiler pin supplied.')
    with (OUT/'qualification-plan.json').open('x',encoding='utf-8') as f:json.dump(declaration,f,indent=2)
    transport=_load_transport();start=time.perf_counter();allrows=[];perfts=0
    for name,binary in arms:
        plan=copy.deepcopy(old);plan['binary']=binary;plan['files'].pop(old['binary']);plan['files'][binary]=sha(binary);plan['max_go']=96;plan['seconds_cap']=300
        provider=SessionKRNMaterialProvider(plan,OUT/name.lower(),stop=lambda:transport.stop_check(Path.cwd()))
        try:
            provider.start()
            for family in declaration['roots']:
                for prefix in (False,True):
                    s=GameSession(c,roots[family]['setup'])
                    if prefix:s.submit(s.legal_actions()[0])
                    perfts+=1;provider.perft_one(s)
                    for r,n in profiles:
                        action,nodes=provider.choose(s,s.state,r,n,.25,None)
                        allrows.append(dict(arm=name,family=family,prefix=prefix,R=r,requested_nodes=n,actual_nodes=nodes,action=repr(action)))
        finally:provider.close()
    left=[x for x in allrows if x['arm']=='ORIGINAL'];right=[x for x in allrows if x['arm']=='REBUILT'];assert len(left)==len(right)==96
    mismatches=[]
    for a,b in zip(left,right):
        if {k:v for k,v in a.items() if k!='arm'}!={k:v for k,v in b.items() if k!='arm'}:mismatches.append((a,b))
    out=dict(status='PASS_EXPOSED_FUNCTIONAL_CONTROLS' if not mismatches else 'MISMATCH_PRESERVED',searches=len(allrows),perft=perfts,pairs=96,mismatches=mismatches,rows=allrows,seconds=time.perf_counter()-start,
        scope='Same action and actual reported nodes on all96cold fixed-node pairs ifPASS; metadata differs. All oldgame results remain pinned to ORIGINAL, no proof of universal equivalence or fresh-machine acceptance.')
    with (OUT/'qualification.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
    print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
if __name__=='__main__':run()
