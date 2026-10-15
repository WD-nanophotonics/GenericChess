"""Physically execute every defense in the stored censored-endpoint witness.

Single actual writer plus cursor observation, no prover or Native calls. This
is proof-execution qualification, never relabeling original policy outcomes.
"""
from copy import copy
from pathlib import Path
import json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import SessionStrategyCursor
from scripts.generic_session_proof_player import SessionProofMaterialPlayer,SessionDecision,commit_session_decision
start=time.perf_counter();c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1822/rules.json').read_text()));data=json.loads(Path('results/dev_aux/task1827/witness-366-0-65536-5.0.json').read_text());s,cert=decode_session_certificate(c,data)
player=SessionProofMaterialPlayer(c,lambda position,target:0);player.cursor=SessionStrategyCursor(s,cert,max_nodes=262144,seconds=3.)
def forbidden(*a,**kw):raise AssertionError('new proof while executing saved witness')
player.proof_search=forbidden;leaves=[];edges=0

def walk(current,p,path):
    global edges
    if current.result.status is not SessionStatus.ONGOING:
        assert current.result.winner==cert.target and p.cursor.node.rank==0
        leaves.append(dict(extra_moves=len(path),status=current.result.status.value,winner=current.result.winner,record=json.loads(serialize_game_record(current.to_record()))));return
    node=p.cursor.node;expected_edges=node.edges
    for choice,child in expected_edges:
        branch=copy(current);branch_player=copy(p);branch_player.cursor=copy(p.cursor)
        if branch.state.position.side_to_move==cert.target:
            d=branch_player.choose(branch,max_nodes=0,seconds=3.,allow_new_proof=False)
            assert d.source=='PROOF_CONTINUATION' and d.choice==choice and d.nodes==0
        else:d=SessionDecision(choice,'COVERED_DEFENSE','no_new_proof',0,0,0,0.,'physical_execution',None,branch.to_record(),branch.state,branch.result)
        before=len(branch.to_record().actions);commit_session_decision(branch,d,[branch_player]);edges+=1
        assert len(branch.to_record().actions)==before+1 and branch_player.cursor.node==child and child.rank<node.rank
        walk(branch,branch_player,path+[choice])
walk(s,player,[])
assert len(leaves)==14 and edges==71 and max(x['extra_moves'] for x in leaves)==cert.tree.rank
out=dict(status='PASS_ALL_ACTUAL_DEFENSE_BRANCHES',edges=edges,terminal_leaves=len(leaves),min_extra_moves=min(x['extra_moves'] for x in leaves),max_extra_moves=max(x['extra_moves'] for x in leaves),rank=cert.tree.rank,all_winner=cert.target,leaves=leaves,seconds=time.perf_counter()-start,new_proof_calls=0,new_native_go=0,original_policy_rewards_unchanged=True)
with Path('results/dev_aux/task1835/result.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='leaves'}))
