"""Verify exported actual-Session certificates without rerunning any search."""
import argparse,gzip,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,state_sha
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.leaper_microgames import role_stop_requested

def verify(path):
    packet=json.loads(gzip.decompress(path.read_bytes()));data=packet['history_proofs']
    root=data['inputs']['roots'][3];c=compile_rule(ruleset_from_dict(root['rule']));rows=[];beg=time.perf_counter()
    candidates=[data['recovery_rows'][0]]+[r for r in data['action_rows']if r['certificate']is not None]
    for row in candidates:
        s,cert=decode_session_certificate(c,row['certificate'],max_nodes=100000)
        receipt=verify_session_certificate(s,cert,max_nodes=100000,seconds=15,cancel=role_stop_requested)
        assert receipt['verified'] and row['verification']['verified']
        if 'child'in row:assert state_sha(s.state)==row['child']
        else:assert state_sha(s.state)==root['id']
        rows.append(dict(id=state_sha(s.state),target=cert.target,rank=cert.tree.rank,receipt=receipt))
    assert len(rows)==2 and data['action_summary']['bounds']=={'S4':[-1,1],'U4':[1,1]}
    assert len(data['original_retained_rows'])==3 and all(r['status']=='UNKNOWN'for r in data['original_retained_rows'])
    return dict(status='PASS',seconds=time.perf_counter()-beg,certificates=rows,
                scope='Actual public Session root/complete-defender/terminal/rank replay only;no proof-search rerun. Failed original fourth transport remains failed;Static action stays UNKNOWN.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('packet',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=verify(a.packet);a.output.write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
