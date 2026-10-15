"""Produce/consume public replay artifacts on three fixed actual sessions."""
import json,hashlib,time
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from generic_chess.core.pieces import Piece
from generic_chess.rules.schema import RuleDeclaration
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset,deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_proof_rnb_bridge import uci
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_win_proof import SessionStrategyCursor
from scripts.generic_session_certificate_json import export_session_certificate,decode_session_certificate

FOLDER=Path(__file__).parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def cases():
    old=json.loads(Path('results/dev_aux/task1808/plan.json').read_text(encoding='utf-8'))
    for label,root,declarations,prefix in [
      ('EXPOSED_ROOT0_NONE',old['roots'][0],(),None),
      ('ACTUAL_IMMEDIATE_WIN',dict(k=1,b=3,r=8),(RuleDeclaration('claim',0,require_not_in_check=False,failure_outcome='WIN'),),None),
      ('PLAYED_PREFIX_DEFENDER_LOSS',dict(k=0,b=2,r=9),(RuleDeclaration('claim',1,require_not_in_check=False,failure_outcome='LOSS'),),'b3c3')]:
        board=[None]*16
        for key,owner,kind in [('k',0,'K'),('b',1,'K'),('r',0,'R')]:board[root[key]]=Piece(owner,kind,kind)
        rs=replace(krk_ruleset(4),initial_position=tuple(tuple(board[i:i+4]) for i in range(0,16,4)),declarations=declarations,max_ply=8)
        current=GameSession(compile_ruleset_for_execution(rs))
        if prefix:current.submit(next(a for a in current.legal_actions() if uci(a)==prefix))
        yield label,rs,current

def produce():
    manifest={'purpose':'independent actual certificate replay and execution, not more price/game evidence','nodes_cap':65536,'seconds_cap':1.,'max_depth':9,'cases':[],'new_native_go':0,'training_games':0,'source_sha256':{p:sha(p) for p in ['scripts/generic_session_win_proof_pn.py','scripts/generic_session_win_proof.py','scripts/generic_session_certificate_json.py','results/dev_aux/task1817/artifacts.py']}}
    for index,(label,rs,current) in enumerate(cases()):
        result=prove_session_win_pn(current,target=0,max_nodes=manifest['nodes_cap'],seconds=manifest['seconds_cap'],max_depth=manifest['max_depth'])
        assert result.status=='PROVEN_WIN','fixed artifact qualification failed; do not increase cap'
        raw=export_session_certificate(current,result.certificate)
        rules=FOLDER/('rules_'+str(index)+'.json');artifact=FOLDER/('certificate_'+str(index)+'.json')
        with rules.open('x',encoding='utf-8') as f:f.write(serialize_ruleset(rs))
        with artifact.open('x',encoding='utf-8') as f:json.dump(raw,f,indent=2,sort_keys=True)
        manifest['cases'].append(dict(label=label,rules_file=rules.name,rules_sha256=sha(rules),certificate_file=artifact.name,certificate_sha256=sha(artifact),proof_nodes=result.nodes,proof_seconds=result.seconds,proof_rank=result.certificate.tree.rank,actual_root_prefix_actions=len(current.to_record().actions)))
    with (FOLDER/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)

def consume(destination):
    manifest=json.loads((FOLDER/'manifest.json').read_text(encoding='utf-8'));rows=[]
    def forbidden(*args,**kwargs):raise AssertionError('proof search must not run when consuming a saved witness')
    with patch('scripts.generic_session_win_proof.prove_session_win',forbidden),patch('scripts.generic_session_win_proof_pn.prove_session_win_pn',forbidden):
      for case in manifest['cases']:
        rules=FOLDER/case['rules_file'];artifact=FOLDER/case['certificate_file']
        assert sha(rules)==case['rules_sha256'] and sha(artifact)==case['certificate_sha256']
        compiled=compile_ruleset_for_execution(deserialize_ruleset(rules.read_text(encoding='utf-8')))
        t=time.perf_counter();current,cert=decode_session_certificate(compiled,json.loads(artifact.read_text(encoding='utf-8')))
        original=current.to_record();cursor=SessionStrategyCursor(current,cert,max_nodes=262144,seconds=3.)
        path=[]
        while current.result.status is SessionStatus.ONGOING:
            choice=cursor.choose(current) if current.state.position.side_to_move==cert.target else cursor.node.edges[0][0]
            rank=cursor.node.rank;cursor.commit(current,choice);assert cursor.node.rank<rank;path.append(choice.kind)
        assert current.result.winner==cert.target
        rows.append(dict(label=case['label'],verification=cursor.receipt,physical_path=path,physical_terminal=current.result.status.value,physical_declaration=current.result.declaration_outcome,winner=current.result.winner,root_record_prefix=len(original.actions),seconds=time.perf_counter()-t))
    result=dict(status='ALL_SAVED_WITNESSES_INDEPENDENTLY_VERIFIED_AND_EXECUTED',cases=rows,proof_calls_at_consumption=0,new_native_go=0,training_games=0)
    Path(destination).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':
 import sys
 produce() if sys.argv[1]=='produce' else consume(sys.argv[2])
