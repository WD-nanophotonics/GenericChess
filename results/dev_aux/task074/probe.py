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
source=(R/'.local_agent/fixed_q4_tradeoff/.local_agent/native-capsule-q4-20261011/producer.py').read_bytes();cls=next(x for x in ast.parse(source).body if isinstance(x,ast.ClassDef) and x.name=='CapsuleRuntime');candidate_source=ast.unparse(cls).replace('old = (self.capsule, self.cache, self.term, self.rawmap)','old = (self.capsule, self.cache, self.term, self.rawmap, self.ply_count)').replace('self.capsule, self.cache, self.term, self.rawmap = self.stack.pop()','self.capsule, self.cache, self.term, self.rawmap, self.ply_count = self.stack.pop()');assert candidate_source!=ast.unparse(cls);(B/'proposed_adapter.py').write_bytes((candidate_source+'\n').encode());exec(compile(candidate_source,'<auxiliary projectedply stack candidate>','exec'),globals())
from generic_chess.generation.generator import generate_game
from generic_chess.generation.config import GeneratorConfig
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
meta=(R/'.local_agent/fixed_q4_tradeoff/.local_agent/q4-prospective-20261011-repaired/producer.py').read_bytes();meta_cls=next(x for x in ast.parse(meta).body if isinstance(x,ast.ClassDef) and x.name=='SearchMetadataAdapter');exec(compile(ast.Module(body=[meta_cls],type_ignores=[]),'<fixed metadata adapter>','exec'),globals())
g=generate_game(GeneratorConfig(seed=1008,board_size=8,setup_preset='bilateral_random',allow_hybrid=True));base=compile_legacy_ruleset_for_semantic_execution(g.ruleset);c=SearchMetadataAdapter(ir=base.ir,_legacy_compiled=base._legacy_compiled,support=base.support);s=GameSession(c);rt=CapsuleRuntime(s.state,c,s._search_witnesses);root_snapshot=rt.full_snapshot();parent_state={'position':record_value(rt.state.position),'ply_count':rt.state.ply_count};rows=[];actions=sorted(rt.legal_actions(),key=repr)
for action in actions[:2]:
 rt.push(action);child={'position':record_value(rt.state.position),'ply_count':rt.state.ply_count};assert child['ply_count']==1;rt.pop();after={'position':record_value(rt.state.position),'ply_count':rt.state.ply_count};snap=rt.full_snapshot();assert snap==root_snapshot and after['position']==parent_state['position'];rows.append({'action':record_value(action),'parent_ply':parent_state['ply_count'],'child_ply':child['ply_count'],'restored_Python_ply':after['ply_count'],'restored_Native_ply':snap['ply'],'Python_ply_matches_Native':after['ply_count']==snap['ply'],'position_restored':True,'Native_snapshot_restored':True})
assert all(row['Python_ply_matches_Native'] for row in rows)
rt.assert_balanced();out={'complete':True,'source_sha256':hashlib.sha256(source).hexdigest(),'rows':rows,'scope':'Actual frozen capsule adapter class on existing exposed generated1008 initial root;no product change/search/oldtrace rerun;Private candidate restoresPythonply withparentNative capsule/cache. Doesnot refute matched oldscore/work or Nativefullsnapshotrestoration.'};(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out))
