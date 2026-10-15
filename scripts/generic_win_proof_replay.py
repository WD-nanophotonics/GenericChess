"""Independent PUBLIC-transition replay of saved proof trees and all defenses."""
import json,time,hashlib
from pathlib import Path
from generic_chess.core.actions import action_from_dict
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.terminal import terminal_result,TerminalStatus
from scripts.generic_proof_fixtures import compile_krk,krk_state


def run(folder):
    p=Path(folder);start=time.perf_counter();co=compile_krk();counts=dict(proofs=0,nodes=0,defender_frontiers=0,actual_winning_leaves=0)
    leafkinds={};h=hashlib.sha256();failures=[]
    for line in (p/'calls.jsonl').read_text().splitlines():
        row=json.loads(line)
        if row['status']!='PROVEN_WIN':continue
        i=row['input']['id'];k,b,r,t=i//512,(i//32)%16,(i//2)%16,i%2;color=row['color']
        state=krk_state(co,k,b,r,t^color,color)
        # Root library is independent; shortest finite proof should agree with DTM.
        assert row['rank']==row['input']['rank']
        stack=[(state,row['certificate_tree'])]
        while stack:
            s,n=stack.pop();counts['nodes']+=1
            term=terminal_result(s,co)
            if term.is_terminal:
                assert term.winner==color and n['rank']==0 and not n['edges'] and term.status.value==n['terminal_kind']
                counts['actual_winning_leaves']+=1;leafkinds[term.status.value]=leafkinds.get(term.status.value,0)+1
                h.update(repr(s).encode());continue
            assert n['rank']>0 and n['terminal_kind'] is None
            edges=[(action_from_dict(e['action']),e['child']) for e in n['edges']]
            ll=set(legal_actions(s,co));aa=[a for a,_ in edges]
            assert len(aa)==len(set(aa)) and set(aa)<=ll and edges
            if s.position.side_to_move==color:assert len(edges)==1
            else:assert set(aa)==ll;counts['defender_frontiers']+=1
            for a,child in edges:
                assert child['rank']<n['rank']
                stack.append((apply_action(s,a,co),child))
        counts['proofs']+=1
    out=dict(status='PASS_PUBLIC_ALL_DEFENSE_EXECUTION',counts=counts,leaf_kinds=leafkinds,
             seconds=time.perf_counter()-start,terminal_state_stream_sha256=h.hexdigest(),
             scope='Every branch of all saved winning certificates, public legality/transition/terminal APIs, no SearchPathRuntime verifier calls.')
    (p/'public_replay.json').write_text(json.dumps(out,indent=2));print(out)

if __name__=='__main__':
    import sys;run(sys.argv[1])
