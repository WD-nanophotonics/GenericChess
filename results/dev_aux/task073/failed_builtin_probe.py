import ast,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R/'.local_agent/pinned_bebe'));B=Path(__file__).resolve().parent
from native_initial_fixture import _initial
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native import semantic as ns
from generic_chess.session.session import GameSession
from scripts.research_record import record_value
source=(R/'.local_agent/fixed_q4_tradeoff/.local_agent/native-capsule-q4-20261011/producer.py').read_bytes();cls=next(x for x in ast.parse(source).body if isinstance(x,ast.ClassDef) and x.name=='CapsuleRuntime');exec(compile(ast.Module(body=[cls],type_ignores=[]),'<fixed primary adapter class>','exec'),globals())
c,n,_=_initial();s=GameSession(c);rt=CapsuleRuntime(s.state,c,s._search_witnesses);root_snapshot=rt.full_snapshot();parent_state=record_value(rt.state);rows=[];actions=sorted(rt.legal_actions(),key=repr)
for action in actions[:2]:
 rt.push(action);child=record_value(rt.state);assert child['ply_count']==1;rt.pop();after=record_value(rt.state);snap=rt.full_snapshot();assert snap==root_snapshot and after['position']==parent_state['position'];rows.append({'action':record_value(action),'parent_ply':parent_state['ply_count'],'child_ply':child['ply_count'],'restored_Python_ply':after['ply_count'],'restored_Native_ply':snap['ply'],'Python_ply_matches_Native':after['ply_count']==snap['ply'],'position_restored':True,'Native_snapshot_restored':True})
rt.assert_balanced();out={'complete':True,'source_sha256':hashlib.sha256(source).hexdigest(),'rows':rows,'scope':'Actual frozen capsule adapter class on existing supported Western root;no product change/search/oldtrace rerun;cached parent Position restoresbutseparate Pythonply remainschild. Doesnot refute matched oldscore/work or Nativefullsnapshotrestoration.'};(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out))
